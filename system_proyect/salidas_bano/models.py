# <--- hecho por claude code: Sistema Salidas Baño — modelos
from django.db import models
from django.conf import settings


class PeriodoEscolar(models.Model):
    """Parcial con fechas — configurable manualmente por el admin."""
    # <--- hecho por claude code: 'ambos' = Colegio + Bachillerato, NUNCA incluye CFP
    AREA_CHOICES = [
        ('colegio',      'Colegio'),
        ('bachillerato', 'Bachillerato'),
        ('ambos',        'Ambos'),
        ('cfp',          'CFP'),
    ]
    nombre       = models.CharField("Nombre", max_length=60)          # "Parcial 1 2026"
    parcial      = models.PositiveSmallIntegerField("Número de parcial")
    anio         = models.PositiveSmallIntegerField("Año")
    area         = models.CharField("Área", max_length=20, choices=AREA_CHOICES, default='ambos')
    fecha_inicio = models.DateField("Fecha de inicio")
    fecha_fin    = models.DateField("Fecha de fin")
    activo       = models.BooleanField("Activo", default=False)

    class Meta:
        db_table            = 'sb_periodo_escolar'
        verbose_name        = 'Período Escolar'
        verbose_name_plural = 'Períodos Escolares'
        ordering            = ['-anio', '-parcial']
        unique_together     = ('parcial', 'anio', 'area')

    def __str__(self):
        return f"{self.nombre} ({self.get_area_display()})"


class MaestroClase(models.Model):
    """Define qué maestro imparte qué clase en qué grado/área.

    En CFP el campo `grado` guarda el CURSO (tc.Descripcion de SQL Server).
    """
    # <--- hecho por claude code: 'ambos' = Colegio + Bachillerato, NUNCA incluye CFP
    AREA_CHOICES = [
        ('colegio',      'Colegio'),
        ('bachillerato', 'Bachillerato'),
        ('ambos',        'Ambos'),
        ('cfp',          'CFP'),
    ]
    maestro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clases_bano',
        verbose_name='Maestro',
    )
    clase   = models.CharField("Clase / Materia", max_length=80)
    grado   = models.CharField("Grado", max_length=120)  # "1ero", "2do" o varios separados por coma
    area    = models.CharField("Área", max_length=20, choices=AREA_CHOICES)

    class Meta:
        db_table            = 'sb_maestro_clase'
        verbose_name        = 'Maestro – Clase'
        verbose_name_plural = 'Maestros – Clases'
        ordering            = ['area', 'grado', 'clase']

    def __str__(self):
        nombre = self.maestro.get_full_name() or self.maestro.username
        return f"{nombre} | {self.clase} | {self.grado} ({self.area})"


class SalidaBano(models.Model):
    """Registro individual de una salida al baño."""
    SEMAFORO_CHOICES = [
        ('verde',    'Verde'),
        ('amarillo', 'Amarillo'),
        ('rojo',     'Rojo'),
        ('negro',    'Negro'),
    ]
    AREA_CHOICES = [
        ('colegio',      'Colegio'),
        ('bachillerato', 'Bachillerato'),
        ('cfp',          'CFP'),
    ]

    # ── Identificación del alumno ──────────────────────────────────────────
    # <--- hecho por claude code: en CFP este campo guarda el PersonaID (no el
    # IngrEgrID); el área lo discrimina, son espacios de ID distintos.
    ingr_egr_id = models.IntegerField("ID Alumno (SQL Server)", db_index=True)
    alumno      = models.CharField("Nombre alumno", max_length=120)
    # <--- hecho por claude code: en CFP `grado` guarda el CURSO y `grupo` la jornada
    grado       = models.CharField("Grado", max_length=160)
    grupo       = models.CharField("Grupo", max_length=20, blank=True, default='')
    area        = models.CharField("Área", max_length=20, choices=AREA_CHOICES)

    # ── Período escolar ────────────────────────────────────────────────────
    periodo     = models.ForeignKey(
        PeriodoEscolar,
        on_delete=models.CASCADE,
        related_name='salidas',
        verbose_name='Período',
    )

    # ── Clase en que salió ────────────────────────────────────────────────
    clase       = models.CharField("Clase", max_length=80)

    # ── Semáforo y tiempos ────────────────────────────────────────────────
    semaforo    = models.CharField("Semáforo", max_length=10, choices=SEMAFORO_CHOICES)
    hora_salida = models.TimeField("Hora de salida")
    hora_regreso= models.TimeField("Hora de regreso", null=True, blank=True)
    comentario  = models.TextField("Comentario", blank=True, default='')

    # ── Auditoría ─────────────────────────────────────────────────────────
    maestro     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='salidas_registradas',
        verbose_name='Registrado por',
    )
    fecha       = models.DateField("Fecha", auto_now_add=True)
    creado_en   = models.DateTimeField(auto_now_add=True)
    notificado  = models.BooleanField("Notificación enviada", default=False)

    class Meta:
        db_table            = 'sb_salida_bano'
        verbose_name        = 'Salida al Baño'
        verbose_name_plural = 'Salidas al Baño'
        ordering            = ['-creado_en']

    def __str__(self):
        return f"{self.alumno} — {self.semaforo} — {self.fecha}"

    @property
    def duracion_minutos(self):
        """Calcula minutos de ausencia si hay hora de regreso."""
        if self.hora_salida and self.hora_regreso:
            from datetime import datetime, date
            hoy = date.today()
            salida  = datetime.combine(hoy, self.hora_salida)
            regreso = datetime.combine(hoy, self.hora_regreso)
            diff = (regreso - salida).seconds // 60
            return diff if diff >= 0 else None
        return None


class NotificacionSalida(models.Model):
    """Bell notification para maestros cuando se registra una salida."""
    salida   = models.ForeignKey(SalidaBano, on_delete=models.CASCADE, related_name='notificaciones')
    usuario  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notif_salidas')
    leida    = models.BooleanField(default=False)
    creada_en= models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sb_notificacion_salida'
        unique_together = ('salida', 'usuario')
