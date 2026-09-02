from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import AuditModel

from .sla import SLA_HORAS, URGENCIA_CHOICES, sumar_horas_laborales, minutos_laborales_entre

# <--- hecho por claude code: estados que cuentan como "cerrado" (el SLA se detiene)
ESTADOS_CERRADOS = ('Resuelto', 'Cerrado')


class Ticket(AuditModel):
    ticket_id = models.CharField(max_length=20, unique=True, editable=False, null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    name = models.CharField(max_length=255)
    grade = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    description = models.TextField()
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True)
    status = models.CharField(max_length=50, default='Pendiente')
    comments = models.TextField(blank=True, null=True)

    # <--- hecho por claude code: urgencia (la pone el usuario) + SLA (horas laborales)
    urgencia = models.CharField(max_length=10, choices=URGENCIA_CHOICES, default='medio')
    vence_en = models.DateTimeField(null=True, blank=True, editable=False)
    resuelto_en = models.DateTimeField(null=True, blank=True, editable=False)

    # IA pendiente para más adelante
    ia_bloqueada = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tickets'

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            date_part = datetime.now().strftime("%Y%m%d")
            last_ticket = Ticket.objects.filter(ticket_id__startswith=f"TICKET-{date_part}") \
                                        .order_by('-created_at') \
                                        .first()
            if last_ticket:
                last_number = int(last_ticket.ticket_id.split('-')[-1]) + 1
            else:
                last_number = 1

            self.ticket_id = f"TICKET-{date_part}-{last_number:04d}"

        # <--- hecho por claude code: SLA — marcar resuelto y (re)calcular vencimiento laboral
        if self.status in ESTADOS_CERRADOS:
            if not self.resuelto_en:
                self.resuelto_en = timezone.now()
        else:
            self.resuelto_en = None
            base = self.created_at or timezone.now()
            self.vence_en = sumar_horas_laborales(base, self.sla_horas)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_id} - {self.name}"

    # ── SLA ──────────────────────────────────────────────────────────────────
    @property
    def sla_horas(self):
        return SLA_HORAS.get((self.urgencia or 'medio'), 24)

    @property
    def cerrado(self):
        return self.status in ESTADOS_CERRADOS

    @property
    def sin_atender(self):
        """Aún no lo toma un técnico (Nuevo/Pendiente)."""
        return (self.status or '').strip() in ('Nuevo', 'Pendiente')

    @property
    def sla_restante_min(self):
        """Minutos LABORALES que faltan para vencer (0 si ya venció). None si no aplica."""
        if not self.vence_en or self.cerrado:
            return None
        return minutos_laborales_entre(timezone.now(), self.vence_en)

    @property
    def sla_estado(self):
        """cumplido / incumplido (si cerrado) · a_tiempo / por_vencer / vencido (si abierto)."""
        if self.cerrado:
            if self.vence_en and self.resuelto_en:
                return 'cumplido' if self.resuelto_en <= self.vence_en else 'incumplido'
            return 'cumplido'
        if not self.vence_en:
            return 'a_tiempo'
        if timezone.now() > self.vence_en:
            return 'vencido'
        rest = self.sla_restante_min or 0
        if rest <= self.sla_horas * 60 * 0.25:   # queda <=25% del tiempo
            return 'por_vencer'
        return 'a_tiempo'

    @property
    def sla_texto(self):
        est = self.sla_estado
        if est == 'cumplido':
            return 'Cumplido'
        if est == 'incumplido':
            return 'Incumplido'
        if est == 'vencido':
            return 'Vencido'
        rest = self.sla_restante_min or 0
        h, m = divmod(rest, 60)
        return (f'Vence en {h}h {m}m' if h else f'Vence en {m}m')


class TicketComment(AuditModel):
    TIPO_CHOICES = (
        ('usuario', 'Usuario'),
        ('tecnico', 'Técnico'),
        ('sistema', 'Sistema'),
        # IA pendiente para más adelante
        # ('ia', 'IA'),
    )

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    mensaje = models.TextField("Comentario", blank=True)
    archivo = models.FileField("Adjunto", upload_to='ticket_chat/', null=True, blank=True)
    fecha = models.DateTimeField("Fecha", auto_now_add=True)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='usuario'
    )

    class Meta:
        verbose_name = "Comentario de Ticket"
        verbose_name_plural = "Comentarios de Tickets"
        ordering = ['fecha']

    def __str__(self):
        autor = self.usuario.username if self.usuario else self.get_tipo_display()
        return f"{autor} – {self.fecha.strftime('%d/%m/%Y %H:%M')}: {self.mensaje[:40]}"

    @property
    def es_imagen(self):
        if not self.archivo:
            return False
        ext = self.archivo.name.rsplit('.', 1)[-1].lower() if '.' in self.archivo.name else ''
        return ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg')

    @property
    def archivo_nombre(self):
        import os
        return os.path.basename(self.archivo.name) if self.archivo else ''