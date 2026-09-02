# <--- hecho por claude code: pruebas unitarias SIN base de datos (guard, DTO, errores).
# Se ejecutan con:  ../venv/bin/python -m unittest contabilidad.sqlserver_inventory.tests.test_unit
import datetime
import unittest
from decimal import Decimal

from contabilidad.sqlserver_inventory import guard, dto, errors


class _FakeCursor:
    """Cursor mínimo para probar el guard sin tocar la red."""
    def __init__(self, base, usuario, es_desarrollo):
        self._row = ('irrelevante', base, usuario, es_desarrollo)  # orden no importa: se usa description
        self.description = [('Base',), ('LoginOriginal',), ('UsuarioSql',), ('EsDesarrollo',)]
        self._row = (base, usuario, usuario, es_desarrollo)

    def execute(self, sql, params=None):
        self.ultimo = (sql, params)
        return self

    def fetchone(self):
        return self._row


class GuardTests(unittest.TestCase):
    def test_ok_test2_y_rol(self):
        ident = guard.verificar_ambiente(_FakeCursor('Test2', 'admin2', 1))
        self.assertEqual(ident['base'], 'Test2')
        self.assertEqual(ident['es_desarrollo'], 1)

    def test_base_incorrecta_bloquea(self):
        with self.assertRaises(errors.AmbienteInvalido):
            guard.verificar_ambiente(_FakeCursor('AdmonANASQL', 'admin2', 1))

    def test_sin_rol_bloquea(self):
        with self.assertRaises(errors.AmbienteInvalido):
            guard.verificar_ambiente(_FakeCursor('Test2', 'admin2', 0))

    def test_rol_null_bloquea(self):
        with self.assertRaises(errors.AmbienteInvalido):
            guard.verificar_ambiente(_FakeCursor('Test2', 'admin2', None))

    def test_guard_parametriza_el_rol(self):
        cur = _FakeCursor('Test2', 'admin2', 1)
        guard.identidad(cur)
        # el nombre del rol viaja como parámetro, no concatenado en el SQL
        self.assertIn('%s', cur.ultimo[0])
        self.assertEqual(cur.ultimo[1], ['Des_EquipoInventario'])


class DtoTests(unittest.TestCase):
    def test_articulo_tipos(self):
        a = dto.Articulo.from_dict({
            'ArticuloID': 5, 'Codigo': 'A-1', 'Descripcion': 'Camisa',
            'CategoriaID': 2, 'UnidadMedidaID': 3, 'Activo': True,
            'Observacion': None, 'CostoPromedioActual': Decimal('12.500000'), 'RV': b'\x00\x00\x00\x00\x00\x00\x00\x01',
        })
        self.assertIsInstance(a.articulo_id, int)
        self.assertIsInstance(a.costo_promedio_actual, Decimal)
        self.assertIsInstance(a.rv, bytes)
        self.assertIsInstance(a.activo, bool)

    def test_costo_desde_string_es_decimal_exacto(self):
        # nunca float: str preserva la precisión
        a = dto.Articulo.from_dict({'ArticuloID': 1, 'Codigo': 'X', 'Descripcion': 'Y',
                                    'CostoPromedioActual': '19.600000'})
        self.assertEqual(a.costo_promedio_actual, Decimal('19.600000'))
        self.assertNotIsInstance(a.costo_promedio_actual, float)

    def test_existencia_cantidad_decimal(self):
        e = dto.ExistenciaArticulo.from_dict({'ArticuloID': 1, 'Codigo': 'X', 'Descripcion': 'Y',
                                              'AlmacenID': 1, 'CodigoAlmacen': 'ALM1',
                                              'CantidadActual': Decimal('3.000'),
                                              'UltimoMovimientoID': 9, 'CostoPromedioActual': Decimal('1.0')})
        self.assertIsInstance(e.cantidad_actual, Decimal)

    def test_kardex_fechas_y_decimales(self):
        m = dto.MovimientoKardex.from_dict({
            'MovimientoID': 1, 'FechaMovimiento': datetime.date(2026, 8, 25),
            'FechaAplicacion': datetime.datetime(2026, 8, 25, 10, 0, 0),
            'Cantidad': Decimal('2.000'), 'CostoUnitario': Decimal('5.000000'),
        })
        self.assertIsInstance(m.fecha_movimiento, datetime.date)
        self.assertIsInstance(m.cantidad, Decimal)


class ErroresTests(unittest.TestCase):
    def test_permiso_denegado(self):
        e = errors.traducir_error(Exception("[42000] [SQL Server]permiso denegado (229)"))
        self.assertIsInstance(e, errors.PermisoDenegado)

    def test_conexion(self):
        exc = Exception("no conecta")
        exc.args = ('08001', 'timeout')
        e = errors.traducir_error(exc)
        self.assertIsInstance(e, errors.ConexionInventarioError)

    def test_generico(self):
        e = errors.traducir_error(Exception("algo raro"))
        self.assertIsInstance(e, errors.InventarioSqlError)


if __name__ == '__main__':
    unittest.main()
