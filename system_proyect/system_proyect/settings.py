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
    # <--- hecho por claude code: el contenedor de PRUEBAS (Coolify) se sirve por HTTP en :451
    # y en local por :8001; sin estos orígenes todo POST (login incluido) muere con 403 CSRF.
    'http://192.168.10.6:451',
    'http://localhost:451',
    'http://localhost:8001',
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
    'sponsors',
    'enfermeria',

    'conducta',
    'agendas',
    'core.apps.CoreConfig',
    'rest_framework',   # <--- hecho por claude code: API del frontend de cámaras
    'reloj',
    'calculadoras',
    'cfp',
    'notas_parcial',
    'inventario_camaras',
    'portal_super',   # <--- hecho por claude code: portal nuevo del superusuario (SPA + API)

    # Apps en construcción
    'atencion_padres',
    'salidas_bano',
    'ingresos_notas',  # <--- hecho por claude code: ingreso de notas al sistema academico
    'camaras',
]


# ─────────────────────────────────────────────────────────────
# 5. MIDDLEWARE
# ─────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.MaintenanceModeMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    # <--- hecho por claude code (seguridad): 2FA periódico por correo. Inactivo mientras
    # DOSFA_ACTIVO (constance) esté apagado; va al final, tras autenticación y sesión.
    'accounts.dosfa.Dosfa2FAMiddleware',
]

# <--- hecho por claude code (SOLO Docker/pruebas): en contenedor no hay Apache que sirva
# los estáticos, así que WhiteNoise los sirve desde gunicorn. Gated por USE_WHITENOISE
# para no cambiar el comportamiento del servidor actual (donde Apache los sirve).
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
                'core.context_processors.version_context',   # <--- hecho por claude code: versión + novedades
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
}

# <--- hecho por claude code: las 3 conexiones a SQL Server (Test2, AdmonANASQL,
# zkbiotime) se activan SOLO si USE_SQLSERVER=true (por defecto true → producción
# no cambia). En el entorno de pruebas se pone USE_SQLSERVER=false: no se conecta a
# ningún SQL Server. Los módulos que dependen de él (Notas de Parcial, Ingreso de
# Notas, reloj biométrico, consulta de padres/enfermería) no funcionarán ahí.
if os.getenv('USE_SQLSERVER', 'true') == 'true':
    DATABASES['padres_sqlserver'] = {
        'ENGINE': 'mssql',
        'NAME': os.getenv('MSSQL_TEST2_DB_NAME', 'Test2'),
        'USER': os.getenv('MSSQL_TEST2_DB_USER', 'admin2'),
        'PASSWORD': os.getenv('MSSQL_TEST2_DB_PASSWORD'),
        'HOST': os.getenv('MSSQL_TEST2_DB_HOST', '192.168.10.2'),
        'PORT': os.getenv('MSSQL_TEST2_DB_PORT', '1433'),
        'OPTIONS': {
            'driver': os.getenv('MSSQL_ODBC_DRIVER', 'ODBC Driver 17 for SQL Server'),
        },
    }
    # base ACADÉMICA REAL (AdmonANASQL), mismo servidor/credenciales que Test2.
    DATABASES['academico_real'] = {
        'ENGINE': 'mssql',
        'NAME': os.getenv('MSSQL_REAL_DB_NAME', 'AdmonANASQL'),
        'USER': os.getenv('MSSQL_TEST2_DB_USER', 'admin2'),
        'PASSWORD': os.getenv('MSSQL_TEST2_DB_PASSWORD'),
        'HOST': os.getenv('MSSQL_TEST2_DB_HOST', '192.168.10.2'),
        'PORT': os.getenv('MSSQL_TEST2_DB_PORT', '1433'),
        'OPTIONS': {
            'driver': os.getenv('MSSQL_ODBC_DRIVER', 'ODBC Driver 17 for SQL Server'),
        },
    }
    DATABASES['zkbio_sqlserver'] = {
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

# Sesión sin expiración por tiempo (dura hasta que el usuario cierre manualmente)
SESSION_COOKIE_AGE = 60 * 60 * 24 * 365  # 1 año — no expira en la práctica

# Renovar la sesión con cada request
SESSION_SAVE_EVERY_REQUEST = True

# No cerrar la sesión al cerrar el navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# <--- hecho por claude code (seguridad): el sitio SOLO se sirve por HTTPS (único vhost
# *:437 con SSLEngine on; no hay vhost por HTTP). El navegador siempre conecta por https,
# así que la cookie con flag Secure viaja bien. Antes iban sin él y podían filtrarse si
# alguna vez se accedía por http plano.
# <--- hecho por claude code: en PRUEBAS se navega por HTTP → las cookies no pueden ser
# "solo HTTPS" o el navegador nunca las envía (segunda causa del 403 CSRF del login).
# Default false en este repo de pruebas; poner COOKIES_SECURE=true si se sirve con TLS.
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
    # 2FA por correo. APAGADO por defecto: se enciende cuando el equipo lo tenga claro.
    # Al encender, se pide un código al correo según el rol (superusuario cada 15 días,
    # staff cada 30, usuario cada 60).
    'DOSFA_ACTIVO': (
        False,
        'Activar verificación en dos pasos (2FA) por correo. Apagado = no se pide a nadie.',
        bool,
    ),
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
        'fields': ('REGISTRO_USUARIOS_ACTIVO', 'DOSFA_ACTIVO'),
        'collapse': False,
    },
}

# ─────────────────────────────────────────────────────────────
# 13. CORREO ELECTRÓNICO (SMTP)
# ─────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
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





GOOGLE_FORMS_SHARED_TOKEN = os.getenv("GOOGLE_FORMS_SHARED_TOKEN", "")




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

# Clave secreta de la API de OpenAI (GPT-4o, GPT-3.5, etc.)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Opcional: Puedes definir el modelo por defecto a usar
OPENAI_MODEL_DEFAULT = os.getenv('OPENAI_MODEL_DEFAULT', 'gpt-4o')

# Seguridad: Recomendado usar límite de tokens por respuesta
OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '500'))

# Opcional: Configura el timeout para las llamadas a la API (segundos)
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
    "COLORS": {
        "primary": {
            "50":  "oklch(98.1% 0.019 75)",
            "100": "oklch(95.4% 0.050 76)",
            "200": "oklch(90.1% 0.100 75)",
            "300": "oklch(83.7% 0.152 69)",
            "400": "oklch(75.6% 0.183 55)",
            "500": "oklch(67.6% 0.189 43)",
            "600": "oklch(60.1% 0.176 38)",
            "700": "oklch(50.3% 0.150 35)",
            "800": "oklch(41.5% 0.122 34)",
            "900": "oklch(34.7% 0.102 33)",
            "950": "oklch(25.7% 0.083 33)",
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
        "navigation": [
            {
                "title": _("Usuarios"),
                "separator": True,
                "items": [
                    {
                        "title": _("Usuarios"),
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Grupos"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("Tickets"),
                "separator": True,
                "items": [
                    {"title": _("Tickets"), "icon": "confirmation_number", "link": reverse_lazy("admin:tickets_ticket_changelist")},
                    {"title": _("Comentarios"), "icon": "chat", "link": reverse_lazy("admin:tickets_ticketcomment_changelist")},
                ],
            },
            {
                "title": _("Conducta"),
                "separator": True,
                "items": [
                    {"title": _("Incisos"), "icon": "menu_book", "link": reverse_lazy("admin:conducta_incisoconductual_changelist")},
                    {"title": _("Reportes Conductuales"), "icon": "report", "link": reverse_lazy("admin:conducta_reporteconductual_changelist")},
                    {"title": _("Reportes Informativos"), "icon": "info", "link": reverse_lazy("admin:conducta_reporteinformativo_changelist")},
                    {"title": _("Progress Reports"), "icon": "bar_chart", "link": reverse_lazy("admin:conducta_progressreport_changelist")},
                    {"title": _("Evidencias"), "icon": "photo_camera", "link": reverse_lazy("admin:conducta_evidenciareporte_changelist")},
                ],
            },
            {
                "title": _("Agendas"),
                "separator": True,
                "items": [
                    {"title": _("Dashboard Agendas"), "icon": "dashboard", "link": "/agendas/coordinador/"},
                    {"title": _("Grados (Agenda)"), "icon": "grade", "link": reverse_lazy("admin:agendas_gradoagenda_changelist")},
                    {"title": _("Agendas"), "icon": "calendar_month", "link": reverse_lazy("admin:agendas_agenda_changelist")},
                    {"title": _("Imágenes Agenda"), "icon": "photo_library", "link": reverse_lazy("admin:agendas_imagenagenda_changelist")},
                ],
            },
            {
                "title": _("Enfermería"),
                "separator": True,
                "items": [
                    {"title": _("Atenciones"), "icon": "medical_services", "link": reverse_lazy("admin:enfermeria_atencionmedica_changelist")},
                    {"title": _("Inventario Medicamentos"), "icon": "medication", "link": reverse_lazy("admin:enfermeria_inventariomedicamento_changelist")},
                ],
            },
            {
                "title": _("Inventario"),
                "separator": True,
                "items": [
                    {"title": _("Inventario"), "icon": "inventory_2", "link": reverse_lazy("admin:inventario_inventoryitem_changelist")},
                    {"title": _("Computadoras"), "icon": "computer", "link": reverse_lazy("admin:inventario_computadora_changelist")},
                ],
            },
            {
                "title": _("Mantenimiento"),
                "separator": True,
                "items": [
                    {"title": _("Registros"), "icon": "build", "link": reverse_lazy("admin:mantenimiento_maintenancerecord_changelist")},
                ],
            },

            {
                "title": _("Control de Accesos"),
                "separator": True,
                "items": [
                    {"title": _("Registros de Acceso"), "icon": "manage_accounts", "link": reverse_lazy("admin:accounts_registroacceso_changelist")},
                ],
            },
            {
                "title": _("Configuración del Sistema"),
                "separator": True,
                "items": [
                    {"title": _("Ajustes Generales"), "icon": "tune", "link": reverse_lazy("admin:constance_config_changelist")},
                ],
            },
        ],
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
