from django.urls import path
from . import views

app_name = 'agendas'

urlpatterns = [
    path('form/',              views.form_agenda,             name='form_agenda'),
    path('historial/',         views.historial_maestro,       name='historial_maestro'),
    path('coordinador/',       views.dashboard_coordinador,   name='dashboard_coordinador'),
    path('bloqueo/guardar/',   views.bloqueo_config_guardar,  name='bloqueo_config_guardar'),
    path('modo/toggle/',       views.toggle_modo_maestro,     name='toggle_modo'),
    path('<int:pk>/editar/',   views.editar_agenda,           name='editar_agenda'),
    path('<int:pk>/pptx/',     views.descargar_pptx_agenda,   name='descargar_pptx'),
    path('imagen/subir/',      views.subir_imagen,            name='subir_imagen'),
    path('imagen/<int:pk>/eliminar/', views.eliminar_imagen,  name='eliminar_imagen'),
    path('<int:pk>/eliminar/',        views.eliminar_agenda,   name='eliminar_agenda'),
]
