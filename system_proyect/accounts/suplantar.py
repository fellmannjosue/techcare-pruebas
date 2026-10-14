# <--- hecho por claude code (12-oct-2026): "Iniciar sesión como" (el *Log in as* de Moodle). SOLO superusuario.
# El superusuario entra a la cuenta de otro usuario para ver el sistema exactamente como lo ve esa persona.
# - Nunca se puede entrar como otro superusuario ni como un usuario inactivo.
# - La sesión guarda quién es el superusuario real (SESION_SUPER); un aviso fijo en todas las páginas permite volver.
# - Cada entrada queda en la bitácora `Suplantacion` (quién, a quién, IP, inicio, fin).
# - Mientras dura: no se envía 2FA al usuario, no se cambia su último acceso y no se puede cambiar su contraseña.
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Suplantacion

SESION_SUPER = 'tc_suplantador_id'
SESION_REG = 'tc_suplantacion_id'
_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def suplantando(request):
    return bool(getattr(request, 'session', None) and request.session.get(SESION_SUPER))


def _ip(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    return (ip.split(',')[0].strip() if ip else '') or None


def _motivo_no_permitido(super_user, destino):
    if destino.pk == super_user.pk:
        return 'Ya estás en tu propia cuenta.'
    if destino.is_superuser:
        return 'No se puede iniciar sesión como otro superusuario.'
    if not destino.is_active:
        return 'El usuario está inactivo.'
    return ''


def _destino_inicial(user):
    """Mismo destino que tendría el usuario al iniciar sesión él mismo."""
    if user.is_staff:
        return reverse('menu')   # menu_view redirige a coordinadores, maestros, reloj, multi-rol…
    from .views import _GRUPO_A_ROL
    roles = [_GRUPO_A_ROL[g.name.lower()] for g in user.groups.all() if g.name.lower() in _GRUPO_A_ROL]
    if len(roles) == 1:
        return roles[0]['url'] if roles[0]['url'].startswith('/') else reverse(roles[0]['url'])
    if roles:
        return reverse('seleccion_rol')
    return reverse('menu')


@login_required
def confirmar(request, pk):
    """GET: pantalla de confirmación. POST: entra a la cuenta."""
    if not request.user.is_superuser or suplantando(request):
        return HttpResponseForbidden('Solo el superusuario puede iniciar sesión como otro usuario.')
    destino = get_object_or_404(User, pk=pk)
    motivo = _motivo_no_permitido(request.user, destino)
    if request.method == 'POST' and not motivo:
        sup = request.user
        ultimo = destino.last_login
        login(request, destino, backend=_BACKEND)        # login() vacía la sesión del superusuario (otra cuenta)
        User.objects.filter(pk=destino.pk).update(last_login=ultimo)   # su "último acceso" no cambia por nosotros
        reg = Suplantacion.objects.create(superusuario=sup, usuario=destino, super_username=sup.username,
                                          username=destino.username, ip=_ip(request))
        request.session[SESION_SUPER] = sup.pk
        request.session[SESION_REG] = reg.pk
        messages.info(request, f'Iniciaste sesión como {destino.get_full_name() or destino.username}.')
        return redirect(_destino_inicial(destino))
    recientes = Suplantacion.objects.filter(usuario=destino).select_related('superusuario')[:5]
    return render(request, 'accounts/suplantar_confirmar.html',
                  {'destino': destino, 'motivo': motivo, 'recientes': recientes,
                   'grupos': destino.groups.order_by('name').values_list('name', flat=True)})


def _cerrar_registro(session, como):
    rid = session.get(SESION_REG)
    if rid:
        Suplantacion.objects.filter(pk=rid, fin__isnull=True).update(fin=timezone.now(), cierre=como)


@require_POST
def volver(request):
    """Termina la suplantación y regresa a la cuenta del superusuario."""
    sid = request.session.get(SESION_SUPER)
    if not sid:
        return redirect('menu')
    _cerrar_registro(request.session, 'volver')
    sup = User.objects.filter(pk=sid, is_active=True, is_superuser=True).first()
    destino_pk = request.user.pk if request.user.is_authenticated else None
    if not sup:   # el superusuario dejó de serlo mientras tanto: se cierra todo
        logout(request)
        return redirect('login')
    login(request, sup, backend=_BACKEND)   # vacía la sesión del usuario suplantado
    messages.success(request, 'Volviste a tu cuenta.')
    if destino_pk:
        return redirect('settings_usuario_editar', pk=destino_pk)
    return redirect('menu')


@receiver(user_logged_out)
def _al_cerrar_sesion(sender, request, user, **kwargs):
    if request is not None and getattr(request, 'session', None) and request.session.get(SESION_SUPER):
        _cerrar_registro(request.session, 'logout')


def context(request):
    """Context processor: datos del aviso fijo."""
    if not suplantando(request):
        return {}
    sup = User.objects.filter(pk=request.session.get(SESION_SUPER)).first()
    return {'tc_suplantando': True, 'tc_suplantador': sup}


_BLOQUEADAS_POST = ('settings_perfil',)   # ahí el usuario cambia SU contraseña


class SuplantacionMiddleware:
    """Mientras se suplanta: no se cambia la contraseña del usuario."""
    def __init__(self, get_response):
        self.get_response = get_response
        self._rutas = None

    def __call__(self, request):
        if request.method == 'POST' and suplantando(request):
            if self._rutas is None:
                self._rutas = {reverse(n) for n in _BLOQUEADAS_POST}
            if request.path in self._rutas and request.POST.get('action') == 'password':
                messages.error(request, 'Mientras usas la cuenta de otro usuario no puedes cambiar su contraseña.')
                return redirect(request.path)
        return self.get_response(request)
