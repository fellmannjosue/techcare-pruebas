from django.contrib import admin
from core.audit_admin import AuditAdminMixin
from .models import (
    InventoryItem,
    Computadora,
    Televisor,
    Impresora,
    Router,
    DataShow,
)

@admin.register(InventoryItem)
class InventoryItemAdmin(AuditAdminMixin):
    list_display = ('category', 'details')
    search_fields = ('category', 'details')


@admin.register(Computadora)
class ComputadoraAdmin(AuditAdminMixin):
    list_display = ('asset_id', 'modelo', 'serie', 'ip', 'asignado_a', 'area', 'grado', 'fecha_instalado')
    search_fields = ('asset_id', 'modelo', 'serie', 'ip', 'asignado_a', 'area', 'grado')


@admin.register(Televisor)
class TelevisorAdmin(AuditAdminMixin):
    list_display = ('asset_id', 'modelo', 'serie', 'ip', 'grado', 'area')
    search_fields = ('asset_id', 'modelo', 'serie', 'ip', 'grado', 'area')


@admin.register(Impresora)
class ImpresoraAdmin(AuditAdminMixin):
    list_display = (
        'asset_id', 'nombre', 'modelo', 'serie', 'asignado_a',
        'nivel_tinta', 'ultima_vez_llenado', 'cantidad_impresiones', 'a_color'
    )
    list_filter = ('a_color',)
    search_fields = ('asset_id', 'nombre', 'modelo', 'serie', 'asignado_a')


@admin.register(Router)
class RouterAdmin(AuditAdminMixin):
    list_display = ('asset_id', 'modelo', 'serie', 'nombre_router', 'ip_asignada', 'ip_uso', 'ubicado')
    search_fields = ('asset_id', 'modelo', 'serie', 'nombre_router', 'ubicado')


@admin.register(DataShow)
class DataShowAdmin(AuditAdminMixin):
    list_display = ('asset_id', 'nombre', 'modelo', 'serie', 'estado')
    list_filter = ('estado', 'cable_corriente', 'hdmi', 'vga', 'extension')
    search_fields = ('asset_id', 'nombre', 'modelo', 'serie')
