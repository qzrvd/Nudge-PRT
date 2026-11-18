import unittest
import numpy as np
import pandas as pd
from eficiencia_rm import stats,standardized


class StandardizationTest(unittest.TestCase):
    def data(self,extra=0):
        rows=[]
        for plant,mult in [('P1',1),('P2',10)]:
            for peak in [False,True]:
                for case,seconds,n in [('rapido',600,80 if peak else 20),('lento',2400,20 if peak else 80)]:
                    rows.append(dict(planta=plant,mes=1,dia_semana=0,resultado='A',tipo_vehiculo=case,
                        pico=peak,segundos=seconds+(extra if peak else 0),revisiones=n*mult))
        return pd.DataFrame(rows)

    def test_no_confundir_mezcla_con_diferencia_de_duracion(self):
        d=self.data()
        raw=[stats(g.segundos,g.revisiones)['mediana_min'] for _,g in d.groupby('pico')]
        self.assertEqual(raw,[40,10])
        adjusted,_=standardized(d,['planta','mes','dia_semana','resultado','tipo_vehiculo'],'pico',[False,True],reference_peak=True)
        self.assertTrue(np.allclose(adjusted.mediana_min,[10,10]))
        self.assertTrue(np.allclose(adjusted.cobertura_soporte_pct,100))

    def test_recuperar_diferencia_dentro_de_casos_comparables(self):
        adjusted,_=standardized(self.data(extra=300),['planta','mes','dia_semana','resultado','tipo_vehiculo'],'pico',[False,True],reference_peak=True)
        adjusted=adjusted.set_index('pico')
        self.assertEqual(adjusted.loc[True,'mediana_min']-adjusted.loc[False,'mediana_min'],5)

    def test_soporte_comun_para_seis_dias(self):
        rows=[dict(planta='P1',mes=1,resultado='A',tipo_vehiculo='1',dia_semana=i,
                   segundos=600+60*i,revisiones=20) for i in range(6)]
        adjusted,_=standardized(pd.DataFrame(rows),['planta','mes','resultado','tipo_vehiculo'],'dia_semana',list(range(6)))
        self.assertEqual(adjusted.mediana_min.tolist(),[10,11,12,13,14,15])


if __name__=='__main__':
    unittest.main()
