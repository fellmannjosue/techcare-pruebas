# <--- hecho por claude code: Mapeo de Cámaras
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

FEATURES = [
    {"icon": "ti-camera",           "label": "Mapa interactivo"},
    {"icon": "ti-map-pin",          "label": "Ubicación por edificio"},
    {"icon": "ti-eye",              "label": "Vista previa en vivo"},
    {"icon": "ti-settings",         "label": "Configuración de cámaras"},
    {"icon": "ti-shield-check",     "label": "Control de acceso"},
    {"icon": "ti-download",         "label": "Exportar plano"},
]

@login_required
def index(request):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    return render(request, 'construccion_base.html', {
        'app_nombre':    'Mapeo de Cámaras',
        'app_icono':     'ti-camera',
        'app_color':     'red',
        'app_desc':      'Visualización interactiva del mapa de cámaras de seguridad por edificio y zona.',
        'features_json': json.dumps(FEATURES),
    })
