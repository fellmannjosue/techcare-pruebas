from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .models import Ticket, TicketComment
from .forms import TicketForm, TicketCommentForm
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST, require_GET
import json
from threading import Thread

# IA pendiente para más adelante
# from core.utils_ai import consultar_ia

# 🔔 Notificaciones globales
from core.utils_notifications import crear_notificacion

PUBLIC_IMAGE_URL = ""


# ======================================================
# HELPER: notificar nuevo ticket a técnicos y superusers
# ======================================================
def _notificar_nuevo_ticket(ticket, usuario_solicitante=None):
    User = get_user_model()
    mensaje_staff = f"Nuevo ticket #{ticket.ticket_id} de {ticket.name} — {ticket.grade}"

    # Técnicos
    tecnicos = User.objects.filter(groups__name__icontains="tecnico")
    for tech in tecnicos:
        crear_notificacion(usuario=tech, mensaje=mensaje_staff, modulo="tickets", tipo="info", enviar_correo=False)

    # Superusuarios (excluyendo técnicos ya notificados)
    ids_tecnicos = set(tecnicos.values_list('id', flat=True))
    for su in User.objects.filter(is_superuser=True):
        if su.id not in ids_tecnicos:
            crear_notificacion(usuario=su, mensaje=mensaje_staff, modulo="tickets", tipo="info", enviar_correo=False)

    # Confirmación al solicitante
    if usuario_solicitante and usuario_solicitante.is_authenticated:
        crear_notificacion(
            usuario=usuario_solicitante,
            mensaje=f"Tu ticket #{ticket.ticket_id} ha sido recibido. Te atenderemos pronto.",
            modulo="tickets",
            tipo="exito",
            enviar_correo=False,
        )


# ======================================================
# ASYNC EMAIL
# ======================================================
def send_email_async(subject, message, recipient_list):
    Thread(
        target=send_mail,
        args=(subject, '', 'techcare.app2024@gmail.com', recipient_list),
        kwargs={'html_message': message, 'fail_silently': True},
        daemon=True,
    ).start()


def enviar_correo_ticket_resuelto(ticket):
    """Envía el historial del chat al usuario y al técnico cuando el ticket se resuelve."""
    comentarios = TicketComment.objects.filter(ticket=ticket).order_by('fecha')
    chat_conversacion = [
        {
            'autor': (c.usuario.get_full_name() or c.usuario.username) if c.usuario else 'Sistema',
            'fecha': c.fecha.strftime('%d/%m/%Y %H:%M'),
            'mensaje': c.mensaje,
        }
        for c in comentarios
    ]
    html_msg = render_to_string('tickets/email/ticket_update.html', {
        'ticket': ticket,
        'chat_conversacion': chat_conversacion,
    })
    asunto = f"Ticket #{ticket.ticket_id} – Resuelto"
    send_email_async(asunto, html_msg, [ticket.email])
    send_email_async(asunto, html_msg, ['techcare.app2024@gmail.com'])


# ======================================================
# 🔥 SUBMIT TICKET
# ======================================================
@csrf_exempt
def submit_ticket(request):
    User = get_user_model()

    if request.method == 'POST':

        # JSON request (API / chatbot / móvil)
        if request.headers.get('Content-Type') == 'application/json':
            try:
                data = json.loads(request.body)
                name = data.get('name')
                grade = data.get('grade')
                description = data.get('description')
                email = request.user.email if request.user.is_authenticated else data.get('email')

                if not all([name, grade, email, description]):
                    return JsonResponse({'error': 'Todos los campos son obligatorios'}, status=400)

                ticket = Ticket.objects.create(
                    name=name,
                    grade=grade,
                    email=email,
                    description=description,
                    usuario=request.user if request.user.is_authenticated else None
                )

                # 🔔 Notificaciones
                _notificar_nuevo_ticket(ticket, request.user)

                # 📧 Correos
                subject_technician = f'Nuevo Ticket #{ticket.ticket_id} - {ticket.name}'
                html_msg = render_to_string(
                    'tickets/email/email_notification.html',
                    {'ticket': ticket, 'img_url': PUBLIC_IMAGE_URL}
                )
                send_email_async(subject_technician, html_msg, ['techcare.app2024@gmail.com'])

                subject_user = f'Ticket #{ticket.ticket_id} - Confirmación de Recepción'
                send_email_async(subject_user, html_msg, [ticket.email])

                return JsonResponse({
                    'message': f'Ticket #{ticket.ticket_id} creado exitosamente',
                    'redirect_url': reverse('ticket_comments', args=[ticket.id]),
                }, status=201)

            except json.JSONDecodeError:
                return JsonResponse({'error': 'Error al procesar data JSON'}, status=400)

        # FORM request (web)
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)

            if request.user.is_authenticated:
                ticket.usuario = request.user
                ticket.email = request.user.email

            ticket.save()

            # 🔔 Notificaciones
            _notificar_nuevo_ticket(ticket, request.user)

            # 📧 Correos
            subject = f'Nuevo Ticket #{ticket.ticket_id} - {ticket.name}'
            html_msg = render_to_string(
                'tickets/email/email_notification.html',
                {'ticket': ticket, 'img_url': PUBLIC_IMAGE_URL}
            )
            send_email_async(subject, html_msg, ['techcare.app2024@gmail.com'])
            send_email_async(subject, html_msg, [ticket.email])

            return JsonResponse({
                'message': f'Ticket #{ticket.ticket_id} creado exitosamente',
                'redirect_url': reverse('ticket_comments', args=[ticket.id]),
            }, status=201)

        return JsonResponse({'error': 'Error en formulario', 'details': form.errors.as_json()}, status=400)

    form = TicketForm()
    return render(request, 'tickets/submit_ticket.html', {
        'form': form,
        'user_email': request.user.email if request.user.is_authenticated else ""
    })


# ======================================================
# DASHBOARD ADMINISTRACIÓN (tickets únicamente)
# ======================================================
@login_required
def dashboard_administracion(request):
    request.session['modo_tickets'] = 'admin'
    return render(request, 'tickets/dashboard_administracion.html')


@login_required
def mis_tickets(request):
    request.session['modo_tickets'] = 'admin'
    tickets = Ticket.objects.filter(usuario=request.user).order_by('-id')
    return render(request, 'tickets/mis_tickets.html', {'tickets': tickets})


# ======================================================
# DASHBOARD TÉCNICO
# ======================================================
@login_required
def technician_dashboard(request):
    tickets = Ticket.objects.all()
    return render(request, 'tickets/technician_dashboard.html', {'tickets': tickets})


# ======================================================
# 🔥 COMENTARIOS DE TICKET (CHAT HUMANO)
# ======================================================
@login_required
def ticket_comments(request, ticket_id):
    User = get_user_model()
    ticket = get_object_or_404(Ticket, id=ticket_id)
    comentarios = TicketComment.objects.filter(ticket=ticket).order_by('fecha')

    # MENSAJE AUTOMÁTICO INICIAL
    if not comentarios.exists():
        default_staff = User.objects.filter(is_staff=True).first() or User.objects.first()
        TicketComment.objects.create(
            ticket=ticket,
            usuario=default_staff,
            mensaje="Soporte técnico: ¿En qué podemos ayudarte?",
            tipo="tecnico"
        )

    status_resuelto = ticket.status.lower() == "resuelto"

    # POST → Nuevo comentario o cambio de estado
    if request.method == 'POST':
        new_status = request.POST.get("status")
        mensaje = request.POST.get("mensaje", "").strip()

        # -------------------- CAMBIO DE ESTADO --------------------
        if new_status and new_status != ticket.status:
            old_status = ticket.status
            ticket.status = new_status
            ticket.save()

            # Mensaje de sistema en el chat
            if new_status.lower() == "resuelto":
                msg_sistema = (
                    f"El técnico ha finalizado el ticket. "
                    f"Gracias y esté pendiente de su correo, ahí se enviará el historial de esta conversación."
                )
            else:
                msg_sistema = f"El técnico ha cambiado el estado de '{old_status}' a '{new_status}'."
            TicketComment.objects.create(ticket=ticket, usuario=None, mensaje=msg_sistema, tipo="sistema")

            # 🔔 Notificaciones por estado
            if new_status.lower() == "en proceso" and ticket.usuario:
                crear_notificacion(
                    usuario=ticket.usuario,
                    mensaje=f"Tu ticket #{ticket.ticket_id} está en proceso.",
                    modulo="tickets",
                    tipo="info",
                    enviar_correo=False,
                )

            if new_status.lower() == "resuelto":
                if ticket.usuario:
                    crear_notificacion(
                        usuario=ticket.usuario,
                        mensaje=f"Tu ticket #{ticket.ticket_id} ha sido resuelto.",
                        modulo="tickets",
                        tipo="exito",
                        enviar_correo=False,
                    )

                for tech in User.objects.filter(groups__name__icontains="tecnico"):
                    crear_notificacion(
                        usuario=tech,
                        mensaje=f"El ticket #{ticket.ticket_id} fue marcado como resuelto.",
                        modulo="tickets",
                        tipo="info",
                        enviar_correo=False,
                    )

                enviar_correo_ticket_resuelto(ticket)

        # -------------------- NUEVO COMENTARIO --------------------
        form = TicketCommentForm(request.POST)
        if form.is_valid() and mensaje:
            comentario = form.save(commit=False)
            comentario.ticket = ticket
            comentario.usuario = request.user
            comentario.tipo = "usuario" if not request.user.is_staff else "tecnico"
            comentario.save()

            # 🔔 Notificar según quién comenta
            if comentario.tipo == "usuario":
                for tech in User.objects.filter(groups__name__icontains="tecnico"):
                    crear_notificacion(
                        usuario=tech,
                        mensaje=f"Nuevo mensaje en ticket #{ticket.ticket_id} por {request.user.username}.",
                        modulo="tickets",
                        tipo="info",
                        enviar_correo=False,
                    )
            else:
                if ticket.usuario:
                    crear_notificacion(
                        usuario=ticket.usuario,
                        mensaje=f"Un técnico respondió en tu ticket #{ticket.ticket_id}.",
                        modulo="tickets",
                        tipo="info",
                        enviar_correo=False,
                    )

        return redirect('ticket_comments', ticket_id=ticket.id)

    form = TicketCommentForm()
    template = 'tickets/ticket_comments_tech.html' if request.user.is_staff else 'tickets/ticket_comments_user.html'

    if request.user.is_staff:
        sidebar_tickets = Ticket.objects.all().order_by('-id')[:60]
    else:
        sidebar_tickets = Ticket.objects.filter(usuario=request.user).order_by('-id')

    return render(request, template, {
        'ticket': ticket,
        'comentarios': comentarios,
        'form': form,
        'status_resuelto': status_resuelto,
        'sidebar_tickets': sidebar_tickets,
    })


# ======================================================
# AJAX → Render parcial de comentarios (GET)
# ======================================================
@login_required
def ticket_comments_ajax(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    comentarios = TicketComment.objects.filter(ticket=ticket).order_by('fecha')

    template = 'tickets/_comments_partial_tech.html' if request.user.is_staff else 'tickets/_comments_partial_user.html'
    html = render_to_string(template, {"comentarios": comentarios, "request": request})

    return JsonResponse({'html': html})


# ======================================================
# AJAX → Enviar comentario (POST)
# ======================================================
@require_POST
@login_required
def ticket_send_comment_ajax(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if ticket.status.lower() == "resuelto":
        return JsonResponse({"ok": False, "error": "Ticket cerrado"}, status=400)

    mensaje = request.POST.get("mensaje", "").strip()
    if not mensaje:
        return JsonResponse({"ok": False, "error": "Mensaje vacío"}, status=400)

    comentario = TicketComment.objects.create(
        ticket=ticket,
        usuario=request.user,
        mensaje=mensaje,
        tipo="usuario" if not request.user.is_staff else "tecnico"
    )

    # Notificaciones
    if comentario.tipo == "usuario":
        for tech in User.objects.filter(groups__name__icontains="tecnico"):
            crear_notificacion(
                usuario=tech,
                mensaje=f"Nuevo mensaje en ticket #{ticket.ticket_id} por {request.user.username}.",
                modulo="tickets",
                tipo="info"
            )
    else:
        if ticket.usuario:
            crear_notificacion(
                usuario=ticket.usuario,
                mensaje=f"Un técnico respondió en tu ticket #{ticket.ticket_id}.",
                modulo="tickets",
                tipo="info"
            )

    return JsonResponse({"ok": True})


# ======================================================
# AJAX → Actualizar estado
# ======================================================
@require_POST
@login_required
def ticket_status_update_ajax(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    new_status = (request.POST.get("status") or "").strip()
    comments = (request.POST.get("comments") or "").strip()

    if new_status not in ["Pendiente", "En Proceso", "Resuelto"]:
        return JsonResponse({"ok": False}, status=400)

    old_status = ticket.status
    if new_status != old_status:
        ticket.status = new_status
        ticket.comments = comments
        ticket.save()

        # Mensaje de sistema en el chat
        if new_status == "Resuelto":
            msg_sistema = (
                "El técnico ha finalizado el ticket. "
                "Gracias y esté pendiente de su correo, ahí se enviará el historial de esta conversación."
            )
        else:
            msg_sistema = f"El técnico ha cambiado el estado de '{old_status}' a '{new_status}'."
        TicketComment.objects.create(ticket=ticket, usuario=None, mensaje=msg_sistema, tipo="sistema")
    else:
        ticket.comments = comments
        ticket.save()

    # 🔔 Notificaciones
    if new_status == "En Proceso" and ticket.usuario:
        crear_notificacion(
            usuario=ticket.usuario,
            mensaje=f"Tu ticket #{ticket.ticket_id} está en proceso.",
            modulo="tickets",
            tipo="info",
            enviar_correo=False,
        )

    if new_status == "Resuelto":
        if ticket.usuario:
            crear_notificacion(
                usuario=ticket.usuario,
                mensaje=f"Tu ticket #{ticket.ticket_id} ha sido resuelto.",
                modulo="tickets",
                tipo="exito",
                enviar_correo=False,
            )
        enviar_correo_ticket_resuelto(ticket)

    return JsonResponse({"ok": True})


# ======================================================
# AJAX → Eliminar ticket
# ======================================================
@login_required
@require_POST
def ticket_eliminar_ajax(request, ticket_id):
    if not request.user.is_staff:
        return JsonResponse({"ok": False, "error": "Sin permiso"}, status=403)
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.delete()
    return JsonResponse({"ok": True})


# ======================================================
# AJAX → Obtener estado
# ======================================================
@require_GET
@login_required
def ticket_status_get_ajax(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    return JsonResponse({"status": ticket.status, "comments": ticket.comments})


# ======================================================
# AJAX → Reporte de ticket (GET) para modal
# ======================================================
@require_GET
@login_required
def ticket_reporte_ajax(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    comentarios = TicketComment.objects.filter(ticket=ticket).order_by('fecha')
    return JsonResponse({
        'ticket_id': ticket.ticket_id,
        'name': ticket.name,
        'grade': ticket.grade,
        'email': ticket.email,
        'description': ticket.description,
        'status': ticket.status,
        'created_at': ticket.created_at.strftime('%d/%m/%Y %H:%M'),
        'attachment_url': ticket.attachment.url if ticket.attachment else None,
        'chat_url': reverse('ticket_comments', args=[ticket.id]),
        'chat': [
            {
                'autor': c.usuario.get_full_name() or c.usuario.username if c.usuario else 'Sistema',
                'fecha': c.fecha.strftime('%d/%m/%Y %H:%M'),
                'mensaje': c.mensaje,
                'tipo': c.tipo,
            }
            for c in comentarios
        ],
    })


# ======================================================
# IA pendiente para más adelante
# BOTÓN: "NO ME AYUDÓ, CONTACTAR TÉCNICO"
# ======================================================
"""
@require_POST
@login_required
def ticket_contact_technician(request, ticket_id):
    User = get_user_model()
    ticket = get_object_or_404(Ticket, id=ticket_id)

    ticket.ia_bloqueada = True
    ticket.save()

    mensaje_ia = (
        "Gracias por tu consulta. "
        "Ahora te pasaré con un técnico humano para continuar asistiendo tu ticket."
    )

    TicketComment.objects.create(
        ticket=ticket,
        usuario=None,
        mensaje=mensaje_ia,
        tipo="ia"
    )

    tecnicos = User.objects.filter(groups__name__icontains="tecnico")
    for tech in tecnicos:
        crear_notificacion(
            usuario=tech,
            mensaje=f"El usuario solicita asistencia humana en el ticket #{ticket.ticket_id}.",
            modulo="tickets",
            tipo="alerta"
        )

    return JsonResponse({"ok": True})
"""


# ======================================================
# IA pendiente para más adelante
# CHAT IA
# ======================================================
"""
@csrf_exempt
@require_POST
@login_required
def ticket_chat_ai_ajax(request, ticket_id):
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)

        if ticket.ia_bloqueada:
            return JsonResponse({
                "ok": False,
                "error": "La IA está bloqueada en este ticket. Un técnico continuará la atención."
            }, status=403)

        mensaje_usuario = request.POST.get("mensaje", "").strip()
        if not mensaje_usuario:
            return JsonResponse({"ok": False, "error": "Mensaje vacío"}, status=400)

        comentario_user = TicketComment.objects.create(
            ticket=ticket,
            usuario=request.user,
            mensaje=mensaje_usuario,
            tipo="usuario"
        )

        mensajes_ia = [
            {"role": "system", "content": "Eres un asistente técnico amigable y útil de ANA-HN."},
            {"role": "user", "content": mensaje_usuario}
        ]

        respuesta_ia = consultar_ia(mensajes_ia)

        comentario_ai = TicketComment.objects.create(
            ticket=ticket,
            usuario=None,
            mensaje=respuesta_ia,
            tipo="ia"
        )

        return JsonResponse({
            "ok": True,
            "mensaje_usuario": {
                "id": comentario_user.id,
                "mensaje": comentario_user.mensaje,
                "fecha": comentario_user.fecha.strftime("%d/%m/%Y %H:%M"),
                "autor": request.user.username,
                "tipo": "usuario",
            },
            "mensaje_ia": {
                "id": comentario_ai.id,
                "mensaje": comentario_ai.mensaje,
                "fecha": comentario_ai.fecha.strftime("%d/%m/%Y %H:%M"),
                "autor": "IA TechCare",
                "tipo": "ia",
            }
        })

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
"""