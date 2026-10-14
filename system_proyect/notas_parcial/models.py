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


class CierreNotas(models.Model):
    """<--- hecho por claude code (12-oct-2026): cierre de escritura de los MAESTROS asignados.

    Un registro por alcance: un grado-sección (grado+seccion) o TODO el parcial del área
    (grado='' y seccion=''). `revocado` corta la escritura ya; `cierre_en` la corta sola al
    llegar esa fecha y hora. Los coordinadores y el superusuario nunca quedan bloqueados.
    Se valida en el servidor (guardar_comentario / finalizar_revision), no solo en pantalla."""
    area      = models.CharField(max_length=20)
    parcial   = models.IntegerField()
    anio      = models.IntegerField()
    grado     = models.CharField(max_length=20, blank=True, default='')
    seccion   = models.CharField(max_length=20, blank=True, default='')
    revocado  = models.BooleanField('Permisos revocados', default=False)
    cierre_en = models.DateTimeField('Fecha y hora de cierre', null=True, blank=True)
    # <--- hecho por claude code (12-oct-2026): "Cerrar parcial" (solo en la fila de todo el parcial): además de cortar la
    # escritura, el parcial DESAPARECE de "Mis Reportes" de los maestros (veían el 3 y el 4 a la vez). Se puede reabrir.
    parcial_cerrado = models.BooleanField('Parcial cerrado', default=False)
    parcial_cerrado_en = models.DateTimeField('Parcial cerrado el', null=True, blank=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='+')
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = 'notas_cierre'
        unique_together = ('area', 'parcial', 'anio', 'grado', 'seccion')
        verbose_name        = 'Cierre de escritura'
        verbose_name_plural = 'Cierres de escritura'

    def __str__(self):
        alcance = f'{self.grado} {self.seccion}'.strip() or 'todo el parcial'
        return f'{self.area} P{self.parcial}/{self.anio} · {alcance}'


class MaestroGuia(models.Model):
    """<--- hecho por claude code (13-oct-2026): maestro guía de un grado-sección en el año (como en Tutorías).
    Su nombre sale bajo la línea "Firma del Maestro Guía" del PDF de Notas a Mitad de Parcial.
    Es por AÑO (el guía no cambia de parcial a parcial)."""
    area    = models.CharField(max_length=20)
    anio    = models.IntegerField()
    grado   = models.CharField(max_length=20)
    seccion = models.CharField(max_length=20, blank=True, default='')
    nombre  = models.CharField('Maestro guía', max_length=120)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='+')
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = 'notas_maestro_guia'
        unique_together = ('area', 'anio', 'grado', 'seccion')
        verbose_name        = 'Maestro guía'
        verbose_name_plural = 'Maestros guía'

    def __str__(self):
        return f'{self.area} {self.grado} {self.seccion} {self.anio} → {self.nombre}'
