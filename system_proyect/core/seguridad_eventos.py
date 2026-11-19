# core/seguridad_eventos.py
# <--- hecho por claude code (09-nov-2026, revisión ISO 27001/COBIT): bitácora de EVENTOS DE SEGURIDAD.
"""Registro de eventos de seguridad de TechCare.

Qué registra (logger ``techcare.seguridad`` → ``logs/seguridad.log``, una línea JSON por evento):
  - login correcto, login fallido, logout
  - bloqueo por intentos (cuenta o IP)
  - alta/baja de usuarios, cambios de is_superuser / is_staff / is_active
  - cambio de contraseña (solo el HECHO, nunca el valor ni el hash)
  - altas y bajas de usuarios en grupos, alta/baja de grupos
  - cambios de la configuración dinámica (constance): solo la CLAVE, nunca el valor
  - otros eventos que las vistas reporten con ``evento()`` (p. ej. borrado de una atención médica)

Reglas:
  - NUNCA se escriben contraseñas, hashes, tokens, códigos 2FA ni contenido médico. ``_limpiar`` descarta
    cualquier clave sospechosa aunque una vista la mande por error.
  - La IP es ``REMOTE_ADDR``. Apache sirve con mod_wsgi directo (sin proxy), así que la cabecera
    ``X-Forwarded-For`` la controla el cliente y NO se usa para la IP (ver ``ip_cliente``).
  - Si el archivo de log no se puede escribir, la aplicación sigue funcionando (handler tolerante).
  - Es complementario a django-simple-history (cambios de datos) y a RegistroAcceso / Suplantacion.
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger('techcare.seguridad')

_CLAVES_PROHIBIDAS = ('pass', 'pwd', 'token', 'secret', 'clave', 'codigo', 'code', 'hash', 'key', 'diagn',
                      'sintoma', 'medic', 'tratamiento')


def ip_cliente(request):
    """IP del cliente. Solo confía en X-Forwarded-For si settings.TECHCARE_CONFIAR_XFF=True
    (únicamente detrás de un proxy propio que la reescriba)."""
    if request is None:
        return None
    meta = getattr(request, 'META', {}) or {}
    if getattr(settings, 'TECHCARE_CONFIAR_XFF', False):
        xff = (meta.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip()
        if xff:
            return xff
    return meta.get('REMOTE_ADDR') or None


def _limpiar(detalle):
    limpio = {}
    for k, v in (detalle or {}).items():
        kl = str(k).lower()
        if any(p in kl for p in _CLAVES_PROHIBIDAS):
            continue
        if isinstance(v, (list, tuple, set)):
            v = [str(x)[:80] for x in list(v)[:50]]
        elif v is not None and not isinstance(v, (int, float, bool)):
            v = str(v)[:200]
        limpio[k] = v
    return limpio


def evento(accion, request=None, actor=None, objetivo=None, nivel=logging.INFO, **detalle):
    """Escribe un evento. ``actor``/``objetivo`` pueden ser usuarios o textos."""
    try:
        if actor is None and request is not None:
            u = getattr(request, 'user', None)
            actor = u if (u is not None and getattr(u, 'is_authenticated', False)) else None
        reg = {
            'accion': accion,
            'actor': getattr(actor, 'username', actor) if actor is not None else None,
            'objetivo': getattr(objetivo, 'username', objetivo) if objetivo is not None else None,
            'ip': ip_cliente(request),
            'ruta': (getattr(request, 'path', '') or '')[:200] if request is not None else None,
        }
        if request is not None and getattr(request, 'session', None) is not None:
            try:
                sup = request.session.get('tc_suplantador_id')
                if sup:
                    reg['suplantado_por_id'] = sup
            except Exception:
                pass
        reg.update(_limpiar(detalle))
        logger.log(nivel, json.dumps(reg, ensure_ascii=False, default=str))
    except Exception:   # la bitácora nunca debe tumbar la petición
        pass


# ── Señales ────────────────────────────────────────────────────────────────
_CAMPOS_USUARIO = ('is_superuser', 'is_staff', 'is_active')


def conectar():
    """Se llama desde CoreConfig.ready()."""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
    from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save

    User = get_user_model()

    def _login_ok(sender, request, user, **kw):
        evento('login_ok', request, actor=user,
               suplantacion=bool(request is not None and getattr(request, '_tc_suplantacion', False)))

    def _login_fail(sender, credentials, request=None, **kw):
        # Django ya quita las claves tipo password de `credentials`; igual solo se toma el usuario.
        evento('login_fallido', request, actor=None, objetivo=(credentials or {}).get('username'),
               nivel=logging.WARNING)

    def _logout(sender, request, user, **kw):
        evento('logout', request, actor=user)

    def _user_pre_save(sender, instance, **kw):
        if not instance.pk:
            instance._tc_antes = None
            return
        antes = sender.objects.filter(pk=instance.pk).values(*_CAMPOS_USUARIO, 'password').first()
        instance._tc_antes = antes

    def _user_post_save(sender, instance, created, **kw):
        antes = getattr(instance, '_tc_antes', None)
        if created:
            evento('usuario_creado', None, actor=None, objetivo=instance,
                   is_superuser=instance.is_superuser, is_staff=instance.is_staff)
            return
        if not antes:
            return
        cambios = {c: [antes[c], getattr(instance, c)] for c in _CAMPOS_USUARIO if antes[c] != getattr(instance, c)}
        if cambios:
            evento('usuario_privilegios', None, objetivo=instance, nivel=logging.WARNING,
                   cambios=json.dumps(cambios))
        if antes.get('password') != instance.password:
            evento('contrasena_cambiada', None, objetivo=instance)

    def _user_post_delete(sender, instance, **kw):
        evento('usuario_eliminado', None, objetivo=instance, nivel=logging.WARNING)

    def _grupos(sender, instance, action, pk_set, model, **kw):
        if action not in ('post_add', 'post_remove', 'post_clear'):
            return
        try:
            if isinstance(instance, User):
                nombres = list(Group.objects.filter(pk__in=pk_set or []).values_list('name', flat=True))
                evento('grupos_' + action.split('_')[1], None, objetivo=instance, grupos=nombres)
            else:   # group.user_set.add(...)
                users = list(User.objects.filter(pk__in=pk_set or []).values_list('username', flat=True))
                evento('grupos_' + action.split('_')[1], None, objetivo=','.join(users)[:200], grupos=[instance.name])
        except Exception:
            pass

    def _grupo_creado(sender, instance, created, **kw):
        if created:
            evento('grupo_creado', None, objetivo=instance.name)

    def _grupo_borrado(sender, instance, **kw):
        evento('grupo_eliminado', None, objetivo=instance.name, nivel=logging.WARNING)

    user_logged_in.connect(_login_ok, dispatch_uid='tc_seg_login_ok', weak=False)
    user_login_failed.connect(_login_fail, dispatch_uid='tc_seg_login_fail', weak=False)
    user_logged_out.connect(_logout, dispatch_uid='tc_seg_logout', weak=False)
    pre_save.connect(_user_pre_save, sender=User, dispatch_uid='tc_seg_user_pre', weak=False)
    post_save.connect(_user_post_save, sender=User, dispatch_uid='tc_seg_user_post', weak=False)
    post_delete.connect(_user_post_delete, sender=User, dispatch_uid='tc_seg_user_del', weak=False)
    m2m_changed.connect(_grupos, sender=User.groups.through, dispatch_uid='tc_seg_grupos', weak=False)
    post_save.connect(_grupo_creado, sender=Group, dispatch_uid='tc_seg_grupo_new', weak=False)
    post_delete.connect(_grupo_borrado, sender=Group, dispatch_uid='tc_seg_grupo_del', weak=False)

    try:
        from constance.signals import config_updated

        def _constance(sender, key, old_value, new_value, **kw):
            evento('configuracion_cambiada', None, ajuste=key)   # nunca el valor
        config_updated.connect(_constance, dispatch_uid='tc_seg_constance', weak=False)
    except Exception:
        pass


class ArchivoTolerante(logging.Handler):
    """Handler de archivo con rotación que NUNCA impide arrancar la app: si el archivo no se puede
    abrir (permisos, carpeta inexistente) descarta el registro en silencio."""

    def __init__(self, filename, maxBytes=5 * 1024 * 1024, backupCount=10):
        super().__init__()
        self._args = (filename, maxBytes, backupCount)
        self._h = None
        self._fallo = False

    def _handler(self):
        if self._h is None and not self._fallo:
            try:
                from logging.handlers import RotatingFileHandler
                fn, mb, bc = self._args
                self._h = RotatingFileHandler(fn, maxBytes=mb, backupCount=bc, encoding='utf-8')
                self._h.setFormatter(self.formatter or logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            except Exception:
                self._fallo = True
        return self._h

    def emit(self, record):
        h = self._handler()
        if h is None:
            return
        try:
            h.emit(record)
        except Exception:
            pass
