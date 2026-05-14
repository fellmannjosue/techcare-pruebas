from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='calculadoras_dashboard'),
    path('divisas/', views.divisas, name='calculadoras_divisas'),
    path('tiempo/', views.tiempo, name='calculadoras_tiempo'),
    path('almacenamiento/', views.almacenamiento, name='calculadoras_almacenamiento'),
    path('ip/', views.ip_calculator, name='calculadoras_ip'),
    path('tasa/actualizar/', views.actualizar_tasa, name='calculadoras_tasa_actualizar'),
    path('tasa/auto/', views.fetch_tasas_auto, name='calculadoras_tasa_auto'),
]
