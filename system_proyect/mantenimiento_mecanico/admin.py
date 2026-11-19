import os

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (Comentario, Entrada, Entrega, FotoLimpiezaTanque, Insumo, LecturaBarril, LecturaVehiculo,
                     LimpiezaTanque, MantenimientoVehiculo, MantenimientoVehiculoTarea, Maquinaria, TareaMantVehiculo,
                     TecnicoVehiculo, VehiculoMant)

try:
    from unfold.admin import ModelAdmin as _UnfoldAdmin
except ImportError:   # pragma: no cover
    _UnfoldAdmin = admin.ModelAdmin


# <--- hecho por claude code (seguridad 05-nov-2026): en Mantenimiento Mecánico NADIE elimina, tampoco el superusuario desde /admin/ (regla del usuario: lo registrado es lo que se audita; lo que sobra se desactiva). Todos los modelos del módulo se registran AQUÍ, así core/admin_auto.py no les pone su admin genérico con borrar.
class _SinBorrar:
    def has_delete_permission(self, request, obj=None):
        return False


class _SoloLectura(_SinBorrar):
    """<--- hecho por claude code (seguridad 05-nov-2026): bitácoras y detalle sin historial: solo se ven."""
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Insumo)
class InsumoAdmin(_SinBorrar, SimpleHistoryAdmin):
    list_display = ('nombre', 'clave', 'prefijo', 'categoria', 'presentacion', 'capacidad_envase', 'minimo_alerta', 'requiere_kilometraje', 'orden', 'activo')
    list_editable = ('capacidad_envase', 'minimo_alerta', 'orden', 'activo')


@admin.register(Maquinaria)
class MaquinariaAdmin(_SinBorrar, SimpleHistoryAdmin):
    list_display = ('nombre', 'tipo', 'usa_kilometraje', 'activo', 'creado')
    list_editable = ('tipo', 'usa_kilometraje', 'activo')
    search_fields = ('nombre',)


@admin.register(Entrada)
class EntradaAdmin(_SinBorrar, SimpleHistoryAdmin):
    list_display = ('insumo', 'fecha', 'cantidad', 'tipo', 'registrado_por')
    list_filter = ('insumo', 'tipo')


@admin.register(Entrega)
class EntregaAdmin(_SinBorrar, SimpleHistoryAdmin):
    list_display = ('codigo', 'insumo', 'fecha', 'hora', 'maquinaria', 'kilometraje', 'galones', 'persona', 'registrado_por')
    list_filter = ('insumo', 'maquinaria')
    search_fields = ('persona', 'observaciones')


@admin.register(LecturaBarril)   # <--- hecho por claude code (14-oct-2026): lectura aproximada (solo referencia)
class LecturaBarrilAdmin(_SinBorrar, SimpleHistoryAdmin):
    list_display = ('insumo', 'fecha', 'nivel', 'barriles_llenos', 'galones_aprox', 'registrado_por')
    list_filter = ('insumo', 'nivel')
    date_hierarchy = 'fecha'


# <--- hecho por claude code (seguridad 05-nov-2026): los que antes registraba core/admin_auto.py (con borrar), con columnas parecidas
@admin.register(Comentario)
class ComentarioAdmin(_SoloLectura, SimpleHistoryAdmin, _UnfoldAdmin):   # bitácora de auditoría: no se edita
    list_display = ('__str__', 'entrega', 'mant_vehic_id', 'autor', 'creado')
    list_filter = ('creado',)
    search_fields = ('texto',)
    list_select_related = ('entrega__insumo', 'autor')


@admin.register(LimpiezaTanque)
class LimpiezaTanqueAdmin(_SinBorrar, SimpleHistoryAdmin, _UnfoldAdmin):
    list_display = ('codigo', 'insumo', 'fecha', 'responsable', 'tanque_limpiado', 'filtro_limpiado', 'filtro_cambiado', 'registrado_por')
    list_filter = ('tanque_limpiado', 'filtro_limpiado', 'filtro_cambiado')
    search_fields = ('codigo', 'responsable')


@admin.register(FotoLimpiezaTanque)
class FotoLimpiezaTanqueAdmin(_SoloLectura, _UnfoldAdmin):   # <--- hecho por claude code (seguridad 05-nov-2026): sin historial y el ImageField del admin deja pasar EPS (Ghostscript): las fotos entran SOLO por limpieza_crear (validadas)
    # <--- hecho por claude code (seguridad 05-nov-2026, 2.ª revisión): el ImageField se pintaba como enlace (lista) y como <img> (ficha de Unfold) a /media/mantenimiento_mecanico/, que Apache bloquea (403): solo el nombre, sin enlace; la foto se ve en la ficha PDF de la limpieza
    list_display = ('__str__', 'limpieza', 'archivo', 'subida')
    fields = ('limpieza', 'archivo', 'subida')
    readonly_fields = ('limpieza', 'archivo', 'subida')

    @admin.display(description='Archivo')
    def archivo(self, obj):
        return os.path.basename(obj.imagen.name) if obj.imagen else '—'


@admin.register(VehiculoMant)
class VehiculoMantAdmin(_SinBorrar, SimpleHistoryAdmin, _UnfoldAdmin):   # para retirarlo: "Fuera de uso"
    list_display = ('__str__', 'placa', 'marca', 'tipo', 'anio', 'intervalo', 'no_en_uso')
    list_filter = ('no_en_uso', 'agricultura', 'por_horas', 'sin_tacometro')
    search_fields = ('placa', 'marca', 'tipo', 'chasis')


@admin.register(TareaMantVehiculo)
class TareaMantVehiculoAdmin(_SinBorrar, SimpleHistoryAdmin, _UnfoldAdmin):   # para retirarla: "Activa"
    list_display = ('__str__', 'numero', 'tarea', 'aplica', 'intervalo', 'activo')
    list_filter = ('aplica', 'activo')
    search_fields = ('tarea',)


@admin.register(TecnicoVehiculo)
class TecnicoVehiculoAdmin(_SinBorrar, _UnfoldAdmin):   # para retirarlo: "Activo"
    list_display = ('__str__', 'nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)


@admin.register(LecturaVehiculo)
class LecturaVehiculoAdmin(_SinBorrar, SimpleHistoryAdmin, _UnfoldAdmin):
    list_display = ('__str__', 'vehiculo', 'valor', 'fecha', 'usuario', 'registrado_por', 'creado')
    date_hierarchy = 'fecha'
    search_fields = ('usuario',)
    list_select_related = ('vehiculo', 'registrado_por')


@admin.register(MantenimientoVehiculo)
class MantenimientoVehiculoAdmin(_SinBorrar, SimpleHistoryAdmin, _UnfoldAdmin):
    list_display = ('__str__', 'vehiculo', 'valor', 'fecha', 'tecnico', 'registrado_por', 'creado')
    date_hierarchy = 'fecha'
    search_fields = ('usuario',)
    list_select_related = ('vehiculo', 'tecnico', 'registrado_por')


@admin.register(MantenimientoVehiculoTarea)
class MantenimientoVehiculoTareaAdmin(_SoloLectura, _UnfoldAdmin):   # sin historial: cambiar un "hecho" no dejaría rastro
    list_display = ('__str__', 'mantenimiento', 'tarea', 'hecho')
    list_filter = ('hecho',)
    list_select_related = ('mantenimiento__vehiculo', 'tarea')
