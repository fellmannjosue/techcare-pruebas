# <--- hecho por claude code: admin salidas baño
from django.contrib import admin
from .models import MaestroClase, SalidaBano
# <--- hecho por claude code (06-nov-2026): sin admin de PeriodoEscolar — Salidas usa el Período Escolar general

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
