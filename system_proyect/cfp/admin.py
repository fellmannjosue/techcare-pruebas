from django.contrib import admin

from .models import (
    EjecucionCurso, InformeContable, CfpDatosGenerales, CfpOpcion,
    CursoNota, ModuloNota, NotaIntento, HorasMetaMes, HorasParticipanteMes,
    Participante,
)


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


# ── Programa 2: Notas ──
class ModuloNotaInline(admin.TabularInline):
    model = ModuloNota
    extra = 0


@admin.register(CursoNota)
class CursoNotaAdmin(admin.ModelAdmin):
    list_display = ('curso', 'jornada', 'anio', 'codigo')
    list_filter = ('anio', 'jornada')
    search_fields = ('curso',)
    inlines = [ModuloNotaInline]


@admin.register(Participante)
class ParticipanteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'identidad', 'curso', 'orden')
    list_filter = ('curso',)
    search_fields = ('nombre', 'identidad')
    ordering = ('curso', 'orden')


@admin.register(NotaIntento)
class NotaIntentoAdmin(admin.ModelAdmin):
    list_display = ('modulo', 'nombre', 'identidad', 't1', 't2', 't3', 'p1', 'p2', 'p3')
    search_fields = ('nombre', 'identidad')
    list_filter = ('modulo__curso',)


@admin.register(HorasMetaMes)
class HorasMetaMesAdmin(admin.ModelAdmin):
    list_display = ('curso', 'mes', 'horas')
    list_filter = ('curso',)


@admin.register(HorasParticipanteMes)
class HorasParticipanteMesAdmin(admin.ModelAdmin):
    list_display = ('curso', 'persona_id', 'mes', 'horas')
    list_filter = ('curso',)
