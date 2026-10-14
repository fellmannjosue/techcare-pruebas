from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Entrada, Entrega, Insumo, Maquinaria


@admin.register(Insumo)
class InsumoAdmin(SimpleHistoryAdmin):
    list_display = ('nombre', 'clave', 'prefijo', 'categoria', 'presentacion', 'capacidad_envase', 'minimo_alerta', 'requiere_kilometraje', 'orden', 'activo')
    list_editable = ('capacidad_envase', 'minimo_alerta', 'orden', 'activo')


@admin.register(Maquinaria)
class MaquinariaAdmin(SimpleHistoryAdmin):
    list_display = ('nombre', 'tipo', 'usa_kilometraje', 'activo', 'creado')
    list_editable = ('tipo', 'usa_kilometraje', 'activo')
    search_fields = ('nombre',)


@admin.register(Entrada)
class EntradaAdmin(SimpleHistoryAdmin):
    list_display = ('insumo', 'fecha', 'cantidad', 'tipo', 'registrado_por')
    list_filter = ('insumo', 'tipo')


@admin.register(Entrega)
class EntregaAdmin(SimpleHistoryAdmin):
    list_display = ('codigo', 'insumo', 'fecha', 'hora', 'maquinaria', 'kilometraje', 'galones', 'persona', 'registrado_por')
    list_filter = ('insumo', 'maquinaria')
    search_fields = ('persona', 'observaciones')
