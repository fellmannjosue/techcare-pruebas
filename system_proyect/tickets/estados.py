# <--- hecho por claude code: lógica CENTRALIZADA de "En espera del usuario" (pausa de SLA).
# Reutiliza el motor de sla.py (minutos_laborales_entre); no duplica cálculo de vencimiento.
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Ticket, TicketComment, TicketPausaSLA, ESTADO_ESPERA, ESTADO_INCOMPLETO, ESTADOS_PAUSA
from .sla import minutos_laborales_entre


def _es_gestor(user):
    return bool(user and user.is_authenticated and (
        user.is_superuser or user.has_perm('tickets.view_ticket')
        or user.groups.filter(name__icontains='tecnico').exists()))


@transaction.atomic
def poner_en_pausa(ticket, tecnico, motivo, info_requerida, nuevo_estado=ESTADO_ESPERA):
    """Pone el ticket en un estado de PAUSA (En espera del usuario / Incompleto) y detiene el
    SLA. Solo técnicos/admin. 'En espera' exige motivo+info; 'Incompleto' usa un motivo por
    defecto si no se da."""
    if not _es_gestor(tecnico):
        raise PermissionDenied('Solo técnicos o administradores pueden pausar el ticket.')
    if ticket.cerrado:
        raise ValidationError('El ticket está cerrado.')
    if nuevo_estado not in ESTADOS_PAUSA:
        raise ValidationError('Estado de pausa inválido.')
    motivo = (motivo or '').strip()
    info = (info_requerida or '').strip()
    if nuevo_estado == ESTADO_ESPERA and (not motivo or not info):
        raise ValidationError('Debes indicar el motivo y la información requerida al usuario.')
    if nuevo_estado == ESTADO_INCOMPLETO:
        motivo = motivo or 'Ticket marcado como incompleto'
        info = info or 'Falta información o pasos para continuar.'

    ticket_locked = Ticket.objects.select_for_update().get(pk=ticket.pk)
    # Si ya venía de otra pausa, se cierra primero (acumula su tiempo) para no duplicar.
    if ticket_locked.pausas_sla.filter(fin__isnull=True).exists():
        reanudar(ticket_locked, tecnico, via='tecnico', restaurar_estado=False)
        ticket_locked.refresh_from_db()

    TicketPausaSLA.objects.create(
        ticket=ticket_locked, inicio=timezone.now(),
        motivo=motivo, info_requerida=info, tecnico=tecnico)
    ticket_locked.status = nuevo_estado
    ticket_locked.save()

    TicketComment.objects.create(
        ticket=ticket_locked, usuario=None, tipo='sistema',
        mensaje=f'⏸️ Ticket puesto en «{nuevo_estado}» por {tecnico.get_full_name() or tecnico.username}. '
                f'Motivo: {motivo}. Se solicita: {info}')

    from core.utils_notifications import crear_notificacion
    if ticket_locked.usuario:
        crear_notificacion(
            usuario=ticket_locked.usuario,
            mensaje=(f'Tu ticket #{ticket_locked.ticket_id} está en espera de tu respuesta o '
                     'disponibilidad. Revisa el detalle para conocer la información requerida.'),
            modulo='tickets', tipo='advertencia', enviar_correo=False)
    # <--- hecho por claude code: correo al usuario con el motivo y lo que se le solicita
    from .views import enviar_correo_estado
    enviar_correo_estado(
        ticket_locked,
        'Tu ticket está en espera de tu respuesta',
        f'Soporte Técnico no puede continuar sin ti. Motivo: {motivo}.',
        info_requerida=info, color=('#e8590c', '#f76707'))
    return ticket_locked


# compatibilidad: el endpoint dedicado del botón usa este nombre
def poner_en_espera(ticket, tecnico, motivo, info_requerida):
    return poner_en_pausa(ticket, tecnico, motivo, info_requerida, ESTADO_ESPERA)


@transaction.atomic
def reanudar(ticket, quien, via='tecnico', restaurar_estado=True):
    """Cierra la pausa vigente, suma los minutos laborales pausados y vuelve a 'En Proceso'.
    via='tecnico' (botón) o 'comentario' (el usuario respondió)."""
    ticket_locked = Ticket.objects.select_for_update().get(pk=ticket.pk)
    pausa = ticket_locked.pausas_sla.filter(fin__isnull=True).order_by('-inicio').first()
    if pausa is None:
        raise ValidationError('El ticket no está en espera.')

    ahora = timezone.now()
    minutos = minutos_laborales_entre(pausa.inicio, ahora)
    pausa.fin = ahora
    pausa.reanudado_por = quien if getattr(quien, 'is_authenticated', False) else None
    pausa.reanudado_via = via
    pausa.minutos_laborales = minutos
    pausa.save(update_fields=['fin', 'reanudado_por', 'reanudado_via', 'minutos_laborales'])

    # Acumular la pausa y correr el vencimiento (el save() recalcula con sla_pausa_min).
    ticket_locked.sla_pausa_min = (ticket_locked.sla_pausa_min or 0) + minutos
    if restaurar_estado:
        ticket_locked.status = 'En Proceso'
    ticket_locked.save()

    quien_txt = (quien.get_full_name() or quien.username) if getattr(quien, 'is_authenticated', False) else 'el usuario'
    origen = 'por respuesta del usuario' if via == 'comentario' else f'por {quien_txt}'
    TicketComment.objects.create(
        ticket=ticket_locked, usuario=None, tipo='sistema',
        mensaje=f'▶️ Atención REANUDADA {origen}. El SLA continúa (estuvo pausado {minutos} min laborales).')

    from core.utils_notifications import crear_notificacion
    if ticket_locked.usuario and via == 'comentario':
        for tech in _tecnicos():
            crear_notificacion(
                usuario=tech,
                mensaje=f'El usuario respondió al ticket #{ticket_locked.ticket_id}. El tiempo de atención se ha reanudado.',
                modulo='tickets', tipo='info', enviar_correo=False)
    return ticket_locked


def _tecnicos():
    # <--- hecho por claude code: técnicos + superusers (como el aviso de ticket nuevo), para
    # que la notificación no se pierda si aún no hay nadie en el grupo 'tecnico'.
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    return get_user_model().objects.filter(
        Q(groups__name__icontains='tecnico') | Q(is_superuser=True)).distinct()
