# <--- hecho por claude code: ANA Network Manager — admin
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (Campus, Edificio, Ubicacion, Gabinete, VLAN, Device,
                     NetworkInterface, IPAddress, RedAuditLog,
                     Switch, SwitchPort, NetworkLink)


@admin.register(VLAN)
class VLANAdmin(SimpleHistoryAdmin):
    list_display = ('vlan_id', 'nombre', 'subred', 'estado', 'estado_capacidad', 'cantidad_ip_disponibles')
    list_filter = ('estado', 'estado_capacidad', 'tipo_dhcp')
    search_fields = ('vlan_id', 'nombre', 'subred')


@admin.register(IPAddress)
class IPAddressAdmin(SimpleHistoryAdmin):
    list_display = ('direccion', 'vlan', 'estado', 'tipo', 'hostname', 'mac')
    list_filter = ('estado', 'tipo', 'vlan')
    search_fields = ('direccion', 'mac', 'hostname')


@admin.register(Device)
class DeviceAdmin(SimpleHistoryAdmin):
    list_display = ('nombre', 'tipo', 'ip', 'ubicacion', 'estado')
    list_filter = ('tipo', 'estado', 'criticidad')
    search_fields = ('nombre', 'hostname', 'numero_serie', 'mac_principal', 'ip')


@admin.register(Switch)
class SwitchAdmin(SimpleHistoryAdmin):
    list_display = ('nombre', 'modelo', 'ip_admin', 'ubicacion', 'administrable', 'estado')
    list_filter = ('administrable', 'poe', 'estado')
    search_fields = ('nombre', 'modelo', 'ip_admin')


@admin.register(SwitchPort)
class SwitchPortAdmin(SimpleHistoryAdmin):
    list_display = ('switch', 'numero', 'nombre', 'modo_vlan', 'estado_fisico')
    list_filter = ('modo_vlan', 'estado_fisico', 'tipo', 'switch')


from .models import Plano, Marcador, LineaPlano, RackItem  # noqa: E402

for m in (Campus, Edificio, Ubicacion, Gabinete, NetworkInterface, RedAuditLog, NetworkLink, Plano, Marcador, LineaPlano, RackItem):
    admin.site.register(m)
