import unittest
from duraciones_rm import duration


class DurationTest(unittest.TestCase):
    def test_recepcion_termino(self):
        self.assertEqual(duration('08:00:00','08:25:30'),(8,1530,'positiva'))
        self.assertEqual(duration(8/24,8.5/24),(8,1800,'positiva'))

    def test_no_inventar_duracion_para_horas_inconsistentes(self):
        self.assertEqual(duration('23:50:00','00:10:00'),(23,-1,'fin_anterior'))
        self.assertEqual(duration('08:00:00','08:00:00'),(8,0,'cero'))
        self.assertEqual(duration('08:00:00',None),(8,-1,'hora_invalida'))


if __name__=='__main__':
    unittest.main()
