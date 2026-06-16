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
    path('reportes/', views.reportes_pdf, name='reloj_reportes_pdf'),

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
    path('compensatorio-calculo/<int:pk>/set-dias-adeudados/', views.compensatorio_set_dias_adeudados, name='reloj_compensatorio_set_dias_adeudados'),
    path('compensatorio-calculo/<int:pk>/set-factor/', views.compensatorio_set_factor, name='reloj_compensatorio_set_factor'),
    path('compensatorio-calculo/<int:pk>/dias-no-lab/', views.compensatorio_dias_no_lab_get, name='reloj_compensatorio_dias_no_lab_get'),
    path('compensatorio-calculo/<int:pk>/dias-no-lab/add/', views.compensatorio_dias_no_lab_add, name='reloj_compensatorio_dias_no_lab_add'),
    path('compensatorio-dias-no-lab/<int:dia_pk>/delete/', views.compensatorio_dias_no_lab_delete, name='reloj_compensatorio_dias_no_lab_delete'),
    path('compensatorio-calculo/<int:pk>/set-permisos-extras/', views.compensatorio_set_permisos_extras, name='reloj_compensatorio_set_permisos_extras'),
    # Tabs nuevas de compensatorio  <--- hecho por claude code
    path('compensatorio-calculo/<int:pk>/set-horas-adeudadas/', views.compensatorio_set_horas_adeudadas, name='reloj_compensatorio_set_horas_adeudadas'),
    path('compensatorio-calculo/<int:pk>/set-tomado/', views.compensatorio_set_tomado, name='reloj_compensatorio_set_tomado'),
    path('compensatorio-calculo/<int:pk>/tomado/', views.compensatorio_calculo_get_tomado, name='reloj_compensatorio_get_tomado'),
    path('compensatorio-calculo/<int:pk>/tomado-manual/add/', views.compensatorio_tomado_manual_add, name='reloj_compensatorio_tomado_manual_add'),
    path('compensatorio-tomado-manual/<int:tm_pk>/delete/', views.compensatorio_tomado_manual_del, name='reloj_compensatorio_tomado_manual_del'),
    path('compensatorio/emp-buscar/', views.compensatorio_emp_buscar, name='reloj_compensatorio_emp_buscar'),
    path('compensatorio-mensual/add/', views.compensatorio_mensual_add, name='reloj_compensatorio_mensual_add'),
    path('compensatorio-mensual/cell/', views.compensatorio_mensual_cell, name='reloj_compensatorio_mensual_cell'),
    path('compensatorio-mensual/comentario/', views.compensatorio_mensual_comentario, name='reloj_compensatorio_mensual_comentario'),
    path('compensatorio-mensual/detalle/',        views.compensatorio_mensual_detalle_get,    name='reloj_compensatorio_mensual_detalle_get'),
    path('compensatorio-mensual/detalle/add/',    views.compensatorio_mensual_detalle_add,    name='reloj_compensatorio_mensual_detalle_add'),
    path('compensatorio-mensual-detalle/<int:pk>/delete/', views.compensatorio_mensual_detalle_delete, name='reloj_compensatorio_mensual_detalle_delete'),
    path('compensatorio-mensual/<int:pk>/delete/', views.compensatorio_mensual_delete, name='reloj_compensatorio_mensual_delete'),
    path('compensatorio-instructor/add/', views.compensatorio_instructor_add, name='reloj_compensatorio_instructor_add'),
    path('compensatorio-instructor/<int:pk>/set/', views.compensatorio_instructor_set, name='reloj_compensatorio_instructor_set'),
    path('compensatorio-instructor/<int:pk>/delete/', views.compensatorio_instructor_delete, name='reloj_compensatorio_instructor_delete'),
    # Instructor: tiempo extra (entradas) y permiso tomado manual
    path('compensatorio-instructor/<int:pk>/te/',        views.compensatorio_instructor_te_get,    name='reloj_compensatorio_instructor_te_get'),
    path('compensatorio-instructor/<int:pk>/te/add/',    views.compensatorio_instructor_te_add,    name='reloj_compensatorio_instructor_te_add'),
    path('compensatorio-instructor-te/<int:te_pk>/delete/', views.compensatorio_instructor_te_del, name='reloj_compensatorio_instructor_te_del'),
    path('compensatorio-instructor/<int:pk>/tomado/',     views.compensatorio_instructor_tomado_get, name='reloj_compensatorio_instructor_tomado_get'),
    path('compensatorio-instructor/<int:pk>/tomado/add/', views.compensatorio_instructor_tomado_add, name='reloj_compensatorio_instructor_tomado_add'),
    path('compensatorio-instructor-tomado/<int:tm_pk>/delete/', views.compensatorio_instructor_tomado_del, name='reloj_compensatorio_instructor_tomado_del'),
    path('compensatorio-calculo/<int:pk>/tiempo-extra/', views.compensatorio_calculo_get_tiempo_extra, name='reloj_compensatorio_calculo_get_te'),
    path('compensatorio-calculo/<int:pk>/tiempo-extra/add/', views.compensatorio_calculo_add_tiempo_extra_entrada, name='reloj_compensatorio_calculo_add_te'),
    path('compensatorio-te/<int:te_pk>/delete/', views.compensatorio_calculo_del_tiempo_extra_entrada, name='reloj_compensatorio_calculo_del_te'),
    path('compensatorio/emp/<str:emp_code>/tiempo-extra/add/', views.compensatorio_add_tiempo_extra_byemp, name='reloj_add_te_byemp'),

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
    # Receso: ajuste manual de marcas de almuerzo
    path('compensatorio-calculo/receso-ajuste/', views.receso_ajuste_set, name='reloj_receso_ajuste_set'),
    # Maestros por hora: horas por día de la semana
    path('permisos/reporte/maestro-dia/',     views.maestro_dia_get, name='reloj_maestro_dia_get'),
    path('permisos/reporte/maestro-dia/set/', views.maestro_dia_set, name='reloj_maestro_dia_set'),
    path('permisos/reporte/save/', views.permiso_reporte_save, name='reloj_permiso_reporte_save'),
    path('permisos/reporte/<int:pk>/delete/', views.permiso_reporte_delete, name='reloj_permiso_reporte_delete'),
    path('permisos/reporte/list-mes/', views.permiso_list_mes, name='reloj_permiso_list_mes'),
    path('permisos/reporte/rebaja-toggle/', views.permiso_rebaja_toggle, name='reloj_permiso_rebaja_toggle'),

    # ─────────────────────────────────────────────
    # Config global (superuser)
    # ─────────────────────────────────────────────
    path('config/toggle-factor/', views.toggle_factor_visible, name='reloj_toggle_factor_visible'),
    path('config/toggle-horas-diarias/', views.toggle_horas_diarias_visible, name='reloj_toggle_horas_diarias_visible'),

    # ─────────────────────────────────────────────
    # Vigilancia  (modo construcción)
    # ─────────────────────────────────────────────
    path('vigilancia/', views.vigilancia_list, name='reloj_vigilancia_list'),

    # ─────────────────────────────────────────────
    # Instructores CFP  (modo construcción)
    # ─────────────────────────────────────────────
    path('cfp/', views.cfp_list, name='reloj_cfp_list'),

    # ─────────────────────────────────────────────
    # Horas diarias laboradas (AJAX)
    # ─────────────────────────────────────────────
    path('permisos/reporte/set-horas-diarias/', views.permiso_reporte_set_horas_diarias, name='reloj_permiso_set_horas_diarias'),
    # Bono por Asistencia
    path('permisos/bono/reglas/', views.bono_reglas_save, name='reloj_bono_reglas_save'),
    path('permisos/bono/regla-extra/', views.bono_regla_extra_add, name='reloj_bono_regla_extra_add'),
    path('permisos/bono/regla-extra/<int:pk>/eliminar/', views.bono_regla_extra_delete, name='reloj_bono_regla_extra_delete'),
    path('permisos/bono/override/', views.bono_override_set, name='reloj_bono_override_set'),

    # Vacaciones
    path('vacaciones/', views.vacaciones_list, name='reloj_vacaciones_list'),
    path('vacaciones/config/save/', views.vacacion_config_save, name='reloj_vacacion_config_save'),
    path('vacaciones/balance/', views.vacacion_balance, name='reloj_vacacion_balance'),
    path('vacaciones/importar/', views.vacaciones_importar, name='reloj_vacaciones_importar'),
    path('vacaciones/editar-dias/', views.vacacion_editar_dias_usados, name='reloj_vacacion_editar_dias'),
]
