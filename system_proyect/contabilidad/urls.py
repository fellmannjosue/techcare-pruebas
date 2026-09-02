# <--- hecho por claude code: rutas del módulo Contabilidad.
from django.urls import path

from . import views
from . import views_inventario_sql as views_sql  # <--- hecho por claude code: lecturas SQL Server (Test2)

app_name = 'contabilidad'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # <--- hecho por claude code: hub de Inventario (por rol) + Venta (rol A) + Auditoría (rol C)
    path('inventario/dashboard/', views.inventario_dashboard, name='inventario_dashboard'),
    path('inventario/venta/nueva/', views.venta_nueva, name='venta_nueva'),
    path('inventario/auditoria/', views.auditoria_lista, name='auditoria_lista'),

    # <--- hecho por claude code: Regalías de proveedores (informe APARTE, no se contabiliza)
    path('regalias/', views.regalias_lista, name='regalias_lista'),
    path('regalias/nueva/', views.regalia_nueva, name='regalia_nueva'),

    # Inventario de uniformes (FASE 2)
    path('inventario/', views.inventario_lista, name='inventario_lista'),
    path('inventario/reporte/', views.inventario_reporte, name='inventario_reporte'),
    path('inventario/producto/nuevo/', views.producto_nuevo, name='producto_nuevo'),
    path('inventario/producto/<int:pk>/', views.producto_kardex, name='producto_kardex'),
    path('inventario/producto/<int:pk>/editar/', views.producto_editar, name='producto_editar'),
    # <--- hecho por claude code: form dedicado de precios (proveedor + venta, ISV 15% auto)
    path('inventario/producto/<int:pk>/precio/', views.producto_precio, name='producto_precio'),
    path('inventario/producto/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('inventario/movimiento/nuevo/', views.movimiento_nuevo, name='movimiento_nuevo'),
    path('inventario/catalogo/agregar/', views.catalogo_agregar, name='catalogo_agregar'),

    # Proveedores (FASE 2.1)
    path('inventario/proveedores/', views.proveedor_lista, name='proveedor_lista'),
    path('inventario/proveedores/nuevo/', views.proveedor_nuevo, name='proveedor_nuevo'),
    path('inventario/proveedores/<int:pk>/', views.proveedor_detalle, name='proveedor_detalle'),
    path('inventario/proveedores/<int:pk>/editar/', views.proveedor_editar, name='proveedor_editar'),
    path('inventario/proveedores/<int:pk>/eliminar/', views.proveedor_eliminar, name='proveedor_eliminar'),

    # Compras (FASE 2.1)
    path('inventario/compras/', views.compra_lista, name='compra_lista'),
    path('inventario/compras/nueva/', views.compra_nueva, name='compra_nueva'),
    path('inventario/compras/<int:pk>/', views.compra_detalle, name='compra_detalle'),
    path('inventario/compras/<int:pk>/confirmar/', views.compra_confirmar, name='compra_confirmar'),
    path('inventario/compras/<int:pk>/anular/', views.compra_anular, name='compra_anular'),
    path('inventario/compras/<int:pk>/eliminar/', views.compra_eliminar, name='compra_eliminar'),

    # <--- hecho por claude code: Inventario institucional en SQL Server (Test2) — SOLO LECTURA
    path('inventario/sql/', views_sql.inv_sql_estado, name='inv_sql_estado'),
    path('inventario/sql/articulos/', views_sql.inv_sql_articulos, name='inv_sql_articulos'),
    path('inventario/sql/articulos/<int:articulo_id>/kardex/', views_sql.inv_sql_kardex, name='inv_sql_kardex'),
    path('inventario/sql/proveedores/', views_sql.inv_sql_proveedores, name='inv_sql_proveedores'),
]
