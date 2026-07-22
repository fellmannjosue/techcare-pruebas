# core/maintenance_modules.py
# <--- hecho por claude code: bloqueo selectivo de formularios durante mantenimiento
"""Módulos que se pueden bloquear individualmente (además del mantenimiento general).

Estados por módulo:
    'normal'    → funciona con normalidad (no se guarda en la config)
    'lectura'   → se puede ver/consultar, pero NO guardar (se bloquean POST/PUT/DELETE)
    'bloqueado' → no se puede ni entrar

A quién afecta lo decide el mismo filtro del mantenimiento general
(MAINTENANCE_AREA / MAINTENANCE_BLOCKED_USERS). El superusuario nunca se bloquea.
"""
import json

ESTADOS = ('normal', 'lectura', 'bloqueado')
ESTADO_LABELS = {
    'normal':    'Normal',
    'lectura':   'Solo lectura',
    'bloqueado': 'Bloqueado',
}

# El orden define cómo se listan en la pantalla de mantenimiento.
MODULOS = [
    {'key': 'agendas',        'label': 'Agendas',
     'icon': 'ti-calendar-week', 'color': 'purple',
     'prefijos': ('/agendas/',)},

    {'key': 'rep_informativo', 'label': 'Reportes informativos',
     'icon': 'ti-file-text', 'color': 'blue',
     'prefijos': ('/conducta/reporte/informativo/', '/conducta/reporte-informativo/')},

    {'key': 'rep_conductual', 'label': 'Reportes conductuales',
     'icon': 'ti-alert-triangle', 'color': 'red',
     'prefijos': ('/conducta/reporte/conductual/', '/conducta/reporte-conductual/')},

    {'key': 'notas_parcial',  'label': 'Notas mitad de parcial',
     'icon': 'ti-file-certificate', 'color': 'green',
     'prefijos': ('/notas-parcial/',)},

    {'key': 'tutorias',       'label': 'Convocatoria de tutorías',
     'icon': 'ti-users-group', 'color': 'orange',
     'prefijos': ('/conducta/tutorias/',)},

    {'key': 'progress',       'label': 'Progress Report',
     'icon': 'ti-chart-line', 'color': 'cyan',
     'prefijos': ('/conducta/progress_report/', '/conducta/progress-report/')},

    {'key': 'tickets',        'label': 'Tickets',
     'icon': 'ti-ticket', 'color': 'indigo',
     'prefijos': ('/tickets/',)},
]

_POR_KEY = {m['key']: m for m in MODULOS}


def leer_estados(config):
    """Devuelve {key: estado} con todos los módulos (default 'normal')."""
    crudo = getattr(config, 'MAINTENANCE_MODULES', '') or ''
    try:
        data = json.loads(crudo) if crudo.strip() else {}
    except ValueError:
        data = {}
    salida = {}
    for m in MODULOS:
        v = str(data.get(m['key'], 'normal')).lower()
        salida[m['key']] = v if v in ESTADOS else 'normal'
    return salida


def guardar_estados(config, nuevos):
    """Guarda solo los módulos que NO están en 'normal'. Devuelve el dict aplicado."""
    limpio = {}
    for m in MODULOS:
        v = str((nuevos or {}).get(m['key'], 'normal')).lower()
        if v in ESTADOS and v != 'normal':
            limpio[m['key']] = v
    config.MAINTENANCE_MODULES = json.dumps(limpio, ensure_ascii=False)
    return leer_estados(config)


def modulo_de_ruta(ruta):
    """Módulo al que pertenece una ruta, o None."""
    for m in MODULOS:
        if any(ruta.startswith(p) for p in m['prefijos']):
            return m
    return None


def modulos_para_ui(config):
    """Lista lista-para-plantilla: módulo + su estado actual."""
    estados = leer_estados(config)
    return [{**m, 'estado': estados[m['key']]} for m in MODULOS]


def hay_restricciones(config):
    return any(v != 'normal' for v in leer_estados(config).values())
