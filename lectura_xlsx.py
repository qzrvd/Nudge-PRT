"""Lector de filas OOXML en flujo, sin construir árboles para cada celda."""
import io
import re
import zipfile
from html import unescape

from lxml import etree


ROW = re.compile(rb'<row\b[^>]*>.*?</row>',re.S)
CELL = re.compile(rb'<c\b([^>]*?)(?:/>|>(.*?)</c>)',re.S)
REF = re.compile(rb'\br="([A-Z]+)\d+"')
TYPE = re.compile(rb'\bt="([^"]+)"')
VALUE = re.compile(rb'<v(?:\s[^>]*)?>(.*?)</v>',re.S)
TEXT = re.compile(rb'<t(?:\s[^>]*)?>(.*?)</t>',re.S)


def normalize(value):
    return re.sub(r'[^A-Z0-9]','',str(value or '').upper())


def xml_rows(handle):
    tail = b''
    while True:
        chunk = handle.read(4*1024*1024)
        data = tail+chunk
        consumed = 0
        for match in ROW.finditer(data):
            yield match.group()
            consumed = match.end()
        tail = data[consumed:]
        if not chunk:
            if b'<row ' in tail or b'<row>' in tail:
                raise ValueError('Fila XML incompleta')
            return
        if len(tail)>32*1024*1024:
            raise ValueError('No se reconoce el formato de filas OOXML')


def rows(data, plants):
    targets = {normalize(x) for x in plants} if isinstance(plants,(set,list,tuple)) else {normalize(plants)}
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        strings = []
        if 'xl/sharedStrings.xml' in book.namelist():
            with book.open('xl/sharedStrings.xml') as handle:
                for _,element in etree.iterparse(handle,events=('end',),tag=ns+'si'):
                    strings.append(''.join(element.itertext()))
                    element.clear()
                    while element.getprevious() is not None:
                        del element.getparent()[0]

        def value(attrs,body):
            if body is None:
                return None
            kind = TYPE.search(attrs)
            kind = kind[1] if kind else None
            if kind == b'inlineStr':
                return ''.join(unescape(m[1].decode('utf-8')) for m in TEXT.finditer(body))
            found = VALUE.search(body)
            if found is None:
                return None
            raw = found[1]
            if kind == b's':
                return strings[int(raw)]
            try:
                return float(raw)
            except ValueError:
                return unescape(raw.decode('utf-8'))

        for name in book.namelist():
            if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml',name):
                continue
            headers = None
            plant_col = None
            with book.open(name) as handle:
                for raw in xml_rows(handle):
                    if headers is None:
                        decoded = {}
                        for cell in CELL.finditer(raw):
                            reference = REF.search(cell[1])
                            if reference:
                                decoded[reference[1]] = normalize(value(cell[1],cell[2]))
                        if 'CODPRT' in decoded.values() and 'FECREVISION' in decoded.values():
                            headers = decoded
                            plant_col = next(k for k,v in headers.items() if v=='CODPRT')
                        continue
                    code = None
                    for cell in CELL.finditer(raw):
                        reference = REF.search(cell[1])
                        if reference and reference[1]==plant_col:
                            code = value(cell[1],cell[2])
                            break
                    if normalize(code) not in targets:
                        yield {'CODPRT':code}
                        continue
                    decoded = {}
                    for cell in CELL.finditer(raw):
                        reference = REF.search(cell[1])
                        if reference:
                            decoded[headers.get(reference[1],'')] = value(cell[1],cell[2])
                    yield decoded
