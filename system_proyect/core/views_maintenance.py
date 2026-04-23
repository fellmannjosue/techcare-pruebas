from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET


@login_required
@require_POST
def toggle_mantenimiento(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    from constance import config
    config.MAINTENANCE_MODE = not config.MAINTENANCE_MODE
    return JsonResponse({'ok': True, 'activo': config.MAINTENANCE_MODE})


@login_required
@require_GET
def estado_mantenimiento(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    from constance import config
    return JsonResponse({'ok': True, 'activo': config.MAINTENANCE_MODE})
