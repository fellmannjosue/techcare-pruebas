# <--- hecho por claude code: ANA Network Manager — admin
from django.contrib import admin
from django.contrib.admin.widgets import AdminFileWidget
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin

from .forms import _ArchivoEnVista
from .models import (Campus, Edificio, Ubicacion, Gabinete, VLAN, Device,
                     NetworkInterface, IPAddress, RedAuditLog,
                     Switch, SwitchPort, NetworkLink)


# <--- hecho por claude code (seguridad 05-nov-2026, 2.a vuelta): media/red/ queda bloqueada en Apache; el enlace «Actualmente» del admin va a la vista con _gate
class _AdminArchivoProtegido(AdminFileWidget):
    def __init__(self, nombre_url, attrs=None):
        self.nombre_url = nombre_url
        super().__init__(attrs)

    def format_value(self, value):
        v = super().format_value(value)
        inst = getattr(value, 'instance', None)
        if v and getattr(inst, 'pk', None):
            return _ArchivoEnVista(v, reverse(self.nombre_url, args=[inst.pk]))
        return v


class _ArchivosProtegidosMixin:
    archivos_protegidos = {}   # campo -> nombre de la vista que lo sirve con _gate

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        nombre = self.archivos_protegidos.get(db_field.name)
        if nombre:
            kwargs['widget'] = _AdminArchivoProtegido(nombre)
        return super().formfield_for_dbfield(db_field, request, **kwargs)


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
class DeviceAdmin(_ArchivosProtegidosMixin, SimpleHistoryAdmin):
    archivos_protegidos = {'fotografia': 'red:device_foto'}   # <--- hecho por claude code (seguridad 05-nov-2026, 2.a vuelta)
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

for m in (Campus, Edificio, Ubicacion, NetworkInterface, RedAuditLog, NetworkLink, Marcador, LineaPlano, RackItem):
    admin.site.register(m)


# <--- hecho por claude code (seguridad 05-nov-2026, 2.a vuelta): Gabinete y Plano salieron del registro genérico para que su archivo enlace a la vista con _gate
@admin.register(Gabinete)
class GabineteAdmin(_ArchivosProtegidosMixin, admin.ModelAdmin):
    archivos_protegidos = {'fotografia': 'red:gabinete_foto'}


@admin.register(Plano)
class PlanoAdmin(_ArchivosProtegidosMixin, admin.ModelAdmin):
    archivos_protegidos = {'imagen': 'red:plano_imagen'}


# <--- hecho por claude code (16-sep-2026): lista de IPs actuales
from .models import IPActual

@admin.register(IPActual)
class IPActualAdmin(SimpleHistoryAdmin):
    list_display = ('ip', 'categoria', 'vlan', 'descripcion', 'tiene_usuario', 'usuario')
    list_filter = ('categoria', 'vlan', 'tiene_usuario')
    search_fields = ('ip', 'descripcion', 'usuario')
