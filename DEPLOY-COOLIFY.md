# Despliegue de pruebas en Coolify

Este repo es una **copia de pruebas** de TechCare, preparada para construir como contenedor.
No apunta a nada por sí solo: todo se configura con variables de entorno.

## ⚠️ Antes que nada
- Este contenedor, con los valores por defecto de `.env.example`, apunta a las **mismas bases
  del servidor** (MySQL en 192.168.10.6, SQL Server en 192.168.10.2). Para pruebas seguras,
  **usa una copia de la base MySQL** y deja `RUN_MIGRATIONS=0`.
- Las lecturas a SQL Server (Test2 / AdmonANASQL / zkbiotime) son mayormente de solo lectura.
- El único módulo que **escribe** al sistema académico legacy es *Ingreso de Notas*: no lo uses
  en el contenedor de pruebas si apunta a datos reales.

## Pasos en Coolify
1. **New Resource → Application → desde este repositorio de Git** (privado).
2. Build Pack: **Dockerfile** (Coolify detecta el `Dockerfile` de la raíz).
3. **Puerto expuesto:** `8000`.
4. **Variables de entorno:** copia el contenido de `.env.example` y rellénalo
   (o pega tu `.env` real de pruebas). Imprescindibles: `DJANGO_SECRET_KEY`,
   `DB_*`, `MSSQL_*`. Deja `USE_WHITENOISE=true`.
5. **Volumen persistente:** monta `/app/system_proyect/media` para no perder las subidas.
6. **Red:** el contenedor debe alcanzar la LAN (192.168.10.x). Si Coolify corre en este
   mismo host, revisa que el contenedor tenga ruta a esas IPs.
7. Deploy. El arranque hace `collectstatic` y levanta gunicorn en el 8000.

## Probar en local (sin Coolify)
```bash
cp .env.example system_proyect/.env    # y rellena los valores
docker compose up --build
# App en http://localhost:8001
```

## Qué trae la imagen
- Python 3.13 · gunicorn · WhiteNoise (sirve los estáticos sin Apache)
- Driver **ODBC 17 for SQL Server** + unixODBC (pyodbc / mssql-django)
- Libs de **WeasyPrint** (pango/cairo) para los PDF
- Zona horaria `America/Tegucigalpa` y locale español

## Diferencias vs. el repo de producción
- Añadido: `Dockerfile`, `entrypoint.sh`, `docker-compose.yml`, `.dockerignore`,
  `.env.example`, este archivo.
- `settings.py`: un bloque **gated por `USE_WHITENOISE`** que solo se activa en contenedor
  (en el servidor actual Apache sigue sirviendo los estáticos; el comportamiento no cambia).
