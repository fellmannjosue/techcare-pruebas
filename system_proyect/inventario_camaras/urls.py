from django.urls import path, include
from django.shortcuts import redirect
from . import views
from . import api          # <--- hecho por claude code
from rest_framework.routers import DefaultRouter

app_name = 'inventario_camaras'


# <--- hecho por claude code: API REST para el frontend Next (build estático)
router = DefaultRouter()
router.register('servidores', api.ServidorVS, basename='api-servidores')
router.register('nvrs', api.NVRVS, basename='api-nvrs')
router.register('gabinetes', api.GabineteVS, basename='api-gabinetes')
router.register('camaras', api.CamaraVS, basename='api-camaras')
router.register('componentes', api.ComponenteVS, basename='api-componentes')
router.register('tipos-falla', api.TipoFallaVS, basename='api-tipos-falla')
router.register('mantenimientos', api.MantenimientoVS, basename='api-mantenimientos')

urlpatterns = [
    path('', views.hub, name='hub'),
    # API + app nueva  <--- hecho por claude code
    path('api/resumen/', api.resumen, name='api_resumen'),
    path('api/', include(router.urls)),
    path('app/', views.app_spa, name='app_spa'),

    # ── Servidores ──
    path('servidores/', views.servidores, name='servidores'),
    path('servidores/<int:pk>/editar/', views.servidor_editar, name='servidor_editar'),
    path('servidores/<int:pk>/eliminar/', views.servidor_eliminar, name='servidor_eliminar'),

    # ── NVRs ──
    path('nvrs/', views.nvrs, name='nvrs'),
    path('nvrs/<int:pk>/editar/', views.nvr_editar, name='nvr_editar'),
    path('nvrs/<int:pk>/eliminar/', views.nvr_eliminar, name='nvr_eliminar'),

    # ── Componentes ──
    path('componentes/', views.componentes, name='componentes'),
    path('componentes/<int:pk>/editar/', views.componente_editar, name='componente_editar'),
    path('componentes/<int:pk>/eliminar/', views.componente_eliminar, name='componente_eliminar'),

    # ── Gabinetes ──
    path('gabinetes/', views.gabinetes, name='gabinetes'),
    path('gabinetes/<int:pk>/editar/', views.gabinete_editar, name='gabinete_editar'),
    path('gabinetes/<int:pk>/eliminar/', views.gabinete_eliminar, name='gabinete_eliminar'),

    # ── Cámaras ──
    path('camaras/', views.camaras, name='camaras'),
    path('camaras/<int:pk>/editar/', views.camara_editar, name='camara_editar'),
    path('camaras/<int:pk>/eliminar/', views.camara_eliminar, name='camara_eliminar'),

    # ── Mantenimiento ──
    path('mantenimiento/', views.mantenimiento_dashboard, name='mantenimiento'),
    path('mantenimiento/<int:pk>/editar/', views.mantenimiento_editar, name='mantenimiento_editar'),
    path('mantenimiento/<int:pk>/eliminar/', views.mantenimiento_eliminar, name='mantenimiento_eliminar'),
    path('mantenimiento/<int:pk>/pdf/', views.download_mantenimiento_pdf, name='mantenimiento_pdf'),
    path('mantenimiento/<int:pk>/firma-solicitada/', views.marcar_firma_solicitada, name='marcar_firma_solicitada'),

    # ── Firma remota (público, sin login) ──
    path('firmar/<uuid:token>/', views.firmar_publico, name='firmar_publico'),

    path('menu/', lambda request: redirect('/accounts/menu/'), name='menu'),
]
