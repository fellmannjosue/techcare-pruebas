# portal_super/urls.py
# <--- hecho por claude code: la app conserva SOLO el sistema de diseño del portal
# (static/portal_super/css/portal.css y js/portal_theme.js, usados por base_app.html).
# La SPA Next (/portal/app/) y su API se retiraron el 26-ago-2026: el Panel Principal
# real es Django (accounts:menu). Prototipo respaldado en /home/admin2/backups.
from django.urls import path

from . import views

app_name = 'portal_super'

urlpatterns = [
    # Solo se mantiene la preferencia de UI (hoy inerte: ningún flujo la activa).
    path('api/ui-preference/', views.ui_preference, name='ui_preference'),
]
