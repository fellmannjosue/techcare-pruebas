# datashow/urls.py
# <--- hecho por claude code (02-nov-2026)
from django.urls import path
from . import views

app_name = 'datashow'

urlpatterns = [
    path('', views.index, name='index'),
    path('crear/', views.crear, name='crear'),
    path('<int:pk>/revisar/', views.revisar, name='revisar'),
    path('<int:pk>/cancelar/', views.cancelar, name='cancelar'),
]
