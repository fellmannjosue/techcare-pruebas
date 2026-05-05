from django.contrib import admin
from core.audit_admin import AuditAdminMixin
from .models import MaintenanceRecord, TipoFalla, MaestroMantenimiento, GradoMantenimiento, FotoMantenimiento


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(AuditAdminMixin):
    list_display  = ('record_id', 'computadora', 'model', 'teacher_name', 'grade', 'tipo_falla', 'date', 'status')
    list_filter   = ('status', 'tipo_falla', 'date')
    search_fields = ('record_id', 'model', 'serie', 'teacher_name', 'grade')
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
