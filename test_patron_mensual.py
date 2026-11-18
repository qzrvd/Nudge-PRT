import unittest
import pandas as pd
from patron_mensual import annotate


def row(vehicle,date,digit,result='A',due=None,start=36000):
    return dict(vehiculo=vehicle,ppu_reconocida=1,digito=digit,planta='B-1348',fecha=date,
        inicio_seg=start,resultado=result,resultado_gases=result,vencimiento=due,
        tipo_vehiculo=1,servicio=3,combustible=1,anio_fabricacion=2015)


class CalendarTest(unittest.TestCase):
    def test_mes_precedente_cruce_de_ano_y_no_forzar_atraso(self):
        d=annotate(pd.DataFrame([row('a','2025-12-01',9),row('b','2025-03-01',1),
                               row('c','2025-02-01',1),row('d','2025-01-01',9)]))
        result=d.set_index('digito').relacion_calendario
        self.assertEqual(d[d.fecha==pd.Timestamp('2025-12-01')].relacion_calendario.iloc[0],'Mes precedente')
        self.assertEqual(d[d.fecha==pd.Timestamp('2025-03-01')].relacion_calendario.iloc[0],'Mes precedente')
        self.assertEqual(d[d.fecha==pd.Timestamp('2025-02-01')].relacion_calendario.iloc[0],'Otros meses: atraso no determinado')
        self.assertEqual(d[d.fecha==pd.Timestamp('2025-01-01')].relacion_calendario.iloc[0],'Mes correspondiente')

    def test_revisita_inferida_no_confundir_con_primera_visita(self):
        d=annotate(pd.DataFrame([row('a','2025-01-31',0,'R'),row('a','2025-02-01',0,'A','2026-02-28')]))
        self.assertEqual(d.reingreso_compatible_15.tolist(),[False,True])
        self.assertEqual(d.inicio_observado_15.tolist(),[True,False])

    def test_no_usar_vencimiento_emitido_hoy_como_previo(self):
        d=annotate(pd.DataFrame([row('a','2024-12-20',9,'A','2025-01-31'),
                               row('a','2025-02-02',9,'A','2026-01-31')]))
        self.assertEqual(d.estado_vencimiento_previo.iloc[0],'Sin vencimiento previo suficiente')
        self.assertEqual(d.estado_vencimiento_previo.iloc[1],'Fecha posterior al vencimiento previo observado')

    def test_aprobacion_con_orden_ambiguo_invalida_el_vencimiento_previo(self):
        d=annotate(pd.DataFrame([row('a','2024-12-20',9,'A','2025-01-31'),
              row('a','2025-01-15',9,'A','2026-01-31'),row('a','2025-01-15',9,'R'),
              row('a','2025-02-02',9,'A','2026-01-31')]))
        self.assertEqual(d.estado_vencimiento_previo.iloc[-1],'Sin vencimiento previo suficiente')


if __name__=='__main__':
    unittest.main()
