# portal_super/views.py
# <--- hecho por claude code: sirve la SPA compilada (Next export) y el toggle de UI.
import json
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


@login_required
def app_spa(request):
    """Devuelve el index.html compilado de la SPA. Solo superusuario.
    Mismo patrón que inventario_camaras.views.app_spa."""
    if not request.user.is_superuser:
        return redirect('menu')
    build = os.path.join(settings.BASE_DIR, 'portal_super', 'static',
                         'portal_super', 'app', 'index.html')
    try:
        with open(build, encoding='utf-8') as fh:
            return HttpResponse(fh.read())
    except FileNotFoundError:
        return render(request, 'portal_super/app_pendiente.html', status=200)


@login_required
@require_POST
def ui_preference(request):
    """Fija perfil.prefer_new_ui (toggle Nueva/Clásica). Solo superusuario.
    Mismo patrón que core.views_version.marcar_version_vista."""
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
    # A dónde ir después de cambiar (el front decide, pero devolvemos la ruta útil)
    destino = '/portal/app/' if prefer else '/accounts/menu/'
    return JsonResponse({'ok': True, 'prefer_new_ui': prefer, 'destino': destino})
