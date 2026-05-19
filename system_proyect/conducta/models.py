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
        if self.coord_asignado:
            return self.coord_asignado
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
