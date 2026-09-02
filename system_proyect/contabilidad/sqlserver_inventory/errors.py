# <--- hecho por claude code: traductor ÚNICO de errores de la capa de Inventario SQL Server.
# Nunca expone cadena de conexión, servidor, stack ni SQL con parámetros al usuario.
import logging

_log = logging.getLogger('contabilidad.inventario_sql')


class InventarioSqlError(Exception):
    """Base de todos los errores de la capa de Inventario SQL Server."""


class InventarioNoConfigurado(InventarioSqlError):
    """El alias inventario_test2 no tiene credenciales/configuración utilizable."""


class AmbienteInvalido(InventarioSqlError):
    """Guard fallido: la base no es Test2 o el usuario no es miembro del rol."""


class PermisoDenegado(InventarioSqlError):
    """El principal SQL no tiene permiso para la operación (no escalar desde la app)."""


class ConexionInventarioError(InventarioSqlError):
    """Fallo de conexión/timeout hacia Test2."""


def _sqlstate_y_numero(exc):
    """Extrae (SQLSTATE, numero_nativo, texto) de una excepción de pyodbc/mssql-django."""
    sqlstate = None
    numero = None
    texto = str(exc)
    # pyodbc.Error suele traer args = (sqlstate, mensaje) donde el mensaje incluye [SQL Server]...(NNN)
    args = getattr(exc, 'args', ()) or ()
    if args and isinstance(args[0], str) and len(args[0]) == 5:
        sqlstate = args[0]
    orig = getattr(exc, '__cause__', None) or exc
    oargs = getattr(orig, 'args', ()) or ()
    if oargs and isinstance(oargs[0], str) and len(oargs[0]) == 5:
        sqlstate = oargs[0]
    # número nativo entre paréntesis, p.ej. "... (229) ..." o "(51221)"
    import re
    m = re.search(r'\((\d{3,6})\)', texto)
    if m:
        try:
            numero = int(m.group(1))
        except ValueError:
            numero = None
    return sqlstate, numero, texto


def traducir_error(exc):
    """Convierte un error de driver/ORM en un error tipado con mensaje SEGURO.
    Registra el detalle técnico en el log, nunca al usuario."""
    sqlstate, numero, _texto = _sqlstate_y_numero(exc)
    _log.warning('SQL inventario error sqlstate=%s numero=%s exc=%r', sqlstate, numero, exc)

    # Permiso / contrato (§8.2): 229 EXECUTE/SELECT denegado, 2812 objeto no encontrado, 297.
    if numero in (229, 230, 297, 2812) or sqlstate in ('42000',):
        return PermisoDenegado(
            'El usuario SQL no tiene permiso sobre el objeto solicitado. '
            'No se modifican permisos desde la aplicación; escalar al DBA.')

    # Conexión / timeout (§8.2): SQLSTATE 08xxx, HYT00/HYT01.
    if (sqlstate and (sqlstate.startswith('08') or sqlstate in ('HYT00', 'HYT01'))):
        return ConexionInventarioError('No se pudo conectar a Test2 (conexión/timeout).')

    return InventarioSqlError('Error al leer el Inventario en SQL Server.')
