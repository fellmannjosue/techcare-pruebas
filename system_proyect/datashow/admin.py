# datashow/admin.py
# <--- hecho por claude code (02-nov-2026)
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import ReservaDataShow


class _Admin(SimpleHistoryAdmin):
    list_display = ('datashow', 'fecha', 'rango_horario', 'solicitante',
                    'estado', 'lugar', 'revisado_por')
    list_filter = ('estado', 'fecha', 'datashow')
    search_fields = ('datashow__asset_id', 'solicitante__username',
                     'solicitante__first_name', 'lugar', 'motivo')
    date_hierarchy = 'fecha'
    autocomplete_fields = ()
    readonly_fields = ('creado_por', 'modificado_por', 'fecha_creado', 'fecha_modificado')

    @admin.display(description='Horario')
    def rango_horario(self, obj):
        return obj.rango_horario


admin.site.register(ReservaDataShow, _Admin)
