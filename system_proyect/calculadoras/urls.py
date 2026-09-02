from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='calculadoras_dashboard'),
    path('divisas/', views.divisas, name='calculadoras_divisas'),
    path('tiempo/', views.tiempo, name='calculadoras_tiempo'),
    path('tiempo/sumar-horas/', views.tiempo_calc, {'calc': 'sumar_horas'}, name='calc_tiempo_sumar_horas'),
    path('tiempo/entre-horas/', views.tiempo_calc, {'calc': 'entre_horas'}, name='calc_tiempo_entre_horas'),
    path('tiempo/horas-dias/', views.tiempo_calc, {'calc': 'horas_dias'}, name='calc_tiempo_horas_dias'),
    path('tiempo/minutos-horas/', views.tiempo_calc, {'calc': 'minutos_horas'}, name='calc_tiempo_minutos_horas'),
    path('tiempo/fecha-fecha/', views.tiempo_calc, {'calc': 'fecha_fecha'}, name='calc_tiempo_fecha_fecha'),
    path('almacenamiento/', views.almacenamiento, name='calculadoras_almacenamiento'),
    path('ip/', views.ip_calculator, name='calculadoras_ip'),
    path('tasa/actualizar/', views.actualizar_tasa, name='calculadoras_tasa_actualizar'),
    path('tasa/auto/', views.fetch_tasas_auto, name='calculadoras_tasa_auto'),
    path('lorem/', views.lorem_ipsum, name='calculadoras_lorem'),
]
