# <--- hecho por claude code: vistas de SOLO LECTURA del Inventario institucional (SQL Server, Test2).
# Estas vistas NO contienen SQL: consumen `sqlserver_inventory.services`. Additivas: no tocan
# los modelos/servicios/vistas de escritura del Inventario MySQL existente.
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .utils import puede
from .sqlserver_inventory import services as inv_sql
from .sqlserver_inventory.errors import InventarioSqlError


def _gate(user, codename='ver_inventario'):
    # Reutiliza el sistema de permisos existente (superuser siempre pasa).
    if not puede(user, codename):
        raise PermissionDenied('Acceso restringido al Inventario.')


@login_required
def inv_sql_estado(request):
    """Salud/guard de la conexión + catálogos (categorías/unidades/almacenes)."""
    _gate(request.user)
    st = inv_sql.health()
    ctx = {'st': st, 'categorias': [], 'unidades': [], 'almacenes': [],
           'error': None, 'nav_home_url': '/'}
    if st.get('ok'):
        try:
            ctx['categorias'] = inv_sql.listar_categorias()
            ctx['unidades'] = inv_sql.listar_unidades()
            ctx['almacenes'] = inv_sql.listar_almacenes()
        except InventarioSqlError as e:
            ctx['error'] = str(e)
    return render(request, 'contabilidad/inv_sql_estado.html', ctx)


@login_required
def inv_sql_articulos(request):
    """Artículos + existencia institucional + costo promedio (todo leído de SQL Server)."""
    _gate(request.user)
    st = inv_sql.health()
    q = (request.GET.get('q') or '').strip() or None
    filas, error = [], None
    if st.get('ok'):
        try:
            articulos = inv_sql.listar_articulos(q)
            exist = {}
            for e in inv_sql.existencias():
                exist[e.articulo_id] = exist.get(e.articulo_id, Decimal('0')) + (e.cantidad_actual or Decimal('0'))
            filas = [{'a': a, 'existencia': exist.get(a.articulo_id)} for a in articulos]
        except InventarioSqlError as ex:
            error = str(ex)
    return render(request, 'contabilidad/inv_sql_articulos.html',
                  {'st': st, 'filas': filas, 'q': q or '', 'error': error, 'nav_home_url': '/'})


@login_required
def inv_sql_kardex(request, articulo_id):
    """Kardex institucional de un artículo (movimiento + detalle) y existencia por almacén."""
    _gate(request.user)
    st = inv_sql.health()
    movimientos, existencias, articulo, error = [], [], None, None
    if st.get('ok'):
        try:
            movimientos = inv_sql.kardex_articulo(articulo_id)
            existencias = inv_sql.existencia_articulo(articulo_id)
            for a in inv_sql.listar_articulos():
                if a.articulo_id == articulo_id:
                    articulo = a
                    break
        except InventarioSqlError as ex:
            error = str(ex)
    return render(request, 'contabilidad/inv_sql_kardex.html',
                  {'st': st, 'movimientos': movimientos, 'existencias': existencias,
                   'articulo': articulo, 'articulo_id': articulo_id, 'error': error, 'nav_home_url': '/'})


@login_required
def inv_sql_proveedores(request):
    """Proveedores institucionales (dbo.tblComProvd, solo lectura)."""
    _gate(request.user)
    st = inv_sql.health()
    q = (request.GET.get('q') or '').strip() or None
    proveedores, error = [], None
    if st.get('ok'):
        try:
            proveedores = inv_sql.listar_proveedores(q)
        except InventarioSqlError as ex:
            error = str(ex)
    return render(request, 'contabilidad/inv_sql_proveedores.html',
                  {'st': st, 'proveedores': proveedores, 'q': q or '', 'error': error, 'nav_home_url': '/'})
