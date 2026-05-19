from django.urls import path
from . import views

app_name = 'finanzas_personales'

urlpatterns = [
    path('', views.index, name='index'),

    # Estado completo
    path('api/data/', views.api_data, name='api_data'),

    # Categorías
    path('api/categorias/', views.api_categoria_crear, name='api_categoria_crear'),
    path('api/categorias/<int:pk>/', views.api_categoria_detalle, name='api_categoria_detalle'),

    # Transacciones
    path('api/transacciones/', views.api_transaccion_crear, name='api_transaccion_crear'),
    path('api/transacciones/<int:pk>/', views.api_transaccion_detalle, name='api_transaccion_detalle'),

    # Pendientes
    path('api/pendientes/', views.api_pendiente_crear, name='api_pendiente_crear'),
    path('api/pendientes/<int:pk>/', views.api_pendiente_eliminar, name='api_pendiente_eliminar'),
    path('api/pendientes/<int:pk>/confirmar/', views.api_pendiente_confirmar, name='api_pendiente_confirmar'),

    # Entradas rápidas
    path('api/quick-entries/', views.api_qe_crear, name='api_qe_crear'),
    path('api/quick-entries/<int:pk>/', views.api_qe_eliminar, name='api_qe_eliminar'),
    path('api/quick-entries/<int:pk>/ejecutar/', views.api_qe_ejecutar, name='api_qe_ejecutar'),

    # Presupuestos
    path('api/presupuestos/', views.api_presupuesto_crear, name='api_presupuesto_crear'),
    path('api/presupuestos/<int:pk>/', views.api_presupuesto_eliminar, name='api_presupuesto_eliminar'),

    # Metas de ahorro
    path('api/metas/', views.api_meta_crear, name='api_meta_crear'),
    path('api/metas/<int:pk>/', views.api_meta_detalle, name='api_meta_detalle'),
    path('api/metas/<int:pk>/ahorrar/', views.api_meta_ahorrar, name='api_meta_ahorrar'),

    # Configuración
    path('api/configuracion/', views.api_configuracion, name='api_configuracion'),

    # Respaldo
    path('api/importar/', views.api_importar, name='api_importar'),
    path('api/limpiar/', views.api_limpiar, name='api_limpiar'),
]
