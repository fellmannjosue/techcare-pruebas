# 5. Procedimiento de respaldo y restauración — TechCare

**Estado:** documenta lo que **existe hoy**, lo que se **probó** el 09-nov-2026 y lo que se **propone** (aprobado el 10-nov-2026).
**Referencias:** ISO 27001:2022 8.13 Respaldo de la información · COBIT 2019 DSS04 (Managed Continuity).

## 5.1 Qué existe hoy

| Elemento | Detalle verificado |
|---|---|
| Programa | `/home/admin2/bin/backup_mensual.py` |
| Cuándo | Cron de `admin2`: **día 1 de cada mes a la 01:30** (`30 1 1 * *`) |
| Qué copia | Un `.tar.gz` de `/home/admin2/techcare_project` sin `venv`, `__pycache__` ni `staticfiles`. **Incluye `system_proyect/.env` (credenciales), `media/` (datos de menores) y las migraciones.** Además, un volcado de MySQL `sponsors2` con `mysqldump --single-transaction --routines --triggers`, comprimido |
| Credenciales | El script las lee del `.env` (no están en el script) y pasa la clave por la variable `MYSQL_PWD`, no por la línea de comandos |
| Dónde queda | `/home/admin2/backups/` (2,8 GB; permisos de archivo 664 y de carpeta 775) |
| Copia externa | Cron de root a las 02:00, `/usr/local/bin/sync_backups.sh`: `rsync` a una carpeta compartida SMB en la PC del administrador. **Falla desde el 17-sep-2026** (ver 5.3) |
| Registro | `/home/admin2/backups/backup_mensual.log` y `/home/admin2/sync_backups.log` |
| Qué NO cubre | Las bases de **SQL Server** (académica y ZKBio): las administra otra área. El **vhost de Apache** y la configuración del sistema operativo (`/etc`). El **venv**: se reconstruye con `requirements.txt`, salvo paquetes instalados a mano |

## 5.2 Qué se probó el 09-nov-2026

| Prueba | Resultado | Cómo |
|---|---|---|
| Integridad del último respaldo de sistema (`system_20261101_013002.tar.gz`) | ✅ Correcta | `gzip -t` |
| Integridad del último volcado (`db_sponsors2_20261101_013002.sql.gz`) | ✅ Correcta | `gzip -t` |
| El volcado terminó completo | ✅ Termina con "Dump completed on 2026-11-01 1:30:43" | Se leyó solo la última línea |
| Contenido del tar | ✅ 2 442 entradas; incluye `manage.py`, migraciones y `routing_bl.json`. ⚠️ Incluye el `.env` | `tar -tzf`, solo nombres |
| **Restauración del código** en una carpeta aislada (sin `.env` ni `media`) | ✅ Se extrajo, `compileall` sin errores, `django.setup()` correcto | En el scratchpad de la sesión, que se borró al terminar |
| Restauración de la **base de datos** | ❌ **NO probada** | Requiere una base MySQL aislada; no se creó para no tocar el servidor de producción |
| Restauración de `media/` | ❌ No probada | — |
| Copia externa | ❌ **Falla desde el 17-sep-2026** | `sync_backups.log`: último "sync OK" el 2026-09-17 y luego 84 "share no disponible" |

## 5.3 Problemas detectados

1. **R33 · Crítico.** Los respaldos de octubre y noviembre **solo existen en el mismo servidor**. Una falla de disco o un ransomware se llevaría el sistema y sus respaldos a la vez.
2. **R31 · Alto.** Con respaldo mensual, se pueden perder hasta unos 31 días de notas, reportes y atenciones médicas.
3. **R30 · Alto.** El respaldo lleva el `.env` y datos de menores **sin cifrar**, y se copia a una PC personal.
4. **R32 · Medio.** Nunca se ha probado restaurar la base de datos.

## 5.4 Procedimiento de restauración (para usar en un incidente)

> **Ensayar primero en un servidor o base aislados.** Nunca restaurar encima de producción sin antes respaldar el estado actual, aunque esté dañado.

**A. Restaurar el código** (archivos borrados o modificados, servidor nuevo):

```bash
# 1. Respaldar lo que haya ahora
tar czf /home/admin2/backups/estado_previo_$(date +%Y%m%d_%H%M).tar.gz -C /home/admin2 techcare_project --exclude=techcare_project/venv
# 2. Extraer el respaldo elegido en una carpeta aparte y comparar
mkdir -p /home/admin2/restauracion && tar xzf /home/admin2/backups/system_AAAAMMDD_HHMMSS.tar.gz -C /home/admin2/restauracion
diff -rq /home/admin2/restauracion/techcare_project/system_proyect /home/admin2/techcare_project/system_proyect | less
# 3. Copiar solo lo necesario (o todo) y reconstruir
cd /home/admin2/techcare_project && python3 -m venv venv && venv/bin/pip install -r system_proyect/requirements.txt   # solo si se perdió el venv
cd system_proyect && sudo ../venv/bin/python manage.py collectstatic --noinput && ../venv/bin/python manage.py check
sudo systemctl restart apache2 && ps -eo pid,lstart,cmd | grep "apache2 -k start" | grep -v grep | head -1
```

Permisos que hay que reponer:
- `.env` en `640 admin2:www-data`.
- `media/` escribible por `www-data`.
- `logs/seguridad.log` y `logs/errores.log` en `660` con grupo `www-data`.

**B. Restaurar la base de datos MySQL:**

```bash
# 1. Detener escrituras: modo mantenimiento general (constance MAINTENANCE_MODE) o detener Apache
# 2. Volcado del estado actual, aunque esté dañado
mysqldump --single-transaction sponsors2 | gzip > /home/admin2/backups/antes_de_restaurar_$(date +%Y%m%d_%H%M).sql.gz
# 3. Restaurar PRIMERO en una base aparte y verificar
mysql -e "CREATE DATABASE sponsors2_restaurada CHARACTER SET utf8mb4"
zcat /home/admin2/backups/db_sponsors2_AAAAMMDD_HHMMSS.sql.gz | mysql sponsors2_restaurada
#    (comparar el conteo de filas de tablas clave: auth_user, enfermeria_atencionmedica, conducta_reporte*, tickets_ticket)
# 4. Solo con autorización: apuntar DB_NAME del .env a la base restaurada, o renombrarla. Reiniciar Apache.
```

Las credenciales se toman del `.env` o del operador. **No escribirlas en la línea de comandos**: usar `MYSQL_PWD` o `~/.my.cnf` con permisos 600.

**C. Después de restaurar:**
- Registrar en la bitácora del incidente qué se restauró, desde qué fecha y qué datos se perdieron.
- Avisar a las áreas afectadas qué deben volver a capturar.

## 5.5 Propuesta (aprobada el 10-nov-2026)

| # | Medida | Detalle |
|---|---|---|
| 1 | **Restablecer la copia externa ya** | Reparar el montaje SMB, o mejor, un destino **institucional siempre encendido** (NAS o almacenamiento en la nube de ANA). Alerta por correo si `sync_backups.log` no tiene "sync OK" en 48 h |
| 2 | Volcado **diario** de MySQL | Cron diario a las 01:30. Retención: 14 diarios, 8 semanales y 12 mensuales. El tar del sistema puede seguir siendo mensual |
| 3 | **Sin `.env` dentro del tar** | `--exclude=techcare_project/system_proyect/.env`. El `.env` se guarda aparte, **cifrado** y con acceso solo de los responsables |
| 4 | **Cifrar** los respaldos | `age` o `gpg` con una clave cuyo resguardo está documentado (dos personas, sobre sellado o gestor de contraseñas institucional) |
| 5 | Permisos | Archivos `600` y carpeta `700` en `/home/admin2/backups` |
| 6 | Prueba de restauración **trimestral** | De la base, en una base aislada, con registro del resultado y del tiempo empleado (insumo para el RTO) |
| 7 | Respaldar `/etc/apache2/sites-available/servicios_ana.conf` y el crontab | Dentro del tar mensual |
| 8 | SQL Server | Confirmar por escrito con el área que lo administra la frecuencia y la retención de sus respaldos |
