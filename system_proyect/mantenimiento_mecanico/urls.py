from django.urls import path

from . import views

app_name = 'mantenimiento_mecanico'

urlpatterns = [
    path('', views.index, name='index'),
    path('maquinaria/add/', views.maquinaria_add, name='maquinaria_add'),
    path('entrega/<int:pk>/pdf/', views.entrega_pdf, name='entrega_pdf'),
    path('entrega/<int:pk>/editar/', views.entrega_editar, name='entrega_editar'),
    path('entrega/<int:pk>/comentario/', views.comentario_crear, name='comentario_crear'),
    path('reporte-general/<slug:fmt>/', views.reporte_general, name='reporte_general'),
    path('<slug:clave>/', views.pagina, name='pagina'),
    path('<slug:clave>/entrega/nueva/', views.entrega_crear, name='entrega_crear'),
    path('<slug:clave>/entrada/nueva/', views.entrada_crear, name='entrada_crear'),
    path('<slug:clave>/lectura/nueva/', views.lectura_crear, name='lectura_crear'),   # <--- hecho por claude code (14-oct-2026)
    path('<slug:clave>/limpieza/nueva/', views.limpieza_crear, name='limpieza_crear'),   # <--- hecho por claude code (19-oct-2026)
    path('limpieza/<int:pk>/pdf/', views.limpieza_pdf, name='limpieza_pdf'),
    path('<slug:clave>/config/', views.insumo_config, name='insumo_config'),
    path('<slug:clave>/reporte/<slug:fmt>/', views.reporte_tabla, name='reporte_tabla'),
]
