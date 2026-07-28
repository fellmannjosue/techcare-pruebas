# portal_super/urls.py
# <--- hecho por claude code
from django.urls import path

from . import api, views

app_name = 'portal_super'

urlpatterns = [
    # SPA (Next export) — /portal/app/
    path('app/', views.app_spa, name='app_spa'),
    # API — /portal/api/...
    path('api/resumen/', api.resumen, name='api_resumen'),
    path('api/nav/', api.nav, name='api_nav'),
    path('api/usuarios/', api.usuarios, name='api_usuarios'),
    path('api/ui-preference/', views.ui_preference, name='ui_preference'),
]
