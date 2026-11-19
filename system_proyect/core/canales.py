# core/canales.py
# <--- hecho por claude code (09-nov-2026): programas por CANAL (Web / App de escritorio .exe / App móvil APK)
"""Qué programas se ven en cada canal por el que se entra a TechCare.

- El canal sale del User-Agent: el .exe es Electron (marca propia `TechCareDesktop`), la APK es
  un WebView de Android (marca propia `TechCareAndroid`; mientras no se recompile, el `; wv)` del
  WebView). Todo lo demás es la Web.
- Se guarda en constance `PROGRAMAS_POR_CANAL` como JSON {canal: [claves OCULTAS]}; vacío = todo visible.
- A diferencia de «Programas ocultos», esto aplica también al SUPERUSUARIO (si no, no podría ver
  cómo queda cada app). Configuración (/accounts/) no es un programa: nunca se bloquea.
- Es para ORGANIZAR qué ofrece cada app, no es un control de seguridad: el User-Agent se puede
  imitar. Los permisos por grupo de cada vista siguen siendo el candado real.
- El superusuario puede "Probar como" un canal desde su navegador (sesión `tc_canal_prueba`).
"""
import contextvars
import json

CANALES = [
    {'key': 'web', 'label': 'Web (navegador)',      'icon': 'ti-world'},
    {'key': 'exe', 'label': 'App de escritorio (.exe)', 'icon': 'ti-device-desktop'},
    {'key': 'apk', 'label': 'App móvil (APK)',      'icon': 'ti-device-mobile'},
]
CANAL_KEYS = [c['key'] for c in CANALES]
CANAL_LABEL = {c['key']: c['label'] for c in CANALES}

SESION_PRUEBA = 'tc_canal_prueba'

# Canal de la petición en curso (lo fija CanalAppMiddleware); lo leen los armadores de menús.
CANAL_ACTUAL = contextvars.ContextVar('tc_canal_actual', default='web')
OCULTOS_ACTUAL = contextvars.ContextVar('tc_canal_ocultos', default=frozenset())


def canal_real(request):
    """Canal según el User-Agent (sin la prueba del superusuario)."""
    ua = request.META.get('HTTP_USER_AGENT', '') or ''
    if 'TechCareAndroid' in ua or ('Android' in ua and '; wv)' in ua):
        return 'apk'
    if 'TechCareDesktop' in ua or 'Electron' in ua:
        return 'exe'
    return 'web'


def canal_de(request):
    """Canal efectivo: el real, o el que el superusuario eligió en «Probar como»."""
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_superuser', False):
        try:
            prueba = request.session.get(SESION_PRUEBA)
        except Exception:
            prueba = None
        if prueba in CANAL_KEYS:
            return prueba
    return canal_real(request)


def config_canales(config):
    """{canal: set(claves ocultas)} con todos los canales presentes."""
    from core.programas import POR_KEY
    crudo = getattr(config, 'PROGRAMAS_POR_CANAL', '') or ''
    try:
        data = json.loads(crudo) if crudo.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return {c: {k for k in (data.get(c) or []) if k in POR_KEY} for c in CANAL_KEYS}


def ocultos_de_canal(config, canal):
    return config_canales(config).get(canal, set())


def guardar_canal(config, canal, programa, visible):
    """Prende/apaga UN programa en UN canal y devuelve la config completa."""
    from core.programas import POR_KEY
    if canal not in CANAL_KEYS or programa not in POR_KEY:
        raise ValueError('canal o programa inválido')
    cfg = config_canales(config)
    if visible:
        cfg[canal].discard(programa)
    else:
        cfg[canal].add(programa)
    config.PROGRAMAS_POR_CANAL = json.dumps({c: sorted(cfg[c]) for c in CANAL_KEYS if cfg[c]})
    return cfg


def mapa_js(claves_ocultas):
    """Lo que necesita tc_canal.js para quitar de la página los enlaces a programas ocultos:
    la lista de programas EN ORDEN (la primera coincidencia manda, igual que programa_de_ruta)."""
    from core.programas import PROGRAMAS
    return {'ocultos': sorted(claves_ocultas),
            'programas': [{'k': p['key'], 'p': list(p['prefijos']), 'x': list(p.get('excepto', ()))}
                          for p in PROGRAMAS]}
