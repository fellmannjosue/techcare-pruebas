# datashow/models.py
# <--- hecho por claude code (02-nov-2026): Solicitud/Reserva de DataShow con calendario y autorización de Soporte.
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from simple_history.models import HistoricalRecords

from core.models import AuditModel
from inventario.models import DataShow


class ReservaDataShow(AuditModel):
    """Una reserva de uso de un DataShow para una fecha y franja horaria.
    El usuario la crea (queda 'pendiente'); Soporte la revisa y la autoriza o rechaza.
    Un DataShow no puede estar reservado dos veces en franjas que se solapen el mismo día
    (solo cuentan las reservas 'pendiente' y 'autorizada')."""

    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_AUTORIZADA = 'autorizada'
    ESTADO_RECHAZADA = 'rechazada'
    ESTADO_CANCELADA = 'cancelada'
    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_AUTORIZADA, 'Autorizada'),
        (ESTADO_RECHAZADA, 'Rechazada'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]
    # Estados que OCUPAN el equipo (bloquean la franja)
    ESTADOS_ACTIVOS = (ESTADO_PENDIENTE, ESTADO_AUTORIZADA)

    datashow = models.ForeignKey(
        DataShow, on_delete=models.PROTECT, related_name='reservas',
        verbose_name='DataShow'
    )
    solicitante = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reservas_datashow',
        verbose_name='Solicitante'
    )
    fecha = models.DateField('Fecha de uso', db_index=True)
    hora_inicio = models.TimeField('Hora de inicio')
    hora_fin = models.TimeField('Hora de fin')
    lugar = models.CharField('Lugar de uso', max_length=150)
    motivo = models.TextField('Motivo / actividad', blank=True)

    estado = models.CharField(
        'Estado', max_length=12, choices=ESTADOS,
        default=ESTADO_PENDIENTE, db_index=True
    )
    revisado_por = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='Revisado por'
    )
    revisado_en = models.DateTimeField('Revisado el', null=True, blank=True)
    comentario_soporte = models.TextField('Comentario de Soporte', blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Reserva de DataShow'
        verbose_name_plural = 'Reservas de DataShow'
        ordering = ['-fecha', 'hora_inicio']

    def __str__(self):
        return f'{self.datashow.asset_id} · {self.fecha} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}'

    # ---- Propiedades de apoyo ----
    @property
    def activa(self):
        """La reserva ocupa el equipo (pendiente o autorizada)."""
        return self.estado in self.ESTADOS_ACTIVOS

    @property
    def estado_color(self):
        return {
            self.ESTADO_PENDIENTE: 'orange',
            self.ESTADO_AUTORIZADA: 'green',
            self.ESTADO_RECHAZADA: 'red',
            self.ESTADO_CANCELADA: 'secondary',
        }.get(self.estado, 'secondary')

    @property
    def estado_icono(self):
        return {
            self.ESTADO_PENDIENTE: 'ti-clock-hour-4',
            self.ESTADO_AUTORIZADA: 'ti-circle-check',
            self.ESTADO_RECHAZADA: 'ti-circle-x',
            self.ESTADO_CANCELADA: 'ti-ban',
        }.get(self.estado, 'ti-circle')

    @property
    def rango_horario(self):
        return f'{self.hora_inicio:%H:%M} – {self.hora_fin:%H:%M}'

    @property
    def es_pasada(self):
        return self.fecha < timezone.now().date()

    def puede_cancelar(self, user):
        """El solicitante (o superusuario) cancela mientras siga activa y no haya pasado."""
        if self.estado not in self.ESTADOS_ACTIVOS:
            return False
        return user.is_superuser or self.solicitante_id == user.id
