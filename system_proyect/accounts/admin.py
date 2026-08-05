from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import RegistroAcceso


@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(ModelAdmin):
    list_display  = ('username', 'ip', 'fecha_hora')
    list_filter   = ('fecha_hora',)
    search_fields = ('username', 'ip')
    readonly_fields = ('usuario', 'username', 'ip', 'agente', 'fecha_hora')
    ordering      = ('-fecha_hora',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# <--- hecho por claude code (seguridad): gestión de la lista blanca de correos
from .models import CorreoInstitucional


@admin.register(CorreoInstitucional)
class CorreoInstitucionalAdmin(ModelAdmin):
    list_display = ('correo', 'nombre', 'activo', 'creado')
    list_filter = ('activo',)
    search_fields = ('correo', 'nombre')
    list_editable = ('activo',)
