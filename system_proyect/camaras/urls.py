from django.urls import path
from . import views

app_name = 'camaras'
urlpatterns = [
    path('', views.index, name='index'),
]
