# TechCare – Sistema de Gestión Institucional

Sistema web desarrollado en Django para la **Asociación Nuevo Amanecer (ANA)**. Centraliza la gestión de tickets, asistencia, conducta estudiantil, inventario, citas, enfermería, agendas docentes, notas parciales, finanzas y calculadoras internas.

- **URL de producción:** https://servicios.ana-hn.org:437
- **Servidor:** Apache + mod_wsgi
- **Stack:** Django 6.0.5 · Python 3.13.3 · MySQL + SQL Server
- **UI:** Tabler UI v1.0.0-beta19 + Tabler Icons Webfont v3.11.0
- **Admin:** Unfold Admin Theme

---

## Stack técnico

| Componente | Versión |
|-----------|---------|
| Python | 3.13.3 |
| Django | 6.0.5 |
| Tabler UI | 1.0.0-beta19 |
| ReportLab | 4.5.0 |
| WeasyPrint | 68.1 |
| openpyxl | 3.1.5 |
| python-pptx | 1.0.2 |
| Base de datos principal | MySQL (`sponsors2` en `192.168.10.6`) |
| Base de datos secundaria | SQL Server (módulo Reloj y datos alumnos/padres) |

---

## Estructura del repositorio

```
techcare_project/
├── system_proyect/
│   ├── accounts/            # Autenticación, settings, panel principal
│   ├── agendas/             # Agendas semanales docentes
│   ├── calculadoras/        # Calculadoras utilitarias
│   ├── conducta/            # Reportes conductuales y académicos
│   ├── core/                # Context processors y utilidades compartidas
│   ├── enfermeria/          # Atención médica y medicamentos
│   ├── finanzas_personales/ # Finanzas personales internas
│   ├── inventario/          # Inventario de equipos y activos
│   ├── mantenimiento/       # Registro de mantenimientos
│   ├── notas_parcial/       # Notas de mitad de parcial
│   ├── querys/              # Consultas SQL directas
│   ├── reloj/               # Control de asistencia (SQL Server)
│   ├── sponsors/            # Gestión de patrocinadores
│   ├── tickets/             # Tickets de soporte técnico
│   ├── static/              # CSS/JS globales
│   ├── staticfiles/         # Carpeta collectstatic (no editar)
│   └── templates/           # Templates globales (403.html, admin/)
├── django_test/             # Entorno de pruebas
└── datos/                   # Scripts SQL y CSV de ejemplo
```

---

## Templates globales

| Archivo | Descripción |
|---------|-------------|
| `templates/403.html` | Página de error 403 personalizada estilo TechCare (ícono candado, botón inicio/volver) |
| `templates/admin/` | Overrides del panel de administración Unfold |

---

## Módulo: Accounts — Autenticación y Configuración

Login con redirección automática según rol. Sidebar unificado compartido por todos los módulos vía `accounts/templates/accounts/_sidebar.html`.

### Plantillas (`accounts/templates/accounts/`)

| Template | Descripción |
|----------|-------------|
| `login.html` | Formulario de inicio de sesión |
| `register.html` | Registro de usuarios (maestros / staff) |
| `seleccion_rol.html` | Selección de rol cuando el usuario tiene múltiples roles |
| `menu.html` | Panel principal con tarjetas por módulo |
| `settings_base.html` | Layout base de la sección Settings con sidebar de tabs |
| `settings_perfil.html` | Edición de perfil del usuario |
| `settings_notificaciones.html` | Preferencias de notificaciones |
| `settings_usuarios.html` | Listado y gestión de usuarios |
| `settings_usuario_form.html` | Formulario crear/editar usuario |
| `settings_grupos.html` | Listado y gestión de grupos |
| `settings_grupo_form.html` | Formulario crear/editar grupo |
| `settings_actividad.html` | Log de actividad del sistema |
| `settings_logs.html` | Logs de errores del servidor |
| `settings_correos.html` | Configuración de correo SMTP |
| `settings_envio_login.html` | **NUEVO** — Envío masivo de instrucciones de inicio de sesión. Campos editables por sección, lista de destinatarios con checkbox + búsqueda, preview en iframe, envío por correo |
| `settings_coordinadores.html` | Gestión de configuraciones de coordinadores |
| `settings_notificaciones_conducta.html` | Configuración de notificaciones del módulo conducta |
| `settings_roles.html` | Asignación de roles a usuarios |
| `settings_reloj_permisos.html` | Permisos de acceso al módulo Reloj por usuario |
| `_sidebar.html` | Sidebar unificado (incluido en todas las apps) |
| `_user_dropdown.html` | Menú desplegable de usuario (avatar, logout) |
| `_welcome_overlay.html` | Overlay de bienvenida al primer login |
| `_notif_notas_toast.html` | Toast de notificación de notas parciales |
| `password_reset_form.html` | Solicitar reset de contraseña |
| `password_reset_done.html` | Confirmación de envío de email |
| `password_reset_confirm.html` | Nueva contraseña |
| `password_reset_complete.html` | Reset completado |

### Estáticos (`accounts/static/accounts/`)

| Archivo | Descripción |
|---------|-------------|
| `css/login.css` | Estilos de la pantalla de login |
| `css/menu.css` | Estilos del panel principal |
| `css/settings_base.css` | Estilos base de settings |
| `css/settings_correos.css` | Estilos de la sección de correos |
| `css/settings_envio_login.css` | **NUEVO** — Estilos del enviador masivo de instrucciones |
| `css/settings_logs.css` | Estilos de logs |
| `css/welcome_overlay.css` | Estilos del overlay de bienvenida |
| `js/menu.js` | Lógica del panel principal |
| `js/settings_envio_login.js` | **NUEVO** — Checkbox list, búsqueda, preview AJAX, envío con confirmación |
| `js/settings_usuarios.js` | Gestión AJAX de usuarios |
| `js/settings_grupos.js` | Gestión AJAX de grupos |
| `js/settings_coordinadores.js` | Gestión de coordinadores |
| `js/settings_notificaciones_conducta.js` | Configuración de notificaciones |
| `js/settings_reloj_permisos.js` | Permisos reloj por usuario |
| `js/settings_roles.js` | Asignación de roles |
| `js/settings_logs.js` | Visor de logs con filtros |
| `js/settings_actividad.js` | Log de actividad |
| `js/notifications.js` | Notificaciones en tiempo real |
| `js/notif_notas_toast.js` | Toast de notas parciales |
| `js/sidebar.js` | Comportamiento del sidebar |
| `js/user_dropdown.js` | Menú de usuario |
| `js/welcome_overlay.js` | Overlay de bienvenida |

### URLs (`/accounts/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `login/` | `login` | Inicio de sesión |
| `logout/` | `logout` | Cierre de sesión |
| `register/` | `register_maestro` | Registro de usuarios |
| `menu/` | `menu` | Panel principal |
| `seleccion-rol/` | `seleccion_rol` | Selección de rol |
| `aplicar-rol/<rol>/` | `aplicar_rol` | Aplicar rol seleccionado |
| `settings/` | `settings_perfil` | Perfil |
| `settings/notificaciones/` | `settings_notificaciones` | Notificaciones |
| `settings/usuarios/` | `settings_usuarios` | Usuarios |
| `settings/usuarios/crear/` | `settings_usuario_crear` | Crear usuario |
| `settings/usuarios/<pk>/editar/` | `settings_usuario_editar` | Editar usuario |
| `settings/usuarios/<pk>/eliminar/` | `settings_usuario_eliminar` | Eliminar usuario |
| `settings/grupos/` | `settings_grupos` | Grupos |
| `settings/grupos/crear/` | `settings_grupo_crear` | Crear grupo |
| `settings/grupos/<pk>/editar/` | `settings_grupo_editar` | Editar grupo |
| `settings/grupos/<pk>/eliminar/` | `settings_grupo_eliminar` | Eliminar grupo |
| `settings/actividad/` | `settings_actividad` | Actividad del sistema |
| `settings/logs/` | `settings_logs` | Logs del servidor |
| `settings/correos/` | `settings_correos` | Config. correo |
| `settings/correos/envio-login/` | `settings_envio_login` | **NUEVO** — Enviar instrucciones de login |
| `settings/correos/envio-login/preview/` | `settings_envio_login_preview` | **NUEVO** — Preview del correo (AJAX) |
| `settings/conducta/coordinadores/` | `settings_coordinadores` | Coordinadores conducta |
| `settings/conducta/notificaciones/` | `settings_notificaciones_conducta` | Notificaciones conducta |
| `settings/conducta/roles/` | `settings_roles` | Roles |
| `settings/reloj/permisos/` | `settings_reloj_permisos` | Permisos reloj |
| `password_reset/` | — | Recuperar contraseña |

### Roles y grupos

| Grupo | Acceso |
|-------|--------|
| `maestros_bilingue` | Dashboard maestro BL |
| `maestros_colegio` | Dashboard maestro Colegio |
| `coordinador_bilingue` | Dashboard coordinador BL + enfermería + agendas |
| `coord_progress_bl` | **NUEVO** — Coordinador Progress BL + acceso a agendas |
| `coordinadores_colegio` / `coordinadores` | Dashboard coordinador Colegio |
| `administracion` | Acceso administrativo |
| `tecnicos` | Dashboard de tickets |
| Superusuario | Acceso completo + herramientas admin |

---

## Módulo: Conducta — Reportes Académicos y de Conducta

Sistema de reportes para maestros con revisión por coordinadores. Áreas: Bilingüe y Colegio/CFP (flujos independientes).

### Tipos de reportes

| Tipo | Descripción |
|------|-------------|
| Informativo Académico | Comunicación académica general |
| Informativo Conductual | Información conductual sin acción formal |
| Conductual | Falta de conducta — genera PDF individual y PDF "3 Strikes" |
| Progress Report | Seguimiento académico (solo área bilingüe) |

### Plantillas (`conducta/templates/conducta/`)

| Template | Descripción |
|----------|-------------|
| `base_conducta.html` | Layout base del módulo |
| `dashboard_maestros.html` | Dashboard del maestro con tabs por área |
| `dashboard_coordinador.html` | Dashboard del coordinador con filtros, tabla de reportes y accesos rápidos. **NUEVO:** card de Materias-Docentes (solo superuser en área BL) |
| `lista_reportes.html` | **ACTUALIZADO** — Tabla de reportes con badges Tabler (`bg-blue-lt`, `bg-orange-lt`, `bg-red-lt`, `bg-purple-lt`) y modal de edición inline |
| `historial_maestro.html` | Historial de reportes del maestro |
| `materias_docentes_bl.html` | **NUEVO** — Tabla de Materias-Docentes Bilingüe (solo superuser). Buscador, stats cards por coordinador, tabla con badge de coordinador coloreado |
| `form_conductual.html` | Formulario de reporte conductual |
| `form_informativo.html` | Formulario de reporte informativo |
| `form_progress.html` | Formulario de Progress Report |
| `editor_conductual.html` | Editor de reporte conductual existente |
| `editor_informativo.html` | Editor de reporte informativo existente |
| `editor_progress.html` | Editor de Progress Report existente |
| `directorio_telefonos.html` | Directorio de teléfonos de alumnos |

### Estáticos (`conducta/static/conducta/`)

| Archivo | Descripción |
|---------|-------------|
| `css/materias_docentes_bl.css` | **NUEVO** — Estilos de la tabla Materias-Docentes BL |
| `js/materias_docentes_bl.js` | **NUEVO** — Búsqueda debounced 420ms, submit automático |
| `js/coordinador.js` | Lógica del dashboard coordinador |
| `js/dashboard_coordinador.js` | Tabs, filtros y acciones del coordinador |
| `js/editor_reporte.js` | Editor de reportes con evidencias |
| `js/formularios.js` | Validaciones de formularios |
| `js/historial.js` | Filtros e interacciones del historial |

### URLs (`/conducta/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `dashboard/maestro/` | `dashboard_maestro` | Dashboard maestro |
| `coordinador/<area>/` | `dashboard_coordinador` | Dashboard coordinador por área |
| `coordinador/historial/alumno/<id>/` | `historial_alumno_coordinador` | Historial del alumno |
| `coordinador/bl/c1/` … `c4/` | `dashboard_c1` … `c4` | Dashboards por coordinador BL |
| `coordinador/bl/progress/` | `dashboard_coordi_bl` | Dashboard coordinador Progress BL |
| `coordinador/bl/materias/` | `materias_docentes_bl` | **NUEVO** — Tabla Materias-Docentes BL |
| `reporte/conductual/bilingue/` | `reporte_conductual_bilingue` | Crear reporte conductual BL |
| `reporte/informativo/bilingue/` | `reporte_informativo_bilingue` | Crear reporte informativo BL |
| `progress_report/bilingue/` | `progress_report_bilingue` | Crear progress report |
| `reporte-conductual/<pk>/pdf/` | `descargar_pdf_conductual` | PDF conductual |
| `reporte-conductual/<pk>/pdf-3strikes/` | `descargar_pdf_conductual_3_strikes` | PDF 3 Strikes |
| `reporte-informativo/<pk>/pdf/` | `descargar_pdf_informativo` | PDF informativo |
| `progress-report/<pk>/pdf/` | `descargar_pdf_progress` | PDF progress |
| `reporte/editar-ajax/` | `editar_reporte_ajax` | Edición inline AJAX |
| `descargar/zip/` | `descargar_zip_reportes` | ZIP de múltiples reportes |
| `directorio/` | `directorio_telefonos` | Directorio de teléfonos |

### Modelos (`conducta/models.py`)

| Modelo | Descripción |
|--------|-------------|
| `IncisoConductual` | Incisos del reglamento |
| `MateriaDocenteBilingue` | **Materia-Docente BL** con campo `coordinador` (códigos C1–C4) |
| `MateriaDocenteColegio` | Materia-Docente Colegio |
| `ConfiguracionCoordinador` | Config. por coordinador (código, nombre, usuario, área) |
| `ReporteConductual` | Reporte conductual con evidencias |
| `ReporteInformativo` | Reporte informativo/académico |
| `ProgressReport` | Progress report BL |
| `EvidenciaReporte` | Hasta 2 imágenes por reporte |
| `ConfiguracionNotificacion` | Destinatarios de correo por área |

---

## Módulo: Reloj — Control de Asistencia

Conecta con SQL Server para leer marcas del reloj biométrico. Gestiona horarios, compensatorios, permisos, feriados, vacaciones y genera reportes PDF.

### Plantillas (`reloj/templates/reloj/`)

| Template | Descripción |
|----------|-------------|
| `base_reloj.html` | Layout base del módulo |
| `dashboard.html` | Dashboard principal con stats |
| `reporte.html` | Reporte de asistencia con filtros y comentarios |
| `compensatorio_list.html` | **ACTUALIZADO** — Lista de tiempo compensatorio por día. Columna "Tiempo Extra Autorizado", resumen superior con total acumulado (incl. extras) actualizable sin recarga (`#resumen-total-min`, `#resumen-tiempo-txt`) |
| `compensatorio_form.html` | Formulario crear/editar compensatorio |
| `compensatorio_calculo_list.html` | **ACTUALIZADO** — Cálculo del saldo compensatorio por empleado. Nueva columna **T. Extra** con badge cyan + modal de entradas. Fórmula: `Saldo = Total − Compensado − T.Extra`. Badges editables inline para días adeudados, factor h/día, permisos extras, min/día, días no laborables |
| `compensatorio_calculo_form.html` | Formulario crear/editar calculo compensatorio |
| `compensatorio_authorize.html` | Autorización de tiempo extra |
| `horarios_list.html` | Listado de horarios asignados |
| `horario_form.html` | Formulario de horario |
| `feriados_list.html` | Listado de feriados |
| `feriado_form.html` | Formulario de feriado |
| `sabados_list.html` | Sábados especiales |
| `sabado_form.html` | Formulario de sábado especial |
| `permisos_list.html` | Listado de permisos de empleados |
| `permiso_form.html` | Formulario de permiso |
| `permiso_reporte.html` | Reporte mensual de permisos |
| `plantilla_list.html` | Plantillas de horario |
| `plantilla_form.html` | Formulario de plantilla |
| `regla_form.html` | Regla de plantilla |
| `grafica.html` | Gráfica circular de asistencia |
| `vacaciones_list.html` | Listado de vacaciones |
| `vacaciones_importar.html` | Importar vacaciones |
| `test_sql.html` | Diagnóstico de conexión SQL Server |

### Estáticos (`reloj/static/reloj/`)

| Archivo | Descripción |
|---------|-------------|
| `js/compensatorio_list.js` | **ACTUALIZADO** — Guarda tiempo extra por día (AJAX). `actualizarResumenTotales(delta)` actualiza al instante el total acumulado y la línea "incl. Xm extra" sin recargar |
| `js/compensatorio_calculo_list.js` | **ACTUALIZADO** — Modal de T. Extra múltiple: `renderTERows`, `updateTETotals` actualiza badge y recalcula saldo. Modales para días no lab., días adeudados, factor, permisos extras, min/día. Bulk actions |
| `js/reporte.js` | Filtros y notas del reporte |
| `js/grafica.js` | Gráfica circular (Chart.js) |
| `js/horario.js` | Lógica de horarios |
| `js/vacaciones_list.js` | Gestión de vacaciones |
| `css/reloj.css` | Estilos base del módulo |
| `css/reporte.css` | Estilos del reporte |
| `css/permiso_reporte.css` | Estilos del reporte de permisos |

### URLs (`/reloj/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `` | `reloj_dashboard` | Dashboard |
| `reporte/` | `reloj_reporte` | Reporte de asistencia |
| `pdf/` | `reloj_exportar_pdf` | Exportar PDF del reporte |
| `grafica/` | `reloj_grafica` | Gráfica circular |
| `overtime/authorize/` | `reloj_overtime_authorize` | Autorizar tiempo extra |
| `plantillas/` | `reloj_plantilla_list` | Plantillas de horario |
| `horarios/` | `horarios_list` | Horarios asignados |
| `feriados/` | `reloj_feriados_list` | Feriados |
| `sabados/` | `reloj_sabados_list` | Sábados especiales |
| `compensatorio/` | `reloj_compensatorio_list` | Compensatorio por día |
| `compensatorio/set-extra/` | `reloj_compensatorio_set_extra` | Guardar tiempo extra por día (AJAX) |
| `compensatorio-calculo/` | `reloj_compensatorio_calculo_list` | Cálculo de saldo compensatorio |
| `compensatorio-calculo/<pk>/tiempo-extra/` | `reloj_compensatorio_calculo_get_te` | **NUEVO** — GET entradas de T. Extra (AJAX) |
| `compensatorio-calculo/<pk>/tiempo-extra/add/` | `reloj_compensatorio_calculo_add_te` | **NUEVO** — Agregar entrada T. Extra (AJAX) |
| `compensatorio-te/<te_pk>/delete/` | `reloj_compensatorio_calculo_del_te` | **NUEVO** — Eliminar entrada T. Extra (AJAX) |
| `compensatorio-calculo/<pk>/set-dias-adeudados/` | `reloj_compensatorio_set_dias_adeudados` | Editar días adeudados |
| `compensatorio-calculo/<pk>/set-factor/` | `reloj_compensatorio_set_factor` | Editar factor h/día |
| `compensatorio-calculo/<pk>/set-permisos-extras/` | `reloj_compensatorio_set_permisos_extras` | Editar permisos extras |
| `compensatorio-calculo/<pk>/set-min-dia/` | `reloj_compensatorio_calculo_set_min_dia` | Editar min. autorizados/día |
| `compensatorio-calculo/<pk>/dias-no-lab/` | `reloj_compensatorio_dias_no_lab_get` | GET días no laborables |
| `compensatorio-calculo/<pk>/dias-no-lab/add/` | `reloj_compensatorio_dias_no_lab_add` | Agregar día no laborable |
| `compensatorio-dias-no-lab/<dia_pk>/delete/` | `reloj_compensatorio_dias_no_lab_delete` | Eliminar día no laborable |
| `permisos/` | `reloj_permisos_list` | Permisos de empleados |
| `permisos/reporte/` | `reloj_permiso_reporte` | Reporte mensual de permisos |
| `vacaciones/` | `reloj_vacaciones_list` | Vacaciones |
| `google/compensatorio/ingresar/` | `compensatorio_google_hook` | Hook Google Forms |

### Modelos (`reloj/models.py`)

| Modelo | Descripción |
|--------|-------------|
| `ScheduleTemplate` | Plantilla de horario |
| `ScheduleRule` | Regla dentro de una plantilla |
| `EmployeeScheduleAssignment` | Asignación de plantilla a empleado |
| `OvertimeRequest` | Solicitud de tiempo extra |
| `Feriado` / `FeriadoAsignacion` | Feriados y asignación a empleados |
| `SabadoEspecial` / `SabadoAsignacion` | Sábados especiales y asignaciones |
| `TiempoCompensatorio` | Registro de compensatorio manual |
| `CompensatorioCalculo` | Cálculo del saldo (días adeudados, factor, permisos, fecha fin) |
| `DiaNoLaborableANA` | Días no laborables de la institución por empleado |
| `TiempoExtraDia` | **NUEVO** — Entradas de tiempo extra autorizado por empleado/fecha. `unique_together = [("emp_code", "fecha")]` |
| `ReporteNota` | Nota en el reporte de asistencia |
| `ReporteComentario` | Comentario en el reporte |
| `PermisoEmpleado` | Permiso de empleado |
| `ReportePermisoMensual` | Reporte mensual de permisos |
| `PermisoReporte` | Ítem individual en el reporte mensual |
| `VacacionConfig` | Configuración de vacaciones |
| `RelojPermiso` | Permisos de acceso al módulo por usuario |

### Lógica de saldo compensatorio

```
Saldo = max(0, Total_a_compensar − Compensado_hasta_hoy − Tiempo_Extra_autorizado)

Donde:
  Total_a_compensar    = (Días_adeudados × Factor_h/día) + Permisos_extras
  Compensado_hasta_hoy = Días hábiles transcurridos × Min_autorizados_día
  Tiempo_Extra         = SUM(TiempoExtraDia.minutos) por emp_code
```

---

## Módulo: Agendas — Agendas Semanales Docentes

### Plantillas (`agendas/templates/agendas/`)

| Template | Descripción |
|----------|-------------|
| `base_agendas.html` | Layout base |
| `form_agenda.html` | Formulario de agenda con imágenes |
| `historial_maestro.html` | Historial de agendas del maestro |
| `dashboard_coordinador.html` | Dashboard del coordinador por área |
| `editar_agenda.html` | Edición de agenda existente |

### URLs (`/agendas/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `form/` | `form_agenda` | Registrar agenda |
| `historial/` | `historial_maestro` | Historial propio |
| `coordinador/` | `dashboard_coordinador` | Dashboard coordinador |
| `<pk>/editar/` | `editar_agenda` | Editar agenda |
| `<pk>/pptx/` | `descargar_pptx` | Descargar PPTX (BL) / DOCX (Colegio) |
| `<pk>/eliminar/` | `eliminar_agenda` | Eliminar agenda |
| `modo/toggle/` | `toggle_modo` | Alternar modo maestro/coordinador |
| `imagen/subir/` | `subir_imagen` | Subir imagen a agenda |

**Acceso:** grupos `coordinador_bilingue` y `coord_progress_bl` tienen acceso a agendas de coordinador.

---

## Módulo: Notas Parcial — Notas de Mitad de Parcial

Sistema de revisión de notas con caché de 8 horas (`DatabaseCache`), flujo de 3 capas (caché → staging → SP SQL Server).

### Plantillas (`notas_parcial/templates/notas_parcial/`)

| Template | Descripción |
|----------|-------------|
| `base_notas.html` | Layout base |
| `index.html` | Vista principal de notas por maestro |
| `maestro.html` | Vista de maestro (ver notas de su grado) |
| `coordinador.html` | Vista de coordinador (carrusel de grados) |
| `asignaciones.html` | Gestión de asignaciones maestro-grado |
| `revision_comentarios.html` | Revisión de comentarios por coordinador |

### URLs (`/notas-parcial/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `` | `notas_parcial_index` | Vista principal |
| `pdf/` | `notas_parcial_pdf` | Generar PDF |
| `coordinador/` | `notas_parcial_coordinador` | Vista coordinador |
| `maestro/` | `notas_parcial_maestro` | Vista maestro |
| `asignaciones/` | `notas_parcial_asignaciones` | Gestión asignaciones |
| `precargar-cache/` | `notas_parcial_precargar` | Precargar caché |
| `enviar-pdf-email/` | `notas_parcial_enviar_email` | Enviar PDF por correo |

### Modelos

| Modelo | Descripción |
|--------|-------------|
| `NotaComentario` | Comentario de coordinador sobre nota |
| `AsignacionMaestro` | Asignación de maestro a grado/sección |
| `RevisionFinalizada` | Marca de revisión completada |

---

## Módulo: Calculadoras

Calculadoras utilitarias de uso interno.

### Plantillas (`calculadoras/templates/calculadoras/`)

| Template | Descripción |
|----------|-------------|
| `base_calculadoras.html` | Layout base |
| `dashboard.html` | Panel de acceso rápido a todas las calculadoras |
| `tiempo.html` | **ACTUALIZADO** — Calculadoras de tiempo: **Entre dos horas** (nueva), Horas→Días, Minutos→Horas, Fecha a Fecha |
| `divisas.html` | Conversión de divisas (USD/EUR/CHF → Lempira) |
| `almacenamiento.html` | Conversión de almacenamiento (MB→GB, etc.) |
| `ip.html` | Calculadora de subredes IP |

### Estáticos (`calculadoras/static/calculadoras/`)

| Archivo | Descripción |
|---------|-------------|
| `js/tiempo.js` | **ACTUALIZADO** — Añade calculadora "Entre dos horas": ingresa HH:MM inicio/fin, muestra resultado en "X horas Y minutos", horas decimales y minutos totales. Error si fin < inicio |
| `js/divisas.js` | Conversión de divisas con tasas de BD |
| `js/almacenamiento.js` | Conversión de almacenamiento |
| `js/ip.js` | Cálculo de subredes |

### URLs (`/calculadoras/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `` | `calculadoras_dashboard` | Panel principal |
| `tiempo/` | `calculadoras_tiempo` | Calculadoras de tiempo |
| `divisas/` | `calculadoras_divisas` | Divisas |
| `almacenamiento/` | `calculadoras_almacenamiento` | Almacenamiento |
| `ip/` | `calculadoras_ip` | Subredes IP |
| `tasa/actualizar/` | `calculadoras_tasa_actualizar` | Actualizar tasa de cambio |

### Modelos

| Modelo | Descripción |
|--------|-------------|
| `TasaCambio` | Tasas de cambio (USD, EUR, CHF) actualizables manualmente o via API |

---

## Módulo: Inventario

| Plantilla | Descripción |
|-----------|-------------|
| `base_inventario.html` | Layout base |
| `dashboard.html` | Panel con conteos por categoría |
| `inventario_computadoras.html` | Listado de computadoras |
| `inventario_televisores.html` | Listado de televisores |
| `inventario_impresoras.html` | Listado de impresoras |
| `inventario_routers.html` | Listado de routers |
| `inventario_datashows.html` | Listado de datashows |
| `inventario_monitores.html` | Listado de monitores |
| `inventario_por_categoria.html` | Vista unificada por categoría |
| `inventario_registros.html` | Registro de movimientos |
| `item_pdf_template.html` | PDF de ficha de equipo |
| `edit_*.html` | Formularios de edición inline (x6 categorías) |

---

## Módulo: Enfermería

| Plantilla | Descripción |
|-----------|-------------|
| `base_enfermeria.html` | Layout base |
| `dashboard.html` | Panel principal |
| `atencion_form.html` | Registro de atención médica |
| `inventario_list.html` | Inventario de medicamentos |
| `medical_history.html` | Historial médico de alumnos |
| `directorio_telefonos.html` | Directorio con links WhatsApp (SQL Server) |
| `enviar_correo.html` | Enviar correo de atención |

---

## Módulo: Tickets — Soporte Técnico

| Plantilla | Descripción |
|-----------|-------------|
| `base_tickets.html` | Layout base (técnico) |
| `base_tickets_user.html` | Layout base (usuario) |
| `submit_ticket.html` | Crear ticket |
| `technician_dashboard.html` | Panel de técnicos |
| `ticket_comments_tech.html` | Chat del ticket (técnico) |
| `ticket_comments_user.html` | Chat del ticket (usuario) |
| `mis_tickets.html` | Mis tickets (usuario) |
| `email/email_notification.html` | Correo de notificación |

---

## Módulo: Finanzas Personales

Módulo de finanzas personales internas (categorías, transacciones, presupuestos, metas de ahorro, pendientes).

| Plantilla | Descripción |
|-----------|-------------|
| `index.html` | SPA de finanzas con panel lateral y gráficas |

---

## Módulo: Sponsors

Gestión de patrocinadores y padrinos institucionales.

**URLs:** `/sponsors/dashboard/` · `/sponsors/add/` · `/sponsors/list/` · `/sponsors/edit/<id>/`

---

## Módulo: Mantenimiento

Registro de mantenimientos preventivos/correctivos con generación de reportes PDF.

**URLs:** `/mantenimiento/` · `/mantenimiento/download/<id>/` · `/mantenimiento/<pk>/editar/` · `/mantenimiento/<pk>/eliminar/`

---

## Convenciones de código

### Templates
- Comentario de autoría: `{# <--- hecho por claude code: descripción #}` (nunca `<!--{# ... #}-->`)
- Variables Django → JS: usar `<div id="page-config" hidden data-*="{{ valor }}">` (nunca `<script>` inline con valores Django, excepto `window._PAGE` en casos heredados)
- Badges Tabler: `bg-blue-lt text-blue` · `bg-red-lt text-red` · `bg-orange-lt text-orange` · `bg-green-lt text-green` · `bg-purple-lt text-purple` · `bg-cyan-lt text-cyan`

### JavaScript
- Los archivos JS viven en `<app>/static/<app>/js/<nombre>.js`
- Deben copiarse también a `staticfiles/<app>/js/` con `sudo cp` (no hay `collectstatic` automático)
- Agregar `?v=N` al `<script src>` en el template al actualizar un JS (cache-bust del navegador)

### Archivos estáticos en producción
- Apache sirve desde `staticfiles/` (generada por `collectstatic`)
- Al editar un `.js` o `.css`, sincronizar manualmente:
```bash
sudo cp system_proyect/<app>/static/<app>/js/archivo.js system_proyect/staticfiles/<app>/js/archivo.js
```
- Luego agregar `?v=N` al tag `<script src>` o `<link href>` correspondiente

---

## Variables de entorno (`.env`)

```env
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False

# MySQL (base de datos principal)
DB_NAME=sponsors2
DB_USER=admin3
DB_PASSWORD=...
DB_HOST=192.168.10.6
DB_PORT=3306

# SQL Server (módulo Reloj y datos de alumnos)
MSSQL_DB_NAME=...
MSSQL_DB_USER=...
MSSQL_DB_PASSWORD=...
MSSQL_DB_HOST=...
MSSQL_DB_PORT=1433

# Correo (Gmail SMTP)
EMAIL_HOST_USER=techcare.app2024@gmail.com
EMAIL_HOST_PASSWORD=...
```

---

## Comandos frecuentes

```bash
# Conectar al servidor
ssh admin2@192.168.10.6

# Activar entorno virtual
cd techcare_project
source venv313/bin/activate
cd system_proyect

# Reiniciar Apache (aplica cambios Python y templates)
echo 'PASSWORD' | sudo -S systemctl restart apache2

# Sincronizar archivo estático sin collectstatic
sudo cp reloj/static/reloj/js/archivo.js staticfiles/reloj/js/archivo.js

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Shell interactiva
python manage.py shell

# Verificar configuración
python manage.py check

# Crear superusuario
python manage.py createsuperuser

# Precargar caché de notas parciales
python manage.py shell -c "from notas_parcial.views import _precargar_notas; _precargar_notas()"
```

---

## Despliegue

El proyecto corre con **Apache + mod_wsgi** en producción.

```bash
# Recargar código Python (sin reiniciar Apache completo)
touch system_proyect/wsgi.py

# Reinicio completo (necesario para cambios en settings, middleware, etc.)
sudo systemctl restart apache2

# Actualizar archivo estático en producción
sudo cp <app>/static/<path>/archivo.js staticfiles/<path>/archivo.js
# Agregar ?v=N al <script src> en el template correspondiente
```

---

*© 2025 Soporte Técnico – Asociación Nuevo Amanecer*
