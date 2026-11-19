from django.contrib import admin
from django.urls import reverse              # <--- hecho por claude code (seguridad 05-nov-2026)
from django.utils.html import format_html    # <--- hecho por claude code (seguridad 05-nov-2026)
from core.audit_admin import AuditAdminMixin, _AdminBase   # <--- hecho por claude code (seguridad 05-nov-2026): _AdminBase = Unfold (mismo aspecto)
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
    # <--- hecho por claude code (seguridad 05-nov-2026): el widget enlazaba a /media/inventario_camaras/ (Apache lo bloquea) y dejaba subir cualquier archivo sin validar; ahora se ve por la vista con candado y se sube solo desde la ficha
    fields = ('ver_foto', 'orden')
    readonly_fields = ('ver_foto',)

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Foto')
    def ver_foto(self, obj):
        if not obj.pk or not obj.imagen:
            return '—'
        return format_html('<a href="{}" target="_blank" rel="noopener">Ver foto {}</a>',
                           reverse('inventario_camaras:foto_ver', args=[obj.pk]), obj.pk)


# <--- hecho por claude code (seguridad 05-nov-2026): sin esto core/admin_auto registraba las fotos con un admin genérico (enlace roto a /media/ y subida sin validar)
@admin.register(FotoMantenimientoCamara)
class FotoMantenimientoCamaraAdmin(_AdminBase):
    list_display = ('id', 'registro', 'ver_foto', 'orden')
    fields = ('registro', 'ver_foto', 'orden')
    readonly_fields = ('registro', 'ver_foto')
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    @admin.display(description='Foto')
    def ver_foto(self, obj):
        return FotoMantenimientoCamaraInline.ver_foto(self, obj)


@admin.register(MantenimientoCamara)
class MantenimientoCamaraAdmin(AuditAdminMixin):
    list_display  = ('record_id', 'grupo', 'tipo_falla', 'date', 'status', 'firmado')
    list_filter   = ('status', 'tipo_falla', 'date', 'grupo')
    search_fields = ('record_id', 'grupo', 'tecnico_nombre', 'responsable_nombre')
    ordering      = ('-date',)
    date_hierarchy = 'date'
    inlines = [FotoMantenimientoCamaraInline]
    readonly_fields = ('token_firma', 'firmado_en')
