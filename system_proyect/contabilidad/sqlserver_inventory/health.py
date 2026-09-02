# <--- hecho por claude code: health check no destructivo. Reporta si el alias está
# configurado y si el guard (Test2 + rol) pasa, SIN exponer cadena/servidor/secretos y
# SIN tocar dbo.tblInv*. Nunca lanza excepción.
import logging

from django.db import connections

from . import config, guard
from .connection import cursor_test2, alias_configurado

_log = logging.getLogger('contabilidad.inventario_sql')


def estado():
    """dict con el estado de la conexión/guard. No lanza. No revela secretos."""
    cfg = connections.databases.get(config.ALIAS) or {}
    driver = (cfg.get('OPTIONS') or {}).get('driver')
    out = {
        'configurado': alias_configurado(),
        'ok': False,
        'bloqueado': True,
        'base': None,
        'login': None,
        'usuario_sql': None,
        'es_desarrollo': None,
        'driver': driver,
        'app_name': config.APP_NAME,
        'db_esperada': config.DB_ESPERADA,
        'rol': config.ROL_DESARROLLO,
        'motivo': None,
    }
    if not out['configurado']:
        out['motivo'] = 'El alias inventario_test2 no tiene credenciales configuradas en el entorno.'
        return out
    try:
        # verificar=False: queremos la identidad aunque el guard fallaría, para poder
        # reportar es_desarrollo=0 en vez de solo "bloqueado".
        with cursor_test2(verificar=False) as cur:
            ident = guard.identidad(cur)
        out.update(ident)
        if ident['base'] != config.DB_ESPERADA:
            out['motivo'] = (f"La base conectada es '{ident['base']}', se requiere "
                             f"'{config.DB_ESPERADA}'. Consultas bloqueadas.")
        elif ident['es_desarrollo'] != 1:
            out['motivo'] = (f"El usuario '{ident['usuario_sql']}' NO es miembro de "
                             f"'{config.ROL_DESARROLLO}'. Consultas tblInv* bloqueadas "
                             f"(el DBA debe otorgar el rol).")
        else:
            out['ok'] = True
            out['bloqueado'] = False
            out['motivo'] = (f"Conexión válida: base '{ident['base']}' y usuario "
                             f"'{ident['usuario_sql']}' miembro de '{config.ROL_DESARROLLO}'.")
    except Exception as e:  # noqa: BLE001 — health nunca debe romper la UI
        _log.warning('health check inventario_test2 falló: %r', e)
        out['motivo'] = 'No se pudo validar la conexión a Test2 (ver logs del servidor).'
    return out
