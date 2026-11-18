"""Valida los denominadores y la conciliación de gráficos y horas."""
from html.parser import HTMLParser
import json
import sqlite3

import numpy as np
import openpyxl
import pandas as pd

from graficos_rm import DEST,DB


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.external=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script':
            self.external.extend(v for k,v in attrs if k=='src')


def main():
    c=sqlite3.connect(DB)
    assert c.execute('SELECT count(*),sum(registros),sum(sin_hora) FROM horas_importadas').fetchone()==(12,2320324,0)
    raw=pd.read_sql_query('SELECT planta,fecha,sum(revisiones) AS n FROM flujo_horario_rm GROUP BY planta,fecha',c)
    baseline=pd.read_sql_query("SELECT planta,fecha,revisiones AS n FROM flujo_diario WHERE planta LIKE 'B-%' OR planta LIKE 'AB%'",c)
    pd.testing.assert_frame_equal(raw.sort_values(['planta','fecha']).reset_index(drop=True),baseline.sort_values(['planta','fecha']).reset_index(drop=True))
    cal=pd.read_csv(DEST/'calendario_promedio.csv').set_index('dia')
    assert cal.index.tolist()==list(range(1,32))
    assert cal.loc[29,'meses_disponibles']==11 and cal.loc[30,'meses_disponibles']==11 and cal.loc[31,'meses_disponibles']==7
    months=pd.read_csv(DEST/'comparacion_meses.csv').set_index('mes')
    assert int(months.total.sum())==2320324
    assert months.loc[3,'ranking_total']==2 and months.loc[3,'ranking_promedio']==4
    hours=pd.read_csv(DEST/'distribucion_horaria.csv').set_index('hora')
    assert int(hours.revisiones.sum())==2320324 and hours.revisiones.idxmax()==11
    assert np.isclose(hours.porcentaje.sum(),100)
    for file in ['semana_hora_porcentaje.csv','dia_mes_hora_porcentaje.csv']:
        frame=pd.read_csv(DEST/file,index_col=0)
        sums=frame.sum(axis=1,min_count=1).dropna()
        assert np.allclose(sums,100)
    book=openpyxl.load_workbook(DEST/'datos_graficos.xlsx',read_only=True)
    assert book['horas'].max_row==25 and book['cobertura_horaria'].max_row==13
    parser=Scripts();parser.feed((DEST/'informe_interactivo.html').read_text(encoding='utf-8'))
    assert not parser.external,parser.external
    result=dict(meses_horarios=12,registros_conciliados=2320324,horas_sin_interpretar=0,
                denominadores_calendario='ok',porcentajes_horarios='ok',excel='ok',
                informe_sin_scripts_externos='ok')
    (DEST/'validacion_graficos.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
