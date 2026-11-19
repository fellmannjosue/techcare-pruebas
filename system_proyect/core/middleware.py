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


# <--- hecho por claude code (17-nov-2026): área a la que pertenece una petición (para el bloqueo por formulario).
_TOKENS_AREA = {
    'bilingue': {'bilingue', 'bilingüe', 'bl', 'colegio_bl', 'primaria_bl', 'primaria'},
    'colegio':  {'colegio', 'col', 'bachillerato'},
}


def _peticion_de_otra_area(request, config):
    """True si la petición es claramente de un área distinta a la bloqueada y el usuario también pertenece a esa área.

    Solo aplica con un área concreta (bilingue/colegio). Las pistas del área: la URL, el parámetro `area`
    (GET, POST o JSON) y, en Agendas, el área del modo maestro guardada en la sesión. Sin pistas → se bloquea.
    """
    area = getattr(config, 'MAINTENANCE_AREA', 'all')
    if area not in _TOKENS_AREA:
        return False
    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return False
    otras = [a for a in _TOKENS_AREA if a != area]
    grupos = set(user.groups.values_list('name', flat=True))
    otras = [a for a in otras if grupos & set(_AREA_GROUPS.get(a, ()))]
    if not otras:
        return False                      # solo pertenece al área bloqueada
    pistas = [seg.lower() for seg in request.path_info.split('/') if seg]
    for v in (request.GET.get('area'), request.POST.get('area') if request.method == 'POST' else None):
        if v:
            pistas.append(str(v).lower())
    if request.method == 'POST' and 'json' in (request.content_type or ''):
        try:
            import json as _json
            cuerpo = _json.loads(request.body or b'{}')
            if isinstance(cuerpo, dict) and cuerpo.get('area'):
                pistas.append(str(cuerpo['area']).lower())
        except Exception:
            pass
    if request.path_info.startswith('/agendas/'):
        try:
            if request.session.get('agenda_modo_maestro') and request.session.get('agenda_area_maestro'):
                pistas.append(str(request.session['agenda_area_maestro']).lower())
            elif request.GET.get('modo') == 'maestro' and request.GET.get('area'):
                pistas.append(str(request.GET['area']).lower())
        except Exception:
            pass
    pistas = set(pistas)
    if pistas & _TOKENS_AREA[area]:
        return False                      # la petición es del área bloqueada
    return any(pistas & _TOKENS_AREA[a] for a in otras)


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
        # <--- hecho por claude code (10-sep-2026): programas ocultos (Configuración → Seguridad)
        bloqueo = self._chequear_programa_oculto(request, config)
        if bloqueo is not None:
            return bloqueo
        bloqueo = self._chequear_modulos(request, config)
        if bloqueo is not None:
            return bloqueo
        return self._aplicar_solo_lectura(request, config, self.get_response(request))

    # <--- hecho por claude code (10-sep-2026): un programa oculto no se puede abrir ni por URL.
    # Aplica a TODO usuario autenticado que no sea superusuario (el anónimo llega al login igual).
    def _chequear_programa_oculto(self, request, config):
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated) or user.is_superuser:
            return None
        from core.programas import programa_oculto_de_ruta
        prog = programa_oculto_de_ruta(request.path_info, config)
        if not prog:
            return None
        try:
            inicio = reverse('menu')
        except NoReverseMatch:
            inicio = '/'
        return render(request, 'core/formulario_bloqueado.html', {
            'mod_label':   prog['label'],
            'mod_key':     prog['key'],
            'desactivado': True,
            'solo_lectura': False,
            'inicio_url':  inicio,
        }, status=503)

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
        # <--- hecho por claude code (17-nov-2026): pedido del usuario — el bloqueo por formulario solo afecta el ÁREA
        # elegida. Un usuario de dos áreas (p. ej. maestra de Bilingüe y de Colegio) sigue libre en lo de la otra área.
        if _peticion_de_otra_area(request, config):
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


# <--- hecho por claude code (28-sep-2026): cierre de sesión por INACTIVIDAD del lado del servidor.
# El JS (idle_logout.js) solo actúa con una pestaña abierta; si el usuario cerraba el navegador la
# sesión seguía viva (cookie de 1 año). Ahora cada petición autenticada renueva la caducidad a
# SESION_INACTIVIDAD_MIN minutos (deslizante): sin peticiones en ese tiempo, la sesión caduca sola.
class SesionInactividadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def minutos():
        try:
            from constance import config
            m = int(config.SESION_INACTIVIDAD_MIN)
            return m if m > 0 else 240
        except Exception:
            return 240

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and hasattr(request, 'session'):
            try:
                request.session.set_expiry(self.minutos() * 60)
            except Exception:
                pass
        return response


# <--- hecho por claude code (seguridad 05-nov-2026): CANDADO GLOBAL DE SESIÓN. Antes cada vista tenía que acordarse de @login_required y un olvido la dejaba pública en internet (pasó 3 veces: enfermería, dashboard C1, PDF/QR de inventario). Ahora TODO pide sesión salvo lo marcado con @login_not_required (login, PWA, firmas por token, PNG de WhatsApp, Google Forms, formulario de tickets) y las vistas de Django REST Framework, que hacen su propia autenticación (IsAuthenticated por defecto) y responden 401/403 en vez de redirigir.
from django.contrib.auth.middleware import LoginRequiredMiddleware as _DjLoginRequiredMiddleware


class TechCareLoginRequiredMiddleware(_DjLoginRequiredMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        cls = getattr(view_func, 'cls', None)
        if cls is not None:
            try:
                from rest_framework.views import APIView
                if isinstance(cls, type) and issubclass(cls, APIView):
                    return None
            except Exception:
                pass
        return super().process_view(request, view_func, view_args, view_kwargs)


# <--- hecho por claude code (09-nov-2026): programas por CANAL (Web / .exe / APK), ver core/canales.py.
class CanalAppMiddleware:
    """Fija el canal de la petición (para los armadores de menús) y bloquea las rutas de los
    programas que ese canal no tiene activados. Aplica también al superusuario (así ve cómo
    queda cada app); /accounts/ no es un programa, así que Configuración nunca se bloquea."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from core.canales import canal_de, ocultos_de_canal, CANAL_ACTUAL, OCULTOS_ACTUAL, CANAL_LABEL
        canal = 'web'
        oc = frozenset()
        try:
            from constance import config
            canal = canal_de(request)
            oc = frozenset(ocultos_de_canal(config, canal))
        except Exception:
            pass
        request.tc_canal = canal
        request.tc_canal_ocultos = oc
        t1 = CANAL_ACTUAL.set(canal)
        t2 = OCULTOS_ACTUAL.set(oc)
        try:
            user = getattr(request, 'user', None)
            if oc and user is not None and user.is_authenticated:
                from core.programas import programa_de_ruta
                prog = programa_de_ruta(request.path_info)
                if prog and prog['key'] in oc:
                    try:
                        inicio = reverse('menu')
                    except NoReverseMatch:
                        inicio = '/'
                    return render(request, 'core/formulario_bloqueado.html', {
                        'mod_label':   prog['label'],
                        'mod_key':     prog['key'],
                        'desactivado': True,
                        'canal_label': CANAL_LABEL.get(canal, canal),
                        'solo_lectura': False,
                        'inicio_url':  inicio,
                    }, status=403)
            return self.get_response(request)
        finally:
            CANAL_ACTUAL.reset(t1)
            OCULTOS_ACTUAL.reset(t2)


# <--- hecho por claude code (09-nov-2026): modo VENTANA (?embed=1). El launcher «Registrar» de Servicio Técnico
# carga el formulario REAL dentro de su ventana (iframe). Aquí: (1) se permite meterlo en un iframe del MISMO sitio
# (X-Frame-Options SAMEORIGIN solo para ?embed=1; el resto sigue DENY) y (2) cuando el POST termina en redirección
# (guardado o error), en vez de seguir a la lista se responde una página mínima que avisa a la ventana padre
# con los mensajes de Django. Si la redirección abre OTRO formulario (caso especial, ?nuevo=), sigue en la ventana.
class EmbedVentanaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        embed = request.GET.get('embed') == '1'
        response = self.get_response(request)
        if not embed:
            return response
        response['X-Frame-Options'] = 'SAMEORIGIN'
        if request.method == 'POST' and response.status_code in (301, 302, 303):
            destino = response.get('Location', '') or ''
            if 'caso_especial=' in destino or 'nuevo=' in destino:
                sep = '&' if '?' in destino else '?'
                response['Location'] = destino + sep + 'embed=1'
                return response
            from django.contrib import messages as _msgs
            lista = [{'nivel': m.level_tag, 'texto': str(m)} for m in _msgs.get_messages(request)]
            ok = not any(m['nivel'] == 'error' for m in lista)
            r = render(request, 'core/embed_resultado.html',
                       {'resultado': {'ok': ok, 'mensajes': lista, 'destino': destino}})
            r['X-Frame-Options'] = 'SAMEORIGIN'
            return r
        return response


# <--- hecho por claude code (09-nov-2026, revisión ISO 27001 · fuga de información): descargas sin caché
_TIPOS_PRIVADOS = (
    'application/pdf', 'application/zip', 'application/x-zip-compressed',
    'application/vnd.openxmlformats-officedocument', 'application/vnd.ms-excel',
    'application/msword', 'text/csv', 'application/octet-stream',
)


class DescargasPrivadasMiddleware:
    """Los documentos que genera TechCare (ficha médica, notas, reportes de conducta, planillas,
    exportes) llevan datos de menores y de personal. Sin cabecera, el navegador o un proxy pueden
    guardarlos en caché en equipos compartidos. Se agrega `Cache-Control: private, no-store` a toda
    respuesta de documento o de descarga (Content-Disposition) que no haya fijado su propia caché.
    No afecta a /static/ ni /media/ (los sirve Apache)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            tipo = (response.get('Content-Type') or '').lower()
            if response.has_header('Cache-Control'):
                return response
            if response.has_header('Content-Disposition') or tipo.startswith(_TIPOS_PRIVADOS):
                response['Cache-Control'] = 'private, no-store'
                response['Pragma'] = 'no-cache'
        except Exception:
            pass
        return response
