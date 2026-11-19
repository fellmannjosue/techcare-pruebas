# system_proyect/settings_test.py
# <--- hecho por claude code (09-nov-2026, revisión ISO 27001/COBIT): configuración AISLADA para pruebas.
"""Pruebas automáticas sin tocar producción.

- Base de datos SQLite en memoria (datos sintéticos que se crean y se destruyen en cada corrida).
- Ninguna conexión a MySQL ni a SQL Server: los alias externos apuntan a SQLite vacías y los
  routers externos se desactivan.
- Correo en memoria (locmem): nunca sale un correo real.
- Caché local en memoria.
- Clave secreta sintética: NO es la de producción.

Uso (desde system_proyect/):
    DJANGO_SECRET_KEY=solo-pruebas ../venv/bin/python manage.py test --settings=system_proyect.settings_test seguridad_tests
"""
import os

os.environ.setdefault('DJANGO_SECRET_KEY', 'solo-pruebas-no-es-la-clave-real')

from .settings import *  # noqa: E402,F401,F403

SECRET_KEY = 'solo-pruebas-no-es-la-clave-real'
DEBUG = False

_SQLITE = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}
DATABASES = {'default': dict(_SQLITE)}
DATABASE_ROUTERS = []

CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']  # solo velocidad en pruebas

# Sin integraciones externas.
ANTHROPIC_API_KEY = ''
MEDIA_ROOT = os.path.join('/tmp', 'techcare_test_media')

# Los tests usan el host real permitido; las cookies seguras no impiden el cliente de pruebas.
ALLOWED_HOSTS = ['servicios.ana-hn.org', 'testserver']
