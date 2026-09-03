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
from core.utils_ai import consultar_ia  # <--- hecho por claude code: chat IA activo en pruebas

# 🔔 Notificaciones globales
from core.utils_notifications import crear_notificacion

PUBLIC_IMAGE_URL = ""


def _es_gestor_tickets(user):
    """<--- hecho por claude code: 'gestor/técnico de tickets' = superusuario, con permiso
    tickets.view_ticket, o en un grupo de técnicos. NO se basa en is_staff: el grupo
    'administracion' es is_staff pero NO gestiona tickets — solo debe ver los SUYOS, como
    un usuario normal (antes veía todos por usar is_staff en la vista de chat)."""
    return bool(
        getattr(user, 'is_authenticated', False) and (
            user.is_superuser
            or user.has_perm('tickets.view_ticket')
            or user.groups.filter(name__icontains='tecnico').exists()
        )
    )


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
def _tickets_extra_recipients():
    """Usuarios con toggle 'tickets' activo en DestinatarioEmail."""
    try:
        from accounts.models import DestinatarioEmail
        return list(DestinatarioEmail.objects
                    .filter(tickets=True)
                    .exclude(user__email='')
                    .values_list('user__email', flat=True))
    except Exception:
        return []

def send_email_async(subject, message, recipient_list):
    Thread(
        target=send_mail,
        args=(subject, '', 'techcare.app2024@gmail.com', recipient_list),
        kwargs={'html_message': message, 'fail_silently': True},
        daemon=True,
    ).start()

def _send_tickets_notif(subject, html_msg):
    """Envía notificación al Gmail fijo + usuarios con tickets toggle activo."""
    fixed = ['techcare.app2024@gmail.com']
    extras = _tickets_extra_recipients()
    all_to = list(set(fixed + extras))
    send_email_async(subject, html_msg, all_to)


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
    _send_tickets_notif(asunto, html_msg)


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
                    urgencia=(data.get('urgencia') or 'medio'),  # <--- hecho por claude code
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
                _send_tickets_notif(subject_technician, html_msg)

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
            _send_tickets_notif(subject, html_msg)
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
    # <--- hecho por claude code: antes cualquier usuario logueado veía TODOS los tickets del sistema
    if not (request.user.is_superuser or request.user.has_perm('tickets.view_ticket')):
        return redirect('dashboard_administracion')
    tickets = Ticket.objects.all()
    return render(request, 'tickets/technician_dashboard.html', {'tickets': tickets})


# <--- hecho por claude code: tickets SIN ATENDER (Nuevo/Pendiente) para la alerta cada 10 min
@login_required
def tickets_sin_atender_ajax(request):
    if not _es_gestor_tickets(request.user):
        return JsonResponse({'ok': False, 'count': 0, 'tickets': []})
    from django.utils import timezone
    from .sla import minutos_laborales_entre
    qs = Ticket.objects.filter(status__in=['Nuevo', 'Pendiente']).order_by('created_at')
    data = []
    ahora = timezone.now()
    for t in qs:
        data.append({
            'id': t.id,
            'ticket_id': t.ticket_id,
            'name': t.name,
            'urgencia': t.urgencia,
            'espera_min': (minutos_laborales_entre(t.created_at, ahora) if t.created_at else 0),
            'vencido': t.sla_estado == 'vencido',
        })
    return JsonResponse({'ok': True, 'count': len(data), 'tickets': data})


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
            comentario.tipo = "usuario" if not _es_gestor_tickets(request.user) else "tecnico"
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
    template = 'tickets/ticket_comments_tech.html' if _es_gestor_tickets(request.user) else 'tickets/ticket_comments_user.html'

    if _es_gestor_tickets(request.user):
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

    template = 'tickets/_comments_partial_tech.html' if _es_gestor_tickets(request.user) else 'tickets/_comments_partial_user.html'
    html = render_to_string(template, {"comentarios": comentarios, "request": request})

    return JsonResponse({'html': html})


# ======================================================
# AJAX → Enviar comentario (POST)
# ======================================================
@require_POST
@login_required
def ticket_send_comment_ajax(request, ticket_id):
    User = get_user_model()
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if ticket.status.lower() == "resuelto":
        return JsonResponse({"ok": False, "error": "Ticket cerrado"}, status=400)

    mensaje = request.POST.get("mensaje", "").strip()
    archivo = request.FILES.get("archivo")
    if not mensaje and not archivo:
        return JsonResponse({"ok": False, "error": "Mensaje vacío"}, status=400)

    # Límite de tamaño: 15 MB
    if archivo and archivo.size > 15 * 1024 * 1024:
        return JsonResponse({"ok": False, "error": "El archivo supera el límite de 15 MB"}, status=400)

    comentario = TicketComment.objects.create(
        ticket=ticket,
        usuario=request.user,
        mensaje=mensaje,
        archivo=archivo,
        tipo="usuario" if not _es_gestor_tickets(request.user) else "tecnico"
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
    if not _es_gestor_tickets(request.user):
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
# CHAT IA — <--- hecho por claude code: ACTIVADO en pruebas
# ======================================================
def _pide_tecnico(texto):
    """<--- hecho por claude code: detecta que el usuario quiere atención HUMANA.
    Normaliza tildes para que "técnico" y "tecnico" cuenten igual."""
    import unicodedata
    t = unicodedata.normalize('NFKD', (texto or '').lower())
    t = ''.join(ch for ch in t if not unicodedata.combining(ch))
    if 'tecnico' in t and any(v in t for v in (
            'hablar', 'quiero', 'necesito', 'llama', 'contactar', 'comunicar',
            'atienda', 'pasame', 'con un', 'con el')):
        return True
    return any(f in t for f in ('hablar con una persona', 'hablar con alguien',
                                'atencion humana', 'una persona real', 'un humano'))


def _escalar_a_tecnico(ticket, solicitante):
    """<--- hecho por claude code: notifica a técnicos y superusers, deja el ticket
    pendiente de atención humana y APAGA la IA de este ticket (ia_bloqueada)."""
    User = get_user_model()
    msg = f"🔔 {ticket.name} pide hablar con un TÉCNICO en el ticket #{ticket.ticket_id} — {ticket.grade}"
    tecnicos = User.objects.filter(groups__name__icontains="tecnico")
    for tech in tecnicos:
        crear_notificacion(usuario=tech, mensaje=msg, modulo="tickets", tipo="alerta", enviar_correo=False)
    ids = set(tecnicos.values_list('id', flat=True))
    for su in User.objects.filter(is_superuser=True):
        if su.id not in ids:
            crear_notificacion(usuario=su, mensaje=msg, modulo="tickets", tipo="alerta", enviar_correo=False)
    ticket.ia_bloqueada = True
    campos = ['ia_bloqueada']
    if (ticket.status or '').lower() in ('completado', 'cerrado', 'resuelto'):
        ticket.status = 'Pendiente'   # el ticket se REABRE para el técnico
        campos.append('status')
    ticket.save(update_fields=campos)


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

        # <--- hecho por claude code: "hablar con técnico" → notifica, reabre si hacía
        # falta, y la IA TERMINA en este ticket (el guard de arriba bloquea lo siguiente).
        if _pide_tecnico(mensaje_usuario):
            _escalar_a_tecnico(ticket, request.user)
            comentario_ai = TicketComment.objects.create(
                ticket=ticket, usuario=None, tipo="sistema",
                mensaje=("🔔 Un técnico ha sido notificado y continuará la atención en este "
                         "ticket. El asistente de IA finaliza aquí — gracias por tu paciencia."))
        else:
            mensajes_ia = [
                {"role": "system", "content": (
                    "Eres un asistente técnico amigable y útil de ANA-HN. Responde en español, "
                    "breve y claro. Si el problema requiere intervención física o no puedes "
                    "resolverlo, sugiérele al usuario escribir 'hablar con técnico' para que "
                    "lo atienda una persona.")},
                {"role": "user", "content": mensaje_usuario}
            ]

            respuesta_ia = consultar_ia(mensajes_ia)

            comentario_ai = TicketComment.objects.create(
                ticket=ticket,
                usuario=None,
                mensaje=respuesta_ia or "No pude generar respuesta. Escribe 'hablar con técnico' para atención humana.",
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
                "autor": "Sistema" if comentario_ai.tipo == "sistema" else "IA TechCare",
                "tipo": comentario_ai.tipo,
                "ia_finalizada": ticket.ia_bloqueada,
            }
        })

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ======================================================
# <--- hecho por claude code: SANDBOX de IA (solo pruebas). No guarda NADA en la base
# (este contenedor apunta a las mismas BD del servidor): pregunta → OpenAI → respuesta.
# ======================================================
@login_required
def ia_sandbox(request):
    if not request.user.is_superuser:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, "tickets/ia_sandbox.html")


@require_POST
@login_required
def ia_sandbox_ajax(request):
    if not request.user.is_superuser:
        return JsonResponse({"ok": False, "error": "Solo superusuario"}, status=403)
    mensaje = (request.POST.get("mensaje") or "").strip()
    if not mensaje:
        return JsonResponse({"ok": False, "error": "Escribe un mensaje"}, status=400)

    # <--- hecho por claude code: el front manda el historial → la IA tiene MEMORIA de la
    # conversación, y si el usuario pide un técnico se crea un TICKET REAL con la transcripción.
    import json as _json
    try:
        historial = _json.loads(request.POST.get("historial") or "[]")[-12:]
        historial = [{"role": h["role"], "content": str(h["content"])[:2000]}
                     for h in historial if h.get("role") in ("user", "assistant")]
    except Exception:
        historial = []

    if _pide_tecnico(mensaje):
        transcripcion = "\n".join(
            f"{'Usuario' if h['role'] == 'user' else 'IA'}: {h['content']}" for h in historial)
        u = request.user
        ticket = Ticket.objects.create(
            usuario=u,
            name=(u.get_full_name() or u.username),
            grade="Chat IA",
            email=(u.email or ""),
            description=("Solicitud de atención con un TÉCNICO desde el chat de IA.\n\n"
                         f"Último mensaje: {mensaje}\n\n— Transcripción del chat —\n"
                         + (transcripcion or "(sin historial)")),
            urgencia="medio",
            ia_bloqueada=True,   # nace escalado: la IA ya terminó aquí
        )
        _notificar_nuevo_ticket(ticket, u)
        return JsonResponse({"ok": True, "escalado": True, "ticket_id": ticket.ticket_id,
                             "respuesta": (f"🔔 Listo: creé el ticket {ticket.ticket_id} con el resumen "
                                           "de esta conversación y ya notifiqué a un técnico. Te "
                                           "atenderán pronto — puedes darle seguimiento en «Mis "
                                           "tickets». El asistente de IA finaliza aquí.")})

    try:
        mensajes = [{"role": "system", "content": (
            "Eres un asistente técnico amigable y útil de ANA-HN. Responde en español, breve y "
            "claro. Si no puedes resolver el problema, sugiérele al usuario escribir "
            "'hablar con técnico' para crear un ticket y que lo atienda una persona.")}]
        mensajes += historial + [{"role": "user", "content": mensaje}]
        respuesta = consultar_ia(mensajes)
        return JsonResponse({"ok": True, "respuesta": respuesta or "No pude generar respuesta."})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
