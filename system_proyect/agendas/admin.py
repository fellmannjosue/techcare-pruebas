from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import GradoAgenda, Agenda, ImagenAgenda


class ImagenAgendaInline(TabularInline):
    model   = ImagenAgenda
    extra   = 0
    fields  = ('imagen', 'descripcion', 'subida_por', 'subida_en')
    readonly_fields = ('subida_en',)


@admin.register(GradoAgenda)
class GradoAgendaAdmin(ModelAdmin):
    list_display  = ('nombre', 'area', 'tipo_materias', 'activo', 'orden')
    list_filter   = ('area', 'tipo_materias', 'activo')
    list_editable = ('activo', 'orden')
    search_fields = ('nombre',)
    ordering      = ('area', 'orden', 'nombre')


@admin.register(Agenda)
class AgendaAdmin(ModelAdmin):
    list_display   = ('grado', 'semana_inicio', 'semana_fin', 'usuario', 'estado', 'fecha_creado')
    list_filter    = ('estado', 'grado__area', 'grado')
    search_fields  = ('grado__nombre', 'usuario__username', 'usuario__first_name')
    readonly_fields = ('fecha_creado', 'fecha_modificado', 'creado_por', 'modificado_por')
    inlines        = [ImagenAgendaInline]
    ordering       = ('-semana_inicio',)


@admin.register(ImagenAgenda)
class ImagenAgendaAdmin(ModelAdmin):
    list_display  = ('agenda', 'descripcion', 'subida_por', 'subida_en')
    list_filter   = ('agenda__grado__area',)
    readonly_fields = ('subida_en',)
