from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import AuditModel

from .sla import SLA_HORAS, URGENCIA_CHOICES, sumar_horas_laborales, minutos_laborales_entre, en_horario_laboral, proxima_apertura

# <--- hecho por claude code: estados que cuentan como "cerrado" (el SLA se detiene)
ESTADOS_CERRADOS = ('Resuelto', 'Cerrado')
# <--- hecho por claude code: estados que PAUSAN el SLA (soporte no puede avanzar)
ESTADO_ESPERA = 'En espera del usuario'
ESTADO_INCOMPLETO = 'Incompleto'
ESTADOS_PAUSA = (ESTADO_ESPERA, ESTADO_INCOMPLETO)


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

    # <--- hecho por claude code: SLA pausable — minutos LABORALES acumulados de todas las
    # pausas (En espera del usuario). El deadline se corre por esta cantidad, sin reiniciar.
    sla_pausa_min = models.PositiveIntegerField(default=0)

    # <--- hecho por claude code (29-sep-2026): tickets vinculados a Gestión de Desarrollo. Un ticket que nace de un
    # requerimiento (o que se convierte en uno) NO lleva SLA (un desarrollo dura semanas, no horas), no entra a la
    # alerta de "sin atender" y queda asignado al responsable del requerimiento. Su estado lo manda el requerimiento.
    sin_sla = models.BooleanField('Sin SLA (ticket de desarrollo)', default=False)
    asignado_a = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='tickets_asignados',
                                   verbose_name='Asignado a')

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
        elif self.sin_sla:
            self.resuelto_en = None
            self.vence_en = None          # ticket de desarrollo: sin vencimiento
        else:
            self.resuelto_en = None
            base = self.created_at or timezone.now()
            # <--- hecho por claude code: el deadline = SLA base + tiempo que estuvo pausado.
            # Determinístico y acumulativo (soporta varias pausas sin reiniciar ni perder tiempo).
            self.vence_en = sumar_horas_laborales(base, self.sla_horas + (self.sla_pausa_min or 0) / 60)

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
        """Aún no lo toma un técnico (Nuevo/Pendiente). Los tickets de desarrollo no cuentan."""
        return (not self.sin_sla) and (self.status or '').strip() in ('Nuevo', 'Pendiente')

    @property
    def req_desarrollo(self):
        """Requerimiento de Gestión de Desarrollo enlazado (None si no tiene)."""
        try:
            return self.requerimiento
        except Exception:
            return None

    # <--- hecho por claude code: pausa del SLA ────────────────────────────────────────
    @property
    def en_espera(self):
        # <--- hecho por claude code: cualquier estado que pausa el SLA
        return (self.status or '').strip() in ESTADOS_PAUSA

    @property
    def pausa_abierta(self):
        """La pausa vigente (sin cerrar), o None."""
        return self.pausas_sla.filter(fin__isnull=True).order_by('-inicio').first()

    @property
    def sla_pausado(self):
        return self.en_espera and self.pausa_abierta is not None

    @property
    def fuera_horario(self):
        # <--- hecho por claude code: SLA abierto y NO pausado por espera, pero fuera de la
        # ventana laboral → el tiempo no avanza (el motor solo cuenta horas laborales).
        if self.cerrado or self.sla_pausado:
            return False
        return not en_horario_laboral()

    @property
    def fuera_horario_texto(self):
        pa = proxima_apertura()
        if not pa:
            return ''
        from django.utils import timezone as _tz
        hoy = _tz.localdate()
        cuando = 'hoy' if pa.date() == hoy else ('mañana' if (pa.date() - hoy).days == 1 else pa.strftime('el %d/%m'))
        return f'Fuera de horario laboral — el SLA continúa {cuando} a las {pa.strftime("%H:%M")}'

    @property
    def sla_restante_min(self):
        """Minutos LABORALES que faltan para vencer (0 si ya venció). None si no aplica."""
        if self.sin_sla or not self.vence_en or self.cerrado:
            return None
        # Pausado: el restante queda CONGELADO en el valor que tenía al iniciar la pausa.
        if self.sla_pausado:
            return minutos_laborales_entre(self.pausa_abierta.inicio, self.vence_en)
        return minutos_laborales_entre(timezone.now(), self.vence_en)

    @property
    def sla_estado(self):
        """cumplido / incumplido (cerrado) · pausado · a_tiempo / por_vencer / vencido (abierto) · sin_sla."""
        if self.sin_sla:
            return 'sin_sla'
        if self.cerrado:
            if self.vence_en and self.resuelto_en:
                return 'cumplido' if self.resuelto_en <= self.vence_en else 'incumplido'
            return 'cumplido'
        # <--- hecho por claude code: en espera → SLA pausado, NUNCA vencido
        if self.sla_pausado:
            return 'pausado'
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
        if est == 'sin_sla':
            return 'Sin SLA (desarrollo)'
        if est == 'cumplido':
            return 'Cumplido'
        if est == 'incumplido':
            return 'Incumplido'
        if est == 'pausado':
            return f'SLA pausado — {self.status}'
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

    # <--- hecho por claude code (30-sep-2026): los mensajes de sistema se pintan como burbuja (no como línea larga).
    # Devuelve {'clase': pausa|ok|info, 'titulo': str, 'lineas': [str]} a partir del texto guardado.
    @property
    def sistema_partes(self):
        m = (self.mensaje or '').strip()
        clase = 'info'
        if m.startswith('⏸️') or '«En espera del usuario»' in m or '«Incompleto»' in m:
            clase = 'pausa'
        elif m.startswith('✅') or 'Resuelto' in m or 'PRODUCCIÓN' in m or 'reanud' in m.lower():
            clase = 'ok'
        m = m.lstrip('⏸️✅▶️ ').strip()
        titulo, lineas = m, []
        for sep in (' Motivo: ', ' Se solicita: '):
            if sep in titulo:
                titulo, resto = titulo.split(sep, 1)
                lineas.append(sep.strip() + ' ' + resto)
        # "Motivo: X. Se solicita: Y" quedó partido: la 2ª línea puede venir dentro de la 1ª
        out = []
        for l in lineas:
            if ' Se solicita: ' in l:
                a, b = l.split(' Se solicita: ', 1); out += [a.rstrip('. '), 'Se solicita: ' + b]
            else:
                out.append(l)
        return {'clase': clase, 'titulo': titulo.rstrip('. '), 'lineas': out}

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


# <--- hecho por claude code: historial COMPLETO de pausas del SLA (varias por ticket).
# Nunca se sobrescribe una pausa anterior; cada entrada/salida de "En espera" es una fila.
class TicketPausaSLA(AuditModel):
    VIA_CHOICES = (('tecnico', 'Reanudado por técnico'),
                   ('comentario', 'Reanudado por respuesta del usuario'))
    ticket        = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='pausas_sla')
    inicio        = models.DateTimeField("Inicio de la pausa", default=timezone.now)
    fin           = models.DateTimeField("Fin de la pausa", null=True, blank=True)
    motivo        = models.CharField("Motivo de la espera", max_length=300)
    info_requerida = models.TextField("Información/acción requerida al usuario")
    tecnico       = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='+', verbose_name="Técnico que la inició")
    reanudado_por = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='+', verbose_name="Quién reanudó")
    reanudado_via = models.CharField(max_length=12, choices=VIA_CHOICES, blank=True)
    minutos_laborales = models.PositiveIntegerField("Minutos laborales pausados", default=0)

    class Meta:
        db_table = 'tickets_pausa_sla'
        ordering = ['inicio']
        verbose_name = 'Pausa de SLA'
        verbose_name_plural = 'Pausas de SLA'
        constraints = [
            # <--- hecho por claude code: como mucho UNA pausa abierta (fin NULL) por ticket
            models.UniqueConstraint(fields=['ticket'], condition=models.Q(fin__isnull=True),
                                    name='una_pausa_abierta_por_ticket'),
        ]

    @property
    def abierta(self):
        return self.fin is None

    def __str__(self):
        return f'Pausa {self.ticket.ticket_id} · {self.inicio:%d/%m %H:%M}'
