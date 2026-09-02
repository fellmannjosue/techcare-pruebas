# <--- hecho por claude code: rutas del módulo de desarrollo.
from django.urls import path
from . import views

app_name = 'desarrollo'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Roadmap / Mis requerimientos (FASE 5)
    path('roadmap/', views.roadmap, name='roadmap'),
    path('mis-requerimientos/', views.mis_requerimientos, name='mis_requerimientos'),

    # Requerimientos (FASE 2)
    path('requerimientos/', views.requerimiento_list, name='req_list'),
    path('requerimientos/exportar/', views.requerimiento_exportar, name='req_exportar'),
    path('requerimientos/nuevo/', views.requerimiento_nuevo, name='req_nuevo'),
    path('solicitantes/agregar/', views.solicitante_agregar, name='solicitante_agregar'),
    path('catalogo/agregar/', views.catalogo_agregar, name='catalogo_agregar'),
    path('requerimientos/<str:codigo>/', views.requerimiento_detail, name='req_detail'),
    path('requerimientos/<str:codigo>/editar/', views.requerimiento_editar, name='req_editar'),
    path('requerimientos/<str:codigo>/comentar/', views.comentario_agregar, name='req_comentar'),
    path('requerimientos/<str:codigo>/adjuntar/', views.adjunto_subir, name='req_adjuntar'),
    path('requerimientos/<str:codigo>/convertir/', views.requerimiento_convertir, name='req_convertir'),
    path('requerimientos/<str:codigo>/mover/', views.requerimiento_mover, name='req_mover'),
    path('adjuntos/<int:pk>/eliminar/', views.adjunto_eliminar, name='adjunto_eliminar'),

    # Proyectos (FASE 3)
    path('proyectos/', views.proyecto_list, name='proy_list'),
    path('proyectos/nuevo/', views.proyecto_nuevo, name='proy_nuevo'),
    path('proyectos/<str:codigo>/', views.proyecto_detail, name='proy_detail'),
    path('proyectos/<str:codigo>/editar/', views.proyecto_editar, name='proy_editar'),
]
