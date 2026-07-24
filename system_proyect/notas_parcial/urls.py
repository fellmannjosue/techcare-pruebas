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
    path('enviar-pdf-email/',      views.enviar_pdf_email,            name='notas_parcial_enviar_email'),
    path('asignaciones/',          views.asignaciones_vista,           name='notas_parcial_asignaciones'),
    # <--- hecho por claude code: persistir el 'Revisado' del coordinador
    path('marcar-revisado/',       views.marcar_revisado,              name='notas_parcial_marcar_revisado'),
    path('eliminar-asignacion/',   views.eliminar_asignacion,          name='notas_parcial_eliminar_asignacion'),
    path('actualizar-fecha/',      views.actualizar_fecha_limite,      name='notas_parcial_actualizar_fecha'),
    path('precargar-cache/',       views.precargar_cache,              name='notas_parcial_precargar'),
    path('revision-comentarios/',  views.revision_comentarios_view,    name='notas_parcial_revision_comentarios'),
    path('eliminar-comentario/',   views.eliminar_comentario,          name='notas_parcial_eliminar_comentario'),
]
