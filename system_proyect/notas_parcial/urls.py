from django.urls import path
from . import views

urlpatterns = [
    path('',                   views.notas_index,          name='notas_parcial_index'),
    path('pdf/',               views.generar_pdf,           name='notas_parcial_pdf'),
    path('comentario/',        views.guardar_comentario,    name='notas_parcial_comentario'),
    path('grados/',            views.grados_secciones,      name='notas_parcial_grados'),
    path('coordinador/',       views.coordinador_notas,     name='notas_parcial_coordinador'),
    path('asignar-maestro/',   views.asignar_maestro_view,  name='notas_parcial_asignar'),
    path('maestro/',           views.maestro_notas,         name='notas_parcial_maestro'),
    path('finalizar/',         views.finalizar_revision,    name='notas_parcial_finalizar'),
    path('leer-notificacion/',  views.leer_notificacion,   name='notas_parcial_leer_notif'),
    path('notificaciones-json/', views.notificaciones_json, name='notas_parcial_notif_json'),
    path('enviar-pdf-email/',   views.enviar_pdf_email,    name='notas_parcial_enviar_email'),
]
