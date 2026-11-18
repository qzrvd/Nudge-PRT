"""Descarga pública e importación reproducible de revisiones SGPRT clase B."""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import unquote, urljoin, urlparse
import zipfile
from lxml import etree
from lectura_xlsx import rows as optimized_xlsx_rows

import openpyxl
import requests
import truststore

ROOT = Path(__file__).resolve().parent
BASE = 'https://www.prt.cl/Descargas/index.html'
RAW = ROOT / 'fuentes'
DB = ROOT / 'datos/prt.sqlite'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href' and v)


def links(html, base):
    parser = Links()
    parser.feed(html)
    return list(dict.fromkeys(urljoin(base, x) for x in parser.links))


def download(url, path):
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    truststore.inject_into_ssl()
    print(f'Descargando {url}', flush=True)
    temporary = path.with_suffix(path.suffix + '.part')
    started = time.monotonic()
    with requests.get(url, timeout=(30, 90), stream=True) as response:
        response.raise_for_status()
        with temporary.open('wb') as out:
            for chunk in response.iter_content(64 * 1024):
                out.write(chunk)
                if time.monotonic() - started > 600:
                    raise TimeoutError(f'Descarga excedió diez minutos: {url}')
    temporary.replace(path)
    return path


def discover(year):
    index = download(BASE, RAW / 'descargas_prt.html').read_text(encoding='utf-8-sig')
    pages = [u for u in links(index, BASE) if f'/sites/{year}/' in u]
    manifest = []
    for page in pages:
        month = int(re.search(r'/sites/\d+/(\d+)\.', page)[1])
        html = download(page, RAW / f'{year}-{month:02d}.html').read_text(encoding='utf-8-sig')
        archives = [u for u in links(html, page)
                    if re.search(r'/SGPRT_RB[_-][^/]+\.zip$', u, re.I)]
        if len(archives) != 1:
            raise ValueError(f'Se esperaba un ZIP SGPRT RB en {page}: {archives}')
        manifest.append(dict(periodo=f'{year}-{month:02d}', url=archives[0]))
    if len(manifest) != 12:
        raise ValueError(f'El año {year} tiene {len(manifest)} meses publicados; se requieren 12.')
    path = RAW / f'manifiesto_{year}.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def normalize(value):
    return re.sub(r'[^A-Z0-9]', '', str(value or '').upper())


def clean_time(value):
    if value is None:
        return None
    if isinstance(value, (float, int)) and 0 <= value < 1:
        seconds = round(value * 86400) % 86400
        return f'{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}'
    if hasattr(value, 'strftime'):
        return value.strftime('%H:%M:%S')
    match = re.search(r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?', str(value))
    if match:
        h, m, s = (int(x or 0) for x in match.groups())
        if h < 24 and m < 60 and s < 60:
            return f'{h:02d}:{m:02d}:{s:02d}'
    return None


def clean_date(value):
    if isinstance(value, (float, int)):
        value = openpyxl.utils.datetime.from_excel(value)
    if isinstance(value, (datetime, date)):
        return value.strftime('%Y-%m-%d')
    value = str(value or '').strip().split(' ')[0]
    for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    raise ValueError(f'Fecha no reconocida: {value!r}')


def fast_xlsx_rows(data, plant):
    """Lee XML en flujo y decodifica solo las filas de la planta seleccionada."""
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    targets = {normalize(x) for x in plant} if isinstance(plant, (set, list, tuple)) else {normalize(plant)}
    with zipfile.ZipFile(io.BytesIO(data)) as workbook:
        strings = []
        if 'xl/sharedStrings.xml' in workbook.namelist():
            with workbook.open('xl/sharedStrings.xml') as handle:
                for _, element in etree.iterparse(handle, events=('end',), tag=ns + 'si'):
                    strings.append(''.join(element.itertext()))
                    element.clear()
                    while element.getprevious() is not None:
                        del element.getparent()[0]

        def cell_value(cell):
            value = cell.find(ns + 'v')
            if cell.get('t') == 'inlineStr':
                inline = cell.find(ns + 'is')
                return ''.join(inline.itertext()) if inline is not None else None
            if value is None:
                return None
            if cell.get('t') == 's':
                return strings[int(value.text)]
            try:
                return float(value.text)
            except (TypeError, ValueError):
                return value.text

        for sheet in workbook.namelist():
            if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml', sheet):
                continue
            headers = None
            plant_col = None
            with workbook.open(sheet) as handle:
                for _, row in etree.iterparse(handle, events=('end',), tag=ns + 'row'):
                    cells = list(row)
                    if headers is None:
                        candidate = {re.sub(r'\d', '', c.get('r', '')): normalize(cell_value(c)) for c in cells}
                        if 'CODPRT' in candidate.values() and 'FECREVISION' in candidate.values():
                            headers = candidate
                            plant_col = next(k for k, v in headers.items() if v == 'CODPRT')
                    else:
                        code = next((cell_value(c) for c in cells if re.sub(r'\d', '', c.get('r', '')) == plant_col), None)
                        if normalize(code) in targets:
                            yield {headers.get(re.sub(r'\d', '', c.get('r', '')), ''): cell_value(c) for c in cells}
                        else:
                            yield {'CODPRT': code}
                    row.clear()
                    while row.getprevious() is not None:
                        del row.getparent()[0]


def rows_from_zip(path, plant):
    with zipfile.ZipFile(path) as archive:
        supported = 0
        for member in archive.namelist():
            if member.lower().endswith('.xlsx') and not Path(member).name.startswith('~$'):
                supported += 1
                print(f'Leyendo {member}', flush=True)
                yield from optimized_xlsx_rows(archive.read(member), plant)
            elif member.lower().endswith(('.csv', '.txt')):
                supported += 1
                print(f'Leyendo {member}', flush=True)
                raw = archive.read(member)
                try:
                    decoded = raw.decode('utf-8-sig')
                except UnicodeDecodeError:
                    decoded = raw.decode('cp1252')
                dialect = csv.Sniffer().sniff(decoded[:65536], delimiters=';\t,|')
                yield from mapped_rows(csv.reader(io.StringIO(decoded), dialect))
        if not supported:
            raise ValueError(f'ZIP sin CSV/TXT/XLSX reconocidos: {archive.namelist()}')


def mapped_rows(rows):
    headers = None
    for row in rows:
        if not headers:
            candidate = [normalize(x) for x in row]
            if 'CODPRT' in candidate and 'FECREVISION' in candidate:
                headers = candidate
            continue
        if any(x is not None and str(x).strip() for x in row):
            yield dict(zip(headers, row))


def connect():
    DB.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB)
    connection.executescript((ROOT / 'esquema.sql').read_text(encoding='utf-8'))
    return connection


def load_plants(connection):
    path = download('https://www.prt.cl/Descargas/docs/Codigos_Plantas.xlsx', RAW / 'Codigos_Plantas.xlsx')
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for row in book.worksheets[0].iter_rows(values_only=True):
        if len(row) >= 6 and isinstance(row[2], (int, float)):
            connection.execute('INSERT OR REPLACE INTO plantas VALUES (?,?,?,?,?)',
                               (str(row[1]).strip(), row[2], row[3], row[4], row[5]))
    book.close()
    connection.commit()


def import_month(connection, item, plant):
    url, period = item['url'], item['periodo']
    if connection.execute('SELECT 1 FROM archivos WHERE url=?', (url,)).fetchone():
        print(f'{period}: ya importado (use una base nueva para cambiar planta).', flush=True)
        return
    path = download(url, RAW / unquote(urlparse(url).path.rsplit('/', 1)[-1]))
    with path.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    read = selected = invalid = 0
    records = {}
    for row in rows_from_zip(path, plant):
        read += 1
        if normalize(row.get('CODPRT')) != normalize(plant):
            continue
        selected += 1
        try:
            day = clean_date(row.get('FECREVISION'))
            if day[:7] != period:
                raise ValueError('Fecha fuera del período publicado')
        except ValueError:
            invalid += 1
            continue
        start = clean_time(row.get('HORAINI'))
        end = clean_time(row.get('HORAFIN'))
        result = str(row.get('RESULTADOCRT') or '').strip().upper()
        result = result if result in ('A', 'R') else None
        # La fuente reutiliza certificados incluso dentro de una planta y fecha.
        # Eliminar solo filas completamente idénticas; conservar registros distintos.
        # Solo se guarda la huella, sin patente, VIN, motor ni chasis en la base.
        key = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()
        records[key] = (key, plant, day, start, end, result, str(row.get('CODVEHICULO') or ''), url)
    if not selected or invalid:
        raise ValueError(f'{period}: filas planta={selected}, fechas inválidas={invalid}; no se carga el mes.')
    with connection:
        connection.execute('INSERT INTO archivos VALUES (?,?,?,?,?,?,?,?)',
                           (url, period, digest, datetime.now(timezone.utc).isoformat(),
                            read, selected, invalid, len(records)))
        connection.executemany('INSERT OR IGNORE INTO revisiones VALUES (?,?,?,?,?,?,?,?)', records.values())
    print(f'{period}: {read:,} filas fuente; {selected:,} planta; {len(records):,} revisiones únicas.', flush=True)


def export(connection, year):
    out = ROOT / 'resultados'
    out.mkdir(exist_ok=True)
    import pandas as pd
    sheets = {}
    for view in ('flujo_anual', 'flujo_mensual', 'flujo_diario', 'flujo_semana_mes',
                 'flujo_semanal_calendario', 'flujo_horario'):
        frame = pd.read_sql_query(f'SELECT * FROM {view}', connection)
        frame.to_csv(out / f'{view}.csv', index=False, encoding='utf-8-sig')
        sheets[view] = frame
    coverage = pd.read_sql_query('SELECT * FROM archivos ORDER BY periodo', connection)
    coverage.to_csv(out / 'cobertura.csv', index=False, encoding='utf-8-sig')
    sheets['cobertura'] = coverage
    with pd.ExcelWriter(out / f'analisis_{year}.xlsx', engine='openpyxl') as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name[:31], index=False)
    print(f'Cobertura: {len(coverage)}/12 meses. Exportado a {out}', flush=True)
    if len(coverage) == 12:
        monthly = sheets['flujo_mensual'].sort_values('revisiones', ascending=False)
        print('Meses por volumen:\n' + monthly.to_string(index=False), flush=True)
        weeks = sheets['flujo_semana_mes']
        print('Semana con mayor volumen en cada mes:\n' +
              weeks.loc[weeks.groupby('mes').revisiones.idxmax()].to_string(index=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, default=2025)
    parser.add_argument('--plant', default='B-1348')
    parser.add_argument('--discover-only', action='store_true')
    parser.add_argument('--export-only', action='store_true')
    parser.add_argument('--months', nargs='*', type=int)
    parser.add_argument('--download-only', action='store_true')
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    connection = connect()
    if args.export_only:
        export(connection, args.year)
        return
    manifest = discover(args.year)
    if args.discover_only:
        return
    if args.download_only:
        selected = [item for item in manifest if not args.months or int(item['periodo'][-2:]) in args.months]
        errors = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            jobs = [executor.submit(download, item['url'], RAW / unquote(urlparse(item['url']).path.rsplit('/', 1)[-1])) for item in selected]
            for job in as_completed(jobs):
                try:
                    print(f'Disponible: {job.result().name}', flush=True)
                except Exception as exc:
                    errors.append(str(exc))
                    print(f'Fallo de descarga: {exc}', flush=True)
        if errors:
            raise SystemExit(f'{len(errors)} descargas pendientes; vuelva a ejecutar para reintentar.')
        return
    load_plants(connection)
    for item in manifest:
        if args.months and int(item['periodo'][-2:]) not in args.months:
            continue
        import_month(connection, item, args.plant)
        export(connection, args.year)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
