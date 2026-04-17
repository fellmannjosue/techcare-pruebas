from django.contrib import admin
from core.audit_admin import AuditAdminMixin
from .models import MaintenanceRecord, TipoFalla

@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(AuditAdminMixin):
    list_display = (
        'id', 'equipment_id', 'model', 'serie',
        'teacher_name', 'grade', 'tipo_falla', 'date', 'status'
    )
    list_filter = ('status', 'tipo_falla', 'date')
    search_fields = (
        'equipment_id', 'model', 'serie',
        'teacher_name', 'grade'
    )
    ordering = ('-date',)
    date_hierarchy = 'date'

@admin.register(TipoFalla)
class TipoFallaAdmin(AuditAdminMixin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)
