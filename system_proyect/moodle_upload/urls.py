from django.urls import path

from . import views

app_name = 'moodle_upload'

urlpatterns = [
    path('', views.index, name='index'),
    path('conexion/', views.guardar_conexion, name='conexion'),
    path('publicar/', views.publicar, name='publicar'),
]
