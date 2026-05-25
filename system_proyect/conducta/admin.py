from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from core.audit_admin import AuditAdminMixin
from .models import (
    IncisoConductual,
    ConfiguracionCoordinador,
    ConfiguracionNotificacion,
    MateriaDocenteBilingue,
    MateriaDocenteColegio,
    ReporteConductual,
    ReporteInformativo,
    ProgressReport,
    EvidenciaReporte,
)


# ─── Configuración de Coordinadores ────────────────────────────────────────────

@admin.register(ConfiguracionCoordinador)
class ConfiguracionCoordinadorAdmin(AuditAdminMixin):
    list_display  = ['nombre', 'area_badge', 'codigo', 'email_display', 'activo']
    list_filter   = ['area', 'activo']
    search_fields = ['nombre', 'codigo', 'usuario__email', 'usuario__first_name', 'usuario__last_name']
    list_editable = ['activo']
    ordering      = ['area', 'codigo']
    fields        = ('area', 'codigo', 'nombre', 'usuario', 'activo')
    autocomplete_fields = ['usuario']

    def area_badge(self, obj):
        color = '#1971c2' if obj.area == 'bilingue' else '#2f9e44'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600">{}</span>',
            color, obj.get_area_display()
        )
    area_badge.short_description = 'Área'
    area_badge.admin_order_field = 'area'

    def email_display(self, obj):
        if obj.email:
            return format_html('<a href="mailto:{0}">{0}</a>', obj.email)
        return mark_safe('<span style="color:#adb5bd">Sin usuario asignado</span>')
    email_display.short_description = 'Correo electrónico'


# ─── Materia-Docente Bilingüe ───────────────────────────────────────────────────

@admin.register(MateriaDocenteBilingue)
class MateriaDocenteBilingueAdmin(AuditAdminMixin):
    list_display  = ['materia', 'docente', 'coord_display', 'activo']
    list_filter   = ['activo', 'coordinador']
    search_fields = ['materia', 'docente']
    list_editable = ['activo']
    fields        = ('materia', 'docente', 'coordinador', 'activo')

    def coord_display(self, obj):
        if not obj.coordinador:
            return format_html('<span style="color:#adb5bd">—</span>')
        codigos = [c.strip() for c in obj.coordinador.split(',') if c.strip()]
        badges = []
        color_map = {'C1': '#c92a2a', 'C2': '#1971c2', 'C3': '#2f9e44', 'C4': '#e67700'}
        for c in codigos:
            col = color_map.get(c, '#6c757d')
            # Try to get the coordinator's display name from ConfiguracionCoordinador
            cfg = ConfiguracionCoordinador.objects.filter(area='bilingue', codigo=c).first()
            label = f"{c} – {cfg.nombre}" if cfg else c
            badges.append(
                f'<span style="background:{col};color:#fff;padding:2px 8px;border-radius:20px;'
                f'font-size:11px;font-weight:600;margin-right:3px">{label}</span>'
            )
        return mark_safe(''.join(badges))
    coord_display.short_description = 'Coordinador(es)'


# ─── Materia-Docente Colegio ────────────────────────────────────────────────────

@admin.register(MateriaDocenteColegio)
class MateriaDocenteColegioAdmin(AuditAdminMixin):
    list_display  = ['materia', 'docente', 'coord_colegio_display', 'activo']
    list_filter   = ['activo']
    search_fields = ['materia', 'docente']
    list_editable = ['activo']
    filter_horizontal = ['coordinadores']
    fields        = ('materia', 'docente', 'coordinadores', 'activo')

    def coord_colegio_display(self, obj):
        coords = list(obj.coordinadores.filter(activo=True))
        if not coords:
            return mark_safe(
                '<span style="color:#f59f00;font-size:11px">⚠ Sin asignar (notifica a todos)</span>'
            )
        badges = [
            f'<span style="background:#2f9e44;color:#fff;padding:2px 8px;border-radius:20px;'
            f'font-size:11px;font-weight:600;margin-right:3px">{c.nombre}</span>'
            for c in coords
        ]
        return mark_safe(''.join(badges))
    coord_colegio_display.short_description = 'Coordinadores'


# ─── Reglas de Notificación ────────────────────────────────────────────────────

@admin.register(ConfiguracionNotificacion)
class ConfiguracionNotificacionAdmin(AuditAdminMixin):
    list_display  = ['coord_badge', 'area_badge', 'tipos_display', 'activo']
    list_filter   = ['area', 'activo']
    list_editable = ['activo']
    ordering      = ['area', 'coordinador']
    fields        = (
        'area', 'coordinador',
        ('recibe_conductual', 'recibe_informativo_academico',
         'recibe_informativo_conductual', 'recibe_progress'),
        'activo',
    )

    def area_badge(self, obj):
        color = '#1971c2' if obj.area == 'bilingue' else '#2f9e44'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600">{}</span>',
            color, obj.get_area_display()
        )
    area_badge.short_description = 'Área'
    area_badge.admin_order_field = 'area'

    def coord_badge(self, obj):
        return format_html(
            '<span style="font-weight:600">{}</span>',
            obj.coordinador.nombre
        )
    coord_badge.short_description = 'Coordinador'
    coord_badge.admin_order_field = 'coordinador__nombre'

    _TIPO_LABELS = [
        ('recibe_conductual',             'Conductual',             '#f03e3e'),
        ('recibe_informativo_academico',  'Inf. Académico',         '#1971c2'),
        ('recibe_informativo_conductual', 'Inf. Conductual',        '#e67700'),
        ('recibe_progress',               'Progress',               '#0ca678'),
    ]

    def tipos_display(self, obj):
        badges = [
            f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:20px;'
            f'font-size:11px;font-weight:600;margin-right:3px">{label}</span>'
            for campo, label, color in self._TIPO_LABELS if getattr(obj, campo)
        ]
        return mark_safe(''.join(badges)) if badges else mark_safe(
            '<span style="color:#adb5bd;font-size:11px">Sin tipos asignados</span>'
        )
    tipos_display.short_description = 'Tipos de reporte que recibe'


# ─── Incisos ────────────────────────────────────────────────────────────────────

@admin.register(IncisoConductual)
class IncisoConductualAdmin(AuditAdminMixin):
    list_display  = ['tipo', 'descripcion', 'activo']
    list_filter   = ['tipo', 'activo']
    search_fields = ['descripcion']


# ─── Reportes ───────────────────────────────────────────────────────────────────

@admin.register(ReporteConductual)
class ReporteConductualAdmin(AuditAdminMixin):
    list_display   = ['alumno_nombre', 'materia', 'usuario', 'area', 'estado', 'coordinador_firma', 'fecha']
    list_filter    = ['area', 'estado', 'coordinador_firma']
    search_fields  = ['alumno_nombre', 'materia', 'docente', 'usuario__username']
    readonly_fields = ['fecha']


@admin.register(ReporteInformativo)
class ReporteInformativoAdmin(AuditAdminMixin):
    list_display   = ['alumno_nombre', 'materia', 'usuario', 'area', 'estado', 'coordinador_firma', 'fecha']
    list_filter    = ['area', 'estado', 'coordinador_firma']
    search_fields  = ['alumno_nombre', 'materia', 'docente', 'usuario__username']
    readonly_fields = ['fecha']


@admin.register(ProgressReport)
class ProgressReportAdmin(AuditAdminMixin):
    list_display   = ['alumno_nombre', 'usuario', 'grado', 'semana_inicio', 'semana_fin',
                      'estado', 'coordinador_firma', 'fecha', 'materias_resumen']
    list_filter    = ['estado', 'coordinador_firma']
    search_fields  = ['alumno_nombre', 'usuario__username', 'grado']
    readonly_fields = ['fecha', 'materias_json']

    def materias_resumen(self, obj):
        if not obj.materias_json:
            return "-"
        if isinstance(obj.materias_json, list):
            nombres = [m.get('materia', '') for m in obj.materias_json if m.get('materia')]
            return ", ".join(nombres) if nombres else "-"
        return "-"
    materias_resumen.short_description = "Materias"

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'materias_json' and field is not None:
            field.widget.attrs['style'] = 'font-family:monospace; min-width: 400px; min-height: 100px;'
        return field


# ─── Evidencias ─────────────────────────────────────────────────────────────────

@admin.register(EvidenciaReporte)
class EvidenciaReporteAdmin(AuditAdminMixin):
    list_display   = ['tipo', 'subido_por', 'comentario', 'fecha', 'preview']
    list_filter    = ['tipo']
    readonly_fields = ['fecha', 'preview']
    search_fields  = ['comentario', 'subido_por__username']

    def preview(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" width="60" style="border-radius:4px;object-fit:cover;"/>',
                obj.imagen.url
            )
        return "-"
    preview.short_description = "Vista previa"
