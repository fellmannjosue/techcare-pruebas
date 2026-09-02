# <--- hecho por claude code: API de SOLO LECTURA que consumen las views de Django.
# Las views NO contienen SQL: llaman a estas funciones. Cada consulta corre el guard
# (Test2 + rol) por debajo (queries -> connection.leer(verificar=True)).
from decimal import Decimal

from . import queries
from . import health as _health


def health():
    """Estado del guard/conexión (no lanza)."""
    return _health.estado()


# ── Catálogos ──
def listar_categorias():
    return queries.categorias()


def listar_unidades():
    return queries.unidades()


def listar_almacenes():
    return queries.almacenes()


# ── Artículos, existencias y costo ──
def listar_articulos(filtro=None):
    return queries.articulos(filtro=filtro)


def existencia_articulo(articulo_id):
    """Existencia por almacén (lista de ExistenciaArticulo) del artículo."""
    return queries.existencias(articulo_id=articulo_id)


def existencia_institucional(articulo_id):
    """SUM(CantidadActual) por artículo (suma de almacenes). Decimal, no float."""
    total = Decimal('0')
    for e in queries.existencias(articulo_id=articulo_id):
        if e.cantidad_actual is not None:
            total += e.cantidad_actual
    return total


def existencias(articulo_id=None):
    """Existencia por almacén de todos los artículos (o de uno)."""
    return queries.existencias(articulo_id=articulo_id)


def costo_articulo(articulo_id):
    """CostoPromedioActual del artículo (leído de dbo.tblInvArticulo, sin recalcular)."""
    arts = queries.articulos()
    for a in arts:
        if a.articulo_id == articulo_id:
            return a.costo_promedio_actual
    return None


# ── Proveedores institucionales ──
def listar_proveedores(patron=None):
    return queries.proveedores(patron=patron)


# ── Kardex ──
def kardex_articulo(articulo_id):
    return queries.kardex(articulo_id)
