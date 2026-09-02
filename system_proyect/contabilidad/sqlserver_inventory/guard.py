# <--- hecho por claude code: guard de ambiente/rol. Se ejecuta ANTES de cualquier lectura.
# La app se niega a operar si la base no es Test2 o el usuario no es miembro del rol de
# desarrollo. Es SOLO un SELECT de funciones de sistema (no toca dbo.tblInv*).
from . import config
from .errors import AmbienteInvalido

# IS_ROLEMEMBER se parametriza con el nombre del rol (no se concatena).
SQL_IDENTIDAD = (
    "SELECT DB_NAME() AS Base, "
    "ORIGINAL_LOGIN() AS LoginOriginal, "
    "SUSER_SNAME() AS UsuarioSql, "
    "IS_ROLEMEMBER(%s) AS EsDesarrollo"
)


def identidad(cursor):
    """Devuelve dict con base/login/usuario_sql/es_desarrollo. No lanza por rol/base."""
    cursor.execute(SQL_IDENTIDAD, [config.ROL_DESARROLLO])
    row = cursor.fetchone()
    cols = [c[0] for c in cursor.description]
    d = dict(zip(cols, row))
    es_dev = d.get('EsDesarrollo')
    return {
        'base': d.get('Base'),
        'login': d.get('LoginOriginal'),
        'usuario_sql': d.get('UsuarioSql'),
        'es_desarrollo': (int(es_dev) if es_dev is not None else None),
    }


def verificar_ambiente(cursor):
    """Corre el guard y LANZA AmbienteInvalido si no es Test2 o el usuario no está en el rol.
    Devuelve el dict de identidad si todo está OK."""
    ident = identidad(cursor)
    if ident['base'] != config.DB_ESPERADA:
        raise AmbienteInvalido(
            f"CONEXIÓN BLOQUEADA: se requiere la base '{config.DB_ESPERADA}'.")
    if ident['es_desarrollo'] != 1:
        raise AmbienteInvalido(
            f"CONEXIÓN BLOQUEADA: el usuario SQL no es miembro de "
            f"'{config.ROL_DESARROLLO}'. Consultas de Inventario detenidas.")
    return ident
