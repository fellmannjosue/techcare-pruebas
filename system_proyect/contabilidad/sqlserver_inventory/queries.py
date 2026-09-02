# <--- hecho por claude code: consultas de SOLO LECTURA (SELECT parametrizado) sobre los
# objetos autorizados. NADA de INSERT/UPDATE/DELETE, SP, TVP ni núcleo privado.
# Existencia y costo promedio se LEEN tal cual (no se recalculan en Python).
from . import dto
from .connection import leer, filas_como_dicts


def _map(sql, params, clase):
    cols, filas = leer(sql, params)
    return [clase.from_dict(d) for d in filas_como_dicts(cols, filas)]


# 1) Categorías ─ dbo.tblInvCategoria
def categorias():
    sql = ("SELECT CategoriaID, Codigo, Nombre, Activo, RV "
           "FROM dbo.tblInvCategoria ORDER BY Codigo")
    return _map(sql, [], dto.Categoria)


# 2) Unidades de medida ─ dbo.tblInvUnidadMedida
def unidades():
    sql = ("SELECT UnidadMedidaID, Codigo, Nombre, DecimalesCantidad, Activo, RV "
           "FROM dbo.tblInvUnidadMedida ORDER BY Codigo")
    return _map(sql, [], dto.Unidad)


# 3) Almacenes ─ dbo.tblInvAlmacen
def almacenes():
    sql = ("SELECT AlmacenID, Codigo, Nombre, EsPredeterminado, Activo, RV "
           "FROM dbo.tblInvAlmacen ORDER BY Codigo")
    return _map(sql, [], dto.Almacen)


# 4) Artículos ─ dbo.tblInvArticulo (incluye 7) CostoPromedioActual)
def articulos(filtro=None):
    base = ("SELECT ArticuloID, Codigo, Descripcion, CategoriaID, UnidadMedidaID, "
            "Activo, Observacion, CostoPromedioActual, RV FROM dbo.tblInvArticulo ")
    if filtro:
        patron = '%' + str(filtro) + '%'
        sql = base + "WHERE Codigo LIKE %s OR Descripcion LIKE %s ORDER BY Codigo"
        return _map(sql, [patron, patron], dto.Articulo)
    return _map(base + "ORDER BY Codigo", [], dto.Articulo)


# 6) + 7) Existencia por almacén y costo institucional (consulta canónica §4.2)
def existencias(articulo_id=None):
    sql = (
        "SELECT a.ArticuloID, a.Codigo, a.Descripcion, "
        "al.AlmacenID, al.Codigo AS CodigoAlmacen, "
        "e.CantidadActual, e.UltimoMovimientoID, a.CostoPromedioActual "
        "FROM dbo.tblInvExistencia AS e "
        "JOIN dbo.tblInvArticulo AS a ON a.ArticuloID = e.ArticuloID "
        "JOIN dbo.tblInvAlmacen  AS al ON al.AlmacenID = e.AlmacenID "
        "WHERE (%s IS NULL OR a.ArticuloID = %s) "
        "ORDER BY a.Codigo, al.Codigo")
    return _map(sql, [articulo_id, articulo_id], dto.ExistenciaArticulo)


# 5) Proveedores institucionales ─ dbo.tblComProvd (consulta canónica §4.2)
def proveedores(patron=None):
    like = '%' + (str(patron) if patron else '') + '%'
    sql = ("SELECT ProveedorID, [Compañia] AS Compania, PersonaContacto, RTN, "
           "Telefono, EMail, Direccion, Pais "
           "FROM dbo.tblComProvd "
           "WHERE [Compañia] LIKE %s "
           "ORDER BY [Compañia], ProveedorID")
    return _map(sql, [like], dto.Proveedor)


# 8) Kardex ─ dbo.tblInvMovimiento + dbo.tblInvMovimientoDetalle (consulta canónica §4.2)
def kardex(articulo_id):
    sql = (
        "SELECT m.MovimientoID, m.TipoMovimiento, m.Estado, "
        "m.FechaMovimiento, m.FechaAplicacion, "
        "m.OrigenSistema, m.OrigenTipo, m.OrigenClave, "
        "m.ClaveIdempotencia, m.MovimientoOriginalID, "
        "d.LineaNo, d.ArticuloID, d.OrigenDetalleClave, "
        "d.Cantidad, d.CostoUnitario, d.CostoTotal, "
        "d.ExistenciaAntes, d.ExistenciaDespues, "
        "d.ExistenciaDespues - d.ExistenciaAntes AS CambioCantidad, "
        "d.CostoPromedioAntes, d.CostoPromedioDespues "
        "FROM dbo.tblInvMovimiento AS m "
        "JOIN dbo.tblInvMovimientoDetalle AS d ON d.MovimientoID = m.MovimientoID "
        "WHERE d.ArticuloID = %s "
        "ORDER BY m.FechaAplicacion, m.MovimientoID, d.LineaNo")
    return _map(sql, [articulo_id], dto.MovimientoKardex)
