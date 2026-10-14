from django.urls import path

from . import views

app_name = 'moodle_upload'

urlpatterns = [
    path('', views.index, name='index'),
    path('conexion/', views.guardar_conexion, name='conexion'),
    path('publicar/', views.publicar, name='publicar'),
    path('cursos.json', views.cursos_json, name='cursos_json'),
    path('agenda/<int:pk>/publicar/', views.publicar_agenda, name='publicar_agenda'),
]
