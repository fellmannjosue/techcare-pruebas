from django.contrib import admin
from django.utils.html import format_html  # <--- hecho por claude code: necesario para renderizar HTML seguro en el admin (preview de imagen)
from .models import (
    IncisoConductual, MateriaDocenteBilingue, MateriaDocenteColegio,
    ReporteConductual, ReporteInformativo, ProgressReport,
    EvidenciaReporte  # <--- hecho por claude code: importar el nuevo modelo de evidencias
)

@admin.register(IncisoConductual)
class IncisoConductualAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'descripcion', 'activo']
    list_filter = ['tipo', 'activo']
    search_fields = ['descripcion']

@admin.register(MateriaDocenteBilingue)
class MateriaDocenteBilingueAdmin(admin.ModelAdmin):
    list_display = ['materia', 'docente', 'activo']
    list_filter = ['activo']
    search_fields = ['materia', 'docente']

@admin.register(MateriaDocenteColegio)
class MateriaDocenteColegioAdmin(admin.ModelAdmin):
    list_display = ['materia', 'docente', 'activo']
    list_filter = ['activo']
    search_fields = ['materia', 'docente']

@admin.register(ReporteConductual)
class ReporteConductualAdmin(admin.ModelAdmin):
    list_display = [
        'alumno_nombre', 'materia', 'usuario', 'area', 'estado',
        'coordinador_firma', 'comentario_coordinador', 'fecha'
    ]
    list_filter = ['area', 'estado', 'coordinador_firma']
    search_fields = ['alumno_nombre', 'materia', 'docente', 'usuario__username']
    readonly_fields = ['fecha']

@admin.register(ReporteInformativo)
class ReporteInformativoAdmin(admin.ModelAdmin):
    list_display = [
        'alumno_nombre', 'materia', 'usuario', 'area', 'estado',
        'coordinador_firma', 'comentario_coordinador', 'fecha'
    ]
    list_filter = ['area', 'estado', 'coordinador_firma']
    search_fields = ['alumno_nombre', 'materia', 'docente', 'usuario__username']
    readonly_fields = ['fecha']

@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    list_display = [
        'alumno_nombre', 'usuario', 'grado', 'semana_inicio', 'semana_fin',
        'estado', 'coordinador_firma', 'comentario_coordinador', 'fecha', 'materias_resumen'
    ]
    list_filter = ['estado', 'coordinador_firma']
    search_fields = ['alumno_nombre', 'usuario__username', 'grado']
    readonly_fields = ['fecha', 'materias_json']

    def materias_resumen(self, obj):
        """Muestra un resumen de materias en el listado admin."""
        if not obj.materias_json:
            return "-"
        # Si el JSON está vacío, muestra nada.
        if isinstance(obj.materias_json, list):
            nombres = [m.get('materia', '') for m in obj.materias_json if m.get('materia')]
            return ", ".join(nombres) if nombres else "-"
        return "-"
    materias_resumen.short_description = "Materias"

    # Opcional: para ver el JSON bonito en la vista detalle
    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'materias_json' and field is not None:  # <--- hecho por claude code: guard para evitar AttributeError si field es None
            field.widget.attrs['style'] = 'font-family:monospace; min-width: 400px; min-height: 100px;'
        return field


# ─────────────────────────────────────────────────────────────
# Admin de EvidenciaReporte  <--- hecho por claude code
# Muestra las evidencias subidas con preview visual de la imagen.
# El método preview() usa format_html para evitar XSS al
# renderizar la etiqueta <img> de forma segura.
# ─────────────────────────────────────────────────────────────
@admin.register(EvidenciaReporte)
class EvidenciaReporteAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'subido_por', 'comentario', 'fecha', 'preview']
    list_filter = ['tipo']
    readonly_fields = ['fecha', 'preview']
    search_fields = ['comentario', 'subido_por__username']

    def preview(self, obj):
        # Muestra miniatura de la imagen si existe, "-" si no hay imagen
        if obj.imagen:
            return format_html('<img src="{}" width="60" style="border-radius:4px; object-fit:cover;"/>', obj.imagen.url)
        return "-"
    preview.short_description = "Vista previa"
