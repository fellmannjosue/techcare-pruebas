# <--- hecho por claude code: Ingreso de Notas — URLs
from django.urls import path
from . import views

app_name = 'ingresos_notas'

urlpatterns = [
    # ── Formulario 1: Notas ──────────────────────────────────────────────────
    path('',                views.index,       name='index'),

    # ── APIs de los desplegables en cascada y la rejilla ─────────────────────
    path('api/clases/',     views.api_clases,  name='api_clases'),
    path('api/alumnos/',    views.api_alumnos, name='api_alumnos'),
    path('api/guardar/',    views.api_guardar, name='api_guardar'),

    # ── Tab Tareas (Record de Hábitos) ───────────────────────────────────────
    path('api/tareas/',         views.api_tareas,        name='api_tareas'),
    path('api/tareas/guardar/', views.api_tarea_guardar, name='api_tarea_guardar'),

    # ── Tab Asistencias ──────────────────────────────────────────────────────
    path('api/ausencias/',         views.api_ausencias,        name='api_ausencias'),
    path('api/ausencias/guardar/', views.api_ausencia_guardar, name='api_ausencia_guardar'),
]
