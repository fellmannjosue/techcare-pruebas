# ─────────────────────────────────────────────────────────────
# 1. IMPORTACIONES BÁSICAS
# ─────────────────────────────────────────────────────────────
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar las variables desde el archivo .env
load_dotenv()

# ─────────────────────────────────────────────────────────────
# 2. DIRECTORIO BASE DEL PROYECTO
# ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────────────────────
# 3. SEGURIDAD
# ─────────────────────────────────────────────────────────────
_secret_key = os.getenv('DJANGO_SECRET_KEY')
if not _secret_key:
    raise ValueError("DJANGO_SECRET_KEY no está definida en el archivo .env")
SECRET_KEY = _secret_key
DEBUG = (os.getenv('DJANGO_DEBUG', 'false') == 'true')


ALLOWED_HOSTS = [
    'servicios.ana-hn.org',
    'www.servicios.ana-hn.org',
    '192.168.10.6',
    '127.0.0.1',
    'localhost',
]

CSRF_TRUSTED_ORIGINS = [
    'https://servicios.ana-hn.org:437',
    'https://192.168.10.6:437',
    # <--- hecho por claude code (PRUEBAS): Coolify sirve por HTTP en :451; pruebas directo (sin Coolify) en :455
    'http://192.168.10.6:451',
    'http://localhost:451',
    'http://localhost:8001',
    'http://192.168.10.6:455',
    'http://localhost:455',
]

# ─────────────────────────────────────────────────────────────
# 4. APLICACIONES INSTALADAS
# ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Jazzmin (comentado — reemplazado por Unfold)
    # 'jazzmin',

    # Unfold — panel de administración
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.inlines',
    'unfold.contrib.import_export',
    'unfold.contrib.simple_history',
    'unfold.contrib.constance',
    # guardian y location_field requieren configuración adicional
    # 'unfold.contrib.guardian',
    # 'unfold.contrib.location_field',

    # Apps de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',

    # Paquetes de terceros requeridos por unfold contrib
    'import_export',
    'simple_history',
    'constance',
    'constance.backends.database',

    # Apps personalizadas
    'accounts',
    'tickets',
    'inventario',
    'mantenimiento',
    'servicio_tecnico',
    'mantenimiento_mecanico',   # <--- hecho por claude code (01-oct-2026): control de combustibles y aceites   # <--- hecho por claude code (28-sep-2026): hub Control y Servicio Técnico (Inventario + Mantenimiento)
    'sponsors',
    'enfermeria',

    'conducta',
    'agendas',
    'moodle_upload',   # <--- hecho por claude code (15-oct-2026): publicar las agendas en Moodle (plugin local_techcareagenda)
    'core.apps.CoreConfig',
    'rest_framework',   # <--- hecho por claude code: API del frontend de cámaras
    'rest_framework.authtoken',  # <--- hecho por claude code: tokens para la API REST de Red (scripts/integraciones)
    'reloj',
    'calculadoras',
    'cfp',
    'notas_parcial',
    'inventario_camaras',
    'portal_super',   # <--- hecho por claude code: portal nuevo del superusuario (SPA + API)

    # Apps en construcción
    # <--- hecho por claude code: 'atencion_padres' y 'camaras' eliminadas (no se usaban)
    'salidas_bano',
    'ingresos_notas',  # <--- hecho por claude code: ingreso de notas al sistema academico
    'desarrollo',  # <--- hecho por claude code: Gestión de Desarrollo (requerimientos/proyectos)
    'contabilidad',  # <--- hecho por claude code: Programa de Contabilidad (TC-PRY-0002)
    'red',  # <--- hecho por claude code: ANA Network Manager (IPAM/documentación de red) — Fase 1
    'datashow',   # <--- hecho por claude code (03-nov-2026): Solicitud/reserva de DataShow con calendario y autorización
    'asistente',  # <--- hecho por claude code (26-oct-2026; producción 06-nov-2026): asistente IA (Claude)
]


# ─────────────────────────────────────────────────────────────
# 5. MIDDLEWARE
# ─────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.DescargasPrivadasMiddleware',   # <--- hecho por claude code (09-nov-2026): PDF/Excel/ZIP con Cache-Control: private, no-store
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.TechCareLoginRequiredMiddleware',   # <--- hecho por claude code (seguridad 05-nov-2026): todo pide sesión salvo @login_not_required
    'core.middleware.SesionInactividadMiddleware',   # <--- hecho por claude code (28-sep-2026): caducidad deslizante por inactividad
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.MaintenanceModeMiddleware',
    'core.auditoria.AuditoriaMiddleware',   # <--- hecho por claude code (10-nov-2026): rol Auditoría (ve como superusuario, solo lectura; GET siempre en rollback)
    'core.middleware.EmbedVentanaMiddleware',   # <--- hecho por claude code (09-nov-2026): formularios dentro de la ventana «Registrar» (?embed=1)
    'core.middleware.CanalAppMiddleware',   # <--- hecho por claude code (09-nov-2026): programas por canal (Web/.exe/APK)
    'simple_history.middleware.HistoryRequestMiddleware',
    # <--- hecho por claude code (seguridad): 2FA periódico por correo. Inactivo mientras
    # DOSFA_ACTIVO (constance) esté apagado; va al final, tras autenticación y sesión.
    'accounts.dosfa.Dosfa2FAMiddleware',
    'accounts.suplantar.SuplantacionMiddleware',   # <--- hecho por claude code (12-oct-2026): "Iniciar sesión como" (solo superusuario)
    'core.offline_beta.OfflineBetaMiddleware',   # <--- hecho por claude code (12-nov-2026): modo sin conexión (beta), solo superusuario
]

# <--- hecho por claude code (PRUEBAS): sin Apache para estáticos, WhiteNoise los sirve desde gunicorn (USE_WHITENOISE).
if os.getenv('USE_WHITENOISE', 'false') == 'true':
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
    }

# ─────────────────────────────────────────────────────────────
# django-simple-history
# ─────────────────────────────────────────────────────────────
SIMPLE_HISTORY_HISTORY_ID_USE_UUID = True
SIMPLE_HISTORY_REVERT_DISABLED = True


# ─────────────────────────────────────────────────────────────
# 6. URLS Y WSGI
# ─────────────────────────────────────────────────────────────
ROOT_URLCONF = 'system_proyect.urls'
WSGI_APPLICATION = 'system_proyect.wsgi.application'


# ─────────────────────────────────────────────────────────────
# 7. TEMPLATES
# ─────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.current_year',
                'core.context_processors.nav_context',
                'asistente.context_processors.asistente_context',   # <--- hecho por claude code: asistente IA (se muestra solo si hay ANTHROPIC_API_KEY)
                'core.context_processors.version_context',
                'core.auditoria.context',   # <--- hecho por claude code (10-nov-2026): aviso «Modo auditoría»
                'core.offline_beta.context',   # <--- hecho por claude code (12-nov-2026): modo sin conexión (beta), solo superusuario
                'accounts.suplantar.context',   # <--- hecho por claude code (12-oct-2026): aviso "Estás usando la cuenta de…"   # <--- hecho por claude code: versión + novedades
            ],
        },
    },
]


# ─────────────────────────────────────────────────────────────
# 8. BASE DE DATOS (MySQL)
# ─────────────────────────────────────────────────────────────
DATABASES = {
    # Base de datos principal (MySQL Workbench → sponsors3)
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'sponsors2'),
        'USER': os.getenv('DB_USER', 'admin3'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', '192.168.10.6'),
        'PORT': os.getenv('DB_PORT', '3306'),
    },

    # Conexión al SQL Server remoto (Test2)
    'padres_sqlserver': {
    'ENGINE': 'mssql',
    'NAME': os.getenv('MSSQL_TEST2_DB_NAME', 'Test2'),
    'USER': os.getenv('MSSQL_TEST2_DB_USER', 'admin2'),
    'PASSWORD': os.getenv('MSSQL_TEST2_DB_PASSWORD'),
    'HOST': os.getenv('MSSQL_TEST2_DB_HOST', '192.168.10.2'),
    'PORT': os.getenv('MSSQL_TEST2_DB_PORT', '1433'),
    'OPTIONS': {
        'driver': os.getenv('MSSQL_ODBC_DRIVER', 'ODBC Driver 17 for SQL Server'),
    },
},

# <--- hecho por claude code: base ACADÉMICA REAL (AdmonANASQL), mismo servidor y
# credenciales que Test2 — solo cambia el nombre de la base. Hoy `admin2` NO tiene
# permisos ahí; hasta que se los den, `NOTAS_PARCIAL_DB` sigue apuntando a Test2.
'academico_real': {
    'ENGINE': 'mssql',
    'NAME': os.getenv('MSSQL_REAL_DB_NAME', 'AdmonANASQL'),
    'USER': os.getenv('MSSQL_TEST2_DB_USER', 'admin2'),
    'PASSWORD': os.getenv('MSSQL_TEST2_DB_PASSWORD'),
    'HOST': os.getenv('MSSQL_TEST2_DB_HOST', '192.168.10.2'),
    'PORT': os.getenv('MSSQL_TEST2_DB_PORT', '1433'),
    'OPTIONS': {
        'driver': os.getenv('MSSQL_ODBC_DRIVER', 'ODBC Driver 17 for SQL Server'),
    },
},

# Conexión al SQL Server remoto (zkbiotime)
'zkbio_sqlserver': {
    'ENGINE': 'mssql',
    'NAME': os.getenv('MSSQL_ZKBIO_DB_NAME', 'zkbiotime'),
    'USER': os.getenv('MSSQL_ZKBIO_DB_USER', 'sa'),
    'PASSWORD': os.getenv('MSSQL_ZKBIO_DB_PASSWORD'),
    'HOST': os.getenv('MSSQL_ZKBIO_DB_HOST', '192.168.10.2'),
    'PORT': os.getenv('MSSQL_ZKBIO_DB_PORT', '14332'),
    'OPTIONS': {
        'driver': os.getenv('MSSQL_ODBC_DRIVER', 'ODBC Driver 17 for SQL Server'),
    },
}


}

# <--- hecho por claude code: alias INDEPENDIENTE para el Inventario institucional en
# SQL Server (base Test2). Es SOLO LECTURA; su capa de acceso vive en
# contabilidad/sqlserver_inventory. Usa variables propias INV_TEST2_DB_* (por ahora sus
# valores pueden corresponder a admin2: si no están definidas, caen a las MSSQL_TEST2_*
# ya existentes). NO reutiliza el alias padres_sqlserver.
# - extra_params fija el APP name que identifica la app/ambiente en la auditoría SQL.
# - Encrypt/TrustServerCertificate SOLO si el DBA define la política (sin valores asumidos).
_inv_extra_params = 'APP=ANA-Inventario-Python-Test2'
if os.getenv('INV_TEST2_ENCRYPT'):
    _inv_extra_params += ';Encrypt=' + os.getenv('INV_TEST2_ENCRYPT')
if os.getenv('INV_TEST2_TRUST_CERT'):
    _inv_extra_params += ';TrustServerCertificate=' + os.getenv('INV_TEST2_TRUST_CERT')

DATABASES['inventario_test2'] = {
    'ENGINE': 'mssql',
    'NAME': os.getenv('INV_TEST2_DB_NAME') or os.getenv('MSSQL_TEST2_DB_NAME', 'Test2'),
    'USER': os.getenv('INV_TEST2_DB_USER') or os.getenv('MSSQL_TEST2_DB_USER', 'admin2'),
    'PASSWORD': os.getenv('INV_TEST2_DB_PASSWORD') or os.getenv('MSSQL_TEST2_DB_PASSWORD'),
    'HOST': os.getenv('INV_TEST2_DB_HOST') or os.getenv('MSSQL_TEST2_DB_HOST', '192.168.10.2'),
    'PORT': os.getenv('INV_TEST2_DB_PORT') or os.getenv('MSSQL_TEST2_DB_PORT', '1433'),
    'OPTIONS': {
        'driver': os.getenv('INV_TEST2_ODBC_DRIVER') or os.getenv('MSSQL_ODBC_DRIVER', 'ODBC Driver 17 for SQL Server'),
        'extra_params': _inv_extra_params,
    },
}

# <--- hecho por claude code: router que BLINDA el alias inventario_test2 contra migraciones
# (jamás se crean/alteran objetos Django ni institucionales dbo.tblInv* en Test2).
DATABASE_ROUTERS = ['contabilidad.db_router.InventarioTest2Router']

# <--- hecho por claude code: la tarjeta "Inventario institucional (SQL Server)" del hub de
# Inventario NO se muestra hasta autorización explícita. Se enciende con
# INV_TEST2_MOSTRAR_TARJETA=1 en el .env (por defecto apagada).
INVENTARIO_SQL_TARJETA = os.getenv('INV_TEST2_MOSTRAR_TARJETA', '0') == '1'

# <--- hecho por claude code: qué base usa "Notas Mitad de Parcial". Se cambia con
# la variable de entorno NOTAS_PARCIAL_DB=academico_real (sin tocar código) en
# cuanto admin2 tenga permisos de lectura en AdmonANASQL. El resto de módulos
# (Ingreso de Notas, reloj, enfermería…) siguen en Test2.
NOTAS_PARCIAL_DB = os.getenv('NOTAS_PARCIAL_DB', 'padres_sqlserver')

# <--- hecho por claude code: se migra ÁREA POR ÁREA, según dónde ya haya permisos
# en AdmonANASQL. Las que estén aquí usan NOTAS_PARCIAL_DB; el resto sigue en Test2.
# Vacío = ninguna migrada. Se listan separadas por coma en el .env.
NOTAS_PARCIAL_AREAS_REAL = [
    a.strip() for a in os.getenv('NOTAS_PARCIAL_AREAS_REAL', '').split(',') if a.strip()
]

# ─────────────────────────────────────────────────────────────
# 9. VALIDADORES DE CONTRASEÑAS
# ─────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ─────────────────────────────────────────────────────────────
# 10. INTERNACIONALIZACIÓN
# ─────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-hn'
TIME_ZONE = 'America/Tegucigalpa'
USE_I18N = True
USE_TZ = False


# ─────────────────────────────────────────────────────────────
# 11. CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS Y MEDIA
# ─────────────────────────────────────────────────────────────
STATIC_URL = '/static/'

# Lista “bruta” de posibles carpetas static por app
_raw_static_dirs = [
    BASE_DIR / "system_proyect/tickets/static",
    BASE_DIR / "system_proyect/accounts/static",
    BASE_DIR / "system_proyect/inventario/static",
    BASE_DIR / "system_proyect/mantenimiento/static",
    BASE_DIR / "system_proyect/sponsors/static",
    BASE_DIR / "system_proyect/agendas/static",
    BASE_DIR / "system_proyect/calculadoras/static",
    BASE_DIR / "system_proyect/conducta/static",
    BASE_DIR / "system_proyect/core/static",
    BASE_DIR / "system_proyect/enfermeria/static",
    BASE_DIR / "system_proyect/cfp/static",
    BASE_DIR / "system_proyect/notas_parcial/static",
    BASE_DIR / "system_proyect/reloj/static",
    BASE_DIR / "system_proyect/static",
    BASE_DIR / "system_proyect/system_proyect/static",
]

# Filtra solo las que existen en disco
STATICFILES_DIRS = [
    str(p) for p in _raw_static_dirs
    if p.exists()
]

STATIC_ROOT = BASE_DIR / "staticfiles"

# ─────────────────────────────────────────────────────────────
# 12. ARCHIVOS DE USUARIO (MEDIA)
# ─────────────────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ──────────────────────────────
# SESIONES Y LOGIN (1 HORA)
# ──────────────────────────────

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/accounts/menu/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# <--- hecho por claude code (28-sep-2026): tope de la cookie; la caducidad REAL la pone SesionInactividadMiddleware
# (constance SESION_INACTIVIDAD_MIN, deslizante en cada petición). Antes era 1 año y la sesión nunca caducaba.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 días como máximo absoluto

# Renovar la sesión con cada request
SESSION_SAVE_EVERY_REQUEST = True

# No cerrar la sesión al cerrar el navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# <--- hecho por claude code (seguridad): el sitio SOLO se sirve por HTTPS (único vhost
# *:437 con SSLEngine on; no hay vhost por HTTP). El navegador siempre conecta por https,
# así que la cookie con flag Secure viaja bien. Antes iban sin él y podían filtrarse si
# alguna vez se accedía por http plano.
# <--- hecho por claude code (PRUEBAS): por HTTP las cookies no pueden ser solo-HTTPS (COOKIES_SECURE=true para volverlas seguras)
SESSION_COOKIE_SECURE = (os.getenv('COOKIES_SECURE', 'false') == 'true')
CSRF_COOKIE_SECURE = (os.getenv('COOKIES_SECURE', 'false') == 'true')
SESSION_COOKIE_HTTPONLY = True          # ya lo estaba de facto; se fija explícito
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# HSTS: el navegador recuerda usar HTTPS para servicios.ana-hn.org. Sin includeSubDomains
# NI preload a propósito, para no afectar otros subdominios de ana-hn.org que puedan usar
# HTTP. Empieza en 1 día (reversible); subir a 1 año cuando esté probado.
SECURE_HSTS_SECONDS = 86400
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

# <--- hecho por claude code (09-nov-2026, revisión ISO 27001/COBIT) ─────────────────────────
# Recuperación de contraseña: el correo dice "válido por 24 horas"; el valor por defecto de Django son 3 días.
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24

# Apache sirve con mod_wsgi DIRECTO (sin proxy inverso): la cabecera X-Forwarded-For la escribe el
# cliente y no sirve para saber la IP. Solo poner True si algún día se pone un proxy propio delante.
TECHCARE_CONFIAR_XFF = False

# Bitácora de seguridad y de errores en archivo (logs/). Antes NO había LOGGING: con DEBUG=False los
# errores 500 no quedaban en ningún lado. El handler es tolerante: si www-data no puede escribir en la
# carpeta, la app arranca igual (ver docs/seguridad/04_guia_configuracion_despliegue.md).
TECHCARE_LOG_DIR = os.getenv('TECHCARE_LOG_DIR', str(BASE_DIR / 'logs'))
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'linea': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'},
    },
    'filters': {
        'require_debug_true': {'()': 'django.utils.log.RequireDebugTrue'},
    },
    'handlers': {
        'seguridad': {
            'class': 'core.seguridad_eventos.ArchivoTolerante',
            'filename': os.path.join(TECHCARE_LOG_DIR, 'seguridad.log'),
            'formatter': 'linea',
        },
        'errores': {
            'class': 'core.seguridad_eventos.ArchivoTolerante',
            'filename': os.path.join(TECHCARE_LOG_DIR, 'errores.log'),
            'formatter': 'linea',
            'level': 'WARNING',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['require_debug_true'],
        },
    },
    'loggers': {
        'techcare.seguridad': {'handlers': ['seguridad'], 'level': 'INFO', 'propagate': False},
        'django.security': {'handlers': ['seguridad', 'errores'], 'level': 'WARNING', 'propagate': False},
        'django.request': {'handlers': ['errores'], 'level': 'ERROR', 'propagate': False},
        'django': {'handlers': ['console'], 'level': 'INFO'},
    },
}

# Motor de sesiones: solo BD (más estable frente a reinicios de Apache)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
    }
}

# Opcional: Si usas subdominios y quieres que la cookie funcione en todos, descomenta:
# SESSION_COOKIE_DOMAIN = '.ana-hn.org'
# CSRF_COOKIE_DOMAIN = '.ana-hn.org'


# ─────────────────────────────────────────────────────────────
# CONSTANCE (configuración dinámica desde el admin)
# ─────────────────────────────────────────────────────────────
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_CONFIG = {
    'MAINTENANCE_MODE':    (False, 'Activar/desactivar modo mantenimiento', bool),
    'MAINTENANCE_AREA':    ('all', 'Área bloqueada: all | bilingue | colegio', str),
    'MAINTENANCE_MESSAGE': (
        'El sistema se encuentra temporalmente en mantenimiento. '
        'Disculpe los inconvenientes. Estaremos de vuelta pronto.',
        'Mensaje que verán los usuarios en la página de mantenimiento',
        str,
    ),
    'MAINTENANCE_END_TIME': (
        '',
        'Fecha y hora de fin del mantenimiento (formato YYYY-MM-DDTHH:MM). Vacío = sin límite.',
        str,
    ),
    'MAINTENANCE_BLOCKED_USERS': (
        '',
        'Emails bloqueados específicamente (separados por coma). Si hay valores, SOLO esos usuarios ven el mantenimiento.',
        str,
    ),
    # <--- hecho por claude code: bloqueo selectivo de formularios (JSON {modulo: lectura|bloqueado})
    'MAINTENANCE_MODULES': (
        '',
        'Bloqueo por formulario, en JSON. Ej: {"agendas":"lectura","tickets":"bloqueado"}. Vacío = todo normal.',
        str,
    ),
    # <--- hecho por claude code (seguridad): crear usuarios ON/OFF. Apagado = nadie
    # puede crear cuentas, ni siquiera un administrador desde la pantalla de registro.
    'REGISTRO_USUARIOS_ACTIVO': (
        True,
        'Permitir crear usuarios nuevos (registro). Apagado = creación de cuentas bloqueada.',
        bool,
    ),
    # <--- hecho por claude code (28-sep-2026): cierre de sesión por INACTIVIDAD. Lo usan el JS (aviso + cierre con la
    # pestaña abierta) y el middleware SesionInactividadMiddleware (la sesión del servidor caduca si no hay peticiones
    # en ese tiempo, p. ej. con la pestaña cerrada). Antes la sesión duraba 1 año y solo cerraba el JS.
    'SESION_INACTIVIDAD_MIN': (
        240,
        'Minutos sin actividad para cerrar la sesión automáticamente (aplica a todos los usuarios).',
        int,
    ),
    # 2FA por correo. APAGADO por defecto: se enciende cuando el equipo lo tenga claro.
    # Al encender, se pide un código al correo según el rol (superusuario cada 15 días,
    # staff cada 30, usuario cada 60).
    'DOSFA_ACTIVO': (
        False,
        'Activar verificación en dos pasos (2FA) por correo. Apagado = no se pide a nadie.',
        bool,
    ),
    # <--- hecho por claude code (10-sep-2026): programas ocultos a TODOS los usuarios
    # (lista JSON de claves de core/programas.py). Se maneja desde Configuración → Seguridad.
    'PROGRAMAS_OCULTOS': (
        '',
        'Programas desactivados/ocultos para todos los usuarios, en JSON. Ej: ["sponsors","reloj"]. Vacío = todos visibles.',
        str,
    ),
    # <--- hecho por claude code (09-nov-2026): programas OCULTOS por canal, JSON {"web":[...],"exe":[...],"apk":[...]}.
    # Se maneja desde Configuración → Programas por aplicación (core/canales.py).
    # <--- hecho por claude code (10-nov-2026): programas donde el rol Auditoría puede EDITAR (JSON lista de claves)
    'AUDITORIA_EDITAR': (
        '',
        'Rol Auditoría: programas donde puede editar, en JSON. Ej: ["reloj"]. Vacío = solo lectura en todo.',
        str,
    ),
    'PROGRAMAS_POR_CANAL': (
        '',
        'Programas ocultos por canal (web / exe / apk), en JSON. Vacío = todo visible en todos.',
        str,
    ),
    # <--- hecho por claude code (13-nov-2026): modo sin conexión (beta), solo superusuario — Configuración → Sistema → Modo sin conexión
    'OFFLINE_BETA': (True, 'Modo sin conexión (beta) para el superusuario: guarda las páginas que abre para verlas sin red.', bool),
}
CONSTANCE_CONFIG_FIELDSETS = {
    'Modo Mantenimiento': {
        'fields': (
            'MAINTENANCE_MODE',
            'MAINTENANCE_AREA',
            'MAINTENANCE_MESSAGE',
            'MAINTENANCE_END_TIME',
            'MAINTENANCE_BLOCKED_USERS',
            'MAINTENANCE_MODULES',
        ),
        'collapse': False,
    },
    # <--- hecho por claude code (seguridad): interruptores de seguridad
    'Seguridad': {
        'fields': ('REGISTRO_USUARIOS_ACTIVO', 'SESION_INACTIVIDAD_MIN', 'DOSFA_ACTIVO', 'PROGRAMAS_OCULTOS', 'PROGRAMAS_POR_CANAL', 'AUDITORIA_EDITAR', 'OFFLINE_BETA'),
        'collapse': False,
    },
}

# ─────────────────────────────────────────────────────────────
# 13. CORREO ELECTRÓNICO (SMTP)
# ─────────────────────────────────────────────────────────────
# <--- hecho por claude code (PRUEBAS): con datos copiados de producción, un envío real le llegaría a usuarios REALES.
# Default: LISTA BLANCA — SMTP solo a EMAILS_PRUEBA_PERMITIDOS; a los demás se escribe en el log. EMAILS_REALES=true = como producción.
if os.getenv('EMAILS_REALES', 'false') == 'true':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'core.email_backend_pruebas.ListaBlancaBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'techcare.app2024@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ── SMTP secundario: Módulo Enfermería ──────────────────────
# Usa enfermeria@ana-hn.org; si EMAIL_ENF_PASSWORD está vacío
# cae automáticamente al SMTP principal (Gmail).
EMAIL_ENFERMERIA = {
    'HOST':     os.getenv('EMAIL_ENF_HOST',     'mail.ana-hn.org'),
    'PORT':     int(os.getenv('EMAIL_ENF_PORT', 587)),
    'USE_TLS':  os.getenv('EMAIL_ENF_USE_TLS',  'True')  == 'True',
    'USE_SSL':  os.getenv('EMAIL_ENF_USE_SSL',  'False') == 'True',
    'USER':     os.getenv('EMAIL_ENF_USER',     'enfermeria@ana-hn.org'),
    'PASSWORD': os.getenv('EMAIL_ENF_PASSWORD', ''),
}

# ── SMTP secundario: Coordinación Bilingüe ──────────────────
# Conducta BL, Notas Parcial BL, confirmaciones BL
EMAIL_COORD_BL = {
    'HOST':     os.getenv('EMAIL_COORD_BL_HOST',     'mail.ana-hn.org'),
    'PORT':     int(os.getenv('EMAIL_COORD_BL_PORT', 587)),
    'USE_TLS':  os.getenv('EMAIL_COORD_BL_USE_TLS',  'True')  == 'True',
    'USE_SSL':  os.getenv('EMAIL_COORD_BL_USE_SSL',  'False') == 'True',
    'USER':     os.getenv('EMAIL_COORD_BL_USER',     'coordinacion_bl@ana-hn.org'),
    'PASSWORD': os.getenv('EMAIL_COORD_BL_PASSWORD', ''),
}

# ── SMTP secundario: Coordinación Colegio ───────────────────
# Conducta Colegio, Notas Parcial Colegio
EMAIL_COORD_COL = {
    'HOST':     os.getenv('EMAIL_COORD_COL_HOST',     'mail.ana-hn.org'),
    'PORT':     int(os.getenv('EMAIL_COORD_COL_PORT', 587)),
    'USE_TLS':  os.getenv('EMAIL_COORD_COL_USE_TLS',  'True')  == 'True',
    'USE_SSL':  os.getenv('EMAIL_COORD_COL_USE_SSL',  'False') == 'True',
    'USER':     os.getenv('EMAIL_COORD_COL_USER',     'coordinacion_col@ana-hn.org'),
    'PASSWORD': os.getenv('EMAIL_COORD_COL_PASSWORD', ''),
}









# ─────────────────────────────────────────────────────────────
# 14. CAMPO PRIMARY KEY POR DEFECTO
# ─────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─────────────────────────────────────────────────────────────
# 15. URL PARA ADMIN (opcional, por si quieres moverla)
# ─────────────────────────────────────────────────────────────
ADMIN_SITE_URL = '/accounts/login/'


# ─────────────────────────────────────────────────────────────
# 16. INTEGRACIÓN OPENAI / IA
# ─────────────────────────────────────────────────────────────

# <--- hecho por claude code (03-sep-2026): IA desactivada en PRODUCCIÓN a pedido del usuario.
# El experimento del chat IA se moverá a techcare-pruebas. Para reactivar: descomentar
# estas 4 líneas y las OPENAI_* del .env (validado 03-sep-2026: la clave funciona).
# <--- hecho por claude code (PRUEBAS): aquí la IA SÍ está activa (sandbox /tickets/ia/)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL_DEFAULT = os.getenv('OPENAI_MODEL_DEFAULT', 'gpt-4o')
OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '500'))
OPENAI_TIMEOUT = int(os.getenv('OPENAI_TIMEOUT', '20'))


# ─────────────────────────────────────────────────────────────
# JAZZMIN — comentado (reemplazado por Unfold)
# ─────────────────────────────────────────────────────────────
# JAZZMIN_SETTINGS = { ... }
# JAZZMIN_UI_TWEAKS = { ... }

# ─────────────────────────────────────────────────────────────
# UNFOLD — Configuración del panel de administración
# ─────────────────────────────────────────────────────────────
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_TITLE": "Plataforma Admin ANA",
    "SITE_HEADER": "Plataforma Admin ANA",
    "SITE_SUBHEADER": "Asociación Nuevo Amanecer",
    "SITE_URL": "javascript:history.back()",
    "SITE_ICON": lambda request: "/static/accounts/img/nuevo.ico",
    "SITE_LOGO": lambda request: "/static/accounts/img/ana-transformed.png",
    "SITE_SYMBOL": "settings",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "DASHBOARD_CALLBACK": "core.admin_dashboard.dashboard_callback",
    # <--- hecho por claude code (16-oct-2026): paleta de TechCare (índigo, entre el azul #2563eb y el violeta #7c3aed); antes naranja
    "COLORS": {
        "primary": {
            "50":  "oklch(96.2% 0.018 272.314)",
            "100": "oklch(93.0% 0.034 272.788)",
            "200": "oklch(87.0% 0.065 274.039)",
            "300": "oklch(78.5% 0.115 274.713)",
            "400": "oklch(67.3% 0.182 276.935)",
            "500": "oklch(58.5% 0.233 277.117)",
            "600": "oklch(51.1% 0.262 276.966)",
            "700": "oklch(45.7% 0.240 277.023)",
            "800": "oklch(39.8% 0.195 277.366)",
            "900": "oklch(35.9% 0.144 278.697)",
            "950": "oklch(25.7% 0.090 281.288)",
        },
    },
    "ENVIRONMENT": None,
    # Sin THEME fijo → aparece el toggle claro/oscuro/automático en la barra superior
    "LOGIN": {
        "redirect_after_login": "/admin/",
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        # <--- hecho por claude code (16-oct-2026): menú por PROGRAMA armado desde los modelos registrados (core/admin_nav.py)
        "navigation": "core.admin_nav.navegacion",
    },
}

# ─────────────────────────────────────────────────────────────
# SYSTEM CHECK SILENCIADOS
# ─────────────────────────────────────────────────────────────
# urls.W005: Warning conocido de compatibilidad django-unfold con Django 6.x
# El namespace 'admin' duplicado es interno de unfold y no afecta funcionamiento
SILENCED_SYSTEM_CHECKS = ['urls.W005']


# <--- hecho por claude code: API para el frontend estático de inventario_camaras.
# Autenticación por SESIÓN (mismo dominio) => sin CORS ni JWT. Todo endpoint
# exige usuario autenticado; los permisos finos van en cada ViewSet.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'UNAUTHENTICATED_USER': None,
}


# ─────────────────────────────────────────────────────────────
# ASISTENTE IA — <--- hecho por claude code (26-oct-2026; producción 06-nov-2026)
# La API key va en el .env del servidor (ANTHROPIC_API_KEY); nunca en el .exe ni en git.
# ASISTENTE_LIMITE_DIA = consultas por usuario y día (chat + redactar); el superusuario no tiene tope.
# ─────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
ASISTENTE_MODELO = os.getenv('ASISTENTE_MODELO', 'claude-sonnet-5-5')
ASISTENTE_LIMITE_DIA = int(os.getenv('ASISTENTE_LIMITE_DIA', '30') or 30)


# <--- hecho por claude code (19-nov-2026): PRUEBAS DIRECTO (sin Coolify, servicio techcare-pruebas-directo en :455).
# Con TC_RECARGA_EN_VIVO=1 los cambios se ven al recargar: plantillas sin caché y estáticos leídos de cada app
# (sin collectstatic). gunicorn --reload recarga los .py. En Coolify/producción esta variable no existe → no cambia nada.
if os.getenv('TC_RECARGA_EN_VIVO', '0') == '1':
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_AUTOREFRESH = True
    for _tpl in TEMPLATES:
        if _tpl.get('BACKEND', '').endswith('DjangoTemplates'):
            _tpl['APP_DIRS'] = False
            _tpl.setdefault('OPTIONS', {})['loaders'] = [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]
