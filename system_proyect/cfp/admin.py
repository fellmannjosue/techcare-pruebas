from django.contrib import admin

from .models import EjecucionCurso, InformeContable, CfpDatosGenerales, CfpOpcion


@admin.register(EjecucionCurso)
class EjecucionCursoAdmin(admin.ModelAdmin):
    list_display = ('anio', 'taller', 'no_ejecucion', 'no_contrato', 'nombre_curso',
                    'horas', 'part_pago', 'costo_hora', 'horario')
    list_filter = ('anio', 'taller')
    search_fields = ('nombre_curso', 'no_contrato', 'no_ejecucion', 'no_curso')
    ordering = ('-anio', 'taller', 'no_ejecucion')


@admin.register(InformeContable)
class InformeContableAdmin(admin.ModelAdmin):
    list_display = ('ejecucion', 'convenio', 'regional', 'centro_programa', 'egresados', 'actualizado')
    search_fields = ('ejecucion__nombre_curso', 'convenio')
    autocomplete_fields = ('ejecucion',)


@admin.register(CfpDatosGenerales)
class CfpDatosGeneralesAdmin(admin.ModelAdmin):
    """Datos generales compartidos por todos los cursos (registro único)."""
    list_display = ('localidad', 'instructor', 'horario', 'lugar', 'fecha_lugar')


@admin.register(CfpOpcion)
class CfpOpcionAdmin(admin.ModelAdmin):
    """Opciones de los selects agregables (Localidad, Dirección, Instructor, Horario, Lugar)."""
    list_display = ('campo', 'valor')
    list_filter = ('campo',)
    search_fields = ('valor',)
    ordering = ('campo', 'valor')
