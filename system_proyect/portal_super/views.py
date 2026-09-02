# portal_super/views.py
# <--- hecho por claude code: la SPA Next (app_spa) se retiró el 26-ago-2026. El Panel
# Principal es Django (accounts:menu). Se conserva ui_preference por compatibilidad con
# el campo PerfilUsuario.prefer_new_ui, pero ya no redirige a ningún portal externo.
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def ui_preference(request):
    """Fija perfil.prefer_new_ui. Solo superusuario. Ya no existe portal alterno:
    el destino es siempre el Panel Principal de Django."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False}, status=403)
    try:
        data = json.loads(request.body or b'{}')
    except ValueError:
        data = {}
    prefer = bool(data.get('prefer_new_ui', False))
    try:
        perfil = request.user.perfil
        perfil.prefer_new_ui = prefer
        perfil.save(update_fields=['prefer_new_ui'])
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': True, 'prefer_new_ui': prefer, 'destino': '/accounts/menu/'})
