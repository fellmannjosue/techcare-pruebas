from django.db import models
from django.conf import settings


class NotaComentario(models.Model):
    ingr_egr_id     = models.IntegerField(db_index=True)
    parcial         = models.IntegerField()
    anio            = models.IntegerField()
    area            = models.CharField(max_length=20)
    # Maestro autor del comentario (un comentario por maestro por alumno)
    maestro         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notas_comentarios_propios',
    )
    comentario      = models.TextField(blank=True, default='')
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='notas_comentarios',
    )
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = 'notas_parcial_comentario'
        unique_together = ('ingr_egr_id', 'parcial', 'anio', 'area', 'maestro')

    def __str__(self):
        return f"Comentario {self.ingr_egr_id} P{self.parcial}/{self.anio}"


class AsignacionMaestro(models.Model):
    maestro      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='asignaciones_notas',
    )
    area         = models.CharField(max_length=20)
    parcial      = models.IntegerField()
    anio         = models.IntegerField()
    grado        = models.CharField(max_length=20)
    seccion      = models.CharField(max_length=20, blank=True, default='')
    asignado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='asignaciones_hechas_notas',
    )
    asignado_en  = models.DateTimeField(auto_now_add=True)
    fecha_limite = models.DateTimeField(null=True, blank=True, verbose_name='Fecha límite')

    class Meta:
        db_table        = 'notas_asignacion_maestro'
        unique_together = ('area', 'parcial', 'anio', 'grado', 'seccion', 'maestro')
        verbose_name        = 'Asignación de maestro'
        verbose_name_plural = 'Asignaciones de maestros'

    def __str__(self):
        nombre = self.maestro.get_full_name() or self.maestro.username
        return f'{nombre} → {self.area} P{self.parcial}/{self.anio} G{self.grado} {self.seccion}'


class RevisionFinalizada(models.Model):
    maestro  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='revisiones_finalizadas_notas',
    )
    area     = models.CharField(max_length=20)
    parcial  = models.IntegerField()
    anio     = models.IntegerField()
    grado    = models.CharField(max_length=20)
    seccion  = models.CharField(max_length=20, blank=True, default='')
    fecha    = models.DateTimeField(auto_now=True)
    leida    = models.BooleanField(default=False)

    class Meta:
        db_table        = 'notas_revision_finalizada'
        unique_together = ('maestro', 'area', 'parcial', 'anio', 'grado', 'seccion')
        verbose_name        = 'Revisión finalizada'
        verbose_name_plural = 'Revisiones finalizadas'

    def __str__(self):
        nombre = self.maestro.get_full_name() or self.maestro.username
        return f'{nombre} finalizó {self.area} P{self.parcial}/{self.anio} G{self.grado} {self.seccion}'
