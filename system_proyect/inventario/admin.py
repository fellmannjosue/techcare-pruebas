from django.contrib import admin
from core.audit_admin import AuditAdminMixin
from .models import (
    CategoriaInventario,
    InventoryItem,
    Computadora,
    Televisor,
    Impresora,
    Router,
    DataShow,
    ModeloTelevisor,
    GradoTelevisor,
    AreaTelevisor,
    ModeloComputadora,
    ModeloMonitor,
    SerieComputadora,
    AsignadoAComputadora,
    AreaComputadora,
    GradoComputadora,
    SubtipoGradoComputadora,
    EdificioComputadora,
)

try:
    from unfold.admin import ModelAdmin as UnfoldModelAdmin
except ImportError:
    UnfoldModelAdmin = admin.ModelAdmin

def _catalogo_admin(nombre_desc):
    """Factory para admins simples de catálogos de computadora."""
    def inner(cls):
        cls.list_display  = ('nombre',)
        cls.search_fields = ('nombre',)
        cls.ordering      = ('nombre',)
        cls.fieldsets = ((None, {"fields": ("nombre",), "description": nombre_desc}),)
        return cls
    return inner


@admin.register(ModeloComputadora)
@_catalogo_admin("Modelos disponibles (ej: HP EliteBook, Dell Latitude, Lenovo ThinkPad).")
class ModeloComputadoraAdmin(UnfoldModelAdmin): pass

@admin.register(ModeloMonitor)
@_catalogo_admin("Modelos de monitor disponibles (ej: Samsung 24\", LG 27\", Dell P2422H).")
class ModeloMonitorAdmin(UnfoldModelAdmin): pass


@admin.register(SerieComputadora)
@_catalogo_admin("Series disponibles (ej: Core i5 10ma Gen, Core i7 12va Gen, Ryzen 5).")
class SerieComputadoraAdmin(UnfoldModelAdmin): pass


@admin.register(AsignadoAComputadora)
@_catalogo_admin("Personas o departamentos a los que se asignan computadoras.")
class AsignadoAComputadoraAdmin(UnfoldModelAdmin): pass


@admin.register(AreaComputadora)
@_catalogo_admin("Áreas disponibles (ej: Bilingüe, Colegio, Administración).")
class AreaComputadoraAdmin(UnfoldModelAdmin): pass


@admin.register(GradoComputadora)
@_catalogo_admin("Grados o ubicaciones disponibles (ej: Kinder, Primero 1, Sala de Maestros).")
class GradoComputadoraAdmin(UnfoldModelAdmin): pass


@admin.register(SubtipoGradoComputadora)
@_catalogo_admin("Sub-tipos para el grado 'Otros' (ej: Dirección Vocacional, Dirección Bilingüe).")
class SubtipoGradoComputadoraAdmin(UnfoldModelAdmin): pass


@admin.register(EdificioComputadora)
@_catalogo_admin("Edificios donde se ubican los equipos generales (ej: Edificio A, Edificio Administrativo).")
class EdificioComputadoraAdmin(UnfoldModelAdmin): pass


@admin.register(CategoriaInventario)
class CategoriaInventarioAdmin(UnfoldModelAdmin):
    list_display  = ('nombre',)
    search_fields = ('nombre',)


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


@admin.register(ModeloTelevisor)
class ModeloTelevisorAdmin(UnfoldModelAdmin):
    list_display   = ('nombre',)
    search_fields  = ('nombre',)
    ordering       = ('nombre',)
    fieldsets = (
        (None, {
            "fields": ("nombre",),
            "description": "Modelos disponibles para televisores (ej: Samsung 55\", LG 43\").",
        }),
    )


@admin.register(GradoTelevisor)
class GradoTelevisorAdmin(UnfoldModelAdmin):
    list_display  = ('nombre',)
    search_fields = ('nombre',)
    ordering      = ('nombre',)
    fieldsets = (
        (None, {
            "fields": ("nombre",),
            "description": "Grados disponibles (ej: Kinder, Primero 1, Segundo 2).",
        }),
    )


@admin.register(AreaTelevisor)
class AreaTelevisorAdmin(UnfoldModelAdmin):
    list_display  = ('nombre',)
    search_fields = ('nombre',)
    ordering      = ('nombre',)
    fieldsets = (
        (None, {
            "fields": ("nombre",),
            "description": "Áreas disponibles (ej: Bilingüe, Colegio, Vocacional).",
        }),
    )


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
