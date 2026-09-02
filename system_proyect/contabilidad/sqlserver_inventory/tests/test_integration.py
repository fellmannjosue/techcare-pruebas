# <--- hecho por claude code: pruebas de INTEGRACIÓN no destructivas contra Test2.
# Requieren Django + red. El health check corre siempre (no destructivo); las 8 lecturas
# solo si el guard pasa (Test2 + IS_ROLEMEMBER=1). Nada de escritura.
# Ejecutar con:  ../venv/bin/python -m unittest contabilidad.sqlserver_inventory.tests.test_integration
import os
import unittest


def setUpModule():
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'system_proyect.settings')
    try:
        django.setup()
    except Exception as e:  # noqa: BLE001
        raise unittest.SkipTest(f'Django no disponible: {e}')


def _servicios():
    from contabilidad.sqlserver_inventory import services
    return services


class HealthTests(unittest.TestCase):
    def test_estado_no_lanza_y_no_expone_secretos(self):
        st = _servicios().health()
        self.assertIsInstance(st, dict)
        for k in ('configurado', 'ok', 'bloqueado', 'base', 'es_desarrollo', 'driver',
                  'app_name', 'db_esperada', 'rol', 'motivo'):
            self.assertIn(k, st)
        # nunca debe filtrar credenciales/cadena de conexión
        blob = repr(st).lower()
        self.assertNotIn('password', blob)
        self.assertNotIn('pwd=', blob)
        self.assertEqual(st['db_esperada'], 'Test2')


class LecturasTests(unittest.TestCase):
    """Solo corren si el guard pasa (Test2 + rol). Si no, se saltan (bloqueo reportado)."""

    def setUp(self):
        st = _servicios().health()
        if not st.get('ok'):
            self.skipTest(f"Guard no OK: {st.get('motivo')}")

    def test_catalogos(self):
        s = _servicios()
        self.assertIsInstance(s.listar_categorias(), list)
        self.assertIsInstance(s.listar_unidades(), list)
        self.assertIsInstance(s.listar_almacenes(), list)

    def test_articulos_y_costo(self):
        s = _servicios()
        arts = s.listar_articulos()
        self.assertIsInstance(arts, list)
        if arts:
            from decimal import Decimal
            a = arts[0]
            self.assertTrue(a.costo_promedio_actual is None or isinstance(a.costo_promedio_actual, Decimal))

    def test_proveedores(self):
        self.assertIsInstance(_servicios().listar_proveedores(), list)

    def test_existencias(self):
        self.assertIsInstance(_servicios().existencias(), list)


if __name__ == '__main__':
    unittest.main()
