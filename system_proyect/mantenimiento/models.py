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
    record_id    = models.CharField("ID Registro", max_length=20, unique=True, blank=True)
    computadora  = models.ForeignKey(
        'inventario.Computadora',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Computadora"
    )
    model        = models.CharField("Modelo", max_length=100)
    serie        = models.CharField("Serie", max_length=100, blank=True)
    teacher_name = models.CharField("Nombre del Maestro", max_length=150)
    grade        = models.CharField("Grado", max_length=100)
    tipo_falla   = models.ForeignKey(TipoFalla, on_delete=models.SET_NULL, null=True, verbose_name="Tipo de Falla")
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
    firma         = models.TextField("Firma (base64)", blank=True, null=True)

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
