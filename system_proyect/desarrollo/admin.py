# <--- hecho por claude code: registro en el admin para inspección (superuser).
from django.contrib import admin

from .models import (
    ProyectoDesarrollo, RequerimientoDesarrollo, HistorialRequerimiento,
    ComentarioRequerimiento, AdjuntoRequerimiento, SecuenciaCodigo, SolicitanteCatalogo,
    OpcionCatalogo,
)


@admin.register(SolicitanteCatalogo)
class SolicitanteCatalogoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'orden')
    list_editable = ('activo', 'orden')
    search_fields = ('nombre',)


@admin.register(OpcionCatalogo)
class OpcionCatalogoAdmin(admin.ModelAdmin):
    list_display = ('grupo', 'valor', 'activo', 'orden')
    list_editable = ('activo', 'orden')
    list_filter = ('grupo', 'activo')
    search_fields = ('valor',)


class RequerimientoInline(admin.TabularInline):
    model = RequerimientoDesarrollo
    extra = 0
    fields = ('codigo', 'titulo', 'estado', 'prioridad', 'porcentaje_avance')
    readonly_fields = ('codigo',)
    show_change_link = True


@admin.register(ProyectoDesarrollo)
class ProyectoDesarrolloAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'modulo', 'estado', 'prioridad', 'en_produccion', 'fecha_modificado')
    list_filter = ('estado', 'prioridad', 'en_produccion', 'area')
    search_fields = ('codigo', 'nombre', 'modulo', 'descripcion')
    readonly_fields = ('codigo', 'slug', 'creado_por', 'modificado_por', 'fecha_creado', 'fecha_modificado')
    inlines = [RequerimientoInline]


class HistorialInline(admin.TabularInline):
    model = HistorialRequerimiento
    extra = 0
    readonly_fields = ('fecha', 'estado_anterior', 'estado_nuevo', 'porcentaje_anterior',
                       'porcentaje_nuevo', 'comentario', 'usuario')
    can_delete = False


class ComentarioInline(admin.TabularInline):
    model = ComentarioRequerimiento
    extra = 0


class AdjuntoInline(admin.TabularInline):
    model = AdjuntoRequerimiento
    extra = 0


@admin.register(RequerimientoDesarrollo)
class RequerimientoDesarrolloAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'titulo', 'proyecto', 'estado', 'prioridad',
                    'porcentaje_avance', 'responsable', 'fecha_estimada')
    list_filter = ('estado', 'prioridad', 'tipo', 'clasificacion', 'area')
    search_fields = ('codigo', 'titulo', 'descripcion')
    readonly_fields = ('codigo', 'creado_por', 'modificado_por', 'fecha_creado', 'fecha_modificado')
    autocomplete_fields = ('proyecto',)
    inlines = [HistorialInline, ComentarioInline, AdjuntoInline]


@admin.register(SecuenciaCodigo)
class SecuenciaCodigoAdmin(admin.ModelAdmin):
    list_display = ('clave', 'anio', 'valor')
