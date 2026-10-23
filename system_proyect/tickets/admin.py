from django.contrib import admin
from django.utils.html import format_html
from core.audit_admin import AuditAdminMixin
from .models import Ticket, TicketComment

class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    readonly_fields = ('usuario', 'fecha',)
    fields = ('usuario', 'mensaje', 'fecha')

class TicketAdmin(AuditAdminMixin):
    # <--- hecho por claude code (16-oct-2026): lista práctica — urgencia, estado, SLA, asignado, filtros y búsqueda
    list_display = ('ticket_id', 'name', 'grade', 'urgencia', 'status', 'sla', 'asignado_a', 'attachment_link', 'created_at')
    list_filter = ('status', 'urgencia', 'sin_sla', 'asignado_a', 'created_at')
    search_fields = ('ticket_id', 'name', 'email', 'grade', 'description')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 50
    inlines = [TicketCommentInline]

    def sla(self, obj):
        try:
            return obj.sla_texto
        except Exception:
            return '—'
    sla.short_description = "SLA"

    def attachment_link(self, obj):
        """Muestra el archivo adjunto como un enlace en el panel de administración."""
        if obj.attachment:
            return format_html('<a href="{}" target="_blank">Ver Adjunto</a>', obj.attachment.url)
        return "No disponible"
    attachment_link.short_description = "Adjunto"

class TicketCommentAdmin(AuditAdminMixin):
    list_display = ('ticket', 'usuario', 'mensaje', 'fecha')
    list_filter = ('ticket', 'usuario', 'fecha')
    search_fields = ('mensaje', 'usuario__username', 'ticket__ticket_id')
    readonly_fields = ('usuario', 'fecha')

admin.site.register(Ticket, TicketAdmin)
admin.site.register(TicketComment, TicketCommentAdmin)
