from django.urls import path
from . import views

urlpatterns = [
    # Convocatoria de tutorías (Bilingüe)  <--- hecho por claude code
    path('tutorias/grado/', views.convocatoria_grado, name='convocatoria_grado'),
    path('tutorias/marca/', views.convocatoria_marca_toggle, name='convocatoria_marca_toggle'),
    path('tutorias/cartas-pdf/', views.convocatoria_cartas_pdf, name='convocatoria_cartas_pdf'),
    path('tutorias/tabla-pdf/', views.convocatoria_tabla_pdf, name='convocatoria_tabla_pdf'),
    path('tutorias/nueva/', views.convocatoria_nueva, name='convocatoria_nueva'),
    path('tutorias/<int:pk>/editar/', views.convocatoria_nueva, name='convocatoria_editar'),
    path('tutorias/<int:pk>/eliminar/', views.convocatoria_eliminar, name='convocatoria_eliminar'),
    path('tutorias/horario-grado/', views.convocatoria_horario_ajax, name='convocatoria_horario_ajax'),
    path('tutorias/<int:pk>/pdf/', views.convocatoria_pdf, name='convocatoria_pdf'),
    path('tutorias/coordinador/', views.convocatorias_coordinador, name='convocatorias_coordinador'),
    path('tutorias/firma/', views.convocatoria_firma_guardar, name='convocatoria_firma_guardar'),
    path('tutorias/horario/', views.tutoria_horario_config, name='tutoria_horario_config'),

    # Dashboards
    path('dashboard/maestro/', views.dashboard_maestro, name='dashboard_maestro'),
    path('coordinador/<str:area>/', views.dashboard_coordinador, name='dashboard_coordinador'),
    path('coordinador/historial/alumno/<str:alumno_id>/', views.historial_alumno_coordinador, name='historial_alumno_coordinador'),

    # Dashboards individuales por coordinador bilingüe
    path('coordinador/bl/c1/', views.dashboard_c1, name='dashboard_c1'),
    path('coordinador/bl/c2/', views.dashboard_c2, name='dashboard_c2'),
    path('coordinador/bl/c3/', views.dashboard_c3, name='dashboard_c3'),
    path('coordinador/bl/c4/', views.dashboard_c4, name='dashboard_c4'),
    path('coordinador/bl/progress/', views.dashboard_coordi_bl, name='dashboard_coordi_bl'),

    # Formularios de reportes
    path('reporte/conductual/bilingue/', views.reporte_conductual_bilingue, name='reporte_conductual_bilingue'),
    path('reporte/conductual/colegio/', views.reporte_conductual_colegio, name='reporte_conductual_colegio'),
    path('reporte/informativo/bilingue/', views.reporte_informativo_bilingue, name='reporte_informativo_bilingue'),
    path('reporte/informativo/colegio/', views.reporte_informativo_colegio, name='reporte_informativo_colegio'),
    path('progress_report/bilingue/', views.progress_report_bilingue, name='progress_report_bilingue'),

    # Historial
    path('historial/maestro/bilingue/', views.historial_maestro_bilingue, name='historial_maestro_bilingue'),
    path('historial/maestro/colegio/', views.historial_maestro_colegio, name='historial_maestro_colegio'),
    path('reenviar-reportes/', views.reenviar_reportes_coordinadores, name='reenviar_reportes_coordinadores'),

    # -------------------------------
    # EDICIÓN Y PDF AGRUPADOS
    # -------------------------------

    # --- CONDUCTUAL ---
    path('reporte-conductual/<int:pk>/eliminar/', views.eliminar_reporte_conductual, name='eliminar_reporte_conductual'),
    path('reporte-conductual/<int:pk>/editar/', views.editar_reporte_conductual, name='editar_reporte_conductual'),
    path('reporte-conductual/<int:pk>/pdf/', views.descargar_pdf_conductual, name='descargar_pdf_conductual'),
    path('reporte-conductual/<int:pk>/pdf-3strikes/', views.descargar_pdf_conductual_3_strikes, name='descargar_pdf_conductual_3_strikes'),
    # --- INFORMATIVO ---
    path('reporte-informativo/<int:pk>/eliminar/', views.eliminar_reporte_informativo, name='eliminar_reporte_informativo'),
    path('reportes/bulk-eliminar/', views.bulk_eliminar_reportes, name='bulk_eliminar_reportes'),
    path('reporte-informativo/<int:pk>/editar/', views.editar_reporte_informativo, name='editar_reporte_informativo'),
    path('reporte-informativo/<int:pk>/pdf/', views.descargar_pdf_informativo, name='descargar_pdf_informativo'),

        # --- PROGRESS ---
    path('progress-report/<int:pk>/editar/', views.editar_progress_report, name='editar_progress_report'),
    path('progress-report/<int:pk>/pdf/', views.descargar_pdf_progress, name='descargar_pdf_progress'),


    path('set-coord/', views.set_coord_reporte, name='set_coord_reporte'),
    path('reporte/editar-ajax/', views.editar_reporte_ajax, name='editar_reporte_ajax'),

    # --- EVIDENCIAS ---  <--- hecho por claude code
    # Recibe el POST del modal del dashboard coordinador.
    # Acepta imagen + comentario + tipo + reporte_id y guarda EvidenciaReporte.
    path('evidencia/subir/', views.subir_evidencia, name='subir_evidencia'),
    path('evidencia/<int:pk>/eliminar/', views.eliminar_evidencia, name='eliminar_evidencia'),
    path('descargar/zip/', views.descargar_zip_reportes, name='descargar_zip_reportes'),
    path('historial-alumnado/<str:area>/', views.historial_alumnado, name='historial_alumnado'),
    path('periodos/guardar/', views.periodo_conducta_save, name='periodo_conducta_save'),
    path('periodos/<int:pk>/eliminar/', views.periodo_conducta_delete, name='periodo_conducta_delete'),
    path('directorio/', views.directorio_telefonos, name='directorio_telefonos'),
    path('coordinador/bl/materias/', views.materias_docentes_bl, name='materias_docentes_bl'),
    path('coordinador/bl/materias/crear/', views.materia_bl_create, name='materia_bl_create'),
    path('coordinador/bl/materias/<int:pk>/editar/', views.materia_bl_update, name='materia_bl_update'),
    path('coordinador/bl/materias/<int:pk>/eliminar/', views.materia_bl_delete, name='materia_bl_delete'),
]
