from django.db import models
from django.contrib.auth.models import User
from core.models import AuditModel

# ────────────────
# Choices globales
# ────────────────
AREA_CHOICES = (
    ('bilingue', 'Bilingüe'),
    ('colegio', 'Colegio/CFP'),
)

ESTADO_CHOICES = (
    ('enviado', 'Enviado'),
    ('revisando', 'Revisando'),
    ('revisado', 'Revisado'),
    ('aprobado', 'Aprobado'),
)

COORDINADORES_BL = [
    ("Mr. Martinez", "Mr. Martinez"),
    ("Miss Alcerro", "Miss Alcerro"),
    ("Mr. Ruiz", "Mr. Ruiz"),
    ("Mrs. Varela", "Mrs. Varela"),
]

COORDINADORES_COL = [
    ("profe. Licona", "Profe. Licona"),
    ("profe. Felipe", "Profe. Felipe"),
    ("profe. Gabriela", "Profe. Gabriela"),
]

# ────────────────
# Inciso Conductual
# ────────────────
class IncisoConductual(AuditModel):
    TIPO_CHOICES = (
        ('leve', 'Leve'),
        ('grave', 'Grave'),
        ('muy_grave', 'Muy Grave'),
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name="Tipo de Inciso")
    descripcion = models.CharField(max_length=1000, verbose_name="Descripción del inciso")
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.descripcion}'

    class Meta:
        verbose_name = "Inciso Conductual"
        verbose_name_plural = "Incisos Conductuales"
        ordering = ['tipo', 'descripcion']

# ────────────────
# Materia-Docente (Bilingüe)
# ────────────────
class MateriaDocenteBilingue(AuditModel):
    materia     = models.CharField(max_length=100, verbose_name="Materia")
    docente     = models.CharField(max_length=100, verbose_name="Docente")
    coordinador = models.CharField(max_length=20, default='C2', verbose_name="Coordinador(es)",
                                   help_text="Códigos separados por coma: C1,C2,C3,C4")
    activo      = models.BooleanField(default=True, verbose_name="¿Activo?")

    def __str__(self):
        return f"{self.materia} – {self.docente}"

    class Meta:
        verbose_name = "Materia-Docente Bilingüe"
        verbose_name_plural = "Materias-Docentes Bilingüe"
        ordering = ['materia', 'docente']

# ────────────────
# Configuración de Coordinadores
# ────────────────
class ConfiguracionCoordinador(AuditModel):
    AREA_CHOICES = [
        ('bilingue', 'Bilingüe'),
        ('colegio',  'Colegio/CFP'),
    ]
    area    = models.CharField(max_length=10, choices=AREA_CHOICES, verbose_name="Área")
    codigo  = models.CharField(
        max_length=5, blank=True, verbose_name="Código",
        help_text="Solo Bilingüe: C1, C2, C3, C4. Dejar vacío para Colegio."
    )
    nombre  = models.CharField(max_length=100, verbose_name="Nombre del coordinador")
    usuario = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='config_coordinador', verbose_name="Usuario del sistema",
        help_text="Cuenta del coordinador en TechCare. Su correo se usará para notificaciones."
    )
    activo  = models.BooleanField(default=True, verbose_name="¿Activo?")

    class Meta:
        verbose_name = "Coordinador"
        verbose_name_plural = "Configuración de Coordinadores"
        ordering = ['area', 'codigo']

    def __str__(self):
        return f"{self.nombre} ({self.get_area_display()}{' · ' + self.codigo if self.codigo else ''})"

    @property
    def email(self):
        return self.usuario.email if self.usuario_id else ''

    @property
    def color(self):
        """Color hex asociado al código de coordinador."""
        _COLORS = {
            'C1': '#c92a2a', 'C2': '#1971c2', 'C3': '#2f9e44',
            'C4': '#e67700', 'C5': '#9c36b5', 'C6': '#0c8599',
        }
        return _COLORS.get(self.codigo, '#6c757d')


# ────────────────
# Materia-Docente (Colegio)
# ────────────────
class MateriaDocenteColegio(AuditModel):
    materia       = models.CharField(max_length=100, verbose_name="Materia")
    docente       = models.CharField(max_length=100, verbose_name="Docente")
    coordinadores = models.ManyToManyField(
        ConfiguracionCoordinador, blank=True,
        limit_choices_to={'area': 'colegio', 'activo': True},
        related_name='materias_colegio',
        verbose_name="Coordinadores",
        help_text=(
            "Coordinadores que recibirán notificaciones para esta materia/docente. "
            "Si queda vacío se notificará a todos los coordinadores de Colegio activos."
        ),
    )
    activo        = models.BooleanField(default=True, verbose_name="¿Activo?")

    def __str__(self):
        return f"{self.materia} – {self.docente}"

    class Meta:
        verbose_name = "Materia-Docente Colegio"
        verbose_name_plural = "Materias-Docentes Colegio"
        ordering = ['materia', 'docente']

# ────────────────
# Reporte Conductual
# ────────────────
class ReporteConductual(AuditModel):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuario que reporta")
    area = models.CharField(max_length=10, choices=AREA_CHOICES, default='bilingue', verbose_name="Área")
    alumno_id = models.CharField(max_length=50, verbose_name="ID Alumno")
    alumno_nombre = models.CharField(max_length=120, verbose_name="Nombre del Alumno")
    grado = models.CharField(max_length=50, verbose_name="Grado")
    materia = models.CharField(max_length=100, verbose_name="Materia")
    docente = models.CharField(max_length=100, verbose_name="Docente")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")

    incisos_leve = models.ManyToManyField(
        IncisoConductual, blank=True,
        related_name='conductuales_leve',
        limit_choices_to={'tipo': 'leve', 'activo': True},
        verbose_name="Incisos Leve"
    )
    incisos_grave = models.ManyToManyField(
        IncisoConductual, blank=True,
        related_name='conductuales_grave',
        limit_choices_to={'tipo': 'grave', 'activo': True},
        verbose_name="Incisos Grave"
    )
    incisos_muygrave = models.ManyToManyField(
        IncisoConductual, blank=True,
        related_name='conductuales_muygrave',
        limit_choices_to={'tipo': 'muy_grave', 'activo': True},
        verbose_name="Incisos Muy Grave"
    )

    comentario = models.TextField(blank=True, null=True, verbose_name="Comentario adicional")
    coordinador_firma = models.CharField("Coordinador que aprueba", max_length=100, blank=True, null=True, help_text="Nombre del coordinador que aprobó/firmó el reporte.")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='enviado', verbose_name="Estado del reporte")
    comentario_coordinador = models.TextField("Comentario del Coordinador", blank=True, null=True, help_text="Observación, recomendación o motivo de la revisión/aprobación.")
    coord_asignado = models.CharField("Coordinador asignado", max_length=10, blank=True, default='',
                                      help_text="Override manual del coordinador (C1/C2/C3/C4). Vacío = auto.")

    @property
    def coord_codigo(self):
        # Conductual bilingüe → siempre C3 (Isabel Alcerro), salvo override manual.
        if self.coord_asignado:
            return self.coord_asignado
        if self.area == 'bilingue':
            return 'C3'
        md = MateriaDocenteBilingue.objects.filter(docente=self.docente, activo=True).first()
        if md:
            return md.coordinador.split(',')[0].strip()
        return '—'

    def __str__(self):
        return f'{self.alumno_nombre} - {self.materia} - {self.usuario.username} ({self.get_area_display()})'

    class Meta:
        verbose_name = "Reporte Conductual"
        verbose_name_plural = "Reportes Conductuales"
        ordering = ['-fecha']

# ────────────────
# Reporte Informativo
# ────────────────
class ReporteInformativo(AuditModel):
    TIPO_REPORTE_CHOICES = [
        ('academico',   'Académico'),
        ('conductual',  'Conductual'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuario que reporta")
    area = models.CharField(max_length=10, choices=AREA_CHOICES, default='bilingue', verbose_name="Área")
    alumno_id = models.CharField(max_length=50, verbose_name="ID Alumno")
    alumno_nombre = models.CharField(max_length=120, verbose_name="Nombre del Alumno")
    grado = models.CharField(max_length=50, verbose_name="Grado")
    materia = models.CharField(max_length=100, verbose_name="Materia")
    docente = models.CharField(max_length=100, verbose_name="Docente")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")
    tipo_reporte = models.CharField(max_length=20, choices=TIPO_REPORTE_CHOICES, default='academico', verbose_name="Tipo de Reporte")
    comentario = models.TextField(blank=True, null=True, verbose_name="Comentario")

    coordinador_firma = models.CharField("Coordinador que aprueba", max_length=100, blank=True, null=True, help_text="Nombre del coordinador que aprobó/firmó el reporte.")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='enviado', verbose_name="Estado del reporte")
    comentario_coordinador = models.TextField("Comentario del Coordinador", blank=True, null=True, help_text="Observación, recomendación o motivo de la revisión/aprobación.")
    coord_asignado = models.CharField("Coordinador asignado", max_length=10, blank=True, default='',
                                      help_text="Override manual del coordinador (C1/C2/C3/C4). Vacío = auto.")

    @property
    def coord_codigo(self):
        if self.coord_asignado:
            return self.coord_asignado
        if self.tipo_reporte == 'conductual':
            return 'C3'
        md = MateriaDocenteBilingue.objects.filter(docente=self.docente, activo=True).first()
        if md:
            return md.coordinador.split(',')[0].strip()
        return '—'

    def __str__(self):
        return f'{self.alumno_nombre} - {self.materia} - {self.usuario.username} ({self.get_area_display()})'

    class Meta:
        verbose_name = "Reporte Informativo"
        verbose_name_plural = "Reportes Informativos"
        ordering = ['-fecha']

# ────────────────
# Progress Report
# ────────────────
class ProgressReport(AuditModel):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuario que reporta")
    alumno_id = models.CharField(max_length=50, verbose_name="ID Alumno")
    alumno_nombre = models.CharField(max_length=120, verbose_name="Nombre del Alumno")
    grado = models.CharField(max_length=50, verbose_name="Grado")
    semana_inicio = models.DateField(verbose_name="Semana inicio")
    semana_fin = models.DateField(verbose_name="Semana fin")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")
    materias_json = models.JSONField(verbose_name="Detalle materias", blank=True, default=list)
    comentario_general = models.TextField(blank=True, null=True, verbose_name="Comentario General")

    coordinador_firma = models.CharField("Coordinador que aprueba", max_length=100, blank=True, null=True, help_text="Nombre del coordinador que aprobó/firmó el reporte.")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='enviado', verbose_name="Estado del reporte")
    comentario_coordinador = models.TextField("Comentario del Coordinador", blank=True, null=True, help_text="Observación, recomendación o motivo de la revisión/aprobación.")

    def __str__(self):
        return f'Progress {self.alumno_nombre} ({self.semana_inicio} - {self.semana_fin})'

    class Meta:
        verbose_name = "Progress Report"
        verbose_name_plural = "Progress Reports"
        ordering = ['-fecha']

# ────────────────────────────────────────────────────────────────
# upload_to dinámico para EvidenciaReporte  <--- hecho por claude code
# Genera la ruta de guardado según el área y tipo del reporte.
# Estructura: evidencias/<area>/<tipo>/<filename>
# Ejemplo:    evidencias/bilingue/conductual/foto.jpg
#             evidencias/colegio/informativo/imagen.png
# Se accede al área desde la FK del reporte relacionado.
# ────────────────────────────────────────────────────────────────
def evidencia_upload_to(instance, filename):
    tipo = instance.tipo
    area = 'bilingue'  # valor por defecto
    if tipo == 'conductual' and instance.reporte_conductual_id:
        # Acceder al área sin hacer query extra usando el _id cacheado
        area = instance.reporte_conductual.area
    elif tipo == 'informativo' and instance.reporte_informativo_id:
        area = instance.reporte_informativo.area
    elif tipo == 'progress':
        area = 'bilingue'  # progress solo existe en bilingüe
    return f'evidencias/{area}/{tipo}/{filename}'


# ────────────────────────────────────────────────────────────────
# Evidencia de Reporte  <--- hecho por claude code
# Permite subir imágenes como evidencia asociadas a cualquier tipo
# de reporte (conductual, informativo o progress). Usa tres FK
# nullable para que cada reporte pueda acceder a sus evidencias
# con el reverse manager: r.evidenciareporte_set.all()
# ────────────────────────────────────────────────────────────────
class EvidenciaReporte(AuditModel):
    TIPO_CHOICES = (
        ('conductual', 'Conductual'),
        ('informativo', 'Informativo'),
        ('progress', 'Progress'),
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de reporte")

    # FK nullable a cada tipo de reporte — solo una estará activa por evidencia
    reporte_conductual = models.ForeignKey(
        ReporteConductual, null=True, blank=True,
        on_delete=models.CASCADE, verbose_name="Reporte Conductual"
    )
    reporte_informativo = models.ForeignKey(
        ReporteInformativo, null=True, blank=True,
        on_delete=models.CASCADE, verbose_name="Reporte Informativo"
    )
    reporte_progress = models.ForeignKey(
        ProgressReport, null=True, blank=True,
        on_delete=models.CASCADE, verbose_name="Progress Report"
    )

    # upload_to usa la función dinámica definida arriba para separar por área y tipo
    imagen = models.ImageField(upload_to=evidencia_upload_to, verbose_name="Imagen")
    # <--- hecho por claude code: campo titulo para identificar de quién es la evidencia
    titulo = models.CharField(max_length=200, blank=True, null=True, verbose_name="Título / Nombre")
    comentario = models.TextField(blank=True, null=True, verbose_name="Comentario")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de subida")
    subido_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        verbose_name="Subido por"
    )

    def __str__(self):
        return f"Evidencia {self.get_tipo_display()} – {self.fecha.strftime('%d/%m/%Y') if self.fecha else ''}"

    class Meta:
        verbose_name = "Evidencia de Reporte"
        verbose_name_plural = "Evidencias de Reportes"
        ordering = ['-fecha']


# ────────────────────────────────────────────────────────────────
# Configuración de notificaciones — por coordinador qué tipos recibe
# ────────────────────────────────────────────────────────────────
class ConfiguracionNotificacion(AuditModel):
    area        = models.CharField(max_length=10, choices=AREA_CHOICES, verbose_name="Área")
    coordinador = models.ForeignKey(
        ConfiguracionCoordinador,
        on_delete=models.CASCADE,
        verbose_name="Coordinador",
        related_name='notificaciones',
        help_text="Coordinador que recibirá los tipos de reporte marcados abajo.",
    )
    recibe_conductual             = models.BooleanField(default=False, verbose_name="Conductual")
    recibe_informativo_academico  = models.BooleanField(default=False, verbose_name="Informativo / Académico")
    recibe_informativo_conductual = models.BooleanField(default=False, verbose_name="Informativo / Conductual")
    recibe_progress               = models.BooleanField(default=False, verbose_name="Progress Report")
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")

    class Meta:
        verbose_name = "Regla de Notificación"
        verbose_name_plural = "Configuración de Notificaciones"
        unique_together = [('area', 'coordinador')]
        ordering = ['area', 'coordinador']

    def __str__(self):
        return f"{self.get_area_display()} – {self.coordinador.nombre}"


# ────────────────
# Período Escolar (propio de conducta — independiente de Salidas Baño)
# ────────────────
class PeriodoEscolarConducta(AuditModel):
    """Parcial con fechas para clasificar los reportes (dashboard/historial).
    Catálogo propio de conducta: sus fechas pueden diferir de Salidas Baño."""
    AREA_CHOICES = [
        ('bilingue', 'Bilingüe'),
        ('colegio',  'Colegio'),
        ('ambas',    'Ambas'),
    ]
    nombre       = models.CharField("Nombre", max_length=60)
    parcial      = models.PositiveSmallIntegerField("Número de parcial")
    anio         = models.PositiveSmallIntegerField("Año")
    area         = models.CharField("Área", max_length=20, choices=AREA_CHOICES, default='ambas')
    fecha_inicio = models.DateField("Fecha de inicio")
    fecha_fin    = models.DateField("Fecha de fin")
    activo       = models.BooleanField("Activo", default=False)

    class Meta:
        db_table            = 'conducta_periodo_escolar'
        verbose_name        = 'Período Escolar (Conducta)'
        verbose_name_plural = 'Períodos Escolares (Conducta)'
        ordering            = ['-anio', '-parcial']
        unique_together     = ('parcial', 'anio', 'area')

    def __str__(self):
        return f"{self.nombre} ({self.get_area_display()})"


# ────────────────
# Convocatoria de Tutorías (Bilingüe)
# ────────────────
# <--- hecho por claude code: sistema de convocatoria de tutorías
DIAS_TUTORIA = [(1, 'Lunes'), (2, 'Martes'), (3, 'Miércoles'), (4, 'Jueves'), (5, 'Viernes')]
DIA_ABREV = {1: 'L', 2: 'M', 3: 'M', 4: 'J', 5: 'V'}

GRADOS_TUTORIA = [
    (1, 'Primero'), (2, 'Segundo'), (3, 'Tercero'), (4, 'Cuarto'),
    (5, 'Quinto'), (6, 'Sexto'), (7, 'Séptimo'), (8, 'Octavo'), (9, 'Noveno'),
]
GRADO_TUTORIA_LABEL = dict(GRADOS_TUTORIA)

# Asignaturas de tutoría y su color
COLOR_ASIGNATURA = {
    'Phonics':             '#0c8599',
    'Math':                '#1971c2',
    'Language':            '#2f9e44',
    'Español':             '#c92a2a',
    'Spelling':            '#9c36b5',
    'Reading':             '#e8590c',
    'Lang. Arts':          '#e8a33d',
    'Lang. Arts/Spelling': '#74b816',
    'Science':             '#343a40',
}

# Asignaturas por grado (1-9) y a qué coordinador notifican (C1 = grados 1-3, C2 = 4-9)
ASIGNATURAS_POR_GRADO = {
    1: ['Phonics', 'Math', 'Language', 'Español'],
    2: ['Phonics', 'Math', 'Language', 'Español'],
    3: ['Phonics', 'Math', 'Language', 'Español'],
    4: ['Phonics', 'Spelling', 'Language', 'Español', 'Math'],
    5: ['Reading', 'Language', 'Math', 'Español'],
    6: ['Reading', 'Language', 'Math', 'Español'],
    7: ['Reading', 'Language', 'Math', 'Español'],
    8: ['Reading', 'Language', 'Math', 'Español'],
    9: ['Reading', 'Language', 'Math', 'Español'],
}


def grupo_coord_de_grado(grado_num):
    """Grados 1-3 → C1 (Catherine Varela); 4-9 → C2 (David Ruiz)."""
    if grado_num in (1, 2, 3):
        return 'C1'
    if grado_num in (4, 5, 6, 7, 8, 9):
        return 'C2'
    return ''


def color_asignatura(nombre):
    return COLOR_ASIGNATURA.get((nombre or '').strip(), '#6c757d')


class TutoriaHorario(AuditModel):
    """Matriz de tutorías: por grado y día, qué asignatura(s) se imparten.
    Configurable por parcial/año. Una fila por (grado, día, asignatura)."""
    grado      = models.PositiveSmallIntegerField("Grado", choices=GRADOS_TUTORIA)
    dia        = models.PositiveSmallIntegerField("Día", choices=DIAS_TUTORIA)
    asignatura = models.CharField("Asignatura", max_length=60)
    docente    = models.CharField("Docente", max_length=80, blank=True, default='')
    color      = models.CharField("Color", max_length=9, blank=True, default='')
    parcial    = models.PositiveSmallIntegerField("Parcial")
    anio       = models.PositiveSmallIntegerField("Año")

    class Meta:
        db_table            = 'conducta_tutoria_horario'
        verbose_name        = 'Horario de Tutoría'
        verbose_name_plural = 'Horarios de Tutoría'
        ordering            = ['anio', 'parcial', 'grado', 'dia', 'asignatura']
        unique_together     = ('grado', 'dia', 'asignatura', 'parcial', 'anio')

    def save(self, *args, **kwargs):
        if not self.color:
            self.color = color_asignatura(self.asignatura)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{GRADO_TUTORIA_LABEL.get(self.grado, self.grado)} {DIA_ABREV.get(self.dia)}: {self.asignatura}"


GRUPOS_TUTORIA = [('C1', 'C1'), ('C2', 'C2')]


class TutoriaGrupoMaestro(AuditModel):
    """Maestros habilitados para convocatorias y su grupo (C1 / C2)."""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tutoria_grupo')
    grupo   = models.CharField("Grupo", max_length=4, choices=GRUPOS_TUTORIA, default='C1')
    activo  = models.BooleanField("Activo", default=True)

    class Meta:
        db_table            = 'conducta_tutoria_grupo_maestro'
        verbose_name        = 'Maestro de Tutoría'
        verbose_name_plural = 'Maestros de Tutoría'
        ordering            = ['grupo', 'usuario__first_name']

    def __str__(self):
        return f"{self.usuario} → {self.grupo}"


class ConvocatoriaTutoria(AuditModel):
    """Convocatoria de tutorías de un alumno para un parcial (carta a padres)."""
    usuario       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='convocatorias')
    area          = models.CharField(max_length=10, choices=AREA_CHOICES, default='bilingue')
    coord_grupo   = models.CharField("Grupo coordinador", max_length=4, choices=GRUPOS_TUTORIA,
                                     blank=True, default='')
    alumno_id     = models.CharField("ID alumno", max_length=30)
    alumno_nombre = models.CharField("Alumno", max_length=200)
    grado         = models.CharField("Grado (texto)", max_length=60, blank=True, default='')
    grado_num     = models.PositiveSmallIntegerField("Grado #", null=True, blank=True)
    seccion       = models.CharField("Sección", max_length=20, blank=True, default='')
    parcial       = models.PositiveSmallIntegerField("Parcial")
    anio          = models.PositiveSmallIntegerField("Año")
    docente_guia  = models.CharField("Docente guía", max_length=120, blank=True, default='')
    coordinador   = models.CharField("Coordinador de área", max_length=120, blank=True, default='')
    fecha         = models.DateField("Fecha de la convocatoria")
    creado_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'conducta_convocatoria_tutoria'
        verbose_name        = 'Convocatoria de Tutoría'
        verbose_name_plural = 'Convocatorias de Tutoría'
        ordering            = ['-creado_at']

    def __str__(self):
        return f"Convocatoria {self.alumno_nombre} — P{self.parcial} {self.anio}"


class ConvocatoriaAsignatura(AuditModel):
    """Asignatura convocada dentro de una convocatoria + los días (1-5) marcados."""
    convocatoria = models.ForeignKey(ConvocatoriaTutoria, on_delete=models.CASCADE,
                                     related_name='asignaturas')
    asignatura   = models.CharField("Asignatura", max_length=60)
    dias         = models.CharField("Días (coma)", max_length=20, blank=True, default='',
                                    help_text="Códigos 1-5 separados por coma (L=1…V=5)")

    class Meta:
        db_table            = 'conducta_convocatoria_asignatura'
        verbose_name        = 'Asignatura de Convocatoria'
        verbose_name_plural = 'Asignaturas de Convocatoria'
        ordering            = ['pk']

    @property
    def dias_lista(self):
        return [int(d) for d in self.dias.split(',') if d.strip().isdigit()]

    def tiene_dia(self, n):
        return n in self.dias_lista

    def __str__(self):
        return f"{self.asignatura} [{self.dias}]"


class ConvocatoriaMarca(AuditModel):
    """Marca de la tabla por grado: un alumno convocado a una asignatura.
    Los días salen fijos del horario (TutoriaHorario) de esa asignatura/grado."""
    area          = models.CharField(max_length=10, choices=AREA_CHOICES, default='bilingue')
    parcial       = models.PositiveSmallIntegerField("Parcial")
    anio          = models.PositiveSmallIntegerField("Año")
    grado_num     = models.PositiveSmallIntegerField("Grado #")
    seccion       = models.CharField("Sección", max_length=20, blank=True, default='')
    alumno_id     = models.CharField("ID alumno", max_length=30)
    alumno_nombre = models.CharField("Alumno", max_length=200)
    asignatura    = models.CharField("Asignatura", max_length=60)
    marcado_por   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='convocatoria_marcas')
    creado_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'conducta_convocatoria_marca'
        verbose_name        = 'Marca de Convocatoria'
        verbose_name_plural = 'Marcas de Convocatoria'
        unique_together     = ('parcial', 'anio', 'area', 'alumno_id', 'asignatura')
        ordering            = ['alumno_nombre', 'asignatura']

    def __str__(self):
        return f"{self.alumno_nombre} → {self.asignatura} (P{self.parcial})"


class ConvocatoriaFirma(models.Model):
    """Coordinador de área que firma la convocatoria de un grado/parcial (para los PDFs)."""
    area              = models.CharField(max_length=10, default='bilingue')
    parcial           = models.PositiveSmallIntegerField()
    anio              = models.PositiveSmallIntegerField()
    grado_num         = models.PositiveSmallIntegerField()
    seccion           = models.CharField(max_length=20, blank=True, default='')
    coordinador_firma = models.CharField(max_length=100, blank=True, default='')
    docente_firma     = models.CharField(max_length=100, blank=True, default='')  # maestro guía

    class Meta:
        db_table        = 'conducta_convocatoria_firma'
        unique_together = ('area', 'parcial', 'anio', 'grado_num', 'seccion')

    def __str__(self):
        return f"Firma {self.grado_num}.{self.seccion} P{self.parcial} → {self.coordinador_firma}"
