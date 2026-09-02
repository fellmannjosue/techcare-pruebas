# <--- hecho por claude code: ANA Network Manager — rutas Fase 1
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from . import api  # <--- hecho por claude code: API REST solo lectura (Fase 5)

app_name = 'red'

_api_router = DefaultRouter()
_api_router.register('vlans', api.VLANVS, basename='api-vlans')
_api_router.register('ips', api.IPVS, basename='api-ips')
_api_router.register('dispositivos', api.DeviceVS, basename='api-dispositivos')
_api_router.register('switches', api.SwitchVS, basename='api-switches')
_api_router.register('enlaces', api.LinkVS, basename='api-enlaces')
_api_router.register('ubicaciones', api.UbicacionVS, basename='api-ubicaciones')
_api_router.register('gabinetes', api.GabineteVS, basename='api-gabinetes')

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('panel/', views.panel, name='panel'),   # Fase 4: panel avanzado
    # ── Fase 4: pruebas de conectividad ──
    path('pruebas/', views.pruebas, name='pruebas'),
    path('pruebas/dispositivo/<int:pk>/', views.device_ping, name='device_ping'),
    path('pruebas/switch/<int:pk>/', views.switch_ping, name='switch_ping'),
    path('migracion/', views.migracion, name='migracion'),   # Fase 4: planificador VLAN
    path('migracion/ejecutar/', views.migracion_ejecutar, name='migracion_ejecutar'),  # ejecución real (POST)
    # ── Fase 5: buscador + exportar ──
    path('buscar/', views.buscar, name='buscar'),
    path('api/buscar/', views.api_buscar, name='api_buscar'),
    path('export/excel/', views.export_excel, name='export_excel'),
    # VLAN
    path('vlans/', views.vlan_list, name='vlan_list'),
    path('vlans/nueva/', views.vlan_form, name='vlan_nueva'),
    path('vlans/<int:pk>/', views.vlan_detail, name='vlan_detail'),
    path('vlans/<int:pk>/editar/', views.vlan_form, name='vlan_editar'),
    # IPAM
    path('vlans/<int:pk>/ipam/', views.ipam_grid, name='ipam_grid'),
    path('vlans/<int:vlan_pk>/ip/nueva/', views.ip_form, name='ip_nueva'),
    path('vlans/<int:vlan_pk>/ip/<int:pk>/editar/', views.ip_form, name='ip_editar'),
    path('ip/<int:pk>/liberar/', views.ip_liberar, name='ip_liberar'),

    # Ubicaciones
    path('ubicaciones/', views.ubicaciones, name='ubicaciones'),
    path('ubicaciones/campus/nuevo/', views.campus_form, name='campus_nuevo'),
    path('ubicaciones/campus/<int:pk>/editar/', views.campus_form, name='campus_editar'),
    path('ubicaciones/edificio/nuevo/', views.edificio_form, name='edificio_nuevo'),
    path('ubicaciones/edificio/<int:pk>/editar/', views.edificio_form, name='edificio_editar'),
    path('ubicaciones/ubicacion/nueva/', views.ubicacion_form, name='ubicacion_nueva'),
    path('ubicaciones/ubicacion/<int:pk>/editar/', views.ubicacion_form, name='ubicacion_editar'),
    path('ubicaciones/gabinete/nuevo/', views.gabinete_form, name='gabinete_nuevo'),
    path('ubicaciones/gabinete/<int:pk>/editar/', views.gabinete_form, name='gabinete_editar'),
    path('ubicaciones/<str:tipo>/<int:pk>/borrar/', views.ubicacion_borrar, name='ubicacion_borrar'),

    # Dispositivos
    path('dispositivos/', views.device_list, name='device_list'),
    path('dispositivos/nuevo/', views.device_form, name='device_nuevo'),
    path('dispositivos/<int:pk>/', views.device_detail, name='device_detail'),
    path('dispositivos/<int:pk>/editar/', views.device_form, name='device_editar'),
    path('dispositivos/<int:pk>/borrar/', views.device_borrar, name='device_borrar'),
    path('dispositivos/<int:device_pk>/interfaz/nueva/', views.interface_form, name='interface_nueva'),
    path('dispositivos/<int:device_pk>/interfaz/<int:pk>/editar/', views.interface_form, name='interface_editar'),
    path('interfaz/<int:pk>/borrar/', views.interface_borrar, name='interface_borrar'),

    # Auditoría
    path('auditoria/', views.auditoria, name='auditoria'),

    # ── Fase 2: Switches / Puertos / Enlaces ──
    path('switches/', views.switch_list, name='switch_list'),
    path('switches/nuevo/', views.switch_form, name='switch_nuevo'),
    path('switches/<int:pk>/', views.switch_detail, name='switch_detail'),
    path('switches/<int:pk>/editar/', views.switch_form, name='switch_editar'),
    path('switches/<int:pk>/borrar/', views.switch_borrar, name='switch_borrar'),
    path('switches/<int:switch_pk>/puerto/nuevo/', views.port_form, name='port_nuevo'),
    path('switches/<int:switch_pk>/puerto/<int:pk>/editar/', views.port_form, name='port_editar'),

    path('enlaces/', views.link_list, name='link_list'),
    path('enlaces/nuevo/', views.link_form, name='link_nuevo'),
    path('enlaces/<int:pk>/editar/', views.link_form, name='link_editar'),
    path('enlaces/<int:pk>/borrar/', views.link_borrar, name='link_borrar'),

    # ── Fase 3: Mapa de campus ──
    path('planos/', views.planos_list, name='planos_list'),
    path('planos/nuevo/', views.plano_form, name='plano_nuevo'),
    path('planos/<int:pk>/', views.plano_view, name='plano_view'),
    path('planos/<int:pk>/editar/', views.plano_form, name='plano_editar'),
    path('planos/<int:plano_pk>/marcador/add/', views.marcador_add, name='marcador_add'),
    path('marcador/<int:pk>/move/', views.marcador_move, name='marcador_move'),
    path('marcador/<int:pk>/delete/', views.marcador_delete, name='marcador_delete'),
    path('marcador/<int:pk>/edit/', views.marcador_edit, name='marcador_edit'),
    path('marcador/<int:pk>/link/', views.marcador_link, name='marcador_link'),
    path('marcadores/bulk/', views.marcadores_bulk, name='marcadores_bulk'),
    path('planos/<int:plano_pk>/linea/add/', views.linea_add, name='linea_add'),
    path('linea/<int:pk>/delete/', views.linea_delete, name='linea_delete'),
    path('linea/<int:pk>/edit/', views.linea_edit, name='linea_edit'),

    # ── Rack / Gabinete (elevación) ──
    path('racks/', views.racks_list, name='racks_list'),
    path('gabinete/<int:gabinete_pk>/rack/', views.rack_view, name='rack_view'),
    path('gabinete/<int:gabinete_pk>/rack/item/add/', views.rack_item_add, name='rack_item_add'),
    path('rack/item/<int:pk>/edit/', views.rack_item_edit, name='rack_item_edit'),
    path('rack/item/<int:pk>/move/', views.rack_item_move, name='rack_item_move'),
    path('rack/item/<int:pk>/delete/', views.rack_item_delete, name='rack_item_delete'),

    # ── Fase 3: Topología (Cytoscape) ──
    path('topologia/', views.topologia, name='topologia'),
    path('nodo/<int:pk>/pos/', views.nodo_pos, name='nodo_pos'),

    # ── Fase 5: API REST de solo lectura (sesión o token) ──
    path('api/v1/', include(_api_router.urls)),
]
