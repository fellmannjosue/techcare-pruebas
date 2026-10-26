# <--- hecho por claude code (26-oct-2026): rutas del asistente IA
from django.urls import path

from . import views

app_name = 'asistente'

urlpatterns = [
    path('chat/', views.chat, name='chat'),
]
