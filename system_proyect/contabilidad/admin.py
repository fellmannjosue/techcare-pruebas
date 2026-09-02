# <--- hecho por claude code: registro en el admin del módulo Contabilidad.
from django.contrib import admin

from .models import (ConfiguracionContabilidad, AreaUniforme, TipoUniforme,
                     ProductoUniforme, MovimientoUniforme,
                     TipoImpuesto, Proveedor, CompraProveedor, DetalleCompra)


@admin.register(ConfiguracionContabilidad)
class ConfiguracionContabilidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'moneda', 'activo', 'fecha_modificado')
    readonly_fields = ('creado_por', 'modificado_por', 'fecha_creado', 'fecha_modificado')


@admin.register(AreaUniforme)
class AreaUniformeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    list_editable = ('activo',)
    search_fields = ('nombre',)


@admin.register(TipoUniforme)
class TipoUniformeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    list_editable = ('activo',)
    search_fields = ('nombre',)


@admin.register(ProductoUniforme)
class ProductoUniformeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'area', 'tipo', 'talla', 'existencia_actual', 'costo_promedio', 'activo')
    list_filter = ('area', 'tipo', 'activo')
    search_fields = ('nombre', 'codigo', 'talla')
    readonly_fields = ('existencia_actual', 'costo_promedio',
                       'creado_por', 'modificado_por', 'fecha_creado', 'fecha_modificado')


@admin.register(MovimientoUniforme)
class MovimientoUniformeAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'producto', 'clase', 'tipo_salida', 'cantidad', 'costo_unitario', 'importe', 'ingreso', 'existencia_despues')
    list_filter = ('clase', 'tipo_salida', 'producto__area', 'producto__tipo')
    search_fields = ('producto__nombre', 'concepto', 'motivo')
    readonly_fields = ('importe', 'ingreso', 'existencia_despues', 'costo_promedio_despues',
                       'creado_por', 'modificado_por', 'fecha_creado', 'fecha_modificado')
    date_hierarchy = 'fecha'


@admin.register(TipoImpuesto)
class TipoImpuestoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'porcentaje', 'activo')
    list_editable = ('porcentaje', 'activo')
    search_fields = ('nombre',)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nombre_comercial', 'contacto', 'telefono', 'color', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'nombre_comercial', 'rtn', 'contacto')
    readonly_fields = ('creado_por', 'modificado_por', 'fecha_creado', 'fecha_modificado')


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 0
    readonly_fields = ('subtotal', 'impuesto', 'total')


@admin.register(CompraProveedor)
class CompraProveedorAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'proveedor', 'fecha', 'estado', 'total_unidades', 'total')
    list_filter = ('estado', 'proveedor')
    search_fields = ('codigo', 'documento', 'proveedor__nombre')
    readonly_fields = ('codigo', 'subtotal', 'impuesto_total', 'total', 'estado',
                       'confirmada_por', 'confirmada_en', 'anulada_por', 'anulada_en',
                       'creado_por', 'modificado_por', 'fecha_creado', 'fecha_modificado')
    inlines = [DetalleCompraInline]
    date_hierarchy = 'fecha'
