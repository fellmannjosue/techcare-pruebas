# <--- hecho por claude code (26-oct-2026): rutas del asistente IA
from django.urls import path

from . import views

app_name = 'asistente'

urlpatterns = [
    path('chat/', views.chat, name='chat'),
    path('redactar/', views.redactar, name='redactar'),   # <--- hecho por claude code (03-nov-2026): mejorar/corregir comentarios
]
