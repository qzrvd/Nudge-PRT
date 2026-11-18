import sqlite3
import tempfile
import unittest
from pathlib import Path
import zipfile

import openpyxl

from rm_2025 import SCHEMA, ingest


class RegionalImportTest(unittest.TestCase):
    def test_region_exact_duplicates_and_peak_ties(self):
        """Conservar certificados reutilizados y empates; excluir otras regiones."""
        c = sqlite3.connect(':memory:')
        c.executescript(SCHEMA)
        c.executemany('INSERT INTO plantas VALUES (?,?,?,?,?,?)',[
            ('B-1301',13,'Comuna A','Operador A','SGPRT',None),
            ('B-1302',13,'Comuna B','Operador B','SGPRT',None),
            ('A-1317',13,'Comuna C','Operador C','SGPRT',None)])
        codes = {'B1301':('B-1301',13),'B1302':('B-1302',13),'B0501':('B-0501',5),
                 'A1317':('A-1317',13)}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            book = openpyxl.Workbook()
            sheet = book.active
            sheet.append(['COD_PRT','FEC_REVISION','NUM_CERTIFICADO','PPU'])
            rows = [
                ['B-1301','01-01-2025',1,'AA0001'],
                ['B-1301','01-01-2025',1,'AA0002'],
                ['B-1301','01-01-2025',1,'AA0002'],
                ['B-1301','02-01-2025',2,'AA0003'],
                ['B-1301','02-01-2025',3,'AA0004'],
                ['B-1302','01-01-2025',4,'AA0005'],
                ['B-0501','01-01-2025',5,'AA0006'],
                ['NO-CATALOGO','01-01-2025',6,'AA0007'],
                ['A-1317','01-01-2025',7,'AA0008']]
            for row in rows:
                sheet.append(row)
            book.save(path/'data.xlsx')
            with zipfile.ZipFile(path/'data.zip','w',zipfile.ZIP_DEFLATED) as z:
                z.write(path/'data.xlsx','data.xlsx')
            ingest(c,{'periodo':'2025-01','url':'https://example.test/data.zip'},path/'data.zip',codes)
        audit = c.execute('SELECT filas_nacionales,filas_rm,duplicados_exactos_rm,registros_distintos_rm FROM archivos').fetchone()
        self.assertEqual(audit,(9,7,1,6))
        self.assertEqual(c.execute('SELECT count(*) FROM concentracion_planta WHERE planta=? AND ranking=1',('B-1301',)).fetchone()[0],2)
        self.assertEqual(c.execute('SELECT revisiones,total_mes,porcentaje_mes FROM concentracion_rm WHERE ranking=1').fetchone(),(3,5,60.0))
        self.assertEqual(c.execute('SELECT codigo,filas FROM codigos_sin_catalogo').fetchall(),[('NO-CATALOGO',1)])
        self.assertEqual(c.execute('SELECT sum(revisiones) FROM flujo_diario').fetchone()[0],6)


if __name__=='__main__':
    unittest.main()
