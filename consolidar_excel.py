"""Reúne los resultados publicados y su procedencia sin exportar patentes."""
import json
import re
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'resultados/rm_2025'


def main():
    wb = Workbook()
    intro = wb.active
    intro.title = 'LEEME'
    for row in [
        ['Contenido', 'Alcance y advertencias'],
        ['Universo', '2025 completo; 33 plantas B/AB de la Región Metropolitana; 2.320.324 registros distintos publicados.'],
        ['Datos incluidos', 'Tablas agregadas de concentración diaria por planta, horarios, duración registrada, calendario y revisitas inferidas.'],
        ['Datos originales', 'Los registros individuales están en los ZIP oficiales enlazados y en la base SQLite local. Este Excel no contiene todas las filas originales ni patentes.'],
        ['Cómo navegar', 'La hoja INDICE permite abrir cada tabla y señala el Excel de procedencia. FUENTES incluye enlaces de descarga.'],
        ['Conteos', 'Revisiones publicadas, no vehículos únicos ni solicitudes de reserva. Se eliminaron únicamente duplicados exactos.'],
        ['Duraciones', 'Tiempo entre inicio y fin registrados; no mide espera exterior. Comparaciones ajustadas describen asociaciones.'],
        ['Calendario', 'Mes precedente no equivale a adelanto confirmado; el dígito no prueba vigencia previa. Reingresos inferidos, sin marca oficial.'],
        ['Parque vehicular', 'Las fuentes INE corresponden a 2024; no permiten calcular cuántos tienen revisión vencida o permiso impago en 2025.'],
        ['Prefijos', 'C: concentración; H: horarios y gráficos; E: eficiencia; P: patrón y calendario.'],
    ]:
        intro.append(row)
    index = wb.create_sheet('INDICE')
    index.append(['Hoja (clic para abrir)', 'Tema', 'Archivo de procedencia', 'Hoja original', 'Filas de datos'])
    sources = wb.create_sheet('FUENTES')
    sources.append(['Fuente', 'URL / ubicación', 'Uso / alcance'])
    manifest = json.loads((ROOT / 'fuentes/manifiesto_2025.json').read_text(encoding='utf-8'))
    for item in manifest:
        sources.append([f"SGPRT RB {item['periodo']}", item['url'], 'ZIP nacional oficial; selección de plantas B/AB de la RM.'])
    for title, url, usage in [
        ('Portal PRT', 'https://www.prt.cl/Descargas/index.html', 'Índice oficial de descargas'),
        ('Catálogo de plantas', 'https://www.prt.cl/Descargas/docs/Codigos_Plantas.xlsx', 'Región, código y clasificación de plantas'),
        ('Diccionario SGPRT RB', 'https://www.prt.cl/Descargas/docs/Campos_SGPRT_RB.xlsx', 'Definiciones de campos'),
        ('Decreto 156, artículo 7', 'https://www.bcn.cl/leychile/navegar?i=10183', 'Calendario y excepciones; revisar versión y fecha de vigencia'),
    ]:
        sources.append([title, url, usage])
    context = BASE / 'graficos/contexto_y_fuentes.md'
    seen = {row[1].value for row in sources.iter_rows(min_row=2)}
    for title, url in re.findall(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', context.read_text(encoding='utf-8')):
        if url not in seen:
            sources.append([title, url, 'Contexto de parque vehicular y permisos; detalle y límites en NOTAS.'])
            seen.add(url)
    for row in sources.iter_rows(min_row=2):
        row[1].hyperlink = row[1].value
        row[1].style = 'Hyperlink'
    books = [
        ('C', 'Concentración', BASE / 'concentracion_rm_2025.xlsx'),
        ('H', 'Horarios y gráficos', BASE / 'graficos/datos_graficos.xlsx'),
        ('E', 'Eficiencia', BASE / 'eficiencia/eficiencia_rm_2025.xlsx'),
        ('P', 'Patrón y calendario', BASE / 'patron_calendario/calendario_y_revisitas_2025.xlsx'),
    ]
    for prefix, theme, path in books:
        source = load_workbook(path, read_only=True, data_only=True)
        for sheet in source:
            name = (prefix + '_' + sheet.title)[:31]
            assert name not in wb.sheetnames, name
            dest = wb.create_sheet(name)
            for row in sheet.iter_rows(values_only=True):
                dest.append(row)
            assert dest.max_row == sheet.max_row, sheet.title
            index.append([name, theme, str(path.relative_to(ROOT)), sheet.title, max(0, dest.max_row - 1)])
            index.cell(index.max_row, 1).hyperlink = f"#'{name}'!A1"
            index.cell(index.max_row, 1).style = 'Hyperlink'
        source.close()
    notes = wb.create_sheet('NOTAS')
    notes.append(['Documento', 'Texto (una línea por fila)'])
    for path in [BASE / 'informe.md', context, BASE / 'eficiencia/informe.md', BASE / 'patron_calendario/informe.md']:
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                notes.append([str(path.relative_to(ROOT)), line])
    for sheet in wb:
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(color='FFFFFF', bold=True)
            cell.fill = PatternFill('solid', fgColor='155E63')
        for col in sheet.iter_cols():
            width = min(65, max(15, max(len(str(c.value or '')) for c in list(col)[:100]) + 2))
            sheet.column_dimensions[col[0].column_letter].width = width
    out = BASE / 'PRT_RM_2025_datos_y_fuentes.xlsx'
    wb.save(out)
    check = load_workbook(out, read_only=True)
    assert len(check.sheetnames) == 55
    print(f'{out}\n{len(check.sheetnames)} hojas; {out.stat().st_size:,} bytes')
    check.close()


if __name__ == '__main__':
    main()
