# ============================================
#  core/hooks.py – Sistema unificado de notificaciones TechCare
# ============================================

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

from core.utils_notifications import crear_notificacion


# ============================================================
# 🔵 UTILIDAD GENERAL: Enviar correo de forma segura
# ============================================================
def enviar_correo(subject, message, recipient):
    """
    Envía correos del sistema TechCare sin interrumpir el flujo
    en caso de error (fail_silently=True).
    """
    if not recipient:
        return

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=True
    )


# ============================================================
# 🔴 MÓDULO TICKETS
# ============================================================

def notify_ticket_creado(ticket, tecnico):
    """
    Notifica al técnico responsable que un ticket nuevo ha sido creado.
    """
    mensaje = f"Nuevo ticket #{ticket.ticket_id} creado por {ticket.name}"

    crear_notificacion(
        usuario=tecnico,
        mensaje=mensaje,
        modulo="tickets",
        tipo="alerta",
        extra={"ticket_id": ticket.ticket_id}
    )

    enviar_correo(
        subject="Nuevo Ticket Creado",
        message=f"Ticket #{ticket.ticket_id}\n\nDescripción:\n{ticket.description}",
        recipient=tecnico.email
    )


def notify_ticket_escalado(ticket, tecnico):
    """
    Notifica al técnico cuando el usuario presiona:
    “No me ayudó, contactar técnico”.
    """
    mensaje = f"El ticket #{ticket.ticket_id} requiere asistencia humana"

    crear_notificacion(
        usuario=tecnico,
        mensaje=mensaje,
        modulo="tickets",
        tipo="alerta",
        extra={"ticket_id": ticket.ticket_id}
    )


def notify_ticket_cerrado(ticket, usuario):
    """
    Notifica al usuario que su ticket ha sido resuelto.
    """
    mensaje = f"Tu ticket #{ticket.ticket_id} ha sido marcado como Resuelto."

    crear_notificacion(
        usuario=usuario,
        mensaje=mensaje,
        modulo="tickets",
        tipo="exito",
        extra={"ticket_id": ticket.ticket_id}
    )

    enviar_correo(
        subject="Ticket Resuelto",
        message=f"Tu ticket #{ticket.ticket_id} ha sido cerrado.",
        recipient=usuario.email
    )


# ============================================================
# 🔵 MÓDULO COORDINACIÓN – Colegio
# ============================================================

def notify_colegio_reporte(reporte, coordinador):
    """
    Notifica cuando un maestro crea un reporte informativo o conductual.
    """
    tipo = "Conductual" if reporte.tipo == "conductual" else "Informativo"
    mensaje = f"Nuevo reporte {tipo} del maestro {reporte.maestro}"

    crear_notificacion(
        usuario=coordinador,
        mensaje=mensaje,
        modulo="coordinacion_col",
        tipo="alerta",
        extra={"reporte_id": reporte.id}
    )


# ============================================================
# 🔵 MÓDULO COORDINACIÓN – Bilingüe
# ============================================================

def notify_bilingue_reporte(reporte, coordinador):
    """
    Notifica reportes Informativos / Conductuales del área bilingüe.
    """
    tipo = reporte.tipo.capitalize()
    mensaje = f"Nuevo reporte {tipo} del maestro {reporte.maestro}"

    crear_notificacion(
        usuario=coordinador,
        mensaje=mensaje,
        modulo="coordinacion_bl",
        tipo="alerta",
        extra={"reporte_id": reporte.id}
    )


def notify_progress_report(report, coordinador):
    """
    Notifica cuando un maestro crea un Progress Report.
    """
    mensaje = f"Nuevo Progress Report creado por {report.teacher}"

    crear_notificacion(
        usuario=coordinador,
        mensaje=mensaje,
        modulo="progress_report",
        tipo="info",
        extra={"report_id": report.id}
    )


# ============================================================
# 🔵 MÓDULO RELOJ – Compensatorio / Permisos
# ============================================================

def notify_compensatorio(admin_usuario, empleado):
    """
    Notifica cuando un usuario registra tiempo compensatorio.
    """
    mensaje = f"{empleado.first_name} registró un tiempo compensatorio."

    crear_notificacion(
        usuario=admin_usuario,
        mensaje=mensaje,
        modulo="reloj",
        tipo="info"
    )


def notify_permiso(admin_usuario, empleado):
    """
    Notifica cuando un empleado ingresa un permiso.
    """
    mensaje = f"{empleado.first_name} ha solicitado un permiso."

    crear_notificacion(
        usuario=admin_usuario,
        mensaje=mensaje,
        modulo="reloj",
        tipo="alerta"
    )

