# <--- hecho por claude code: Ingreso de Notas — URLs
from django.urls import path
from . import views

app_name = 'ingresos_notas'

urlpatterns = [
    # ── Panel de entrada y una pantalla por formulario ───────────────────────
    # <--- hecho por claude code: antes eran tabs de una sola página
    path('',            views.panel, name='panel'),
    path('notas/',       views.index, {'form': 'notas'},       name='index'),
    path('tareas/',      views.index, {'form': 'tareas'},      name='form_tareas'),
    path('asistencias/', views.index, {'form': 'asistencias'}, name='form_asistencias'),
    path('habitos/',     views.index, {'form': 'habitos'},     name='form_habitos'),

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

    # ── Tab Record de Hábitos ────────────────────────────────────────────────
    path('api/habitos/',         views.api_habitos,        name='api_habitos'),
    path('api/habitos/guardar/', views.api_habito_guardar, name='api_habito_guardar'),
]
