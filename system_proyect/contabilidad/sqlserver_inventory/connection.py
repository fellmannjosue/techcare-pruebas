# <--- hecho por claude code: apertura/validación de conexión al alias inventario_test2.
# Encapsula connections['inventario_test2'].cursor(), corre el guard y traduce errores.
# Las views/servicios NO abren cursores directamente: usan `leer()`.
from contextlib import contextmanager

from django.db import connections
from django.db import Error as DjangoDBError

from . import config, guard
from .errors import (InventarioNoConfigurado, AmbienteInvalido, traducir_error)


def alias_configurado():
    """True si el alias tiene credenciales utilizables (password presente)."""
    cfg = connections.databases.get(config.ALIAS)
    return bool(cfg and cfg.get('PASSWORD'))


@contextmanager
def cursor_test2(verificar=True):
    """Context manager que cede un cursor sobre el alias inventario_test2.
    Si `verificar`, corre el guard (Test2 + rol) antes de ceder el cursor."""
    if not alias_configurado():
        raise InventarioNoConfigurado(
            'El alias inventario_test2 no está configurado (faltan credenciales en el entorno).')
    conn = connections[config.ALIAS]
    cur = conn.cursor()
    try:
        if verificar:
            guard.verificar_ambiente(cur)
        yield cur
    finally:
        cur.close()


def leer(sql, params=None, verificar=True):
    """Ejecuta un SELECT parametrizado y devuelve (columnas, filas).
    Propaga AmbienteInvalido/InventarioNoConfigurado; traduce el resto a error seguro."""
    try:
        with cursor_test2(verificar=verificar) as cur:
            cur.execute(sql, list(params or []))
            cols = [c[0] for c in cur.description]
            filas = cur.fetchall()
            return cols, filas
    except (AmbienteInvalido, InventarioNoConfigurado):
        raise
    except DjangoDBError as e:
        raise traducir_error(e)


def filas_como_dicts(cols, filas):
    """Convierte (columnas, filas) en lista de dicts col->valor."""
    return [dict(zip(cols, f)) for f in filas]
