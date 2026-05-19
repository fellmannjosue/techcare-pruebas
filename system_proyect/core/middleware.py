import datetime as dt

from django.shortcuts import render


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
            return self.get_response(request)

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

        # Superuser siempre pasa
        if user and user.is_authenticated and user.is_superuser:
            return self.get_response(request)
        else:
            is_auth       = bool(user and user.is_authenticated)
            is_staff_user = is_auth and user.is_staff

            # Modo usuarios específicos: solo esos usuarios ven el mantenimiento
            blocked_str = getattr(config, 'MAINTENANCE_BLOCKED_USERS', '')
            if blocked_str.strip():
                blocked_emails = {e.strip().lower() for e in blocked_str.split(',') if e.strip()}
                if not is_auth or user.email.lower() not in blocked_emails:
                    return self.get_response(request)
            else:
                # Modo área
                if area == 'staff':
                    # Solo bloquear usuarios staff (excepto excepciones permanentes)
                    if not is_staff_user:
                        return self.get_response(request)
                    if user.email.lower() in _STAFF_EXCEPTIONS_ALL:
                        return self.get_response(request)
                elif area == 'all':
                    # Bloquear todos excepto staff
                    if is_staff_user:
                        return self.get_response(request)
                else:
                    # Área específica (bilingue/colegio): solo maestros del área; staff siempre exentos
                    if is_staff_user:
                        return self.get_response(request)
                    grupos = _AREA_GROUPS.get(area, ())
                    if not (is_auth and grupos and user.groups.filter(name__in=grupos).exists()):
                        return self.get_response(request)

        mensaje  = getattr(config, 'MAINTENANCE_MESSAGE', '')
        end_time = getattr(config, 'MAINTENANCE_END_TIME', '')

        return render(request, 'core/mantenimiento.html', {
            'maint_message':  mensaje,
            'maint_end_time': end_time,
            'maint_area':     _AREA_LABELS.get(area, area),
        }, status=503)
