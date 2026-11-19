# 2. Matriz de riesgos — TechCare (09-nov-2026)

**Escala de prioridad:**
- **Crítica:** explotable hoy, con datos de menores, médicos o credenciales.
- **Alta:** daño serio probable.
- **Media:** daño acotado o que requiere condiciones.
- **Baja:** endurecimiento.

**Columna Estado:**
- **Desplegado:** corregido y en producción desde la v8.0.1 (09-nov-2026).
- **Preparado:** archivo listo para que lo aplique TI.
- **Pendiente:** requiere decisión, recursos o acción institucional.
- **Aceptado:** decisión previa del responsable del sistema.

## Seguridad técnica

| ID | Riesgo | Evidencia (archivo / comportamiento) | Impacto | Prioridad | Tratamiento propuesto | Estado |
|---|---|---|---|---|---|---|
| R01 | Fotos de evidencia de Conducta (menores) descargables **sin sesión** | vhost `Alias /media/` + `Require all granted`; `conducta/models.py` guardaba en `evidencias/<área>/<tipo>/<nombre original>`; las plantillas usaban `ev.imagen.url`. Hay 99 archivos con nombres adivinables y EXIF | Exposición de imágenes de menores y sus metadatos | **Crítica** | Vista `evidencia_ver` con permiso y nombres uuid (hecho). Apache: denegar `media/evidencias` (preparado). Limpiar el EXIF de las existentes (pendiente) | Desplegado + Preparado |
| R02 | `/media/` público por defecto (lista negra) | vhost: solo se niegan carpetas concretas | Cualquier carpeta nueva de subidas nace pública | Alta | `Require all denied` en `/media` y abrir solo `avatars` y `admin-interface` | Preparado |
| R03 | Superusuario sin límite de intentos de login | `accounts/views.py` (`_registrar_fallo_login` devolvía 0 intentos para el superusuario); 2FA apagado | Fuerza bruta contra la cuenta más privilegiada | Alta | Bloqueo temporal de 1 min cada 3 fallos (nunca total) + límite por IP pública (hecho). Encender el 2FA para el superusuario (pendiente) | Desplegado + Pendiente |
| R04 | Sin límite por IP (password spraying) | Solo había contador por usuario | Prueba de claves comunes contra muchas cuentas | Alta | 20 fallos en 15 min por **IP pública** → espera de 15 min. No se aplica a IPs privadas (el 93 % llega por el gateway) | Desplegado |
| R05 | Bloqueo **permanente** de cuentas por un tercero | 5 fallos → `perfil.login_bloqueado=True`; solo lo levanta el superusuario | Un anónimo deja sin acceso a un docente que conoce | Media | Bloqueo con caducidad, o que la recuperación de contraseña desbloquee | Aceptado (decisión del 05-nov-2026); revisar |
| R06 | Sin bitácora de eventos de seguridad | `core/audit_registry.py` excluye `auth`; constance sin historial | No se puede investigar un incidente: quién cambió permisos, intentos de acceso | Alta | `core/seguridad_eventos.py` → `logs/seguridad.log` | Desplegado |
| R07 | Sin `LOGGING`: los errores 500 se pierden | `settings.py` | Fallas invisibles; no hay evidencia | Media | `LOGGING` con archivo rotativo tolerante | Desplegado (necesita permisos de carpeta, ver guía) |
| R08 | IP de auditoría falsificable | Uso de `HTTP_X_FORWARDED_FOR` sin proxy | Bitácoras con IP inventada | Media | `ip_cliente()` = `REMOTE_ADDR` | Desplegado |
| R09 | El registro de accesos dependía de una señal que nunca corría | `accounts/apps.py` (receptor con referencia débil) | Evidencia de accesos incompleta | Baja | `weak=False` y quitar el registro duplicado de la vista | Desplegado |
| R10 | Contraseña inicial enviada en claro por correo y sin cambio obligatorio | `accounts/views.py` `register_maestro`, `_enviar_credenciales_correo` | Clave legible en el buzón o en un reenvío | Media | Enviar un enlace de "crear contraseña" (token) y obligar el cambio en el primer acceso | Pendiente |
| R11 | Recuperación sin límite; enlace de 3 días aunque el correo dice 24 h | `accounts/urls.py`, sin `PASSWORD_RESET_TIMEOUT` | Inundar buzones; enlace con vida larga | Media | `accounts/recuperacion.py` + `PASSWORD_RESET_TIMEOUT=86400` | Desplegado |
| R12 | Reenvío del código 2FA sin espera | `accounts/views.py` (`reenviar`) | Spam de correo | Baja | Espera de 60 s y tope por hora | Pendiente |
| R13 | Logout por GET | `accounts/views.py` | CSRF de cierre de sesión (molestia) | Baja | POST, o GET solo con `?inactive=` | Pendiente |
| R14 | "Volver a mi cuenta" sin reautenticación | `accounts/suplantar.py` | Robo de la sesión suplantada → sesión de superusuario | Baja | Limitar la suplantación a 30 min o ligarla a la sesión | Pendiente |
| R15 | HSTS de 1 día; `ALLOWED_HOSTS` con IP y localhost | `settings.py` | Endurecimiento | Baja | HSTS de 1 año tras confirmar que todo va por HTTPS; revisar hosts | Pendiente |
| R16 | Sin límite de tamaño de petición | No hay `LimitRequestBody`; los chequeos `f.size` ocurren después de escribir en `/tmp` | Llenar el disco con un POST | Media | `LimitRequestBody 31457280` | Preparado |
| R17 | Documentos con datos sensibles cacheables | PDF de enfermería, notas, ZIP de conducta sin `Cache-Control` | Copias en equipos compartidos | Media | `DescargasPrivadasMiddleware` | Desplegado |
| R23 | XSS almacenado en Ruteo BL | `routing_bl.js` (`innerHTML` con `docente`/`materias`) | Ejecutar JS en la sesión de coordinadores o del superusuario | Media | Escape (`_rbEsc`) | Desplegado |
| R24 | `mark_safe` con nombres en el admin de conducta | `conducta/admin.py` | XSS interno en el admin | Baja | `format_html` | Desplegado |
| R25 | Tokens DRF sin caducidad | `red/api.py` (`TokenAuthentication`) | Un token filtrado da acceso permanente a la red | Baja | Revisar la tabla de tokens; quitar TokenAuthentication si no hay integraciones | Pendiente |
| R26 | Moodle: cambiar la URL reutiliza el token sin probarlo; acepta http | `moodle_upload/views.py` | Fuga del token (solo el superusuario puede hacerlo) | Baja | Exigir https y volver a pegar el token al cambiar la URL | Pendiente |
| R27 | Confirmación de ticket anónimo con texto libre; el límite falla abierto | `tickets/views.py` | Phishing interno | Baja | Confirmación sin texto libre; el límite debe fallar cerrado | Pendiente |
| R28 | 73 avisos de vulnerabilidad en 9 dependencias | `pip_audit` del 09-nov-2026: Pillow 12.3.0 (39, corregido en 13.0.0), PyJWT 2.13.0 (15), DRF 3.17.1 (5), WeasyPrint 68.1 (4), certifi, brotli, anyio, httpx2, httpcore2 | Explotación de bibliotecas (sobre todo Pillow, que procesa imágenes subidas) | Alta | Plan de actualización en un entorno de prueba (las versiones mayores primero en pruebas). Ver la guía | Pendiente |
| R29 | **3 credenciales vigentes en el historial de git** | MySQL (`DB_PASSWORD`), cuenta de SQL Server académico y ZKBio: sus valores actuales coinciden con textos del historial (commits anteriores a `e65fb5e`/`be66ab7`). Repo privado | Quien tenga el repo o un clon tiene acceso a las bases, incluida la académica **real** | **Alta** | **Rotar** las tres en los servidores de BD + actualizar el `.env`. Opcional: reescribir el historial (`git filter-repo`), lo que no sustituye la rotación | Pendiente (institucional) |
| R30 | Respaldos sin cifrar con `.env` y datos de menores, copiados a una PC por SMB | `backup_mensual.py`: el tar incluye `system_proyect/.env` y `media/`; archivos 664 | Robo de la PC o de la carpeta compartida = credenciales y datos de menores | **Alta** | Excluir el `.env` del tar (guardarlo aparte y cifrado); cifrar el respaldo (gpg/age); permisos 600 | Pendiente |
| R31 | Pérdida de hasta ~31 días de datos | Solo hay respaldo mensual (cron del día 1) | Pérdida de notas, reportes y atenciones del mes | **Alta** | Volcado diario de MySQL con retención (p. ej. 14 diarios + 12 mensuales) | Pendiente |
| R33 | **La copia externa de respaldos falla desde el 17-sep-2026** | `/home/admin2/sync_backups.log`: último `sync OK` el 2026-09-17; desde entonces 84 "share no disponible" (la PC de destino o el montaje SMB no responde) | Los respaldos de oct y nov solo están en el mismo servidor: si el disco o el servidor se pierden, se pierde todo | **Crítica** | Restablecer el destino (o cambiarlo por un NAS o almacenamiento institucional siempre encendido) y una alerta si el sync falla 2 días seguidos | Pendiente (TI) |
| R32 | Restauración de la BD nunca probada | No hay base aislada | No se sabe si el respaldo sirve ni cuánto tarda | Media | Prueba de restauración trimestral en una base aislada | Pendiente |
| R35 | Validaciones de subida débiles en caminos secundarios | El admin no valida PDF/adjuntos; Moodle solo valida la extensión; JSON/XLSX de superusuario sin tope; `_reducir_foto` devuelve el original si falla | Bajo (admin restringido por IP, archivos servidos con `nosniff`) | Baja | Reutilizar los validadores de la app | Pendiente |
| R40 | Contraseña sudo en texto plano en la memoria local del asistente de IA | `~/.claude/projects/.../memory/` (fuera del repo) | Cualquiera con lectura en el home de admin2 obtiene root | **Alta** | Rotar la contraseña sudo, borrarla de la memoria y usar `sudo` con una regla acotada a `systemctl restart apache2` y `collectstatic` | Pendiente |

## Privacidad y mínimo privilegio

| ID | Riesgo | Evidencia | Impacto | Prioridad | Tratamiento | Estado |
|---|---|---|---|---|---|---|
| R18 | `coord_progress_bl` = coordinador BL completo + Enfermería | `accounts/panel_roles.py:12`, `enfermeria/views.py` (`GRUPOS_ENFERMERIA`), `conducta/views.py` (ZIP, dashboard) | Ve y descarga todos los reportes BL; puede **borrar** atenciones médicas | **Alta** | Separar el grupo de Progress del de coordinación; sacarlo de Enfermería | Pendiente (decisión de Dirección/Coordinación) |
| R19 | En Enfermería, cualquier miembro del candado edita o borra cualquier atención | `enfermeria/views.py` (`atencion_eliminar`) | Pérdida o alteración del expediente médico | Media | Bitácora de borrado (hecho); restringir borrar/editar a `enfermeria` + superusuario (decisión) | Desplegado + Pendiente |
| R20 | Progress Report visible y editable por cualquier maestro BL | `conducta/views.py` (`historial_maestro_bilingue`, `editar_progress_report`) | Acceso a informes de grados que no atiende | Media | Limitarlo a autor, maestros del grado y coordinación | Pendiente (decisión) |
| R21 | Enlace público del PNG de un reporte válido 60 días y no revocable | `conducta/views.py` (`reporte_png`) | Exposición prolongada si se reenvía | Baja | 7–14 días y firma ligada a `updated_at` | Pendiente |
| R22 | El texto de reportes de menores se envía a un proveedor de IA externo | `asistente/views.py` (`redactar`) | Transferencia de datos a un tercero sin política | Baja–Media | Política de uso de IA + limitarlo a grupos de conducta + aviso al usuario | Pendiente (política) |

## Gestión (COBIT)

| ID | Riesgo | Evidencia | Impacto | Prioridad | Tratamiento | Estado |
|---|---|---|---|---|---|---|
| G01 | Producción = copia de trabajo de git; cambios directos sobre `main` | Apache sirve `/home/admin2/techcare_project` | Un cambio sin probar llega a producción al reiniciar | Alta | Rama por cambio + revisión + despliegue desde un commit etiquetado ([política de cambios](politicas/politica_cambios.md)) | Pendiente |
| G02 | Migraciones fuera de git | `system_proyect/.gitignore` (`*/migrations/*.py`) | Imposible reconstruir el esquema desde el repo; riesgo de desalineación | Media | Versionar las migraciones (con un `--fake` inicial coordinado) | Pendiente |
| G03 | Sin responsables formales (seguridad, cambios, accesos, continuidad) | No existe un documento de roles | Dependencia de una persona; sin segregación de funciones | Alta | Designar responsables ([plan de seguridad](07_plan_seguridad.md)) | Pendiente (Dirección) |
| G04 | Sin pruebas automatizadas | `*/tests.py` vacíos salvo `red` | Regresiones de seguridad no detectadas | Media | 27 pruebas de seguridad + `settings_test.py` (hecho); ampliar | Desplegado |
| G05 | `conducta/forms.py` consulta la BD al importarse | `get_coordinadores_choices()` en la definición de la clase | `manage.py check` falla sin BD; arranque frágil | Baja | Pasar las opciones a `__init__` del formulario | Pendiente |
| G06 | Sin procedimiento de incidentes ni de continuidad | No existía | Respuesta improvisada | Media | [06](06_procedimiento_incidentes.md) y [08](08_plan_continuidad_negocio.md) | Aprobado |
