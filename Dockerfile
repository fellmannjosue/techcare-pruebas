# TechCare · imagen de PRUEBAS para Coolify
# Python 3.13 + driver ODBC de SQL Server 17 + libs de WeasyPrint + gunicorn.
FROM python:3.13-slim-bookworm

# ── Ajustes de entorno ──
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=system_proyect.settings \
    TZ=America/Tegucigalpa

# ── Dependencias de sistema ──
#   · build-essential + default-libmysqlclient-dev + pkg-config → compilar mysqlclient
#   · libpango/cairo/gdk-pixbuf/ffi + shared-mime-info + fuentes → WeasyPrint (PDF)
#   · msodbcsql17 + unixodbc-dev → pyodbc / mssql-django (SQL Server)
#   · locales + tzdata → fechas en español y zona horaria de Honduras
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg ca-certificates apt-transport-https \
        build-essential pkg-config default-libmysqlclient-dev \
        libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev libcairo2 \
        shared-mime-info fonts-liberation fonts-dejavu-core \
        unixodbc unixodbc-dev \
        locales tzdata \
    && curl -sSL -O https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && sed -i 's/# es_HN.UTF-8/es_HN.UTF-8/; s/# es_ES.UTF-8/es_ES.UTF-8/' /etc/locale.gen \
    && locale-gen \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV LANG=es_ES.UTF-8 LC_ALL=es_ES.UTF-8

WORKDIR /app

# ── Dependencias de Python (capa cacheable) ──
# <--- hecho por claude code: se EXCLUYE mod_wsgi — es el módulo de Apache (necesita
# apxs/headers de Apache para compilar) y aquí servimos con gunicorn, no con Apache.
COPY system_proyect/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && grep -viE '^[[:space:]]*mod[_-]wsgi' /app/requirements.txt > /app/requirements.docker.txt \
    && pip install -r /app/requirements.docker.txt \
    && pip install "gunicorn>=22" "whitenoise>=6.6"

# ── Código ──
COPY . /app

# gunicorn y manage.py corren desde la carpeta del proyecto
WORKDIR /app/system_proyect

# Puerto de la app (Coolify lo mapea por su proxy)
EXPOSE 8000

# El arranque (collectstatic → migraciones opcionales → gunicorn) va en el entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
