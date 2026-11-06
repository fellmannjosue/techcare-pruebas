"""<--- hecho por claude code (06-nov-2026): Configuración → Variables del sistema (.env). SOLO superusuario.
Ver un valor o cambiar algo exige confirmar la contraseña (desbloquea 5 min). Todo queda en BitacoraEntorno."""
import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import entorno
from .models import BitacoraEntorno

DESBLOQUEO_SEG = 300
MAX_FALLOS, BLOQUEO_SEG = 5, 900


def _ip(request):
    return (request.META.get('REMOTE_ADDR') or '')[:45]


def _log(request, accion, variable='', resultado=''):
    BitacoraEntorno.objects.create(usuario=request.user, accion=accion, variable=variable[:64],
                                   resultado=resultado[:200], ip=_ip(request))


def _restante(request):
    return max(0, int(request.session.get('entorno_hasta', 0) - time.time()))


def _json(data, status=200):
    r = JsonResponse(data, status=status)
    r['Cache-Control'] = 'no-store'
    return r


def _solo_super(vista):
    def envuelta(request, *a, **kw):
        if not request.user.is_superuser:
            if request.method == 'POST':
                return _json({'ok': False, 'msg': 'Solo superusuario.'}, 403)
            messages.error(request, 'Solo los superusuarios pueden ver las variables del sistema.')
            return redirect('settings_perfil')
        return vista(request, *a, **kw)
    envuelta.__name__ = vista.__name__
    return login_required(envuelta)


@_solo_super
def settings_entorno(request):
    grupos, filas = entorno.listar()
    for g in grupos:
        g['prueba'] = entorno.PRUEBA_DE_GRUPO.get(g['g'], '')
    ctx = {
        'active_tab': 'entorno', 'grupos': grupos, 'archivo': entorno.estado_archivo(),
        'restante': _restante(request),
        'tot': {'total': len(filas), 'secreto': sum(f['tipo'] == 'secreto' for f in filas),
                'sin_uso': sum(f['definida'] and not f['en_uso'] for f in filas),
                'deshab': sum(f['deshabilitada'] for f in filas), 'pend': sum(f['pendiente'] for f in filas)},
        'bitacora': BitacoraEntorno.objects.select_related('usuario')[:15],
    }
    return render(request, 'accounts/settings_entorno.html', ctx)


@require_POST
@_solo_super
def entorno_desbloquear(request):
    llave = f'entorno_fallos_{request.user.pk}'
    fallos = cache.get(llave, 0)
    if fallos >= MAX_FALLOS:
        return _json({'ok': False, 'msg': 'Demasiados intentos. Espera 15 minutos.'}, 429)
    if not request.user.check_password(request.POST.get('password', '')):
        cache.set(llave, fallos + 1, BLOQUEO_SEG)
        _log(request, 'fallo')
        quedan = MAX_FALLOS - fallos - 1
        return _json({'ok': False, 'msg': f'Contraseña incorrecta. Te quedan {quedan} intento(s).' if quedan else 'Demasiados intentos. Espera 15 minutos.'}, 403)
    cache.delete(llave)
    request.session['entorno_hasta'] = time.time() + DESBLOQUEO_SEG
    _log(request, 'desbloqueo')
    return _json({'ok': True, 'restante': DESBLOQUEO_SEG})


def _exige_desbloqueo(request):
    return None if _restante(request) else _json({'ok': False, 'bloqueado': True, 'msg': 'Confirma tu contraseña para continuar.'}, 403)


@require_POST
@_solo_super
def entorno_ver(request):
    r = _exige_desbloqueo(request)
    if r:
        return r
    k = request.POST.get('k', '')
    if not entorno.CLAVE_RE.match(k):
        return _json({'ok': False, 'msg': 'Variable inválida.'}, 400)
    _log(request, 'ver', k)
    return _json({'ok': True, **entorno.valor(k), 'restante': _restante(request)})


@require_POST
@_solo_super
def entorno_guardar(request):
    r = _exige_desbloqueo(request)
    if r:
        return r
    k, accion = request.POST.get('k', '').strip(), request.POST.get('accion', '')
    v = request.POST.get('v')
    if accion not in ('editar', 'agregar', 'deshabilitar', 'habilitar'):
        return _json({'ok': False, 'msg': 'Acción inválida.'}, 400)
    ok, msg = entorno.guardar(k, accion, v)
    _log(request, accion, k, ('OK' if ok else 'Rechazado: ') + ('' if ok else msg))
    return _json({'ok': ok, 'msg': msg}, 200 if ok else 400)


@require_POST
@_solo_super
def entorno_probar(request):
    d = request.POST.get('destino', '')
    ok, msg = entorno.probar(d)
    _log(request, 'probar', d, ('OK' if ok else 'Falla'))
    return _json({'ok': ok, 'msg': msg})
