from django.db import models
from django.contrib.auth.models import User
from core.models import AuditModel

AREA_CHOICES = (
    ('primaria',    'Primaria Bilingüe'),
    ('colegio_bl',  'Colegio Bilingüe'),
    ('colegio',     'Colegio'),
)

ESTADO_CHOICES = (
    ('enviado',   'Enviado'),
    ('revisando', 'Revisando'),
    ('revisado',  'Revisado'),
    ('aprobado',  'Aprobado'),
)

TIPO_MATERIAS_CHOICES = (
    ('primaria',    'Primaria Bilingüe (incluye Phonics)'),
    ('colegio_bl',  'Colegio Bilingüe (incluye Cívica)'),
    ('colegio_7_9', 'Colegio 7mo–9no'),
    ('colegio_10',  'Colegio 10mo'),
    ('colegio_11',  'Colegio 11mo'),
)


class GradoAgenda(models.Model):
    nombre        = models.CharField(max_length=100, verbose_name="Nombre del Grado")
    area          = models.CharField(max_length=10, choices=AREA_CHOICES, default='bilingue', verbose_name="Área")
    tipo_materias = models.CharField(max_length=12, choices=TIPO_MATERIAS_CHOICES, default='primaria',
                                     verbose_name="Tipo de materias",
                                     help_text="Determina si incluye Phonics (primaria) o Cívica (colegio)")
    activo        = models.BooleanField(default=True, verbose_name="¿Activo?")
    orden         = models.PositiveIntegerField(default=0, verbose_name="Orden de visualización")

    class Meta:
        verbose_name        = "Grado (Agenda)"
        verbose_name_plural = "Grados (Agenda)"
        ordering            = ['area', 'orden', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_area_display()})"


class Agenda(AuditModel):
    usuario                = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Maestro")
    grado                  = models.ForeignKey(GradoAgenda, on_delete=models.PROTECT, verbose_name="Grado")
    semana_inicio          = models.DateField(verbose_name="Semana inicio")
    semana_fin             = models.DateField(verbose_name="Semana fin")
    materias_json          = models.JSONField(default=list, blank=True, verbose_name="Detalle materias")
    nota_general           = models.CharField(max_length=200, blank=True, default='', verbose_name="Nota")
    estado                 = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='enviado', verbose_name="Estado")
    comentario_coordinador = models.TextField(blank=True, default='', verbose_name="Comentario del coordinador")

    class Meta:
        verbose_name        = "Agenda"
        verbose_name_plural = "Agendas"
        ordering            = ['-semana_inicio', 'grado']

    def __str__(self):
        return f"Agenda {self.grado} ({self.semana_inicio} – {self.semana_fin})"


class ImagenAgenda(models.Model):
    agenda      = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name='imagenes', verbose_name="Agenda")
    imagen      = models.ImageField(upload_to='agendas/imagenes/', verbose_name="Imagen")
    descripcion = models.CharField(max_length=200, blank=True, verbose_name="Descripción")
    materia     = models.CharField(max_length=150, blank=True, default='', verbose_name="Materia")
    subida_en   = models.DateTimeField(auto_now_add=True, verbose_name="Subida el")
    subida_por  = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+', verbose_name="Subida por")

    class Meta:
        verbose_name        = "Imagen de Agenda"
        verbose_name_plural = "Imágenes de Agenda"

    def __str__(self):
        return f"Imagen de {self.agenda} – {self.subida_en:%d/%m/%Y}"


class AgendaBloqueoConfig(models.Model):
    """Horario semanal automático de llenado de agendas (singleton pk=1).
       Lun: solo los 'maestros' permitidos. Mar/Mié: abierto.
       Jue: abierto hasta `jueves_hora_limite`, luego cerrado. Vie: cerrado.
       Los coordinadores nunca se bloquean."""
    from datetime import time as _t
    MSG_LUNES_DEFAULT  = ("Estimados maestros, el día de hoy solo le toca a los asociados. "
                          "Favor esperar a los días que les corresponde.")
    MSG_JUEVES_DEFAULT = "Se cierra el llenado de agendas."
    MSG_VIERNES_DEFAULT = "El día de hoy se mandan las agendas, ya no se podrá llenar más."

    activo          = models.BooleanField("Horario activo", default=False)
    # Maestros permitidos el LUNES (el resto se bloquea ese día)
    maestros        = models.ManyToManyField(User, blank=True, related_name='agenda_bloqueos',
                                             verbose_name="Permitidos el lunes")
    mensaje         = models.TextField("Mensaje lunes", default=MSG_LUNES_DEFAULT)
    mensaje_jueves  = models.TextField("Mensaje jueves (después del límite)", default=MSG_JUEVES_DEFAULT)
    mensaje_viernes = models.TextField("Mensaje viernes", default=MSG_VIERNES_DEFAULT)
    jueves_limite   = models.TimeField("Jueves — hora de cierre", default=_t(12, 0))
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Bloqueo de Agendas"
        verbose_name_plural = "Bloqueo de Agendas"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Horario agendas ({'ON' if self.activo else 'OFF'})"
