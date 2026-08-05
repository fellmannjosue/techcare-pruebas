# <--- hecho por claude code (seguridad): verificación en dos pasos (2FA) por correo,
# PERIÓDICA según el rol. Todo queda inactivo mientras DOSFA_ACTIVO (constance) esté
# apagado; al encenderlo, cada usuario debe meter un código que le llega al correo con
# esta frecuencia:  superusuario cada 15 días · staff cada 30 · usuario normal cada 60.
from datetime import timedelta

from django.utils import timezone
from django.shortcuts import redirect

# Frecuencia de re-verificación por rol (en días)
INTERVALO_SUPERUSER = 15
INTERVALO_STAFF     = 30
INTERVALO_USUARIO   = 60

CODIGO_VIGENCIA_MIN = 10     # el código del correo caduca en 10 minutos
MAX_INTENTOS        = 5

# Rutas que nunca deben pedir 2FA (si no, se haría un bucle o se bloquearía el logout)
_EXENTAS = (
    '/accounts/2fa/', '/accounts/logout/', '/accounts/login/',
    '/accounts/maestro_logout/', '/static/', '/media/', '/admin/login/',
)


def intervalo_de(user):
    if user.is_superuser:
        return timedelta(days=INTERVALO_SUPERUSER)
    if user.is_staff:
        return timedelta(days=INTERVALO_STAFF)
    return timedelta(days=INTERVALO_USUARIO)


def dosfa_activo():
    try:
        from constance import config
        return bool(config.DOSFA_ACTIVO)
    except Exception:
        return False


def necesita_verificar(user):
    """True si a este usuario le toca volver a verificar (o nunca lo hizo)."""
    from .models import Verificacion2FA
    v, _ = Verificacion2FA.objects.get_or_create(usuario=user)
    if v.ultima_verificacion is None:
        return True
    return timezone.now() - v.ultima_verificacion >= intervalo_de(user)


class Dosfa2FAMiddleware:
    """Si el 2FA está activo y al usuario le toca, lo manda a la pantalla de verificación."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = getattr(request, 'user', None)
        if (u and u.is_authenticated and dosfa_activo()
                and not any(request.path.startswith(p) for p in _EXENTAS)
                and necesita_verificar(u)):
            request.session['dosfa_next'] = request.get_full_path()
            return redirect('verificar_2fa')
        return self.get_response(request)
