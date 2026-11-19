# 1. Diagnóstico de seguridad y gestión — TechCare

**Fecha:** 09-nov-2026 · **Versión revisada:** 8.0.0, la de producción más el trabajo pendiente sin commit.

## 1.1 Qué se revisó y cómo

Todo se comprobó en el código y en el servidor, sin dar por buena la documentación previa:

| Fuente | Método |
|---|---|
| Código Django de las 26 apps (`system_proyect/`) | Lectura con 4 revisiones paralelas de solo lectura: autenticación y sesiones · autorización e IDOR · archivos · inyección, XSS, CSRF y API. Después, verificación propia de cada hallazgo usado |
| `settings.py`, middleware, URLs | Lectura directa |
| Vhost de Apache `servicios_ana.conf` | Lectura, sin modificarlo |
| Dependencias | `pip_audit -r requirements.txt` (09-nov-2026) |
| Historial de git | Comparación de **huellas SHA-256** entre los secretos actuales del `.env` y los textos del historial. Nunca se imprimió un valor |
| Respaldos | `gzip -t`, listado del `.tar.gz`, cierre del volcado SQL y restauración del **código** en una carpeta aislada |
| Registro de accesos | Conteo de IPs privadas y públicas de los últimos 14 días, sin imprimir ninguna IP |

**No se tocó:** producción, datos reales, credenciales, Apache, permisos de usuarios ni bases de datos. Todos los cambios de código están en la rama `seguridad/iso27001-cobit`, en una copia de trabajo aparte (`/home/admin2/techcare_seguridad`).

## 1.2 Arquitectura observada

- **Aplicación:** Django 6 · Python 3.13 · Apache 2.4 + mod_wsgi, **sin proxy inverso**. Un solo vhost HTTPS en el puerto 437. Hay **mod_php 7.4 activo en el servidor**, desactivado para `/media/`.
- **Bases de datos:**
  - MySQL `sponsors2`: la principal.
  - SQL Server académico, con **dos bases**: `Test2` (copia) y `AdmonANASQL` (real). La conexión `padres_sqlserver` (Ingreso de Notas) apunta a Test2.
  - SQL Server ZKBio: reloj de asistencia.
  - Alias de solo lectura de inventario.
- **Datos sensibles:**
  - **Médicos:** Enfermería, atenciones de menores.
  - **De menores:** conducta (reportes y fotos de evidencia), notas, salidas al baño, directorio de teléfonos de padres.
  - **Del personal:** asistencia y compensatorio.
  - **De donantes:** Sponsors.
  - **De red:** IPs y contraseñas de equipos, cifradas.
- **Identidades y roles:** usuarios de Django; los roles son **grupos por nombre**. Hay 1 superusuario y gestores delegados (`puede_ver_usuarios`).
- **Clientes:** navegador, app de escritorio (.exe, Electron) y APK Android (WebView). Las dos apps solo abren la web.
- **Integraciones externas:**
  - SMTP: Gmail y cuentas institucionales.
  - Moodle: plugin propio, con token cifrado.
  - API de Anthropic: asistente IA y "redactar con IA".
  - GitHub: código y compilación de las apps.
  - Feed de actualizaciones del .exe en el puerto 453 de la LAN.

## 1.3 Lo que ya estaba bien (controles existentes verificados)

| Control | Evidencia |
|---|---|
| Toda vista exige sesión, salvo las marcadas públicas a propósito | `core.middleware.TechCareLoginRequiredMiddleware` |
| Autorización por objeto (área, autor o grupo) en enfermería, conducta, notas, ingresos, salidas, reloj, agendas, tickets, sponsors, desarrollo y datashow | Revisión del 09-nov: **no se encontró ningún IDOR abierto** por cambio de id |
| SQL parametrizado; los nombres de tabla y columna salen de listas cerradas | `notas_parcial`, `ingresos_notas`, `reloj` (`_sql_codigos`), `contabilidad/sqlserver_inventory` |
| CSRF activo; `csrf_exempt` solo en la rama JSON de `submit_ticket` | `tickets/views.py` |
| Cookies `Secure`, `HttpOnly` y `SameSite=Lax`; HSTS; `nosniff`; `Referrer-Policy`; `X-Frame-Options: DENY` | `settings.py` |
| Caducidad por inactividad (240 min deslizantes) | `SesionInactividadMiddleware` |
| Bloqueo de cuenta tras 5 fallos (desbloqueo por ticket, decisión del 05-nov-2026) | `accounts/views.py` |
| 2FA por correo construido (apagado) | `accounts/dosfa.py`, constance `DOSFA_ACTIVO` |
| "Iniciar sesión como" solo para el superusuario, con bitácora | `accounts/suplantar.py`, modelo `Suplantacion` |
| Historial de cambios de datos en unos 100 modelos | `django-simple-history` |
| Lo subido no se ejecuta: PHP apagado en `/media/`, html/svg/js como descarga con `CSP: sandbox` | vhost |
| Pillow no abre EPS (Ghostscript) | `core/apps.py` |
| Secretos fuera del código: el `.env` no está versionado desde `be66ab7`, y `SECRET_KEY` es obligatoria | `settings.py`, `.gitignore` |

## 1.4 Hallazgos principales

La lista completa, con IDs, está en la [matriz de riesgos](02_matriz_riesgos.md).

### Críticos y altos

1. **R01 · Las fotos de evidencia de Conducta se descargaban sin sesión.**
   - Qué pasaba: `/media/evidencias/` quedó fuera del cierre de `/media/` del 05-nov. Son 99 imágenes con nombres adivinables ("WhatsApp Image <fecha>") y con EXIF.
   - **Código corregido en la rama.** Falta aplicar el cierre en Apache.
2. **R29 · Tres credenciales VIGENTES están en el historial de git:** MySQL, la cuenta de SQL Server académico y ZKBio.
   - El repositorio es privado, pero las ve todo el que tenga acceso al repo o a un clon. Ya hubo integraciones externas con acceso (ramas `codex/*`).
   - **Requiere rotación** (acción institucional).
3. **R33 · La copia externa de los respaldos no funciona desde el 17-sep-2026.** Los respaldos de octubre y noviembre existen **solo en el mismo servidor**.
4. **R30/R31 · Respaldos.**
   - Solo hay respaldo **mensual**: se pueden perder hasta unos 31 días de datos.
   - El archivo **incluye el `.env` y `media/`** (datos de menores) **sin cifrar** y se copia por SMB a una PC.
5. **R03/R04 · Login.**
   - El superusuario no tenía **ningún** límite de intentos.
   - No había límite por IP.
   - **Corregido en la rama**, ver 1.5.
6. **R06/R07 · No había bitácora de eventos de seguridad ni `LOGGING`.**
   - No quedaban registrados los logins fallidos, los cambios de privilegios o grupos ni los cambios de configuración.
   - Los errores 500 no quedaban en ningún lado.
   - **Corregido en la rama.**
7. **R18 · El grupo `coord_progress_bl` tiene más privilegio del que su nombre indica.**
   - Ve todos los reportes de conducta Bilingüe, baja el ZIP del área y tiene acceso completo a Enfermería, con permiso para **borrar atenciones médicas**.
   - **Requiere decisión institucional.**
8. **R28 · 73 avisos de vulnerabilidad en 9 dependencias.**
   - Las principales son Pillow (39) y PyJWT (15).
   - **Requieren un plan de actualización con pruebas.**
9. **R40 · La contraseña sudo del servidor está en texto plano** en la memoria local del asistente de IA (`~/.claude/…/memory/`, fuera del repo).
   - **Hay que rotarla y retirarla.**

### Hallazgo de gestión (COBIT)

- **Control de cambios.**
  - Se trabaja directo sobre `main` y la carpeta de producción **es** la copia de trabajo de git: Apache sirve lo que hay en disco, aunque no tenga commit.
  - Las **migraciones están fuera de git** (`*/migrations/*.py` en `.gitignore`). Un clon no puede reconstruir la base.
  - No había pruebas automatizadas, salvo `red`. Ahora hay 27 pruebas de seguridad y una configuración de pruebas aislada.
- **Roles.** No hay responsables formales designados para la seguridad, la continuidad, la aprobación de cambios ni la gestión de accesos. Todo recae en una persona.
- **Inventario.** El inventario de módulos e integraciones existía solo de hecho, en README y AGENTS. Ahora está en este diagnóstico y en el [plan de continuidad](08_plan_continuidad_negocio.md).

## 1.5 Lo que se corrigió en la rama (resumen)

| Mejora | Archivos |
|---|---|
| Evidencias de conducta servidas **solo con permiso** (autor o coordinación del área; en Progress, quien tiene Progress BL) y con nombre aleatorio en las nuevas subidas | `conducta/views.py` (`evidencia_ver`), `conducta/urls.py`, `conducta/models.py`, plantillas `dashboard_coordinador.html` y `historial_maestro.html`, `conducta/admin.py` |
| Login: límite de 20 fallos por **IP pública** en 15 min; el superusuario recibe el bloqueo **temporal**, nunca el total. Las IPs privadas no se limitan porque el 93 % del tráfico llega por el gateway y se bloquearía toda la red | `accounts/views.py` |
| Bitácora de eventos de seguridad en `logs/seguridad.log`, en JSON y sin contraseñas, hashes, tokens ni datos médicos | `core/seguridad_eventos.py`, `core/apps.py`, `settings.py` (`LOGGING`) |
| Errores 500 y `django.security` a `logs/errores.log` | `settings.py` |
| IP real (`REMOTE_ADDR`): `X-Forwarded-For` lo inventa el cliente | `core/seguridad_eventos.py`, `accounts/apps.py`, `accounts/suplantar.py` |
| Registro de accesos: la señal **nunca funcionaba** (referencia débil); ahora queda un registro por login y la suplantación no cuenta como acceso del usuario | `accounts/apps.py`, `accounts/views.py`, `accounts/suplantar.py` |
| Recuperación de contraseña: 3 solicitudes por correo por hora (y 10 por IP pública), misma respuesta siempre, enlace válido 24 h (antes 3 días) y bitácora | `accounts/recuperacion.py`, `accounts/urls.py`, `settings.py` |
| PDF, Excel y ZIP con `Cache-Control: private, no-store` | `core/middleware.py` (`DescargasPrivadasMiddleware`) |
| XSS almacenado en la tabla de Ruteo BL y en el admin de conducta | `conducta/static/conducta/js/routing_bl.js` (v3), `conducta/admin.py` |
| Bitácora de quién borra una atención médica | `enfermeria/views.py` |
| Configuración de pruebas aislada y 27 pruebas de seguridad; corregida una prueba rota de `red` | `system_proyect/settings_test.py`, `core/tests_seguridad.py`, `red/tests.py` |
| Cambios de Apache preparados (no aplicados) | `docs/seguridad/infra/` |
| `SECURITY.md` real (antes era la plantilla de GitHub) | `SECURITY.md` |
| **Configuración → Documentación**: estas guías, planes y políticas se leen dentro de TechCare (solo el superusuario; visor seguro de `docs/`) | `accounts/views_documentacion.py`, `accounts/urls.py`, `settings_base.html`, `settings_documentacion.html`, `accounts/css/settings_documentacion.css`, `requirements.txt` |

## 1.6 Limitaciones de esta revisión

- Es una revisión de **código y configuración**. No se hizo prueba de penetración externa ni revisión de la red, el firewall, el sistema operativo o los servidores SQL Server.
- La restauración de la **base de datos** no se probó: requiere una base aislada que no existe.
- El JavaScript del navegador solo se validó con `node --check` y una prueba de la función de escape. No hay navegador automatizado en el servidor.
- Las referencias ISO y COBIT se verificaron con fuentes secundarias (ver [README](README.md)).
