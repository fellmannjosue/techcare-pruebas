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
]
