from django.urls import path
from . import views

app_name = 'atencion_padres'
urlpatterns = [
    path('', views.index, name='index'),
]
