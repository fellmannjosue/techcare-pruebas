from django.urls import path
from . import views

app_name = 'cfp'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('taller/<str:taller>/', views.taller, name='taller'),

    path('ejecucion/guardar/', views.ejecucion_guardar, name='ejecucion_guardar'),
    path('ejecucion/<int:pk>/', views.ejecucion_detalle, name='ejecucion_detalle'),
    path('ejecucion/<int:pk>/eliminar/', views.ejecucion_eliminar, name='ejecucion_eliminar'),

    path('informe/<int:pk>/', views.informe_form, name='informe_form'),
    path('informe/<int:pk>/pdf/', views.informe_pdf, name='informe_pdf'),
]
