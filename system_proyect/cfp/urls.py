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

    # ── Programa 2: Notas CFP ──
    path('programas/', views.programas, name='programas'),
    path('notas/', views.notas_cursos, name='notas_cursos'),
    path('notas/resumen/', views.notas_resumen, name='notas_resumen'),
    path('notas/<int:anio>/<str:curso>/', views.notas_curso, name='notas_curso'),
    path('notas/<int:anio>/<str:curso>/excel/', views.notas_excel, name='notas_excel'),
    path('notas/modulo/guardar/', views.modulo_guardar, name='modulo_guardar'),
    path('notas/modulo/eliminar/', views.modulo_eliminar, name='modulo_eliminar'),
    path('notas/guardar/', views.notas_guardar, name='notas_guardar'),
    path('notas/horas/guardar/', views.horas_guardar, name='horas_guardar'),
]
