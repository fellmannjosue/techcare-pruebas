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


# <--- hecho por claude code (12-oct-2026): bitácora de "Iniciar sesión como" (solo lectura: no se edita ni se borra)
from .models import Suplantacion


@admin.register(Suplantacion)
class SuplantacionAdmin(ModelAdmin):
    list_display = ('super_username', 'username', 'inicio', 'fin', 'cierre', 'ip')
    search_fields = ('super_username', 'username')
    list_filter = ('cierre',)
    readonly_fields = [f.name for f in Suplantacion._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
