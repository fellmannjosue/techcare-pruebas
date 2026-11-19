# Manual técnico de TechCare

**Versión del sistema:** 8.0.1 (10-nov-2026) · **Organización:** Asociación Nuevo Amanecer (ANA) · **Dirección:** https://servicios.ana-hn.org:437

> Este manual no contiene contraseñas, tokens ni claves. Cuando se menciona un secreto se indica **dónde** está, nunca su valor.

## 1. Descripción general

TechCare es el sistema web institucional de ANA. Centraliza tickets de soporte, reportes de conducta, notas, agendas, asistencia del personal (reloj), enfermería, inventario y mantenimiento de equipos, mantenimiento mecánico, CFP, sponsors, red, gestión de desarrollo y calculadoras.

- **Tipo:** aplicación web Django (Python), un solo proyecto con una aplicación por área.
- **Acceso:** navegador web (Web), app de escritorio de Windows (.exe) y app de Android (APK). Las dos apps son envoltorios que abren la misma web.
- **Usuarios:** personal de ANA con cuenta institucional; los permisos se dan por **grupos** (roles).

## 2. Versión del sistema y de las aplicaciones

| Componente | Versión | Dónde se ve o se define |
|---|---|---|
| TechCare (web) | **8.0.1** | Pie de página de cada pantalla; `system_proyect/core/changelog.json` |
| App de escritorio (.exe, Windows) | 8.0.0 | `desktop/package.json` |
| App de Android (APK) | 8.0.0 (versionCode 800000) | `mobile/app/build.gradle` |

**Numeración.** Según la cantidad de archivos cambiados en una publicación:

| Archivos cambiados | Segmento que sube | Ejemplo | Ventana de novedades |
|---|---|---|---|
| Menos de 10 | 5.º segmento | `7.8.0.001` | Solo el superusuario |
| 10 a 49 | 3.er segmento | `7.8.1` | Solo el superusuario |
| 50 o más | 2.º segmento | `7.9.0` | Todos los usuarios |

El historial de versiones se genera desde los mensajes de commit (`manage.py gen_changelog`) y cada usuario lo ve una vez en la ventana **Novedades**.

## 3. Programas del servidor (software base)

| Programa | Versión | Uso |
|---|---|---|
| Ubuntu Server | 20.04.6 LTS | Sistema operativo |
| Apache HTTP Server | 2.4.41 | Servidor web (HTTPS en el puerto 437) |
| mod_wsgi | 4.6.8 (paquete del sistema) · 5.0.2 (venv) | Conecta Apache con Django |
| Python | 3.13.3 (entorno virtual `venv`) | Lenguaje de la aplicación |
| Django | 6.0.8 | Framework web |
| MySQL Server | 8.0.42 | Base de datos principal (`sponsors2`) |
| Microsoft ODBC Driver for SQL Server | 17.11 y 18.7 | Conexión a las bases de SQL Server |
| PHP | 7.4.3 | Instalado en el servidor por otros sistemas; **apagado** dentro de `/media/` de TechCare |
| Fuente Noto Color Emoji | paquete `fonts-noto-color-emoji` | Emojis en los PDF de notas |
| Servicio `techcare-updates` (systemd, `python3 -m http.server`) | — | Publica las actualizaciones del .exe (puerto 453) |

## 4. Bases de datos

| Alias en Django | Motor | Base | Uso | Acceso |
|---|---|---|---|---|
| `default` | MySQL 8 | `sponsors2` | Todos los datos propios de TechCare | Lectura y escritura |
| `padres_sqlserver` | SQL Server | `Test2` (copia) | Ingreso de Notas | Escritura controlada (única integración que escribe) |
| alias de la base real | SQL Server | `AdmonANASQL` (real) | Notas mitad de parcial (lectura por procedimientos) | Solo lectura |
| alias del reloj | SQL Server | `zkbiotime` | Marcas del reloj biométrico | Solo lectura |
| `inventario_test2` | SQL Server | `Test2` | Inventario institucional (etapa 0–1) | Solo lectura |

- Las credenciales están en el archivo `.env` del servidor (permisos 640, grupo `www-data`); **nunca** en el repositorio.
- Las tablas heredadas `tbl_gen_*` / `tbl_spn_*` (Sponsors) son `managed = False`: Django no las crea ni las modifica en su estructura.
- Las migraciones de Django **no se versionan** en git (`*/migrations/*.py` en `.gitignore`); viven en el servidor.

## 5. Bibliotecas de Python (requirements.txt)

| Grupo | Bibliotecas y versión |
|---|---|
| Núcleo | Django 6.0.8 · asgiref 3.11.1 · sqlparse 0.6.0 · python-dotenv 1.2.2 · mod_wsgi 5.0.2 |
| Bases de datos | mysqlclient 2.2.8 · mssql-django 1.7.1 · pyodbc 5.3.0 |
| Administración y bitácora | django-unfold 0.91.0 · django-admin-interface 0.32.0 · django-jazzmin 3.0.4 · django-constance 4.3.5 · django-import-export 4.4.0 · django-simple-history 3.11.0 · django-widget-tweaks 1.5.1 · django-guardian 3.3.1 |
| API | djangorestframework 3.17.1 · djangorestframework_simplejwt 5.5.1 · PyJWT 2.13.0 · django-cors-headers 4.9.0 |
| Documentos | reportlab 4.5.0 · weasyprint 68.1 · python-pptx 1.0.2 · python-docx 1.2.0 · openpyxl 3.1.5 · xlsxwriter 3.2.9 · xlrd 2.0.2 · lxml 6.1.0 · pdfplumber 0.11.10 · pypdfium2 5.10.1 |
| Imágenes | Pillow 12.3.0 · qrcode 8.2 |
| Inteligencia artificial | anthropic (Asistente IA, modelo `claude-sonnet-5-5`) · openai 2.33.0 (`core/utils_ai.py`) |
| Seguridad y otros | cryptography 50.0.0 (cifrado Fernet de contraseñas de Red y tokens de Moodle) · markdown-it-py 4.2.0 (visor de Documentación) |

La lista completa con versiones exactas está en `system_proyect/requirements.txt`. Las vulnerabilidades conocidas se revisan con `python -m pip_audit -r system_proyect/requirements.txt`.

## 6. Bibliotecas del navegador (por CDN)

| Biblioteca | Versión | Uso |
|---|---|---|
| Tabler UI (`@tabler/core`) | 1.0.0-beta19 | Diseño de todas las pantallas |
| Tabler Icons (webfont) | 3.11.0 | Íconos |
| jQuery + DataTables | DataTables 1.13.6 / 1.13.7, Responsive 2.5.0, Buttons 2.4.2, RowGroup 1.4.1 | Tablas con búsqueda, orden y exportación |
| Chart.js | 4.4.0 / 4.4.1 | Gráficas de los paneles |
| Select2 | 4.1.0-rc.0 | Listas desplegables con búsqueda |
| SweetAlert2 | 11 | Mensajes y confirmaciones |
| html2canvas | 1.4.1 | Imagen final (PNG) de las agendas |

## 7. Arquitectura

```
Usuario (Web / .exe / APK)
        │  HTTPS :437
        ▼
Apache 2.4 + mod_wsgi  ──►  /static/ (staticfiles, servido por Apache)
        │                  /media/  (subidas; carpetas sensibles bloqueadas)
        ▼
Django 6 (system_proyect/)
   ├── MySQL sponsors2 (datos propios)
   └── SQL Server: AdmonANASQL (lectura), Test2, zkbiotime (lectura)
```

- **Shell único de pantallas:** `templates/base_app.html` (barra lateral, cabecera, pie y tema); las bases de cada módulo la extienden.
- **Diseño:** tokens `--ps-*` en `portal_super/static/portal_super/css/portal.css` + tema «Horizon Split» (`horizon.css`).
- **Regla de código:** nada de JavaScript ni CSS dentro del HTML; cada pantalla tiene sus archivos en `<app>/static/<app>/js|css/`.

### 7.1 Aplicaciones (programas) del proyecto

| App | Ruta | Programa |
|---|---|---|
| `accounts` | `/accounts/` | Inicio de sesión, panel, Configuración, usuarios, seguridad, Documentación |
| `core` | `/core/` | Versión, novedades, notificaciones, middleware de seguridad y mantenimiento |
| `tickets` | `/tickets/` | Tickets de soporte con SLA |
| `servicio_tecnico` | `/servicio-tecnico/` | Hub de Control y Servicio Técnico |
| `inventario` | `/inventario/` | Inventario de equipos e Inventario General |
| `mantenimiento` | `/mantenimiento/` | Fichas de mantenimiento, control, entregas, préstamos |
| `inventario_camaras` | `/inventario-camaras/` | Inventario y mantenimiento de cámaras |
| `mantenimiento_mecanico` | `/mantenimiento-mecanico/`, `/mantenimiento-vehiculos/` | Combustibles, aceites y vehículos |
| `datashow` | `/datashow/` | Reservas de DataShow |
| `enfermeria` | `/enfermeria/` | Atenciones médicas y directorio de teléfonos |
| `conducta` | `/conducta/` | Reportes conductuales e informativos, Progress Report, Período Escolar |
| `notas_parcial` | `/notas-parcial/` | Notas de mitad de parcial (lectura de la base académica) |
| `ingresos_notas` | `/ingresos-notas/` | Ingreso de notas, asistencias y tareas al sistema académico |
| `agendas` | `/agendas/` | Agendas semanales y su diseño |
| `moodle_upload` | `/moodle-upload/` | Publicar en Moodle («Upload Moodle») |
| `salidas_bano` | `/salidas-bano/` | Salidas al baño (Colegio y CFP) |
| `reloj` | `/reloj/` | Asistencia del personal, permisos y compensatorio |
| `cfp` | `/cfp/` | Centro de Formación Profesional: cursos, notas y contabilidad del curso |
| `contabilidad` | `/contabilidad/` | Inventario contable y núcleo contable (partida doble) |
| `sponsors` | `/sponsors/` | Padrinos y donantes (base heredada) |
| `red` | `/red/` | ANA Network Manager (IPAM, planos, racks, monitoreo) |
| `desarrollo` | `/desarrollo/` | Gestión de Desarrollo (requerimientos y proyectos) |
| `calculadoras` | `/calculadoras/` | Calculadoras de tiempo y utilidades |
| `asistente` | `/asistente/` | Asistente IA |
| `portal_super` | `/portal/` | Tema visual y portal del superusuario |

## 8. Seguridad (resumen técnico)

- **Sesión obligatoria en todo el sistema** (`TechCareLoginRequiredMiddleware`); las vistas públicas se marcan a propósito con `@login_not_required`.
- **Roles por grupos de Django**; el área del usuario sale de sus grupos, nunca de la URL.
- **Cierre de sesión por inactividad** (constance `SESION_INACTIVIDAD_MIN`, 240 min) en el servidor y en el navegador.
- **Límites de inicio de sesión:** por cuenta y 20 fallos por IP pública en 15 minutos; recuperación de contraseña limitada y enlace de 24 h.
- **Bitácoras:** `django-simple-history` en ~100 modelos; bitácora de seguridad en `logs/seguridad.log` (JSON) y errores en `logs/errores.log`.
- **Descargas privadas** (`Cache-Control: private, no-store`) en PDF, Excel, ZIP y adjuntos.
- **Cookies seguras** (HTTPS), `/admin/` restringido por IP en Apache, carpetas sensibles de `/media/` bloqueadas.
- Detalle completo: [documentación de seguridad](../seguridad/README.md).

## 9. Tareas programadas (cron del usuario admin2)

| Horario | Tarea |
|---|---|
| Cada 2 horas | `manage.py prewarm_notas_cache` — precarga el caché de notas |
| Cada 15 minutos | `manage.py ping_red` — monitoreo de equipos de red |
| Todos los días, 07:00 | `manage.py avisar_limpieza_tanque` — aviso de limpieza del tanque de diésel |
| Día 1 de cada mes, 01:30 | `/home/admin2/bin/backup_mensual.py` — respaldo del proyecto y de MySQL |
| Todos los días, 02:00 (root) | `/usr/local/bin/sync_backups.sh` — copia de respaldos a la PC del administrador |

Los registros de cada tarea quedan en `system_proyect/logs/`. Toda tarea que use `manage.py` necesita `cd` a `system_proyect` antes.

## 10. Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `system_proyect/` | Código Django (una carpeta por app, `templates/`, `static/`, `staticfiles/`) |
| `system_proyect/system_proyect/` | `settings.py`, `urls.py`, estáticos globales |
| `docs/` | Documentación (se ve en Configuración → Documentación) |
| `desktop/` | Código de la app de escritorio (Electron) |
| `mobile/` | Código de la app de Android |
| `moodle_plugin/` | Plugin `local_techcareagenda` para Moodle |
| `media/` | Archivos subidos (no se versiona) |

## 11. Despliegue y mantenimiento

Siempre desde `system_proyect/`:

```bash
../venv/bin/python manage.py check                    # antes de dar por bueno un cambio
../venv/bin/python manage.py migrate                  # si hay migraciones nuevas
sudo ../venv/bin/python manage.py collectstatic --noinput   # si cambió JS o CSS (y subir ?v=N)
sudo systemctl restart apache2
ps -eo pid,lstart,cmd | grep "apache2 -k start" | grep -v grep | head -1   # confirmar la hora de arranque
```

- **Cambios de Python o plantillas:** reiniciar Apache. **Cambios de JS/CSS:** `collectstatic` con sudo + subir `?v=N` + reiniciar.
- **Pruebas automáticas aisladas:** `DJANGO_SECRET_KEY=solo-pruebas ../venv/bin/python manage.py test --settings=system_proyect.settings_test`.
- **Apps .exe y APK:** se compilan con GitHub Actions; el .exe se actualiza solo desde el feed del puerto 453. Un cambio en la web **no** obliga a recompilarlas.
- **Respaldo y restauración:** ver [respaldo y restauración](../seguridad/05_respaldo_restauracion.md).
- **No rotar el `SECRET_KEY`:** las contraseñas de Red y los tokens de Moodle cifrados dependen de él.
