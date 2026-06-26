from django.contrib import admin
from core.audit_admin import AuditAdminMixin
from .models import (
    Servidor, NVR, Componente, Gabinete, Camara,
    TipoFallaCamara, MantenimientoCamara, FotoMantenimientoCamara,
)


@admin.register(Servidor)
class ServidorAdmin(AuditAdminMixin):
    list_display  = ('server_id', 'nombre', 'ubicacion', 'ip')
    search_fields = ('server_id', 'nombre', 'ubicacion', 'ip')
    ordering      = ('server_id',)


@admin.register(NVR)
class NVRAdmin(AuditAdminMixin):
    list_display  = ('nvr_id', 'nombre', 'modelo', 'serie', 'ip', 'canales', 'servidor')
    search_fields = ('nvr_id', 'nombre', 'modelo', 'serie', 'ip')
    list_filter   = ('servidor',)
    ordering      = ('nvr_id',)


@admin.register(Componente)
class ComponenteAdmin(AuditAdminMixin):
    list_display  = ('comp_id', 'detalle', 'sub_detalle')
    search_fields = ('comp_id', 'detalle', 'sub_detalle')
    ordering      = ('detalle',)


@admin.register(Gabinete)
class GabineteAdmin(AuditAdminMixin):
    list_display  = ('gabinete_id', 'nombre', 'ubicacion', 'nvr')
    search_fields = ('gabinete_id', 'nombre', 'ubicacion')
    list_filter   = ('nvr',)
    filter_horizontal = ('componentes',)
    ordering      = ('gabinete_id',)


@admin.register(Camara)
class CamaraAdmin(AuditAdminMixin):
    list_display  = ('camara_id', 'modelo', 'serie', 'ubicacion', 'grupo', 'gabinete', 'estado', 'version_actualizada')
    search_fields = ('camara_id', 'modelo', 'serie', 'ubicacion', 'estado', 'grupo')
    list_filter   = ('grupo', 'gabinete', 'estado')
    ordering      = ('camara_id',)


@admin.register(TipoFallaCamara)
class TipoFallaCamaraAdmin(AuditAdminMixin):
    list_display  = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering      = ('nombre',)


class FotoMantenimientoCamaraInline(admin.TabularInline):
    model = FotoMantenimientoCamara
    extra = 0


@admin.register(MantenimientoCamara)
class MantenimientoCamaraAdmin(AuditAdminMixin):
    list_display  = ('record_id', 'grupo', 'tipo_falla', 'date', 'status', 'firmado')
    list_filter   = ('status', 'tipo_falla', 'date', 'grupo')
    search_fields = ('record_id', 'grupo', 'tecnico_nombre', 'responsable_nombre')
    ordering      = ('-date',)
    date_hierarchy = 'date'
    inlines = [FotoMantenimientoCamaraInline]
    readonly_fields = ('token_firma', 'firmado_en')
