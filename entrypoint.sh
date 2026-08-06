#!/bin/sh
# Arranque del contenedor TechCare (pruebas).
set -e

cd /app/system_proyect

echo "▶ collectstatic…"
python manage.py collectstatic --noinput

# ⚠️ Migraciones DESACTIVADAS por defecto: este contenedor de pruebas apunta por
# defecto a las MISMAS bases del servidor. Migrar alteraría producción. Solo se
# ejecutan si RUN_MIGRATIONS=1 (úsalo únicamente contra una base de PRUEBA).
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "▶ migrate… (RUN_MIGRATIONS=1)"
  python manage.py migrate --noinput
else
  echo "▶ migrate OMITIDO (RUN_MIGRATIONS!=1) — no se toca el esquema de la BD."
fi

echo "▶ gunicorn en :8000"
exec gunicorn system_proyect.wsgi:application \
     --bind 0.0.0.0:8000 \
     --workers "${GUNICORN_WORKERS:-3}" \
     --timeout 120 \
     --access-logfile - --error-logfile -
