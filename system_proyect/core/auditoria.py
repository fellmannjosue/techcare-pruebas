# core/auditoria.py
# <--- hecho por claude code (10-nov-2026): rol AUDITORÍA = ve todo como el superusuario, pero en SOLO LECTURA.
"""Rol Auditoría (grupo de Django ``auditoria``).

Cómo funciona (``AuditoriaMiddleware``):
  - Durante cada petición del auditor, ``request.user`` se trata EN MEMORIA como superusuario
    (``is_superuser``/``is_staff`` = True). Nunca se guarda en la base: un ``pre_save`` de User
    restaura los valores reales antes de cualquier ``save()``.
  - GET/HEAD/OPTIONS: se ejecutan dentro de una transacción que SIEMPRE se revierte, así que
    una vista que escriba al abrirse (get_or_create, marcar leído, historial…) no deja rastro.
  - POST/PUT/PATCH/DELETE: se rechazan (403) salvo
      · las rutas técnicas de la sesión (salir, marcar novedades/notificaciones), o
      · los programas que el superusuario habilitó para EDITAR en
        Configuración → Permisos → Rol Auditoría (constance ``AUDITORIA_EDITAR``, claves de
        ``core/programas.py``).
  - Zonas que el auditor NUNCA abre, ni para leer: ``/admin/``, «Iniciar sesión como» y la propia
    pantalla de configuración del rol.
  - Cada página o descarga que abre y cada edición permitida quedan en la bitácora de seguridad
    (``logs/seguridad.log``: ``auditoria_vista`` / ``auditoria_edicion`` / ``auditoria_bloqueo``).

El superusuario real nunca pasa por aquí. Si la cuenta auditora fuera superusuario de verdad,
el middleware no hace nada (no hay nada que restringir).
"""
import json

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.shortcuts import render

GRUPO = 'auditoria'

# Rutas que el auditor no abre nunca (ni GET).
PROHIBIDAS = (
    '/admin/',
    '/accounts/iniciar-como/',
    '/accounts/settings/auditoria-rol/',
    # Directorio de teléfonos de los encargados (pedido del usuario, 10-nov-2026): el auditor no lo ve
    '/enfermeria/directorio/',
    '/conducta/directorio/',
)

# POST técnicos de la sesión que no cambian datos del negocio.
POST_PERMITIDOS = (
    '/accounts/logout/',
    '/accounts/maestro_logout/',
    '/core/api/notificaciones/marcar/',
    '/core/api/version/visto/',   # «Entendido» de Novedades (si no, la ventana sale en cada recarga)
    '/notas-parcial/leer-notificacion/',
)

_SEGUROS = ('GET', 'HEAD', 'OPTIONS')


def es_auditor(user):
    """True si el usuario es auditor (grupo ``auditoria``) y NO es superusuario real."""
    if not getattr(user, 'is_authenticated', False):
        return False
    orig = getattr(user, '_tc_aud_orig', None)
    if orig is not None:
        return True
    if user.is_superuser:
        return False
    return user.groups.filter(name=GRUPO).exists()


def programas_editables():
    """Claves de programas (core/programas.py) que el auditor puede EDITAR."""
    try:
        from constance import config
        data = json.loads(getattr(config, 'AUDITORIA_EDITAR', '') or '[]')
        return {str(k) for k in data} if isinstance(data, list) else set()
    except Exception:
        return set()


def guardar_editables(claves):
    from constance import config
    from core.programas import POR_KEY
    config.AUDITORIA_EDITAR = json.dumps(sorted(k for k in claves if k in POR_KEY))


def _elevar(user):
    if getattr(user, '_tc_aud_orig', None) is None:
        user._tc_aud_orig = (user.is_superuser, user.is_staff)
    user.is_superuser = True
    user.is_staff = True


def _es_ajax(request):
    acc = request.headers.get('Accept', '')
    return (request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in acc or request.content_type == 'application/json')


def _bloqueo(request, motivo):
    from core.seguridad_eventos import evento
    evento('auditoria_bloqueo', request, objetivo=request.path, metodo=request.method, motivo=motivo)
    msg = 'Modo auditoría: solo lectura. Esta acción no está permitida.'
    if _es_ajax(request):
        return JsonResponse({'ok': False, 'success': False, 'error': msg}, status=403)
    return render(request, '403.html', {'mensaje': msg, 'exception': msg}, status=403)


def _registrar_vista(request, response):
    """Deja en la bitácora las páginas y descargas (no los sondeos JSON/estáticos)."""
    try:
        ctype = response.get('Content-Type', '') or ''
        descarga = 'attachment' in (response.get('Content-Disposition', '') or '')
        if response.status_code < 400 and ('text/html' in ctype or descarga):
            from core.seguridad_eventos import evento
            evento('auditoria_vista', request, objetivo=request.get_full_path()[:300],
                   descarga=descarga or None)
    except Exception:
        pass


class AuditoriaMiddleware:
    """Va después de MaintenanceModeMiddleware (el auditor respeta mantenimiento y programas ocultos)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if not es_auditor(user):
            return self.get_response(request)

        ruta = request.path
        if any(ruta.startswith(p) for p in PROHIBIDAS):
            return _bloqueo(request, 'zona_prohibida')

        _elevar(user)
        request.tc_auditoria = True

        if request.method in _SEGUROS:
            # Todo lo que la vista escriba al abrirse se deshace.
            with transaction.atomic():
                response = self.get_response(request)
                transaction.set_rollback(True)
            _registrar_vista(request, response)
            return response

        if any(ruta.startswith(p) for p in POST_PERMITIDOS):
            return self.get_response(request)

        from core.programas import programa_de_ruta
        prog = programa_de_ruta(ruta)
        if prog and prog['key'] in programas_editables():
            from core.seguridad_eventos import evento
            evento('auditoria_edicion', request, objetivo=ruta, metodo=request.method, programa=prog['key'])
            return self.get_response(request)
        return _bloqueo(request, 'solo_lectura')


# ── Candado: el "superusuario en memoria" NUNCA se guarda en la base ─────────────────────────
@receiver(pre_save, sender=get_user_model(), dispatch_uid='tc_auditoria_pre_save')
def _no_guardar_elevacion(sender, instance, **kwargs):
    orig = getattr(instance, '_tc_aud_orig', None)
    if orig is not None:
        instance.is_superuser, instance.is_staff = orig


@receiver(post_save, sender=get_user_model(), dispatch_uid='tc_auditoria_post_save')
def _reelevar(sender, instance, **kwargs):
    if getattr(instance, '_tc_aud_orig', None) is not None:
        instance.is_superuser = True
        instance.is_staff = True


def context(request):
    """Context processor: ``tc_auditoria`` para el aviso fijo «Modo auditoría · solo lectura»."""
    activo = bool(getattr(request, 'tc_auditoria', False))
    editable = False
    if activo:
        from core.programas import programa_de_ruta
        prog = programa_de_ruta(request.path)
        editable = bool(prog and prog['key'] in programas_editables())
    # tc_auditoria_bloquea: en esta pantalla los campos de guardar se deshabilitan (core/js/auditoria.js)
    return {'tc_auditoria': activo, 'tc_auditoria_bloquea': activo and not editable}
