"""Concentración diaria por planta, clase B, RM. Usa archivos públicos PRT."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import unquote, urlparse
import zipfile

import openpyxl
from openpyxl.formatting.rule import ColorScaleRule
import pandas as pd
import requests
import truststore

from prt import ROOT, RAW, clean_date, normalize, rows_from_zip

DB = ROOT / 'datos/rm_2025.sqlite'
OUT = ROOT / 'resultados/rm_2025'
SCHEMA = '''
PRAGMA foreign_keys=ON;
DROP VIEW IF EXISTS concentracion_rm;
DROP VIEW IF EXISTS concentracion_planta;
DROP VIEW IF EXISTS diario_rm;
CREATE TABLE IF NOT EXISTS plantas (
 codigo TEXT PRIMARY KEY, region INTEGER, comuna TEXT, concesionario TEXT,
 sistema TEXT, observaciones_catalogo TEXT
);
CREATE TABLE IF NOT EXISTS archivos (
 periodo TEXT PRIMARY KEY, url TEXT NOT NULL, sha256 TEXT NOT NULL,
 bytes INTEGER NOT NULL, importado_utc TEXT NOT NULL,
 filas_nacionales INTEGER NOT NULL, filas_rm INTEGER NOT NULL,
 duplicados_exactos_rm INTEGER NOT NULL, registros_distintos_rm INTEGER NOT NULL,
 fechas_invalidas_rm INTEGER NOT NULL, plantas_con_registros INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS flujo_diario (
 planta TEXT NOT NULL REFERENCES plantas(codigo), fecha TEXT NOT NULL,
 periodo TEXT NOT NULL REFERENCES archivos(periodo), revisiones INTEGER NOT NULL,
 PRIMARY KEY(planta,fecha), CHECK (substr(fecha,1,7)=periodo), CHECK(revisiones>0)
);
CREATE TABLE IF NOT EXISTS codigos_sin_catalogo (
 periodo TEXT NOT NULL, codigo TEXT NOT NULL, filas INTEGER NOT NULL,
 PRIMARY KEY(periodo,codigo)
);
CREATE VIEW IF NOT EXISTS diario_rm AS
 SELECT fecha,periodo,sum(revisiones) AS revisiones,count(*) AS plantas_con_registros
 FROM flujo_diario WHERE planta LIKE 'B-%' OR planta LIKE 'AB%' GROUP BY fecha,periodo;
CREATE VIEW IF NOT EXISTS concentracion_planta AS
 SELECT d.*, cast(substr(fecha,9,2) AS INTEGER) AS dia_mes,
 sum(revisiones) OVER (PARTITION BY planta,periodo) AS total_mes,
 100.0*revisiones/sum(revisiones) OVER (PARTITION BY planta,periodo) AS porcentaje_mes,
 dense_rank() OVER (PARTITION BY planta,periodo ORDER BY revisiones DESC) AS ranking
 FROM flujo_diario d WHERE planta LIKE 'B-%' OR planta LIKE 'AB%';
CREATE VIEW IF NOT EXISTS concentracion_rm AS
 SELECT d.*,cast(substr(fecha,9,2) AS INTEGER) AS dia_mes,
 sum(revisiones) OVER (PARTITION BY periodo) AS total_mes,
 100.0*revisiones/sum(revisiones) OVER (PARTITION BY periodo) AS porcentaje_mes,
 dense_rank() OVER (PARTITION BY periodo ORDER BY revisiones DESC) AS ranking
 FROM diario_rm d;
'''


def connect():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript(SCHEMA)
    return c


def catalog(c):
    book = openpyxl.load_workbook(RAW/'Codigos_Plantas.xlsx', read_only=True, data_only=True)
    all_codes = {}
    for row in book.worksheets[0].iter_rows(values_only=True):
        if len(row) >= 7 and isinstance(row[2], (int,float)):
            code = str(row[1]).strip()
            all_codes[normalize(code)] = (code, int(row[2]))
            if int(row[2]) == 13:
                c.execute('''INSERT INTO plantas VALUES (?,?,?,?,?,?) ON CONFLICT(codigo) DO UPDATE SET
                          region=excluded.region,comuna=excluded.comuna,concesionario=excluded.concesionario,
                          sistema=excluded.sistema,observaciones_catalogo=excluded.observaciones_catalogo''',
                          (code,13,row[3],row[4],row[5],row[6]))
    book.close()
    c.commit()
    return all_codes


def fetch(item):
    """Reanuda solo con Content-Range correcto; verifica CRC de ambos ZIP."""
    url = item['url']
    path = RAW/unquote(urlparse(url).path.rsplit('/',1)[-1])
    part = path.with_suffix('.zip.part')
    if path.exists():
        return path
    last_error = None
    for attempt in range(1,5):
        try:
            with requests.Session() as session:
                head = session.head(url,timeout=(30,90))
                head.raise_for_status()
                total = int(head.headers['Content-Length'])
                offset = part.stat().st_size if part.exists() else 0
                if offset > total:
                    raise ValueError(f'Parcial mayor que el origen: {part}')
                if offset < total:
                    headers = {'Range':f'bytes={offset}-','Accept-Encoding':'identity'} if offset else {'Accept-Encoding':'identity'}
                    if offset and head.headers.get('ETag'):
                        headers['If-Range'] = head.headers['ETag']
                    with session.get(url,headers=headers,stream=True,timeout=(45,120)) as response:
                        response.raise_for_status()
                        if offset and response.status_code != 206:
                            raise ValueError(f'El servidor no reanudó {item["periodo"]}: {response.status_code}')
                        if offset and not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                            raise ValueError('Content-Range no coincide con la posición local')
                        print(f'{item["periodo"]}: descarga {offset/1e6:.1f}/{total/1e6:.1f} MB (intento {attempt})',flush=True)
                        started = last_log = time.monotonic()
                        with part.open('ab' if offset else 'wb') as out:
                            for chunk in response.iter_content(256*1024):
                                out.write(chunk)
                                if time.monotonic()-last_log > 30:
                                    print(f'{item["periodo"]}: {out.tell()/1e6:.1f}/{total/1e6:.1f} MB',flush=True)
                                    last_log = time.monotonic()
                                if time.monotonic()-started > 1800:
                                    raise TimeoutError('Reanudación programada tras 30 minutos')
                if part.stat().st_size != total:
                    raise ValueError('Tamaño descargado no coincide con Content-Length')
                with zipfile.ZipFile(part) as archive:
                    bad = archive.testzip()
                    if bad:
                        raise ValueError(f'CRC inválido: {bad}')
                part.replace(path)
                print(f'{item["periodo"]}: ZIP completo, CRC verificado',flush=True)
                return path
        except Exception as exc:
            last_error = exc
            print(f'{item["periodo"]}: intento {attempt} falló: {exc}',flush=True)
            if attempt < 4:
                time.sleep(3)
    raise RuntimeError(f'{item["periodo"]}: no descargado: {last_error}')


def ingest(c,item,path,all_codes):
    period = item['periodo']
    if c.execute('SELECT 1 FROM archivos WHERE periodo=?',(period,)).fetchone():
        return
    targets = {normalize(row[0]): row[0] for row in c.execute('SELECT codigo FROM plantas')}
    seen = set()
    daily = Counter()
    unknown = Counter()
    national = selected = duplicates = invalid = 0
    start = last_log = time.monotonic()
    for row in rows_from_zip(path,set(targets)):
        national += 1
        code = normalize(row.get('CODPRT'))
        if code not in all_codes:
            unknown[str(row.get('CODPRT'))] += 1
        if code not in targets:
            continue
        selected += 1
        try:
            day = clean_date(row.get('FECREVISION'))
            if day[:7] != period:
                raise ValueError('Fecha fuera de período')
        except (ValueError,TypeError,OverflowError):
            invalid += 1
            continue
        key = hashlib.sha256(json.dumps(row,sort_keys=True,default=str).encode()).digest()
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
            daily[(targets[code],day)] += 1
        if time.monotonic()-last_log > 30:
            print(f'{period}: {national:,} filas nacionales leídas, {selected:,} RM',flush=True)
            last_log = time.monotonic()
    if not selected or invalid:
        raise ValueError(f'{period}: no se importa: seleccionadas={selected}, fechas inválidas={invalid}')
    with path.open('rb') as handle:
        sha = hashlib.file_digest(handle,'sha256').hexdigest()
    with c:
        c.execute('INSERT INTO archivos VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                  (period,item['url'],sha,path.stat().st_size,datetime.now(timezone.utc).isoformat(),
                   national,selected,duplicates,len(seen),invalid,len({p for p,d in daily})))
        c.executemany('INSERT INTO flujo_diario VALUES (?,?,?,?)',
                      [(p,d,period,n) for (p,d),n in daily.items()])
        c.executemany('INSERT INTO codigos_sin_catalogo VALUES (?,?,?)',
                      [(period,code,n) for code,n in unknown.items()])
    print(f'{period}: IMPORTADO {sum(daily.values()):,} registros distintos, '
          f'{len({p for p,d in daily})} plantas, {duplicates} duplicados exactos, '
          f'{time.monotonic()-start:.0f}s',flush=True)


def export(c):
    OUT.mkdir(parents=True,exist_ok=True)
    queries = {
        'peaks_rm': 'SELECT * FROM concentracion_rm WHERE ranking=1 ORDER BY periodo,fecha',
        'peaks_por_planta': '''SELECT d.*,p.comuna,p.concesionario FROM concentracion_planta d
                              JOIN plantas p ON p.codigo=d.planta WHERE ranking=1 ORDER BY planta,periodo,fecha''',
        'diario_rm':'SELECT * FROM concentracion_rm ORDER BY fecha',
        'diario_por_planta':'''SELECT d.*,p.comuna,p.concesionario FROM concentracion_planta d
                             JOIN plantas p ON p.codigo=d.planta ORDER BY planta,fecha''',
        'cobertura_archivos':'''SELECT a.*,
          (SELECT count(DISTINCT planta) FROM flujo_diario d WHERE d.periodo=a.periodo
             AND (d.planta LIKE 'B-%' OR d.planta LIKE 'AB%')) AS plantas_clase_b,
          (SELECT sum(revisiones) FROM flujo_diario d WHERE d.periodo=a.periodo
             AND (d.planta LIKE 'B-%' OR d.planta LIKE 'AB%')) AS registros_clase_b,
          coalesce((SELECT sum(revisiones) FROM flujo_diario d WHERE d.periodo=a.periodo
             AND NOT (d.planta LIKE 'B-%' OR d.planta LIKE 'AB%')),0) AS registros_otras_clases
          FROM archivos a ORDER BY periodo''',
        'cobertura_plantas':'''SELECT p.*,count(DISTINCT d.periodo) AS meses_con_registros,
          min(d.fecha) AS primera_fecha,max(d.fecha) AS ultima_fecha,coalesce(sum(d.revisiones),0) AS revisiones
          FROM plantas p LEFT JOIN flujo_diario d ON d.planta=p.codigo GROUP BY p.codigo ORDER BY p.codigo''',
        'sin_catalogo':'SELECT * FROM codigos_sin_catalogo ORDER BY periodo,codigo',
        'otras_clases_en_rb':'''SELECT d.*,p.comuna,p.concesionario FROM flujo_diario d
          JOIN plantas p ON p.codigo=d.planta WHERE NOT (d.planta LIKE 'B-%' OR d.planta LIKE 'AB%')
          ORDER BY d.fecha,d.planta''',
    }
    frames = {name:pd.read_sql_query(q,c) for name,q in queries.items()}
    plants = frames['cobertura_plantas']
    plants['incluida_en_analisis'] = plants.codigo.str.startswith(('B-','AB'))
    weekdays = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']
    for frame in frames.values():
        if 'fecha' in frame:
            frame['dia_semana'] = pd.to_datetime(frame.fecha).dt.dayofweek.map(dict(enumerate(weekdays)))
    days = frames['diario_rm']
    if not days.empty:
        grid = pd.DataFrame({'fecha':pd.date_range('2025-01-01','2025-12-31').strftime('%Y-%m-%d')})
        grid['periodo'] = grid.fecha.str[:7]
        grid = grid.merge(days.drop(columns='periodo'),on='fecha',how='left')
        covered = set(frames['cobertura_archivos'].periodo)
        grid['estado'] = grid.apply(lambda r:'mes pendiente' if r.periodo not in covered else
                                    ('sin registros publicados' if pd.isna(r.revisiones) else 'con registros'),axis=1)
        frames['calendario_rm'] = grid
        matrix = days.pivot(index='periodo',columns='dia_mes',values='revisiones').reindex(columns=range(1,32))
        frames['matriz_dias_rm'] = matrix.reset_index()
        frames['matriz_porcentaje_rm'] = days.pivot(index='periodo',columns='dia_mes',values='porcentaje_mes').reindex(columns=range(1,32)).reset_index()
    methods = [
        ('Alcance','2025, archivos SGPRT RB, plantas de región 13 según catálogo oficial; A1/A2 excluidas.'),
        ('Códigos clase A en RB','Registros con código de planta A se conservan en la base y la hoja otras_clases_en_rb, pero se excluyen del análisis de plantas B/AB.'),
        ('Unidad','Registros publicados distintos tras eliminar filas completamente idénticas. Incluye reingresos.'),
        ('Peak','Mayor cantidad de registros en una fecha del mes. Se conservan todos los empates.'),
        ('Porcentaje','Registros de la fecha / registros totales del mismo mes y ámbito (planta o RM).'),
        ('Ausencias','Sin registros no equivale a cerrado o a demanda cero. Mes pendiente nunca se completa con ceros.'),
        ('Cobertura','Un mes importado no demuestra que el origen incluya el 100% de las atenciones.'),
        ('Catálogo','Catálogo descargado el 02-11-2026: observaciones pueden describir cierres posteriores a 2025.'),
        ('Privacidad','La base almacena conteos por planta y fecha; no guarda patentes ni identificadores vehiculares.'),
        ('Fuente','https://www.prt.cl/Descargas/index.html'),
    ]
    frames['metodologia'] = pd.DataFrame(methods,columns=['tema','descripcion'])
    for name,frame in frames.items():
        frame.to_csv(OUT/f'{name}.csv',index=False,encoding='utf-8-sig')
    temporary = OUT/f'concentracion_rm_2025.tmp.{os.getpid()}.xlsx'
    with pd.ExcelWriter(temporary,engine='openpyxl') as writer:
        for name,frame in frames.items():
            frame.to_excel(writer,sheet_name=name,index=False)
            sheet = writer.sheets[name]
            sheet.freeze_panes = 'A2'
            sheet.auto_filter.ref = sheet.dimensions
            for col in sheet.columns:
                letter = col[0].column_letter
                sheet.column_dimensions[letter].width = min(60,max(13,len(str(col[0].value))+2))
                if col[0].value == 'porcentaje_mes':
                    for cell in col[1:]:
                        cell.number_format = '0.00"%"'
            if name in ('matriz_dias_rm','matriz_porcentaje_rm') and sheet.max_row > 1:
                sheet.conditional_formatting.add(f'B2:AF{sheet.max_row}',
                    ColorScaleRule(start_type='min',start_color='FFFFFF',
                                   end_type='max',end_color='007F86'))
                if name == 'matriz_porcentaje_rm':
                    for row in sheet.iter_rows(min_row=2,min_col=2,max_col=32):
                        for cell in row:
                            cell.number_format = '0.00"%"'
    temporary.replace(OUT/'concentracion_rm_2025.xlsx')
    print(f'Exportado: {len(frames["cobertura_archivos"])}/12 meses, '
          f'{len(plants.query("revisiones > 0 and incluida_en_analisis"))} plantas B/AB observadas',flush=True)
    coverage = frames['cobertura_archivos']
    observed = plants.query('revisiones > 0 and incluida_en_analisis')
    report = ['# Concentración de revisiones: Región Metropolitana, clase B, 2025','',
              f'Cobertura importada: **{len(coverage)}/12 meses**. Plantas con registros: **{len(observed)}**.',
              '', 'Fuente: [descargas oficiales PRT](https://www.prt.cl/Descargas/index.html).', '',
              '## Día de mayor volumen de cada mes, total RM','',
              '| Mes | Fecha | Día de la semana | Revisiones | Total mensual | % del mes |',
              '|---|---|---|---:|---:|---:|']
    for row in frames['peaks_rm'].itertuples():
        report.append(f'| {row.periodo} | {row.fecha} | {row.dia_semana} | {row.revisiones:,} | {row.total_mes:,} | {row.porcentaje_mes:.2f}% |')
    report += ['', 'Todos los empates se conservan. Los resultados por planta están en la hoja '
               '`peaks_por_planta` del [Excel](concentracion_rm_2025.xlsx) y en [CSV](peaks_por_planta.csv).', '',
               'Las hojas `matriz_dias_rm` y `matriz_porcentaje_rm` muestran los días 1–31 de cada mes '
               'con una escala de color, en cantidad de revisiones y porcentaje del mes, respectivamente. '
               '`diario_por_planta` contiene todos los conteos, no solo el peak.', '',
               '## Interpretación y límites','',
               '- Se cuentan registros publicados distintos después de eliminar filas completamente idénticas. '
               'Se incluyen reingresos; no son reservas, vehículos únicos ni tiempos de espera.',
               '- Un día sin registros no demuestra que la planta estuviera cerrada. '
               'Los meses pendientes no se reemplazan por ceros.',
               '- Se incluyen exclusivamente los archivos SGPRT RB. No se incluyen las categorías A1/A2.',
               '- Si el archivo RB contiene un código de planta clase A, se conserva en la hoja '
               '`otras_clases_en_rb` y en la base, pero se excluye de los totales de plantas B/AB.',
               '- El peak es la mayor cantidad en una fecha concreta, sin ajuste por feriados u horario de apertura. '
               'No se interpreta como un efecto puro del número del día del mes.',
               '- El catálogo consultado en noviembre de 2026 puede describir cierres posteriores a 2025. '
               'La cobertura observada en los archivos se informa por separado.', '',
               '## Archivos de origen','',
               '| Mes | Registros RM distintos | Plantas observadas | Duplicados exactos eliminados | Archivo oficial |',
               '|---|---:|---:|---:|---|']
    for row in coverage.itertuples():
        report.append(f'| {row.periodo} | {row.registros_clase_b:,} | {row.plantas_clase_b} | '
                      f'{row.duplicados_exactos_rm:,} | [ZIP]({row.url}) |')
    (OUT/'informe.md').write_text('\n'.join(report)+'\n',encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--months',nargs='*',type=int)
    parser.add_argument('--export-only',action='store_true')
    args = parser.parse_args()
    truststore.inject_into_ssl()
    c = connect()
    all_codes = catalog(c)
    if args.export_only:
        export(c)
        return
    manifest = json.loads((RAW/'manifiesto_2025.json').read_text(encoding='utf-8'))
    done = {r[0] for r in c.execute('SELECT periodo FROM archivos')}
    jobs = [i for i in manifest if i['periodo'] not in done and
            (not args.months or int(i['periodo'][-2:]) in args.months)]
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch,item):item for item in jobs}
        for future in as_completed(futures):
            item = futures[future]
            try:
                ingest(c,item,future.result(),all_codes)
                export(c)
            except Exception as exc:
                print(f'ERROR {item["periodo"]}: {exc}',flush=True)
                errors.append((item['periodo'],str(exc)))
    export(c)
    if errors:
        raise SystemExit(str(errors))


if __name__=='__main__':
    main()
