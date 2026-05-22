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
    'core',
    'reloj',
    'calculadoras',
    'finanzas_personales',
    'notas_parcial',

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
]


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
        'PASSWORD': os.getenv('DB_PASSWORD', 'Test-12345'),
        'HOST': os.getenv('DB_HOST', '192.168.10.6'),
        'PORT': os.getenv('DB_PORT', '3306'),
    },

    # Conexión al SQL Server remoto (Test2)
    'padres_sqlserver': {
    'ENGINE': 'mssql',
    'NAME': os.getenv('MSSQL_TEST2_DB_NAME', 'Test2'),
    'USER': os.getenv('MSSQL_TEST2_DB_USER', 'admin2'),
    'PASSWORD': os.getenv('MSSQL_TEST2_DB_PASSWORD', '121800-Jfellmann'),
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
    'PASSWORD': os.getenv('MSSQL_ZKBIO_DB_PASSWORD', 'biotime-2026'),
    'HOST': os.getenv('MSSQL_ZKBIO_DB_HOST', '192.168.10.2'),
    'PORT': os.getenv('MSSQL_ZKBIO_DB_PORT', '14332'),
    'OPTIONS': {
        'driver': os.getenv('MSSQL_ODBC_DRIVER', 'ODBC Driver 17 for SQL Server'),
    },
}


}

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
    BASE_DIR / "system_proyect/finanzas_personales/static",
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

# Duración de la sesión: 4 horas (en segundos)
SESSION_COOKIE_AGE = 60 * 60 * 4  # 3600 segundos

# Renovar la sesión con cada request (se reinicia si el usuario navega)
SESSION_SAVE_EVERY_REQUEST = True

# No cerrar la sesión al cerrar el navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Cookies seguras (requerido para HTTPS, déjalo en True si usas HTTPS)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Motor de sesiones recomendado (usa la base de datos cacheada)
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

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
}
CONSTANCE_CONFIG_FIELDSETS = {
    'Modo Mantenimiento': {
        'fields': (
            'MAINTENANCE_MODE',
            'MAINTENANCE_AREA',
            'MAINTENANCE_MESSAGE',
            'MAINTENANCE_END_TIME',
            'MAINTENANCE_BLOCKED_USERS',
        ),
        'collapse': False,
    }
}

# ─────────────────────────────────────────────────────────────
# 13. CORREO ELECTRÓNICO (SMTP)
# ─────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'techcare.app2024@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER





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
