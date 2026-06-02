# <--- hecho por claude code: admin salidas baño
from django.contrib import admin
from .models import PeriodoEscolar, MaestroClase, SalidaBano

@admin.register(PeriodoEscolar)
class PeriodoEscolarAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'parcial', 'anio', 'area', 'fecha_inicio', 'fecha_fin', 'activo')
    list_editable = ('activo',)
    list_filter   = ('area', 'anio', 'activo')

@admin.register(MaestroClase)
class MaestroClaseAdmin(admin.ModelAdmin):
    list_display  = ('maestro', 'clase', 'grado', 'area')
    list_filter   = ('area', 'grado')
    search_fields = ('maestro__first_name', 'maestro__last_name', 'clase', 'grado')
    autocomplete_fields = ['maestro']

@admin.register(SalidaBano)
class SalidaBanoAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'grado', 'grupo', 'area', 'semaforo', 'clase', 'hora_salida', 'hora_regreso', 'fecha', 'maestro')
    list_filter  = ('area', 'semaforo', 'grado', 'fecha')
    search_fields= ('alumno',)
    date_hierarchy = 'fecha'
