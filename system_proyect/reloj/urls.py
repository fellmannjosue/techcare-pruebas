from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='reloj_dashboard'),

    # Reportes
    path('reporte/', views.reporte, name='reloj_reporte'),
    path('reporte/nota/', views.reporte_nota_ajax, name='reloj_reporte_nota_ajax'),
    path('reporte/comentario/add/', views.comentario_add_ajax, name='reloj_comentario_add'),
    path('reporte/comentario/<int:pk>/delete/', views.comentario_delete_ajax, name='reloj_comentario_delete'),
    path('pdf/', views.exportar_pdf, name='reloj_exportar_pdf'),

    # Gráfica (pie) + detalle para modal
    path('grafica/', views.grafica, name='reloj_grafica'),
    path('grafica/detalle/', views.grafica_detalle, name='reloj_grafica_detalle'),

    # Diagnóstico conexión
    path('test_sql/', views.test_sqlserver_connection, name='test_sqlserver_connection'),

    # ─────────────────────────────────────────────
    # Tiempo por hora + autorización de tiempo extra
    # ─────────────────────────────────────────────
    path('overtime/authorize/', views.overtime_authorize, name='reloj_overtime_authorize'),

    # ─────────────────────────────────────────────
    # Gestión de PLANTILLAS y REGLAS
    # ─────────────────────────────────────────────
    path('plantillas/', views.plantilla_list, name='reloj_plantilla_list'),
    path('plantillas/nueva/', views.plantilla_edit, name='reloj_plantilla_new'),
    path('plantillas/<int:pk>/', views.plantilla_edit, name='reloj_plantilla_edit'),
    path('plantillas/<int:template_pk>/regla/nueva/', views.regla_add, name='reloj_regla_add'),
    path('regla/<int:pk>/', views.regla_edit, name='reloj_regla_edit'),

    # ─────────────────────────────────────────────
    # Gestión de Horarios por Empleado (ASIGNACIONES)
    # (Se mantienen los nombres para no romper enlaces previos)
    # ─────────────────────────────────────────────
    path('horarios/', views.horarios_list, name='horarios_list'),
    path('horarios/agregar/', views.horarios_add, name='horarios_add'),
    path('horarios/editar/<int:pk>/', views.horarios_edit, name='horarios_edit'),

    # ─────────────────────────────────────────────
    # Feriados
    # ─────────────────────────────────────────────
    path('feriados/', views.feriados_list, name='reloj_feriados_list'),
    path('feriados/nuevo/', views.feriado_new, name='reloj_feriado_new'),
    path('feriados/<int:pk>/editar/', views.feriado_edit, name='reloj_feriado_edit'),
    path('feriados/<int:pk>/eliminar/', views.feriado_delete, name='reloj_feriado_delete'),
    path('feriados/<int:pk>/asignacion/bulk/', views.feriado_asignacion_bulk, name='reloj_feriado_asignacion_bulk'),

    # ─────────────────────────────────────────────
    # Sábados especiales
    # ─────────────────────────────────────────────
    path('sabados/', views.sabados_list, name='reloj_sabados_list'),
    path('sabados/nuevo/', views.sabado_new, name='reloj_sabado_new'),
    path('sabados/<int:pk>/editar/', views.sabado_edit, name='reloj_sabado_edit'),
    path('sabados/<int:pk>/eliminar/', views.sabado_delete, name='reloj_sabado_delete'),
    path('sabados/<int:pk>/asignacion/bulk/', views.sabado_asignacion_bulk, name='reloj_sabado_asignacion_bulk'),

    # ─────────────────────────────────────────────
    # Tiempo compensatorio (capturas)
    # ─────────────────────────────────────────────
    path('compensatorio/', views.compensatorio_list, name='reloj_compensatorio_list'),
    path('compensatorio/set-extra/', views.compensatorio_list_set_extra, name='reloj_compensatorio_set_extra'),
    path('compensatorio/nuevo/', views.compensatorio_new, name='reloj_compensatorio_new'),
    path('compensatorio/<int:pk>/editar/', views.compensatorio_edit, name='reloj_compensatorio_edit'),
    path('compensatorio/<int:pk>/eliminar/', views.compensatorio_delete, name='reloj_compensatorio_delete'),
    path('compensatorio/<int:pk>/autorizar/', views.compensatorio_authorize, name='reloj_compensatorio_authorize'),


    # ─────────────────────────────────────────────
    # Cálculo de fecha fin compensatorio
    # ─────────────────────────────────────────────
    path('compensatorio-calculo/', views.compensatorio_calculo_list, name='reloj_compensatorio_calculo_list'),
    path('compensatorio-calculo/nuevo/', views.compensatorio_calculo_new, name='reloj_compensatorio_calculo_new'),
    path('compensatorio-calculo/<int:pk>/editar/', views.compensatorio_calculo_edit, name='reloj_compensatorio_calculo_edit'),
    path('compensatorio-calculo/<int:pk>/eliminar/', views.compensatorio_calculo_delete, name='reloj_compensatorio_calculo_delete'),
    path('compensatorio-calculo/<int:pk>/set-min-dia/', views.compensatorio_calculo_set_min_dia, name='reloj_compensatorio_calculo_set_min_dia'),
    path('compensatorio-calculo/<int:pk>/set-compensado/', views.compensatorio_calculo_set_compensado, name='reloj_compensatorio_calculo_set_compensado'),
    path('compensatorio-calculo/<int:pk>/set-tiempo-extra/', views.compensatorio_calculo_set_tiempo_extra, name='reloj_compensatorio_calculo_set_tiempo_extra'),

    # Hook Google Forms (POST Apps Script)
    path('google/compensatorio/ingresar/', views.compensatorio_google_hook, name='compensatorio_google_hook'),
    path('google/compensatorio/empleados/', views.compensatorio_employees_list, name='compensatorio_employees_list'),


    # ─────────────────────────────────────────────
    # Permisos
    # ─────────────────────────────────────────────
    path('permisos/', views.permisos_list, name='reloj_permisos_list'),
    path('permisos/nuevo/', views.permiso_new, name='reloj_permiso_new'),
    path('permisos/<int:pk>/editar/', views.permiso_edit, name='reloj_permiso_edit'),
    path('permisos/<int:pk>/aprobar/', views.permiso_approve, name='reloj_permiso_approve'),
    path('permisos/<int:pk>/eliminar/', views.permiso_delete, name='reloj_permiso_delete'),

    # ─────────────────────────────────────────────
    # Reporte mensual de permisos
    # ─────────────────────────────────────────────
    path('permisos/reporte/', views.permiso_reporte_list, name='reloj_permiso_reporte'),
    path('permisos/reporte/set-campo/', views.permiso_reporte_set_campo, name='reloj_permiso_reporte_set_campo'),
    path('permisos/reporte/save/', views.permiso_reporte_save, name='reloj_permiso_reporte_save'),
    path('permisos/reporte/<int:pk>/delete/', views.permiso_reporte_delete, name='reloj_permiso_reporte_delete'),
    path('permisos/reporte/list-mes/', views.permiso_list_mes, name='reloj_permiso_list_mes'),
    path('permisos/reporte/rebaja-toggle/', views.permiso_rebaja_toggle, name='reloj_permiso_rebaja_toggle'),

    # Vacaciones
    path('vacaciones/', views.vacaciones_list, name='reloj_vacaciones_list'),
    path('vacaciones/config/save/', views.vacacion_config_save, name='reloj_vacacion_config_save'),
    path('vacaciones/balance/', views.vacacion_balance, name='reloj_vacacion_balance'),
    path('vacaciones/importar/', views.vacaciones_importar, name='reloj_vacaciones_importar'),
]
