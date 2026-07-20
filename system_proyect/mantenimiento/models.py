import uuid

from django.db import models
from core.models import AuditModel


class TipoFalla(AuditModel):
    nombre = models.CharField(max_length=100, verbose_name="Tipo de Falla")

    class Meta:
        db_table = 'tipo_falla'
        verbose_name = "Tipo de Falla"
        verbose_name_plural = "Tipos de Falla"

    def __str__(self):
        return self.nombre


class MaestroMantenimiento(models.Model):
    nombre = models.CharField("Nombre", max_length=150, unique=True)

    class Meta:
        verbose_name = "Maestro"
        verbose_name_plural = "Maestros"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class GradoMantenimiento(models.Model):
    nombre = models.CharField("Nombre", max_length=100, unique=True)

    class Meta:
        verbose_name = "Grado"
        verbose_name_plural = "Grados"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class MaintenanceRecord(AuditModel):
    # <--- hecho por claude code: registro polimórfico computadora / impresora
    TIPO_EQUIPO_CHOICES = [
        ('computadora', 'Computadora'),
        ('impresora',   'Impresora'),
    ]
    TIPO_MANT_IMPRESORA_CHOICES = [
        ('llenado_tinta',         'Llenado de tinta'),
        ('actualizacion_sistema', 'Actualización de sistema'),
    ]
    ESTADO_TINTA_CHOICES = [
        ('vacio', 'Vacío'),
        ('media', 'Media'),
        ('llena', 'Llena'),
        ('full',  'Full'),
    ]
    TIPO_TINTA_CHOICES = [
        ('544', '544'),
        ('504', '504'),
    ]

    record_id    = models.CharField("ID Registro", max_length=20, unique=True, blank=True)
    tipo_equipo  = models.CharField("Tipo de equipo", max_length=20, choices=TIPO_EQUIPO_CHOICES, default='computadora')
    computadora  = models.ForeignKey(
        'inventario.Computadora',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Computadora"
    )
    impresora    = models.ForeignKey(
        'inventario.Impresora',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Impresora"
    )
    model        = models.CharField("Modelo", max_length=100, blank=True)
    serie        = models.CharField("Serie", max_length=100, blank=True)
    teacher_name = models.CharField("Nombre del Maestro", max_length=150, blank=True)
    grade        = models.CharField("Grado", max_length=100, blank=True)
    area         = models.CharField("Área", max_length=100, blank=True)  # <--- hecho por claude code: área manual (impresora)
    tipo_falla   = models.ForeignKey(TipoFalla, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tipo de Falla")
    # <--- hecho por claude code: campos específicos de mantenimiento de impresora
    tipo_mant_impresora = models.CharField("Tipo de mantenimiento (impresora)", max_length=30, choices=TIPO_MANT_IMPRESORA_CHOICES, blank=True)
    estado_tinta = models.CharField("Estado de la tinta", max_length=10, choices=ESTADO_TINTA_CHOICES, blank=True)
    tinta_negra    = models.BooleanField("Tinta negra rellenada", default=False)
    tinta_magenta  = models.BooleanField("Tinta magenta rellenada", default=False)
    tinta_amarillo = models.BooleanField("Tinta amarillo rellenada", default=False)
    tinta_cyan     = models.BooleanField("Tinta cyan rellenada", default=False)
    tipo_tinta   = models.CharField("Tipo de tinta", max_length=10, choices=TIPO_TINTA_CHOICES, blank=True)
    solucion     = models.TextField("Solución Aplicada", null=True, blank=True)
    date         = models.DateField("Fecha del Mantenimiento")
    status       = models.CharField(
        max_length=50,
        choices=[
            ('Pendiente', 'Pendiente'),
            ('En Proceso', 'En Proceso'),
            ('Completado', 'Completado'),
        ],
        verbose_name="Estado"
    )
    observaciones = models.TextField(null=True, blank=True, verbose_name="Observaciones")
    # Firma del MAESTRO (evidencia de la reparación). En persona o remota (link wa.me).
    firma         = models.TextField("Firma del maestro (base64)", blank=True, null=True)
    # Firma del TÉCNICO / soporte (en persona, quien hace la reparación).
    firma_tecnico = models.TextField("Firma del técnico (base64)", blank=True, null=True)
    # Firma remota del maestro por link (token público, sin login).
    token_firma      = models.UUIDField("Token de firma", default=uuid.uuid4, unique=True, editable=False)
    firma_solicitada = models.BooleanField("Firma solicitada", default=False)
    firmado_en       = models.DateTimeField("Firmado el", null=True, blank=True)

    @property
    def firmado_maestro(self):
        return bool((self.firma or '').strip())

    class Meta:
        db_table = 'maintenance_record'
        verbose_name = "Registro de Mantenimiento"
        verbose_name_plural = "Registros de Mantenimiento"

    def __str__(self):
        return f"{self.record_id} - {self.teacher_name}"


class FotoMantenimiento(models.Model):
    registro = models.ForeignKey(
        MaintenanceRecord, on_delete=models.CASCADE,
        related_name='fotos', verbose_name="Registro"
    )
    imagen   = models.ImageField("Foto", upload_to='mantenimiento/fotos/')
    orden    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name = "Foto de Mantenimiento"
        verbose_name_plural = "Fotos de Mantenimiento"
