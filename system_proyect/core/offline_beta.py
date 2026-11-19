# core/offline_beta.py
# <--- hecho por claude code (12-nov-2026): MODO SIN CONEXIÓN (beta), SOLO SUPERUSUARIO.
"""Modo sin conexión (beta).

El service worker (``/sw.js``) es el mismo para todos, pero solo GUARDA páginas cuando la respuesta
trae la cabecera ``X-TC-Offline: 1``. Esa cabecera la pone este middleware únicamente a las páginas
HTML del superusuario real (no al auditor, que es superusuario solo en memoria, ni a una sesión de
«Iniciar sesión como»). Así, para el resto de usuarios el comportamiento no cambia.

Privacidad: si en ese navegador se abre una página SIN la cabecera (cerró sesión, entró otro usuario,
«Iniciar sesión como»…), el service worker borra todo lo guardado.

Interruptor: constance ``OFFLINE_BETA`` (Configuración → Sistema → Modo sin conexión).
Al apagarlo, la cabecera deja de enviarse y el service worker borra solo las copias en la siguiente página.
"""
from django.conf import settings


def encendido():
    try:
        from constance import config
        return bool(config.OFFLINE_BETA)
    except Exception:
        return bool(getattr(settings, 'OFFLINE_BETA', True))


def activo_para(request):
    if not encendido():
        return False
    u = getattr(request, 'user', None)
    if not (u and u.is_authenticated and u.is_superuser):
        return False
    if getattr(u, '_tc_aud_orig', None) is not None:      # auditor (superusuario solo en memoria)
        return False
    try:
        if request.session.get('tc_suplantador_id'):        # «Iniciar sesión como»
            return False
    except Exception:
        pass
    return True


class OfflineBetaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if (request.method == 'GET' and response.status_code == 200
                    and 'text/html' in (response.get('Content-Type', '') or '')
                    and 'attachment' not in (response.get('Content-Disposition', '') or '')
                    and activo_para(request)):
                response['X-TC-Offline'] = '1'
        except Exception:
            pass
        return response


def context(request):
    """``tc_offline_beta``: carga el aviso/registro del modo sin conexión en la base."""
    return {'tc_offline_beta': activo_para(request)}
