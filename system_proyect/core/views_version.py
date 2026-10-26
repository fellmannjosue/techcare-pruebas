# core/views_version.py
# <--- hecho por claude code: marca las novedades de la versión actual como vistas por el usuario
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.version import version_actual, novedades


# <--- hecho por claude code (26-oct-2026): novedades en JSON para la app de escritorio (.exe).
# PÚBLICO (sin login): la ventana de novedades/actualización del .exe lo lee ANTES del login.
# Solo expone el changelog (mismas novedades que ya ve cualquier usuario en el footer).
def novedades_json(request):
    try:
        limite = int(request.GET.get('limite', 20))
    except (TypeError, ValueError):
        limite = 20
    limite = max(1, min(limite, 50))
    resp = JsonResponse({
        'version': version_actual(),
        'entradas': novedades(limite=limite),
    })
    resp['Access-Control-Allow-Origin'] = '*'   # por si se consume desde el envoltorio
    resp['Cache-Control'] = 'no-store'
    return resp


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
