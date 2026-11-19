# 4. Guía de configuración segura y despliegue

**Versión:** 09-nov-2026. Aplica a la rama `seguridad/iso27001-cobit`.

> **Desplegado en producción el 09-nov-2026 (v8.0.1, commit `5ac4290`)**; respaldo previo en `/home/admin2/backups/pre_iso27001_20261109_2004.tar.gz`. Esta guía queda como referencia de cómo se llevó, cómo verificarlo y cómo revertirlo. Los comandos con `sudo` los ejecuta el operador del servidor.

## 4.1 Configuración segura vigente y esperada

| Ajuste | Valor esperado | Dónde | Comentario |
|---|---|---|---|
| `DEBUG` | `False` (solo `DJANGO_DEBUG=true` lo activa) | `.env` / `settings.py` | Nunca `true` en producción |
| `SECRET_KEY` | Obligatoria, desde el `.env` | `settings.py` | **No rotarla sin plan:** de ella se deriva la clave que cifra las contraseñas de Red y los tokens de Moodle (`red/crypto.py`). Ver 4.6 |
| `.env` | `640`, dueño `admin2`, grupo `www-data` | servidor | Con `600` la app no arranca; comprobar con `sudo -u www-data test -r .env` |
| `ALLOWED_HOSTS` | dominio, IP interna, localhost | `settings.py` | Quitar IP y localhost si no se usan (R15) |
| Cookies | `Secure`, `HttpOnly`, `SameSite=Lax` | `settings.py` | Sitio solo por HTTPS |
| HSTS | Hoy 1 día | `settings.py` | Subir a 1 año cuando se confirme que todo va por HTTPS |
| Sesión | 240 min de inactividad (constance `SESION_INACTIVIDAD_MIN`), tope de 7 días | `settings.py`, middleware | — |
| `PASSWORD_RESET_TIMEOUT` | 86400 (24 h) | `settings.py` | **Nuevo** |
| `TECHCARE_CONFIAR_XFF` | `False` | `settings.py` | **Nuevo.** Solo `True` detrás de un proxy propio |
| `LOGGING` | `logs/seguridad.log`, `logs/errores.log` | `settings.py` | **Nuevo.** Carpeta configurable con `TECHCARE_LOG_DIR` |
| `/admin/` | Solo red interna | vhost | `LocationMatch ^/admin` |
| `/media/` | Lista blanca (fase B) | vhost | Ver `infra/apache_media.conf` |
| Tamaño de petición | 30 MB | vhost | `LimitRequestBody` (preparado) |
| 2FA | Construido, apagado (`DOSFA_ACTIVO`) | constance | Encender al menos para el superusuario |

**Separación de entornos (ISO 8.31):**

| Entorno | Dónde | Base de datos |
|---|---|---|
| Producción | `/home/admin2/techcare_project`, Apache :437 | MySQL `sponsors2`, SQL Server real |
| Pruebas | `techcare-pruebas`, Coolify | `sponsors2_pruebas` |
| Pruebas automáticas | `settings_test.py` | SQLite en memoria; correo en memoria; sin SQL Server, sin SMTP y sin IA |

**Regla:** nunca correr pruebas, scripts ni POST de prueba contra producción.

## 4.2 Antes de desplegar (verificación en la rama)

Ejecutar desde `/home/admin2/techcare_seguridad/system_proyect`:

```bash
# Pruebas de seguridad (SQLite en memoria, datos sintéticos)
DJANGO_SECRET_KEY=solo-pruebas ../../techcare_project/venv/bin/python manage.py test core.tests_seguridad --settings=system_proyect.settings_test
# Suite completa: 66 pruebas, 0 fallos y 4 omitidas el 09-nov-2026
DJANGO_SECRET_KEY=solo-pruebas ../../techcare_project/venv/bin/python manage.py test --settings=system_proyect.settings_test
node --check conducta/static/conducta/js/routing_bl.js
```

## 4.3 Despliegue a producción

**No hay migraciones nuevas** en esta rama. Los cambios son de Python, plantillas, un `.js`, `settings` y un middleware.

1. **Respaldo del código actual** (reversión rápida):
   ```bash
   cd /home/admin2/techcare_project
   tar czf /home/admin2/backups/pre_iso27001_$(date +%Y%m%d_%H%M).tar.gz --exclude=venv --exclude=staticfiles --exclude=media --exclude=.env system_proyect
   ```
2. **Integrar la rama.** La rama parte de un *snapshot* del trabajo pendiente sin commit de producción del 09-nov-2026 (commit `594bfc1`).
   - Si **no** hubo cambios en producción desde entonces, basta con `git merge seguridad/iso27001-cobit`, que avanza rápido sobre ese snapshot.
   - Si los hubo, primero hacer commit de lo pendiente en `main` y luego el merge. Resolver los conflictos a mano en `accounts/views.py`, `core/middleware.py` y `settings.py`.
   - **Commits con `git -c core.hooksPath=/dev/null`** (el hook post-commit reescribe el changelog).
3. **Carpeta de logs con escritura para Apache:**
   ```bash
   cd /home/admin2/techcare_project/system_proyect
   touch logs/seguridad.log logs/errores.log
   sudo chgrp www-data logs/seguridad.log logs/errores.log
   chmod 660 logs/seguridad.log logs/errores.log
   sudo chgrp www-data logs && chmod 2775 logs   # para que la rotación pueda crear seguridad.log.1 …
   ```
   Si este paso no se hace, la app **arranca igual**: el handler es tolerante y simplemente no escribe.
4. **Estáticos:** cambió `conducta/static/conducta/js/routing_bl.js`, y `routing_bl.html` ya pide `?v=3`.
   ```bash
   sudo ../venv/bin/python manage.py collectstatic --noinput
   cmp staticfiles/conducta/js/routing_bl.js conducta/static/conducta/js/routing_bl.js && echo OK
   ```
5. **Check y reinicio:**
   ```bash
   ../venv/bin/python manage.py check
   sudo systemctl restart apache2
   ps -eo pid,lstart,cmd | grep "apache2 -k start" | grep -v grep | head -1   # la hora debe ser la de ahora
   ```
6. **Apache** (después del código): aplicar la fase A de `docs/seguridad/infra/apache_media.conf`, y la fase B cuando se decida.
7. **Verificación en vivo:**
   - Login correcto e incorrecto. `logs/seguridad.log` debe mostrar `login_ok` y `login_fallido`, sin claves.
   - Coordinación BL ve las miniaturas de evidencia. Sin sesión, `/conducta/evidencia/<id>/ver/` → login.
   - Descargar un PDF de enfermería → cabecera `Cache-Control: private, no-store`.
   - Recuperar la contraseña de una cuenta propia → llega 1 correo; el enlace vence en 24 h.
   - Ruteo BL carga la tabla de docentes.

## 4.4 Reversión

| Qué | Cómo |
|---|---|
| Código | `git revert <merge>` (o `git reset --hard <commit anterior>` solo si no hay trabajo nuevo), o restaurar el tar del paso 1. Después `collectstatic` y reiniciar Apache |
| Apache | Restaurar `servicios_ana.conf.bak_<fecha>`, `apache2ctl configtest` y `reload` |
| Logs | No requieren reversión; se pueden borrar |
| Datos | Esta rama **no** cambia el esquema ni los datos. Las evidencias subidas tras el despliegue tendrán nombre uuid y seguirán funcionando con el código anterior, porque la ruta queda guardada en la BD |

**Efectos de comportamiento a comunicar:**
- El superusuario espera 1 minuto tras 3 fallos de login.
- Desde internet, una IP con 20 fallos en 15 minutos espera 15 minutos.
- La recuperación de contraseña admite 3 solicitudes por hora por correo.
- El panel "Accesos" sigue contando un registro por login. Ahora lo crea la señal, con la IP real, y no la vista. "Iniciar sesión como" ya no aparece como un acceso del usuario suplantado.

## 4.5 Dependencias (R28)

`pip_audit -r requirements.txt` del 09-nov-2026 da 73 avisos en 9 paquetes. Orden sugerido, **siempre primero en `techcare-pruebas` o en un venv aparte**, con las pruebas y una revisión manual de PDFs e imágenes:

1. **Parches menores (bajo riesgo):**
   - `certifi` → 2026.10.18
   - `brotli` → 1.2.1
   - `anyio` → 4.14.2
   - `httpcore2` → 2.10.0
   - `httpx2` → 2.12.0
   - `pyjwt` → 2.15.0
   - `djangorestframework` → 3.18.2: revisar la API de Red y de Cámaras.
2. **Mayores (requieren validación):**
   - `Pillow` 12.3 → 13.0: 39 avisos; procesa **todas** las imágenes subidas. Probar las subidas de mantenimiento, cámaras, avatar, evidencias, agendas y `pdf_emoji`.
   - `WeasyPrint` 68.1 → 70.0: todos los PDF. Comparar el tamaño de hoja (`/MediaBox`) de cada reporte.
3. Instalar en producción en una ventana, con respaldo previo del venv: `tar czf venv_pre_<fecha>.tar.gz venv`.
4. Después de instalar, si quedan residuos `~paquete` en `site-packages`, borrarlos con sudo.

## 4.6 Rotación de credenciales (R29, R40) — acción institucional

**Nunca** escribir los valores en un archivo versionado, en un ticket o en un chat.

| Credencial | Dónde se cambia | Después |
|---|---|---|
| MySQL `DB_PASSWORD` | Servidor MySQL: `ALTER USER … IDENTIFIED BY …` | Actualizar el `.env`, reiniciar Apache, revisar los cron (`ping_red`, `prewarm_notas`, backup) |
| SQL Server académico (cuenta de Test2/AdmonANASQL) | SQL Server: lo hace el DBA de la base académica | `.env` (`MSSQL_TEST2_DB_PASSWORD`; también la usan `academico_real` e `inventario_test2`) |
| ZKBio | SQL Server del reloj | `.env` (`MSSQL_ZKBIO_DB_PASSWORD`) |
| sudo de admin2 | `passwd` | Borrar el valor de la memoria del asistente (`~/.claude/projects/*/memory/`). Preferir una regla `sudoers` acotada a `systemctl restart apache2` y `collectstatic` |
| `SECRET_KEY` | **No rotar** sin antes migrar el cifrado de Red y Moodle a una clave propia (`RED_CRED_KEY`) y volver a cifrar. Decisión vigente del 05-nov-2026 | — |

Opcional, y **no sustituye la rotación**: reescribir el historial de git con `git filter-repo` para quitar los secretos viejos. Obliga a volver a clonar en todas partes (pruebas, Coolify, Actions).
