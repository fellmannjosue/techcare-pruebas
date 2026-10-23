from django.contrib import admin
from core.audit_admin import AuditAdminMixin
from .models import MaintenanceRecord, TipoFalla, MaestroMantenimiento, GradoMantenimiento, FotoMantenimiento


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(AuditAdminMixin):
    # <--- hecho por claude code (16-oct-2026): + tipo de ficha (filtro y columna) y el solicitante del préstamo
    list_display  = ('record_id', 'tipo_equipo', 'computadora', 'teacher_name', 'prest_solicitante', 'grade', 'date', 'status')
    list_filter   = ('tipo_equipo', 'status', 'tipo_falla', 'date')
    search_fields = ('record_id', 'model', 'serie', 'teacher_name', 'grade', 'prest_solicitante', 'firma_nombre')
    list_per_page = 50
    ordering      = ('-date',)
    date_hierarchy = 'date'


@admin.register(TipoFalla)
class TipoFallaAdmin(AuditAdminMixin):
    list_display  = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering      = ('nombre',)


@admin.register(MaestroMantenimiento)
class MaestroMantenimientoAdmin(admin.ModelAdmin):
    list_display  = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(GradoMantenimiento)
class GradoMantenimientoAdmin(admin.ModelAdmin):
    list_display  = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(FotoMantenimiento)
class FotoMantenimientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'registro', 'imagen', 'orden')
