# system_proyect/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as accounts_views

urlpatterns = [

    path('sw.js', accounts_views.pwa_service_worker, name='pwa_sw'),
    path('offline/', accounts_views.pwa_offline, name='pwa_offline'),

    # ──────────────────────────────────────────────────────────────────────────
    # 1) Ruta raíz: redirige al login
    # ──────────────────────────────────────────────────────────────────────────
    path('', lambda request: redirect('/accounts/login/')),

    # ──────────────────────────────────────────────────────────────────────────
    # 2) Admin de Django
    # ──────────────────────────────────────────────────────────────────────────
    path('admin/', admin.site.urls),
    path('core/', include('core.urls')),

    # ──────────────────────────────────────────────────────────────────────────
    # 3) Autenticación y perfil de usuario
    # ──────────────────────────────────────────────────────────────────────────
    path('accounts/', include('accounts.urls')),

    # ──────────────────────────────────────────────────────────────────────────
    # 4) Módulos principales de la aplicación
    # ──────────────────────────────────────────────────────────────────────────
    path('tickets/',       include('tickets.urls')),
    path('inventario/',    include('inventario.urls')),
    path('mantenimiento/', include(('mantenimiento.urls', 'mantenimiento'), namespace='mantenimiento')),

    # ──────────────────────────────────────────────────────────────────────────
    # 5) Módulos agro-sanitarios y de salud
    # ──────────────────────────────────────────────────────────────────────────
    path('enfermeria/',      include(('enfermeria.urls', 'enfermeria'), namespace='enfermeria')),

    # ──────────────────────────────────────────────────────────────────────────
    # 6) Patrocinios
    # ──────────────────────────────────────────────────────────────────────────
    path('sponsors/', include('sponsors.urls')),


    # ──────────────────────────────────────────────────────────────────────────
    # 8) Módulo de Conducta 
    # ──────────────────────────────────────────────────────────────────────────
    path('conducta/', include('conducta.urls')),
    path('agendas/',  include(('agendas.urls', 'agendas'), namespace='agendas')),
    # <--- hecho por claude code: Gestión de Desarrollo (requerimientos y proyectos)
    path('desarrollo/', include(('desarrollo.urls', 'desarrollo'), namespace='desarrollo')),
    path('contabilidad/', include(('contabilidad.urls', 'contabilidad'), namespace='contabilidad')),
    path('red/', include(('red.urls', 'red'), namespace='red')),  # <--- hecho por claude code: ANA Network Manager
    # ──────────────────────────────────────────────────────────────────────────
    # 8) Módulo de reloj
    # ──────────────────────────────────────────────────────────────────────────
    path('reloj/', include('reloj.urls')),

    # ──────────────────────────────────────────────────────────────────────────
    # 9) Módulo de calculadoras
    # ──────────────────────────────────────────────────────────────────────────
    path('calculadoras/', include('calculadoras.urls')),

    path('cfp/', include(('cfp.urls', 'cfp'), namespace='cfp')),

    path('notas-parcial/', include('notas_parcial.urls')),

    # ──────────────────────────────────────────────────────────────────────────
    # 11) Inventario y Mantenimiento de Cámaras
    # ──────────────────────────────────────────────────────────────────────────
    path('inventario-camaras/', include(('inventario_camaras.urls', 'inventario_camaras'), namespace='inventario_camaras')),
    # <--- hecho por claude code: portal nuevo del superusuario
    path('portal/', include('portal_super.urls')),

    # Apps en construcción (solo superuser)
    # <--- hecho por claude code: 'atencion-padres' y 'camaras' eliminadas (no se usaban)
    path('salidas-bano/',    include(('salidas_bano.urls',    'salidas_bano'),    namespace='salidas_bano')),
    path('ingresos-notas/',  include(('ingresos_notas.urls',  'ingresos_notas'),  namespace='ingresos_notas')),  # <--- hecho por claude code
]

# <--- hecho por claude code: sirve archivos de media (imágenes subidas por usuarios)
# en modo desarrollo (DEBUG=True). Necesario para que las evidencias sean accesibles
# en el template vía {{ ev.imagen.url }}.
# En producción nginx debe tener un location /media/ apuntando a MEDIA_ROOT.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
