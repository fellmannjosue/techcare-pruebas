from django.shortcuts import render
from django.urls import reverse


_RUTAS_PERMITIDAS = (
    '/accounts/login/',
    '/accounts/logout/',
    '/mantenimiento-sistema/',
)


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from constance import config
            en_mantenimiento = config.MAINTENANCE_MODE
        except Exception:
            en_mantenimiento = False

        if en_mantenimiento:
            user = getattr(request, 'user', None)
            es_superuser = user and user.is_authenticated and user.is_superuser

            ruta = request.path_info
            permitida = any(ruta.startswith(p) for p in _RUTAS_PERMITIDAS)

            if not es_superuser and not permitida:
                return render(request, 'core/mantenimiento.html', status=503)

        return self.get_response(request)
