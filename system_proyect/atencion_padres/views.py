# <--- hecho por claude code: Atención a Padres
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

FEATURES = [
    {"icon": "ti-calendar-event",   "label": "Agenda de citas"},
    {"icon": "ti-mail",             "label": "Comunicados"},
    {"icon": "ti-chart-line",       "label": "Seguimiento académico"},
    {"icon": "ti-users",            "label": "Perfil de padres"},
    {"icon": "ti-bell",             "label": "Notificaciones"},
    {"icon": "ti-file-description", "label": "Reportes"},
]

@login_required
def index(request):
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    return render(request, 'construccion_base.html', {
        'app_nombre':    'Atención a Padres',
        'app_icono':     'ti-users',
        'app_color':     'blue',
        'app_desc':      'Módulo para gestionar citas, comunicados y seguimiento con padres de familia.',
        'features_json': json.dumps(FEATURES),
    })
