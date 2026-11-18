"""Comprobaciones de cobertura y conciliación de la base regional terminada."""
import json
import sqlite3

import pandas as pd

from rm_2025 import DB, OUT


def main():
    c = sqlite3.connect(DB)
    assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not c.execute('PRAGMA foreign_key_check').fetchall()
    audit = pd.read_sql_query('SELECT * FROM archivos ORDER BY periodo',c)
    assert audit.periodo.tolist() == [f'2025-{i:02d}' for i in range(1,13)]
    assert (audit.fechas_invalidas_rm == 0).all()
    assert (audit.filas_rm == audit.registros_distintos_rm+audit.duplicados_exactos_rm).all()
    assert (audit.filas_nacionales >= audit.filas_rm).all()
    assert c.execute('SELECT count(*) FROM codigos_sin_catalogo').fetchone()[0] == 0
    assert c.execute('SELECT sum(revisiones) FROM flujo_diario').fetchone()[0] == int(audit.registros_distintos_rm.sum())

    raw = pd.read_sql_query('SELECT * FROM flujo_diario',c)
    scoped = raw[raw.planta.str.startswith(('B-','AB'))]
    daily = scoped.groupby(['periodo','fecha'],as_index=False).revisiones.sum()
    expected = daily[daily.revisiones.eq(daily.groupby('periodo').revisiones.transform('max'))]
    exported = pd.read_csv(OUT/'peaks_rm.csv')
    assert set(zip(expected.periodo,expected.fecha,expected.revisiones)) == set(zip(exported.periodo,exported.fecha,exported.revisiones))
    monthly = scoped.groupby('periodo').revisiones.sum()
    for row in exported.itertuples():
        assert row.total_mes == monthly[row.periodo]
        assert abs(row.porcentaje_mes-100*row.revisiones/row.total_mes) < 1e-9

    per_plant = pd.read_csv(OUT/'peaks_por_planta.csv')
    expected_plant = scoped[scoped.revisiones.eq(scoped.groupby(['planta','periodo']).revisiones.transform('max'))]
    assert set(zip(expected_plant.planta,expected_plant.fecha,expected_plant.revisiones)) == set(zip(per_plant.planta,per_plant.fecha,per_plant.revisiones))

    # Conciliación con la base independiente de la planta del análisis inicial.
    initial = sqlite3.connect(DB.parent/'prt.sqlite')
    before = initial.execute('SELECT count(*) FROM revisiones').fetchone()[0]
    after = int(scoped[(scoped.planta=='B-1348') & (scoped.periodo=='2025-01')].revisiones.sum())
    assert before == after == 7410
    summary = {
        'meses_importados':len(audit),
        'plantas_b_ab_observadas':int(scoped.planta.nunique()),
        'registros_b_ab':int(scoped.revisiones.sum()),
        'duplicados_exactos_rm_eliminados':int(audit.duplicados_exactos_rm.sum()),
        'registros_otras_clases_excluidos':int(raw.revisiones.sum()-scoped.revisiones.sum()),
        'fechas_invalidas_rm':0,
        'codigos_sin_catalogo':0,
        'peaks_regionales_exportados':len(exported),
        'peaks_por_planta_exportados':len(per_plant),
        'conciliacion_b_1348_enero':after,
        'integridad_sqlite':'ok',
        'conciliacion_totales_y_peaks':'ok',
    }
    (OUT/'validacion.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
