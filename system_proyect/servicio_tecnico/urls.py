# <--- hecho por claude code (28-sep-2026): rutas del hub Control y Servicio Técnico.
from django.urls import path

from . import views

app_name = 'servicio_tecnico'

urlpatterns = [
    path('', views.hub, name='hub'),
]
