import datetime as dt

from django.shortcuts import render, redirect
from django.urls import reverse, NoReverseMatch


_RUTAS_PERMITIDAS = (
    '/accounts/login/',
    '/accounts/logout/',
    '/mantenimiento-sistema/',
    '/reloj/',
    '/api/mantenimiento/',  # accesible para gestión de mantenimiento
)

_AREA_GROUPS = {
    'bilingue': ('maestros_bilingue',),
    'colegio':  ('maestros_colegio',),
}
_AREA_LABELS = {
    'bilingue': 'Bilingüe',
    'colegio':  'Colegio',
    'all':      'General',
    'staff':    'Staff',
}

# Staff que siempre pasan en cualquier modo
_STAFF_EXCEPTIONS_ALL = frozenset(['yzavala@ana-hn.org', 'glorenzo@ana-hn.org'])


class SoloProgressMiddleware:
    """Restringe a usuarios del grupo solo_progress a únicamente la vista progress_report_bilingue."""

    _RUTAS_LIBRES = ('/accounts/login/', '/accounts/logout/', '/static/', '/media/')

    def __init__(self, get_response):
        self.get_response = get_response
        self._destino = None

    def _get_destino(self):
        if self._destino is None:
            try:
                self._destino = reverse('progress_report_bilingue')
            except NoReverseMatch:
                self._destino = '/'
        return self._destino

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (user and user.is_authenticated and not user.is_superuser
                and user.groups.filter(name='solo_progress').exists()):
            destino = self._get_destino()
            ruta = request.path_info
            if not any(ruta.startswith(p) for p in self._RUTAS_LIBRES) and ruta != destino:
                return redirect(destino)
        return self.get_response(request)


def _audiencia_afectada(user, config):
    """<--- hecho por claude code: ¿el filtro de área/usuarios alcanza a este usuario?

    Misma regla que usaba el mantenimiento general; extraída para reutilizarla
    también en el bloqueo por formulario. El superusuario nunca queda afectado.
    """
    is_auth = bool(user and user.is_authenticated)
    if is_auth and user.is_superuser:
        return False
    is_staff_user = is_auth and user.is_staff

    # Modo usuarios específicos: solo esos correos
    blocked_str = getattr(config, 'MAINTENANCE_BLOCKED_USERS', '') or ''
    if blocked_str.strip():
        if not is_auth:
            return False
        emails = {e.strip().lower() for e in blocked_str.split(',') if e.strip()}
        return (user.email or '').lower() in emails

    area = getattr(config, 'MAINTENANCE_AREA', 'all')
    if area == 'staff':
        if not is_staff_user:
            return False
        return (user.email or '').lower() not in _STAFF_EXCEPTIONS_ALL
    if area == 'all':
        return is_auth          # anónimos no se bloquean (pueden llegar al login)
    if is_staff_user:
        return False            # área específica: staff siempre exento
    grupos = _AREA_GROUPS.get(area, ())
    return bool(is_auth and grupos and user.groups.filter(name__in=grupos).exists())


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from constance import config
            en_mantenimiento = config.MAINTENANCE_MODE
        except Exception:
            return self.get_response(request)

        if not en_mantenimiento:
            # <--- hecho por claude code: el bloqueo por formulario funciona aunque
            # el mantenimiento general esté apagado.
            return self._continuar(request, config)

        # Auto-deactivar cuando se cumple el tiempo de fin
        end_str = getattr(config, 'MAINTENANCE_END_TIME', '')
        if end_str:
            try:
                if dt.datetime.now() >= dt.datetime.fromisoformat(end_str):
                    area_actual = getattr(config, 'MAINTENANCE_AREA', 'all')
                    config.MAINTENANCE_MODE        = False
                    config.MAINTENANCE_END_TIME    = ''
                    config.MAINTENANCE_BLOCKED_USERS = ''
                    from core.views_maintenance import enviar_correo_fin
                    enviar_correo_fin(area_actual)
                    return self.get_response(request)
            except (ValueError, TypeError):
                pass

        # Rutas de login/logout siempre permitidas
        ruta = request.path_info
        if any(ruta.startswith(p) for p in _RUTAS_PERMITIDAS):
            return self.get_response(request)

        user = getattr(request, 'user', None)
        area = getattr(config, 'MAINTENANCE_AREA', 'all')

        # <--- hecho por claude code: misma regla de siempre, ahora en _audiencia_afectada()
        if not _audiencia_afectada(user, config):
            # No le toca el mantenimiento general, pero sí puede tocarle un formulario bloqueado
            return self._continuar(request, config)

        mensaje  = getattr(config, 'MAINTENANCE_MESSAGE', '')
        end_time = getattr(config, 'MAINTENANCE_END_TIME', '')

        return render(request, 'core/mantenimiento.html', {
            'maint_message':  mensaje,
            'maint_end_time': end_time,
            'maint_area':     _AREA_LABELS.get(area, area),
        }, status=503)

    # <--- hecho por claude code: sigue el flujo normal, pero aplicando el bloqueo por
    # formulario y, si el módulo está en "solo lectura", dejando la página no editable.
    def _continuar(self, request, config):
        bloqueo = self._chequear_modulos(request, config)
        if bloqueo is not None:
            return bloqueo
        return self._aplicar_solo_lectura(request, config, self.get_response(request))

    def _aplicar_solo_lectura(self, request, config, response):
        """En modo 'lectura' la página se ve pero NO se puede escribir: deshabilita los
        campos de los formularios que envían datos y oculta los botones de guardar.
        (El corte de POST en el servidor sigue existiendo como respaldo real.)"""
        mod = getattr(request, '_tc_solo_lectura', None)
        if not mod:
            return response
        ctype = (response.get('Content-Type') or '').lower()
        if 'text/html' not in ctype or getattr(response, 'streaming', False):
            return response
        if response.status_code != 200 or not hasattr(response, 'content'):
            return response
        try:
            html = response.content.decode(response.charset or 'utf-8')
        except (UnicodeDecodeError, LookupError):
            return response
        if '</body>' not in html:
            return response

        etiqueta = mod['label'].replace('"', '&quot;')
        extra = """
<div id="tc-solo-lectura-bar" style="position:sticky;top:0;z-index:1080;background:#fff3bf;
     border-bottom:1px solid #f0c000;color:#664d03;padding:.5rem 1rem;font-size:.875rem;text-align:center;">
  <strong>Solo lectura</strong> — %s está temporalmente en consulta. No se pueden guardar cambios.
</div>
<script>
(function(){
  function bloquear(){
    // Solo los formularios que ESCRIBEN (POST). Los de búsqueda (GET) siguen usables.
    document.querySelectorAll('form').forEach(function(f){
      var m = (f.getAttribute('method') || 'get').toLowerCase();
      if (m !== 'post') return;
      f.querySelectorAll('input, select, textarea, button').forEach(function(el){
        if (el.type === 'hidden') return;
        el.disabled = true;
      });
      f.addEventListener('submit', function(e){ e.preventDefault(); }, true);
    });
    // Botones sueltos que suelen guardar/eliminar
    document.querySelectorAll('[type=submit], .btn-primary[onclick], .btn-danger[onclick]').forEach(function(el){
      el.disabled = true;
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bloquear);
  else bloquear();
})();
</script>
""" % etiqueta

        html = html.replace('</body>', extra + '</body>', 1)
        response.content = html.encode(response.charset or 'utf-8')
        if response.has_header('Content-Length'):
            response['Content-Length'] = str(len(response.content))
        return response

    # <--- hecho por claude code: bloqueo selectivo por formulario
    def _chequear_modulos(self, request, config):
        """Devuelve una respuesta si el formulario está restringido para este usuario; si no, None.

        'bloqueado' → no entra. 'lectura' → puede ver pero no guardar (se cortan POST/PUT/DELETE).
        """
        from core.maintenance_modules import modulo_de_ruta, leer_estados, ESTADO_LABELS

        ruta = request.path_info
        if any(ruta.startswith(p) for p in _RUTAS_PERMITIDAS):
            return None

        mod = modulo_de_ruta(ruta)
        if not mod:
            return None

        estado = leer_estados(config).get(mod['key'], 'normal')
        if estado == 'normal':
            return None

        if not _audiencia_afectada(getattr(request, 'user', None), config):
            return None

        # En "solo lectura": la página se muestra, pero marcada para dejarla no editable
        if estado == 'lectura' and request.method in ('GET', 'HEAD', 'OPTIONS'):
            request._tc_solo_lectura = mod
            return None

        # <--- hecho por claude code: pantalla propia (no la de "sistema en mantenimiento"),
        # con botón de volver, porque el resto del sistema sigue disponible.
        try:
            inicio = reverse('menu')
        except NoReverseMatch:
            inicio = '/'

        return render(request, 'core/formulario_bloqueado.html', {
            'mod_label':      mod['label'],
            'mod_key':        mod['key'],
            'solo_lectura':   estado == 'lectura',
            'estado_label':   ESTADO_LABELS.get(estado, estado),
            'maint_end_time': getattr(config, 'MAINTENANCE_END_TIME', ''),
            'inicio_url':     inicio,
        }, status=503)
