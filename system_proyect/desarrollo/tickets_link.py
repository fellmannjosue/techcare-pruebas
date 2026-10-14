# <--- hecho por claude code (29-sep-2026): vínculo Gestión de Desarrollo ↔ Sistema de Tickets.
# Reglas acordadas con el usuario:
#   · el ticket que nace de un requerimiento NO lleva SLA y queda asignado al responsable (fuera de la cola de técnicos);
#   · sincronización en UNA dirección: el requerimiento manda el estado del ticket;
#   · un ticket existente se puede CONVERTIR en requerimiento (no se cierra: queda enlazado y sigue al requerimiento);
#   · los requerimientos ya existentes pueden abrir su ticket con un botón.
from django.db import transaction
from django.utils import timezone

from tickets.models import Ticket, TicketComment

from .models import RequerimientoDesarrollo, HistorialRequerimiento, EstadoReq, Urgencia, TipoReq

# Estado del requerimiento → estado del ticket
ESTADO_TICKET = {
    EstadoReq.RECIBIDO: 'Pendiente', EstadoReq.EVALUACION: 'Pendiente', EstadoReq.PENDIENTE_APROB: 'Pendiente',
    EstadoReq.APROBADO: 'En Proceso', EstadoReq.PLANIFICADO: 'En Proceso', EstadoReq.DESARROLLO: 'En Proceso',
    EstadoReq.PRUEBAS: 'En Proceso', EstadoReq.LISTO_PROD: 'En Proceso',
    EstadoReq.PAUSADO: 'En espera del usuario',
    EstadoReq.PRODUCCION: 'Resuelto',
    EstadoReq.CANCELADO: 'Cerrado', EstadoReq.RECHAZADO: 'Cerrado',
}
URGENCIA_TICKET = {Urgencia.URGENTE: 'urgente', Urgencia.NORMAL: 'medio', Urgencia.ESPERAR: 'bajo'}
URGENCIA_REQ = {'urgente': Urgencia.URGENTE, 'alto': Urgencia.URGENTE, 'medio': Urgencia.NORMAL, 'bajo': Urgencia.ESPERAR}


def _nombre(user, respaldo=''):
    if not user:
        return respaldo or 'Sin solicitante'
    return (user.get_full_name() or user.username or respaldo).strip()


def _comentario_sistema(ticket, mensaje, usuario=None):
    TicketComment.objects.create(ticket=ticket, usuario=usuario, mensaje=mensaje, tipo='sistema')


def _correo_estado(ticket, titulo, mensaje):
    """Correo al solicitante reutilizando la plantilla de cambio de estado de Tickets (nunca rompe el flujo)."""
    try:
        from tickets.views import enviar_correo_estado
        enviar_correo_estado(ticket, titulo, mensaje)
    except Exception:
        pass


def _notificar_responsable(req, mensaje):
    if req.responsable_id:
        try:
            from core.utils_notifications import crear_notificacion
            crear_notificacion(req.responsable, mensaje, 'desarrollo', tipo='info')
        except Exception:
            pass


@transaction.atomic
def abrir_ticket(req, usuario):
    """Crea el ticket de un requerimiento (si no lo tiene) y lo deja enlazado. Devuelve (ticket, creado)."""
    if req.ticket_id:
        return req.ticket, False
    sol = req.solicitante
    nombre = _nombre(sol, getattr(req.solicitante_cat, 'nombre', '') if req.solicitante_cat_id else '')
    partes = [f'[{req.codigo}] {req.titulo}']
    if req.descripcion:
        partes.append(req.descripcion.strip())
    if req.problema_actual:
        partes.append('Problema actual: ' + req.problema_actual.strip())
    if req.resultado_esperado:
        partes.append('Resultado esperado: ' + req.resultado_esperado.strip())
    t = Ticket(usuario=sol, name=nombre[:255], grade=(req.area or 'Desarrollo')[:255],
               email=(getattr(sol, 'email', '') or '')[:255], description='\n\n'.join(partes),
               status=ESTADO_TICKET.get(req.estado, 'Pendiente'),
               urgencia=URGENCIA_TICKET.get(req.urgencia, 'medio'),
               sin_sla=True, asignado_a=req.responsable, creado_por=usuario, modificado_por=usuario)
    t.save()
    _comentario_sistema(t, f'Ticket abierto desde el requerimiento {req.codigo} ({req.get_estado_display()}). '
                           f'El avance se actualiza aquí automáticamente.', usuario)
    req.ticket = t
    req.save(update_fields=['ticket'])
    HistorialRequerimiento.objects.create(requerimiento=req, usuario=usuario, estado_anterior=req.estado,
                                          estado_nuevo=req.estado, comentario=f'Ticket {t.ticket_id} abierto')
    _correo_estado(t, f'Ticket {t.ticket_id} abierto', f'Se registró tu requerimiento {req.codigo}: {req.titulo}. '
                                                     f'Por este ticket recibirás el avance.')
    _notificar_responsable(req, f'Ticket {t.ticket_id} abierto para el requerimiento {req.codigo}.')
    return t, True


def sincronizar_ticket(req, usuario=None):
    """El requerimiento manda: lleva su estado (y su responsable) al ticket enlazado. Devuelve True si cambió algo."""
    if not req.ticket_id:
        return False
    t = req.ticket
    nuevo = ESTADO_TICKET.get(req.estado, t.status)
    cambios = []
    if t.asignado_a_id != req.responsable_id:
        t.asignado_a = req.responsable
        cambios.append('asignado')
    if nuevo != t.status:
        t.status = nuevo
        cambios.append('estado')
    if not cambios:
        return False
    t.modificado_por = usuario
    t.save()
    if 'estado' in cambios:
        if req.estado == EstadoReq.PRODUCCION:
            # El desarrollo terminó: el ticket se CIERRA (Resuelto = estado final del Sistema de Tickets: chat bloqueado)
            ver = f' (versión {req.version_implementada})' if req.version_implementada else ''
            _comentario_sistema(t, f'✅ El requerimiento {req.codigo} ya está en PRODUCCIÓN{ver}. El desarrollo terminó y este ticket queda cerrado.', usuario)
            _correo_estado(t, f'Ticket {t.ticket_id} cerrado: tu requerimiento ya está en producción',
                           f'Tu requerimiento {req.codigo} ({req.titulo}) terminó de desarrollarse y ya está en producción{ver}. El ticket queda cerrado.')
        else:
            _comentario_sistema(t, f'El requerimiento {req.codigo} pasó a "{req.get_estado_display()}" → ticket {nuevo}.', usuario)
            _correo_estado(t, f'Ticket {t.ticket_id}: {nuevo}',
                           f'Tu requerimiento {req.codigo} ({req.titulo}) pasó a "{req.get_estado_display()}".')
    return True


@transaction.atomic
def convertir_ticket_en_requerimiento(ticket, usuario):
    """Crea un requerimiento a partir de un ticket y los enlaza. El ticket NO se cierra: pasa a seguir al requerimiento."""
    existente = ticket.req_desarrollo
    if existente:
        return existente, False
    lineas = [l.strip() for l in (ticket.description or '').splitlines() if l.strip()]
    titulo = (lineas[0] if lineas else f'Ticket {ticket.ticket_id}')[:200]
    req = RequerimientoDesarrollo(
        titulo=titulo, descripcion=ticket.description or '', problema_actual=ticket.description or '',
        solicitante=ticket.usuario, area=(ticket.grade or '')[:60], tipo=TipoReq.MEJORA,
        urgencia=URGENCIA_REQ.get(ticket.urgencia, Urgencia.NORMAL), estado=EstadoReq.RECIBIDO,
        fecha_solicitud=timezone.now().date(), observaciones=f'Creado desde el ticket {ticket.ticket_id}.',
        ticket=ticket, creado_por=usuario, modificado_por=usuario)
    req.save()
    HistorialRequerimiento.objects.create(requerimiento=req, usuario=usuario, estado_anterior='',
                                          estado_nuevo=EstadoReq.RECIBIDO,
                                          comentario=f'Creado desde el ticket {ticket.ticket_id}')
    ticket.sin_sla = True
    ticket.asignado_a = req.responsable
    ticket.status = ESTADO_TICKET[EstadoReq.RECIBIDO]
    ticket.modificado_por = usuario
    ticket.save()
    _comentario_sistema(ticket, f'Este ticket se convirtió en el requerimiento de desarrollo {req.codigo}. '
                                f'Deja de contar SLA y su estado seguirá el avance del requerimiento.', usuario)
    _correo_estado(ticket, f'Ticket {ticket.ticket_id} → requerimiento {req.codigo}',
                   'Tu solicitud se registró como requerimiento de desarrollo. Por este ticket recibirás el avance.')
    return req, True
