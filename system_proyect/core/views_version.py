# core/views_version.py
# <--- hecho por claude code: marca las novedades de la versión actual como vistas por el usuario
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.version import version_actual


@login_required
@require_POST
def marcar_version_vista(request):
    """Guarda en el perfil la versión actual, para no volver a mostrar el modal."""
    v = version_actual()
    try:
        perfil = request.user.perfil
        perfil.version_vista = v
        perfil.save(update_fields=['version_vista'])
    except Exception:
        return JsonResponse({'ok': False}, status=200)   # no romper la UI por esto
    return JsonResponse({'ok': True, 'version': v})
