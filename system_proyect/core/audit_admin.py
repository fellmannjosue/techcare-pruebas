# <--- hecho por claude code: mixin de admin para auditoría automática.
#      Captura request.user al guardar desde el admin y lo asigna a
#      creado_por (solo en creación) y modificado_por (siempre).
#      Los campos de auditoría se muestran como readonly en el admin.
#      Hereda de UnfoldModelAdmin si unfold está instalado, si no usa ModelAdmin.

from django.contrib import admin

try:
    from unfold.admin import ModelAdmin as UnfoldModelAdmin
    _AdminBase = UnfoldModelAdmin
except ImportError:
    _AdminBase = admin.ModelAdmin


class AuditAdminMixin(_AdminBase):
    """Agrega los campos de auditoría como readonly en el admin
    y los rellena automáticamente al guardar."""

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        audit = ['creado_por', 'modificado_por', 'fecha_creado', 'fecha_modificado']
        return base + [f for f in audit if f not in base]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        obj.modificado_por = request.user
        super().save_model(request, obj, form, change)
