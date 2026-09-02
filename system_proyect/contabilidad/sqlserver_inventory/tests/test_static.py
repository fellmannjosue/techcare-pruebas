# <--- hecho por claude code: verificación ESTÁTICA de seguridad de la capa de Inventario.
# Confirma que el paquete NO contiene DML sobre tblInv*, ni llamada al núcleo privado,
# ni `float(` sobre dinero, ni credenciales embebidas.
# Ejecutar con:  ../venv/bin/python -m unittest contabilidad.sqlserver_inventory.tests.test_static
import os
import re
import unittest

PAQUETE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROHIBIDOS = [
    r'insert\s+into\s+dbo\.tblInv',
    r'update\s+dbo\.tblInv',
    r'delete\s+from\s+dbo\.tblInv',
    r'spInvMovimientoAplicarInterno',
    # cualquier EXEC de stored procedures de inventario (no autorizados en esta etapa)
    r'exec\s+dbo\.spInv',
    r'\bfloat\s*\(',            # nunca float en esta capa
]

# Patrones de secreto embebido (no debe haber credenciales en el paquete).
SECRETOS = [
    r'password\s*=\s*[\'"][^\'"]+[\'"]',
    r'pwd\s*=\s*[\'"][^\'"]+[\'"]',
    r'\bUID\s*=\s*[\'"][^\'"]+[\'"]',
]


def _archivos_py():
    for raiz, _dirs, files in os.walk(PAQUETE):
        if os.path.basename(raiz) == 'tests':
            continue  # no escanear las propias pruebas
        for f in files:
            if f.endswith('.py'):
                yield os.path.join(raiz, f)


class EscaneoEstaticoTests(unittest.TestCase):
    def test_sin_dml_ni_nucleo_ni_float(self):
        fallos = []
        for ruta in _archivos_py():
            with open(ruta, 'r', encoding='utf-8') as fh:
                texto = fh.read()
            for pat in PROHIBIDOS:
                if re.search(pat, texto, re.IGNORECASE):
                    fallos.append(f'{os.path.basename(ruta)}: patrón prohibido /{pat}/')
        self.assertEqual(fallos, [], 'Patrones prohibidos encontrados:\n' + '\n'.join(fallos))

    def test_sin_credenciales_embebidas(self):
        fallos = []
        for ruta in _archivos_py():
            with open(ruta, 'r', encoding='utf-8') as fh:
                texto = fh.read()
            for pat in SECRETOS:
                if re.search(pat, texto, re.IGNORECASE):
                    fallos.append(f'{os.path.basename(ruta)}: posible secreto /{pat}/')
        self.assertEqual(fallos, [], 'Posibles credenciales embebidas:\n' + '\n'.join(fallos))

    def test_solo_select_en_queries(self):
        ruta = os.path.join(PAQUETE, 'queries.py')
        with open(ruta, 'r', encoding='utf-8') as fh:
            texto = fh.read().lower()
        for verbo in (' insert ', ' update ', ' delete ', ' merge ', ' exec ', ' truncate '):
            self.assertNotIn(verbo, texto, f'queries.py contiene «{verbo.strip()}»')


if __name__ == '__main__':
    unittest.main()
