from django.contrib.auth.decorators import login_not_required  # <--- hecho por claude code (seguridad 05-nov-2026): candado global de sesión
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
# <--- hecho por claude code (seguridad 05-nov-2026): candados por ticket, CSRF del formulario, límite de envíos anónimos y adjuntos servidos con permiso
import hashlib
import ipaddress
import os
import time
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError as _DjValidationError
from django.core.validators import validate_email
from django.http import FileResponse, Http404
from django.views.decorators.csrf import csrf_protect
from .forms import validar_adjunto, ACCEPT_ADJUNTOS

# IA pendiente para más adelante
# from core.utils_ai import consultar_ia

# 🔔 Notificaciones globales
from core.utils_notifications import crear_notificacion

PUBLIC_IMAGE_URL = ""


def _es_gestor_tickets(user):
    """<--- hecho por claude code: 'gestor/técnico de tickets' = superusuario o con permiso
    tickets.view_ticket. NO se basa en is_staff: el grupo 'administracion' es is_staff pero
    NO gestiona tickets — solo debe ver los SUYOS, como un usuario normal."""
    # <--- hecho por claude code (seguridad 05-nov-2026): mismo criterio que el menú (nav_tickets_tecnico); se quitó groups icontains 'tecnico' (no distingue grupos; hoy no existe ninguno)
    return bool(
        getattr(user, 'is_authenticated', False) and (
            user.is_superuser
            or user.has_perm('tickets.view_ticket')
        )
    )


# <--- hecho por claude code (seguridad 05-nov-2026): estados que el técnico puede poner a mano (mismo set que ticket_status_update_ajax)
_ESTADOS_EDITABLES = ("Pendiente", "En Proceso", "En espera del usuario", "Incompleto", "Resuelto")


def _puede_ver_ticket(user, ticket):
    """<--- hecho por claude code (seguridad 05-nov-2026): IDOR — antes cualquier usuario con sesión leía y escribía
    en el ticket de otro. Pasa: gestor, dueño, asignado (responsable del requerimiento), el ticket anónimo
    enviado con el correo del usuario, y el equipo de Desarrollo si el ticket tiene requerimiento."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if _es_gestor_tickets(user):
        return True
    if ticket.usuario_id and ticket.usuario_id == user.pk:
        return True
    if ticket.asignado_a_id and ticket.asignado_a_id == user.pk:
        return True
    correo = (user.email or '').strip().lower()
    if ticket.usuario_id is None and correo and (ticket.email or '').strip().lower() == correo:
        return True
    if ticket.req_desarrollo is not None:
        try:
            from desarrollo.utils import es_dev_desarrollo
            if es_dev_desarrollo(user):
                return True
        except Exception:
            pass
    return False


def _ticket_autorizado(request, ticket_id):
    """<--- hecho por claude code (seguridad 05-nov-2026): el ticket si el usuario puede verlo; None si no (404 si no existe)."""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    return ticket if _puede_ver_ticket(request.user, ticket) else None


def _sin_permiso_json():
    return JsonResponse({"ok": False, "error": "Sin permiso sobre este ticket."}, status=403)


# ======================================================
# HELPER: notificar nuevo ticket a técnicos y superusers
# ======================================================
def _aviso_horario_laboral(ticket):
    """<--- hecho por claude code: si el ticket se creó FUERA del horario laboral (L-V 7-16),
    avisa al usuario que se atenderá en horas laborables (el SLA no corre fuera de horario).
    Se dispara también cerca del cierre (últimos 15 min), como pidió el usuario ('3:59')."""
    from .sla import en_horario_laboral, proxima_apertura, _local, _LAB_FIN
    from datetime import time as _t, timedelta as _td
    creado = _local(ticket.created_at)
    cerca_cierre = (en_horario_laboral(creado) and creado.time() >= _t(15, 45))
    if en_horario_laboral(creado) and not cerca_cierre:
        return
    pa = proxima_apertura(creado if not cerca_cierre else creado + _td(minutes=20))
    cuando = ''
    if pa:
        from django.utils import timezone as _tz
        hoy = _local(ticket.created_at).date()
        cuando = (' el mismo día' if pa.date() == hoy else ' mañana' if (pa.date() - hoy).days == 1 else pa.strftime(' el %d/%m'))
        cuando += f' a las {pa.strftime("%H:%M")}'
    msg = ('Recibimos tu ticket. Como llegó fuera del horario de atención (lunes a viernes, '
           f'7:00 a 4:00 pm), será atendido en horas laborables{cuando}. El tiempo de atención '
           'solo corre en ese horario.')
    from .models import TicketComment
    TicketComment.objects.create(ticket=ticket, usuario=None, tipo='sistema', mensaje=msg)
    if ticket.usuario:
        crear_notificacion(usuario=ticket.usuario, mensaje=msg, modulo='tickets',
                           tipo='info', enviar_correo=False)


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


def enviar_correo_estado(ticket, titulo, mensaje, info_requerida='', color=('#1864ab', '#228be6')):
    """<--- hecho por claude code: correo al usuario cuando cambia el estado del ticket."""
    if not ticket.email:
        return
    html = render_to_string('tickets/email/ticket_estado.html', {
        'ticket': ticket, 'titulo': titulo, 'mensaje': mensaje,
        'info_requerida': info_requerida, 'color_ini': color[0], 'color_fin': color[1]})
    send_email_async(f'Ticket #{ticket.ticket_id} — {titulo}', html, [ticket.email])


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


# <--- hecho por claude code (seguridad 05-nov-2026): límites de envío (ventana deslizante en la caché de BD, compartida entre procesos de Apache)
_LIM_ANON_IP = (5, 3600)        # anónimo: por IP
_LIM_ANON_CORREO = (3, 3600)    # anónimo: por correo declarado
_LIM_ANON_GLOBAL = (30, 3600)   # anónimo: todos juntos
_LIM_USUARIO = (20, 3600)       # con sesión: por usuario


def _lim_clave(tipo, valor):
    h = hashlib.sha256(str(valor).strip().lower().encode('utf-8')).hexdigest()[:32]
    return f'tickets:lim:{tipo}:{h}'


def _lim_marcas(clave, ventana):
    ahora = time.time()
    return [t for t in (cache.get(clave) or []) if ahora - t < ventana]


def _ip_interna(ip):
    """<--- hecho por claude code (seguridad 05-nov-2026): IP privada/loopback (la red de la escuela llega toda por el NAT del gateway 192.168.10.1)."""
    try:
        a = ipaddress.ip_address(ip)
        return a.is_private or a.is_loopback
    except ValueError:
        return False


def _limites_envio(request, email):
    if request.user.is_authenticated:
        return [(_lim_clave('u', request.user.pk), _LIM_USUARIO)]
    ip = request.META.get('REMOTE_ADDR', '') or 'sin-ip'
    lims = [(_lim_clave('correo', email or ''), _LIM_ANON_CORREO),
            (_lim_clave('global', 'anon'), _LIM_ANON_GLOBAL)]
    # <--- hecho por claude code (seguridad 05-nov-2026): el límite por IP era UN solo cupo para toda la red interna (5/h compartidos por el NAT): solo para IP públicas; la red interna queda con el de correo (3/h) y el global (30/h)
    if not _ip_interna(ip):
        lims.insert(0, (_lim_clave('ip', ip), _LIM_ANON_IP))
    return lims


def _limite_superado(request, email):
    try:
        return any(len(_lim_marcas(c, v)) >= n for c, (n, v) in _limites_envio(request, email))
    except Exception:
        return False


def _registrar_envio(request, email):
    for c, (n, v) in _limites_envio(request, email):
        try:
            marcas = _lim_marcas(c, v)
            marcas.append(time.time())
            cache.set(c, marcas[-(n + 5):], v)
        except Exception:
            pass


def _correo_conocido(email):
    """<--- hecho por claude code (seguridad 05-nov-2026): correo de un usuario activo o de la lista blanca institucional.
    Solo a esos se manda la confirmación de un ticket ANÓNIMO (antes se mandaba a cualquier dirección escrita en el formulario)."""
    e = (email or '').strip()
    if not e:
        return False
    try:
        if get_user_model().objects.filter(email__iexact=e, is_active=True).exists():
            return True
        from accounts.models import CorreoInstitucional
        return CorreoInstitucional.objects.filter(correo__iexact=e).exists()
    except Exception:
        return False


def _primer_error(form):
    for campo, errs in form.errors.items():
        if errs:
            etiqueta = '' if campo == '__all__' else f'{form.fields[campo].label if campo in form.fields else campo}: '
            return f'{etiqueta}{errs[0]}'
    return 'Datos inválidos.'


def _crear_ticket_y_avisar(request, form, asunto_usuario):
    ticket = form.save(commit=False)
    ticket.comments = ''   # <--- hecho por claude code (seguridad 05-nov-2026): el «Comentario general» lo escribe el técnico; quien envía el ticket no lo fija (la rama de formulario lo aceptaba del POST)
    if request.user.is_authenticated:
        ticket.usuario = request.user
        ticket.email = request.user.email
    ticket.save()
    _registrar_envio(request, ticket.email)

    # 🔔 Notificaciones
    _notificar_nuevo_ticket(ticket, request.user)
    _aviso_horario_laboral(ticket)  # <--- hecho por claude code

    # 📧 Correos
    html_msg = render_to_string(
        'tickets/email/email_notification.html',
        {'ticket': ticket, 'img_url': PUBLIC_IMAGE_URL}
    )
    _send_tickets_notif(f'Nuevo Ticket #{ticket.ticket_id} - {ticket.name}', html_msg)
    if request.user.is_authenticated or _correo_conocido(ticket.email):
        send_email_async(asunto_usuario.format(id=ticket.ticket_id, name=ticket.name), html_msg, [ticket.email])
    return ticket


def _respuesta_creado(ticket):
    return JsonResponse({
        'message': f'Ticket #{ticket.ticket_id} creado exitosamente',
        'redirect_url': reverse('ticket_comments', args=[ticket.id]),
    }, status=201)


# ======================================================
# 🔥 SUBMIT TICKET
# ======================================================
@login_not_required  # <--- hecho por claude code (seguridad 05-nov-2026): pública a propósito; el resto del sistema exige sesión (LoginRequiredMiddleware)
@csrf_exempt  # <--- hecho por claude code (seguridad 05-nov-2026): el exento queda SOLO para la rama JSON (la ventana de desbloqueo del login la llama sin token; un POST JSON desde otro sitio exige CORS y no se concede); el formulario web pasa por csrf_protect
def submit_ticket(request):
    if request.method == 'POST' and request.content_type == 'application/json':
        return _submit_ticket_json(request)
    return _submit_ticket_form(request)


def _submit_ticket_json(request):
    """JSON (ventana de desbloqueo del login / API). <--- hecho por claude code (seguridad 05-nov-2026): ahora valida con TicketForm (largos, urgencia), el correo y el límite de envíos."""
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Error al procesar data JSON'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'error': 'Error al procesar data JSON'}, status=400)

    def _txt(k):
        v = data.get(k)
        return v.strip() if isinstance(v, str) else ''

    name, grade, description = _txt('name'), _txt('grade'), _txt('description')
    email = request.user.email if request.user.is_authenticated else _txt('email')
    if not all([name, grade, email, description]):
        return JsonResponse({'error': 'Todos los campos son obligatorios'}, status=400)
    if not request.user.is_authenticated:
        try:
            validate_email(email)
        except _DjValidationError:
            return JsonResponse({'error': 'El correo electrónico no es válido.'}, status=400)
    if _limite_superado(request, email):
        return JsonResponse({'error': 'Demasiadas solicitudes seguidas. Intenta de nuevo más tarde.'}, status=429)

    form = TicketForm({'name': name, 'grade': grade, 'email': email, 'description': description,
                       'urgencia': _txt('urgencia') or 'medio', 'comments': ''})
    if not form.is_valid():
        return JsonResponse({'error': _primer_error(form)}, status=400)
    ticket = _crear_ticket_y_avisar(request, form, 'Ticket #{id} - Confirmación de Recepción')
    return _respuesta_creado(ticket)


@csrf_protect  # <--- hecho por claude code (seguridad 05-nov-2026): el formulario web ya manda el token (FormData + X-CSRFToken)
def _submit_ticket_form(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            email = request.user.email if request.user.is_authenticated else (form.cleaned_data.get('email') or '').strip()
            if not request.user.is_authenticated:
                try:
                    validate_email(email)
                except _DjValidationError:
                    return JsonResponse({'error': 'El correo electrónico no es válido.'}, status=400)
            if _limite_superado(request, email):
                return JsonResponse({'error': 'Demasiadas solicitudes seguidas. Intenta de nuevo más tarde.'}, status=429)
            ticket = _crear_ticket_y_avisar(request, form, 'Nuevo Ticket #{id} - {name}')
            return _respuesta_creado(ticket)

        return JsonResponse({'error': 'Error en formulario: ' + _primer_error(form),
                             'details': form.errors.as_json()}, status=400)

    form = TicketForm()
    return render(request, 'tickets/submit_ticket.html', {
        'form': form,
        'user_email': request.user.email if request.user.is_authenticated else "",
        'accept_adjuntos': ACCEPT_ADJUNTOS,   # <--- hecho por claude code (seguridad 05-nov-2026): el selector ofrece solo los tipos de la lista blanca
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
    tickets = Ticket.objects.select_related('requerimiento', 'asignado_a').all()
    return render(request, 'tickets/technician_dashboard.html', {'tickets': tickets})


# <--- hecho por claude code: tickets SIN ATENDER (Nuevo/Pendiente) para la alerta cada 10 min
@login_required
def tickets_sin_atender_ajax(request):
    if not _es_gestor_tickets(request.user):
        return JsonResponse({'ok': False, 'count': 0, 'tickets': []})
    from django.utils import timezone
    from .sla import minutos_laborales_entre
    qs = Ticket.objects.filter(status__in=['Nuevo', 'Pendiente']).exclude(sin_sla=True).order_by('created_at')   # <--- hecho por claude code (29-sep-2026): los tickets de desarrollo no suenan
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
    ticket = _ticket_autorizado(request, ticket_id)   # <--- hecho por claude code (seguridad 05-nov-2026): antes cualquiera con sesión leía/escribía la conversación ajena
    if ticket is None:
        raise PermissionDenied('No tienes acceso a este ticket.')
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
        # <--- hecho por claude code (seguridad 05-nov-2026): solo el técnico, solo estados válidos y nunca si lo manda un requerimiento (antes cualquiera ponía cualquier texto)
        puede_estado = (_es_gestor_tickets(request.user) and new_status in _ESTADOS_EDITABLES
                        and ticket.req_desarrollo is None)
        if new_status and new_status != ticket.status and puede_estado:
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
        # <--- hecho por claude code (seguridad 05-nov-2026): ticket Resuelto = chat cerrado (como ticket_send_comment_ajax, que responde «Ticket cerrado»); este POST legado lo saltaba. El técnico sí puede seguir escribiendo.
        if mensaje and (ticket.status or '').lower() == 'resuelto' and not _es_gestor_tickets(request.user):
            messages.error(request, 'Este ticket está resuelto: ya no se pueden agregar comentarios.')
            return redirect('ticket_comments', ticket_id=ticket.id)
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
        'accept_adjuntos': ACCEPT_ADJUNTOS,   # <--- hecho por claude code (seguridad 05-nov-2026): el selector de documentos ofrece solo la lista blanca
    })


# ======================================================
# AJAX → Render parcial de comentarios (GET)
# ======================================================
@login_required
def ticket_comments_ajax(request, ticket_id):
    ticket = _ticket_autorizado(request, ticket_id)   # <--- hecho por claude code (seguridad 05-nov-2026): IDOR de lectura
    if ticket is None:
        return _sin_permiso_json()
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
    ticket = _ticket_autorizado(request, ticket_id)   # <--- hecho por claude code (seguridad 05-nov-2026): antes cualquiera escribía (y subía archivos) en el ticket ajeno
    if ticket is None:
        return _sin_permiso_json()

    if ticket.status.lower() == "resuelto":
        return JsonResponse({"ok": False, "error": "Ticket cerrado"}, status=400)

    mensaje = request.POST.get("mensaje", "").strip()
    archivo = request.FILES.get("archivo")
    if not mensaje and not archivo:
        return JsonResponse({"ok": False, "error": "Mensaje vacío"}, status=400)

    # Límite de tamaño: 15 MB
    if archivo and archivo.size > 15 * 1024 * 1024:
        return JsonResponse({"ok": False, "error": "El archivo supera el límite de 15 MB"}, status=400)
    # <--- hecho por claude code (seguridad 05-nov-2026): solo tipos de archivo permitidos (antes cualquiera, también .html/.svg)
    if archivo:
        err_adj = validar_adjunto(archivo)
        if err_adj:
            return JsonResponse({"ok": False, "error": err_adj}, status=400)

    comentario = TicketComment.objects.create(
        ticket=ticket,
        usuario=request.user,
        mensaje=mensaje,
        archivo=archivo,
        tipo="usuario" if not _es_gestor_tickets(request.user) else "tecnico"
    )

    # <--- hecho por claude code: si el USUARIO responde y el ticket está EN ESPERA,
    # se reanuda solo (cierra la pausa, corre el SLA y avisa al técnico).
    # <--- hecho por claude code (seguridad 05-nov-2026): con requerimiento el estado lo manda Desarrollo (tickets_link): el comentario no lo pasa a «En Proceso»
    if comentario.tipo == "usuario" and ticket.en_espera and ticket.pausa_abierta and ticket.req_desarrollo is None:
        from . import estados as _estados
        _estados.reanudar(ticket, request.user, via='comentario')
        ticket.refresh_from_db()

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
    # <--- hecho por claude code (seguridad 05-nov-2026): IDOR de escritura — solo técnicos/admin cambian el estado (mismo criterio que el panel técnico)
    if not _es_gestor_tickets(request.user):
        return JsonResponse({"ok": False, "error": "Solo técnicos o administradores."}, status=403)

    new_status = (request.POST.get("status") or "").strip()
    comments = (request.POST.get("comments") or "").strip()

    if new_status not in _ESTADOS_EDITABLES:
        return JsonResponse({"ok": False}, status=400)
    # <--- hecho por claude code (seguridad 05-nov-2026): el requerimiento manda el estado (en la pantalla el selector ya va deshabilitado); guardar solo la nota sí se permite
    if new_status != ticket.status and ticket.req_desarrollo is not None:
        return JsonResponse({"ok": False, "error": f"El estado lo controla el requerimiento {ticket.req_desarrollo.codigo}."}, status=409)

    from .models import ESTADO_ESPERA, ESTADOS_PAUSA
    from . import estados as _estados
    from django.core.exceptions import ValidationError as _VE
    old_status = ticket.status

    # <--- hecho por claude code: ENTRAR a un estado de pausa (En espera / Incompleto) → pausa el SLA
    if new_status in ESTADOS_PAUSA and old_status != new_status:
        motivo = (request.POST.get('motivo') or '').strip()
        info = (request.POST.get('info_requerida') or '').strip()
        if new_status == ESTADO_ESPERA and (not motivo or not info):
            return JsonResponse({"ok": False, "need_motivo": True,
                                 "error": "Indica el motivo y la información requerida."}, status=400)
        try:
            _estados.poner_en_pausa(ticket, request.user, motivo, info, new_status)
        except _VE as e:
            return JsonResponse({"ok": False, "error": '; '.join(e.messages)}, status=400)
        if comments:
            ticket.refresh_from_db(); ticket.comments = comments; ticket.save(update_fields=['comments'])
        return JsonResponse({"ok": True, "status": new_status})

    # <--- hecho por claude code: SALIR de un estado de pausa → reanuda (acumula tiempo, corre SLA)
    if old_status in ESTADOS_PAUSA and new_status not in ESTADOS_PAUSA and ticket.pausa_abierta:
        _estados.reanudar(ticket, request.user, via='tecnico')
        ticket.refresh_from_db()
        if new_status != 'En Proceso':
            ticket.status = new_status
        ticket.comments = comments
        ticket.save()
    elif new_status != old_status:
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
    if new_status == "En Proceso" and old_status != new_status and ticket.usuario:
        crear_notificacion(
            usuario=ticket.usuario,
            mensaje=f"Tu ticket #{ticket.ticket_id} está en proceso.",
            modulo="tickets",
            tipo="info",
            enviar_correo=False,
        )
        # <--- hecho por claude code: correo de cambio a "En Proceso"
        enviar_correo_estado(
            ticket, 'Tu ticket está siendo atendido',
            'Un técnico de soporte está trabajando en tu solicitud. Te avisaremos ante cualquier novedad.')

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
    # <--- hecho por claude code (seguridad 05-nov-2026): borrar exige el permiso de BORRAR (antes bastaba con poder ver tickets)
    if not (request.user.is_superuser or request.user.has_perm('tickets.delete_ticket')):
        return JsonResponse({"ok": False, "error": "Sin permiso"}, status=403)
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.delete()
    return JsonResponse({"ok": True})


# ======================================================
# <--- hecho por claude code: poner EN ESPERA DEL USUARIO (pausa el SLA) — solo técnicos/admin
# ======================================================
@require_POST
@login_required
def ticket_poner_espera_ajax(request, ticket_id):
    from . import estados as _estados
    from django.core.exceptions import PermissionDenied, ValidationError
    # <--- hecho por claude code (seguridad 05-nov-2026): 403 ANTES de mirar el requerimiento (no revelar su código a quien no gestiona tickets)
    if not _es_gestor_tickets(request.user):
        return JsonResponse({'ok': False, 'error': 'Solo técnicos o administradores pueden pausar el ticket.'}, status=403)
    ticket = get_object_or_404(Ticket, id=ticket_id)
    # <--- hecho por claude code (seguridad 05-nov-2026): el requerimiento manda el estado (igual que ticket_status_update_ajax); antes se podía pausar y mandar correo real al usuario
    if ticket.req_desarrollo is not None:
        return JsonResponse({'ok': False, 'error': f'El estado lo controla el requerimiento {ticket.req_desarrollo.codigo}.'}, status=409)
    motivo = (request.POST.get('motivo') or '').strip()
    info = (request.POST.get('info_requerida') or '').strip()
    try:
        _estados.poner_en_espera(ticket, request.user, motivo, info)
    except PermissionDenied as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=403)
    except ValidationError as e:
        return JsonResponse({'ok': False, 'error': '; '.join(e.messages)}, status=400)
    return JsonResponse({'ok': True, 'status': ticket.status})


# <--- hecho por claude code: reanudar la atención (cierra la pausa, corre el SLA)
@require_POST
@login_required
def ticket_reanudar_ajax(request, ticket_id):
    from . import estados as _estados
    from django.core.exceptions import ValidationError
    if not _es_gestor_tickets(request.user):
        return JsonResponse({'ok': False, 'error': 'Solo técnicos o administradores.'}, status=403)
    ticket = get_object_or_404(Ticket, id=ticket_id)
    # <--- hecho por claude code (seguridad 05-nov-2026): el requerimiento manda el estado (reanudar lo pasaría a «En Proceso»)
    if ticket.req_desarrollo is not None:
        return JsonResponse({'ok': False, 'error': f'El estado lo controla el requerimiento {ticket.req_desarrollo.codigo}.'}, status=409)
    try:
        _estados.reanudar(ticket, request.user, via='tecnico')
    except ValidationError as e:
        return JsonResponse({'ok': False, 'error': '; '.join(e.messages)}, status=400)
    return JsonResponse({'ok': True, 'status': ticket.status})


# ======================================================
# AJAX → Obtener estado
# ======================================================
@require_GET
@login_required
def ticket_status_get_ajax(request, ticket_id):
    ticket = _ticket_autorizado(request, ticket_id)   # <--- hecho por claude code (seguridad 05-nov-2026): IDOR de lectura
    if ticket is None:
        return _sin_permiso_json()
    pa = ticket.pausa_abierta
    return JsonResponse({
        # <--- hecho por claude code (seguridad 05-nov-2026): "comments" es la nota interna del técnico: solo para gestores
        "status": ticket.status, "comments": (ticket.comments if _es_gestor_tickets(request.user) else ""),
        # <--- hecho por claude code: estado del SLA para el panel del detalle
        "sla_estado": ticket.sla_estado, "sla_texto": ticket.sla_texto,
        "sla_pausado": ticket.sla_pausado, "en_espera": ticket.en_espera,
        "pausa_motivo": pa.motivo if pa else "",
        "pausa_info": pa.info_requerida if pa else "",
        "pausa_desde": pa.inicio.strftime('%d/%m/%Y %H:%M') if pa else "",
        # <--- hecho por claude code: SLA congelado por estar fuera del horario laboral
        "fuera_horario": ticket.fuera_horario,
        "fuera_horario_texto": ticket.fuera_horario_texto,
    })


# ======================================================
# AJAX → Reporte de ticket (GET) para modal
# ======================================================
@require_GET
@login_required
def ticket_reporte_ajax(request, ticket_id):
    ticket = _ticket_autorizado(request, ticket_id)   # <--- hecho por claude code (seguridad 05-nov-2026): IDOR de lectura (datos + chat completo)
    if ticket is None:
        return _sin_permiso_json()
    comentarios = TicketComment.objects.filter(ticket=ticket).order_by('fecha')
    return JsonResponse({
        'ticket_id': ticket.ticket_id,
        'name': ticket.name,
        'grade': ticket.grade,
        'email': ticket.email,
        'description': ticket.description,
        'status': ticket.status,
        'created_at': ticket.created_at.strftime('%d/%m/%Y %H:%M'),
        'attachment_url': reverse('ticket_adjunto', args=[ticket.id]) if ticket.attachment else None,   # <--- hecho por claude code (seguridad 05-nov-2026): por la vista con permiso
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
# <--- hecho por claude code (seguridad 05-nov-2026): adjuntos servidos por Django CON permiso del ticket
# (antes salían directo de /media/attachments/ y /media/ticket_chat/ sin sesión). Imágenes y PDF en línea
# con su tipo real; todo lo demás como descarga (octet-stream). nosniff lo agrega SecurityMiddleware.
# ======================================================
_EXT_EN_LINEA = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif',
                 'bmp': 'image/bmp', 'webp': 'image/webp', 'pdf': 'application/pdf'}


def _servir_archivo(fieldfile):
    if not fieldfile:
        raise Http404('Sin archivo')
    nombre = os.path.basename(fieldfile.name or '') or 'adjunto'
    ext = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else ''
    try:
        fh = fieldfile.open('rb')
    except (FileNotFoundError, OSError, ValueError):
        raise Http404('Archivo no encontrado')
    tipo = _EXT_EN_LINEA.get(ext)
    resp = FileResponse(fh, as_attachment=tipo is None, filename=nombre,
                        content_type=tipo or 'application/octet-stream')
    resp['X-Content-Type-Options'] = 'nosniff'
    resp['Cache-Control'] = 'private, no-store'
    return resp


@require_GET
@login_required
def ticket_adjunto(request, ticket_id):
    ticket = _ticket_autorizado(request, ticket_id)
    if ticket is None:
        raise PermissionDenied('No tienes acceso a este ticket.')
    return _servir_archivo(ticket.attachment)


@require_GET
@login_required
def ticket_comentario_archivo(request, comment_id):
    comentario = get_object_or_404(TicketComment.objects.select_related('ticket'), id=comment_id)
    if not _puede_ver_ticket(request.user, comentario.ticket):
        raise PermissionDenied('No tienes acceso a este ticket.')
    return _servir_archivo(comentario.archivo)


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