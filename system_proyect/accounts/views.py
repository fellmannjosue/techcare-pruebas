from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
import datetime

# ⬅️ Nuevo sistema de notificaciones globales
from core.utils_notifications import crear_notificacion

from .forms import MaestroRegisterForm
from tickets.models import Ticket


# =====================================================
# 🔐 LOGIN GENERAL DEL SISTEMA
# =====================================================
def login_view(request):
    """
    Login unificado para todos los usuarios.
    - Maestros → dashboard maestro
    - Técnicos → dashboard tickets
    - Superuser → menú principal
    """
    year = datetime.datetime.now().year
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        is_maestro = request.POST.get('is_maestro') == 'on'

        user = authenticate(request, username=username, password=password)

        if user:
            # Superuser: checkbox false → menú, checkbox true → dashboard maestro
            if user.is_superuser:
                login(request, user)
                request.session['show_welcome'] = True
                return redirect('dashboard_maestro' if is_maestro else 'menu')

            # Staff: redirección según usuario/grupo
            if user.is_staff:
                login(request, user)
                request.session['show_welcome'] = True
                if user.username == 'druiz@ana-hn.org':
                    return redirect('seleccion_rol')
                if user.username == 'glorenzo@ana-hn.org':
                    return redirect('seleccion_rol')
                if user.username == 'yzavala@ana-hn.org':
                    return redirect('reloj_dashboard')
                # Cualquier usuario del área Administración → solo tickets
                if user.groups.filter(name='administracion').exists():
                    return redirect('dashboard_administracion')
                # Coord-maestros: el checkbox determina el modo de agendas
                _coord_maestros = {'cvarela@ana-hn.org', 'ialcerro@ana-hn.org', 'jmartinez@ana-hn.org'}
                if user.username in _coord_maestros:
                    request.session['agenda_modo_maestro'] = is_maestro
                if is_maestro:
                    return redirect('dashboard_maestro')
                if user.groups.filter(name__in=['coordinadores_colegio', 'coordinador_colegio', 'coordinadores']).exists():
                    return redirect('dashboard_coordinador', area='colegio')
                return redirect('dashboard_coordinador', area='bilingue')

            # Técnicos
            if user.groups.filter(name='tecnicos').exists():
                login(request, user)
                request.session['show_welcome'] = True
                return redirect('tickets_dashboard')

            # Usuario regular: debe marcar "Soy maestro"
            if not is_maestro:
                messages.error(request, 'checkbox_hint')
                return render(request, 'accounts/login.html', {'year': year})

            login(request, user)
            request.session['show_welcome'] = True
            # Caso especial: usuario con ambas áreas (BL + Colegio)
            if user.username == 'admin2@ana-hn.org':
                return redirect('seleccion_rol')
            return redirect('dashboard_maestro')

        messages.error(request, 'Credenciales inválidas.')

    return render(request, 'accounts/login.html', {'year': year})


# =====================================================
# 🎭 SELECCIÓN DE ROL (usuarios con múltiples roles)
# =====================================================
_ROLES_POR_USUARIO = {
    'druiz@ana-hn.org': [
        {'titulo': 'Coordinador Bilingüe',  'subtitulo': 'Ver reportes del área BL · gestionar incidencias',  'icon': 'ti-users-group',     'clase': 'icon-coord', 'url': '/accounts/aplicar-rol/coordinador/'},
        {'titulo': 'Maestro – Bilingüe',    'subtitulo': 'Registrar y ver mis reportes del área BL',          'icon': 'ti-school',          'clase': 'icon-bl',    'url': '/accounts/aplicar-rol/maestro_bl/'},
        {'titulo': 'Maestro – Colegio',     'subtitulo': 'Registrar y ver mis reportes del área Colegio',     'icon': 'ti-building-school', 'clase': 'icon-col',   'url': '/accounts/aplicar-rol/maestro_col/'},
    ],
    'admin2@ana-hn.org': [
        {'titulo': 'Maestro – Bilingüe',    'subtitulo': 'Registrar y ver mis reportes del área BL',          'icon': 'ti-school',          'clase': 'icon-bl',    'url': '/conducta/dashboard/maestro/?area=bilingue'},
        {'titulo': 'Maestro – Colegio',     'subtitulo': 'Registrar y ver mis reportes del área Colegio',     'icon': 'ti-building-school', 'clase': 'icon-col',   'url': '/conducta/dashboard/maestro/?area=colegio'},
    ],
    'glorenzo@ana-hn.org': [
        {'titulo': 'Control de Reloj',      'subtitulo': 'Gestión de asistencia y horarios',                  'icon': 'ti-clock',           'clase': 'icon-reloj', 'url': '/reloj/'},
        {'titulo': 'Inventario',            'subtitulo': 'Control de equipos y recursos',                     'icon': 'ti-package',         'clase': 'icon-inv',   'url': '/inventario/'},
    ],
}

@login_required
def seleccion_rol(request):
    roles = _ROLES_POR_USUARIO.get(request.user.username, [])
    return render(request, 'accounts/seleccion_rol.html', {'roles': roles})


@login_required
def aplicar_rol(request, rol):
    """Setea la sesión de agendas según el rol elegido y redirige."""
    if rol == 'coordinador':
        request.session['agenda_modo_maestro'] = False
        request.session.pop('agenda_area_maestro', None)
        return redirect('dashboard_coordinador', area='bilingue')
    elif rol == 'maestro_bl':
        request.session['agenda_modo_maestro'] = True
        request.session['agenda_area_maestro'] = 'bilingue'
        return redirect('dashboard_maestro')
    elif rol == 'maestro_col':
        request.session['agenda_modo_maestro'] = True
        request.session['agenda_area_maestro'] = 'colegio'
        return redirect('dashboard_maestro')
    return redirect('seleccion_rol')


# =====================================================
# 📝 REGISTRO DE MAESTROS / ADMIN / STAFF
# =====================================================
def register_maestro(request):
    """
    Registro completo con envío de correo y asignación de grupos.
    """
    if request.method == 'POST':
        form = MaestroRegisterForm(request.POST)

        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            area = form.cleaned_data['area']
            cargo = form.cleaned_data['cargo']
            password = form.cleaned_data['password']

            # Crear usuario
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Asignar grupos
            if area == 'bilingue':
                group_name = 'maestros_bilingue' if cargo == 'docente' else 'admin_bilingue'
            elif area == 'colegio':
                group_name = 'maestros_colegio' if cargo == 'docente' else 'admin_colegio'
            else:
                group_name = 'administracion'
                user.is_staff = True

            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
            user.save()

            # Enviar correo
            try:
                nombre_completo = f"{first_name} {last_name}".strip()
                texto_plano = (
                    f'Hola {nombre_completo},\n\n'
                    f'Se ha creado una cuenta para ti en el Sistema TechCare.\n\n'
                    f'Usuario    : {email}\n'
                    f'Contraseña : {password}\n\n'
                    f'Accede al sistema en:\n'
                    f'https://servicios.ana-hn.org:437\n\n'
                    f'Por seguridad, cambia tu contraseña en el primer inicio de sesión.'
                )
                html_bienvenida = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10);">
      <tr>
        <td style="background:linear-gradient(135deg,#1864ab,#228be6);padding:32px 40px;text-align:center;">
          <p style="margin:0;font-size:26px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">TechCare</p>
          <p style="margin:6px 0 0;font-size:13px;color:rgba(255,255,255,0.75);">Asociación Nuevo Amanecer</p>
        </td>
      </tr>
      <tr>
        <td style="padding:36px 40px 24px;">
          <p style="margin:0 0 8px;font-size:20px;font-weight:700;color:#1a1a2e;">¡Bienvenido/a, {nombre_completo}!</p>
          <p style="margin:0 0 24px;font-size:14px;color:#6c757d;">Tu cuenta en el Sistema TechCare ha sido creada exitosamente.</p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f9fa;border-radius:8px;padding:20px;margin-bottom:24px;">
            <tr>
              <td style="padding:6px 0;">
                <span style="font-size:12px;color:#6c757d;text-transform:uppercase;letter-spacing:0.5px;">Usuario</span><br>
                <span style="font-size:15px;font-weight:600;color:#1a1a2e;">{email}</span>
              </td>
            </tr>
            <tr><td style="border-top:1px solid #e9ecef;padding-top:12px;margin-top:12px;">
              <span style="font-size:12px;color:#6c757d;text-transform:uppercase;letter-spacing:0.5px;">Contraseña</span><br>
              <span style="font-size:15px;font-weight:600;color:#1a1a2e;font-family:monospace;">{password}</span>
            </td></tr>
          </table>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center">
              <a href="https://servicios.ana-hn.org:437"
                 style="display:inline-block;background:#228be6;color:#ffffff;text-decoration:none;padding:13px 36px;border-radius:8px;font-size:15px;font-weight:600;">
                Acceder al sistema
              </a>
            </td></tr>
          </table>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 40px;border-top:1px solid #e9ecef;text-align:center;">
          <p style="margin:0;font-size:12px;color:#adb5bd;">
            Por seguridad, cambia tu contraseña en el primer inicio de sesión.<br>
            © {datetime.datetime.now().year} Soporte Técnico – Asociación Nuevo Amanecer
          </p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body></html>"""
                msg = EmailMultiAlternatives(
                    'Bienvenido al Sistema TechCare',
                    texto_plano,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
                msg.attach_alternative(html_bienvenida, "text/html")
                msg.send(fail_silently=False)
            except Exception as e:
                messages.warning(request, f"Cuenta creada, pero no se envió el correo: {e}")

            messages.success(request, "¡Registro exitoso!")
            return redirect('login')

    else:
        form = MaestroRegisterForm()

    year = datetime.datetime.now().year
    todos_usuarios = User.objects.filter(is_active=True).exclude(email='').order_by('first_name', 'last_name')
    return render(request, 'accounts/register.html', {
        'form': form,
        'year': year,
        'todos_usuarios': todos_usuarios,
    })


# =====================================================
# 🖥 MENU PRINCIPAL
# =====================================================
@login_required
def menu_view(request):
    """
    Panel principal de TechCare, con tarjetas estadísticas
    y visibilidad por módulos.
    """
    user = request.user
    year = datetime.datetime.now().year

    # =====================================================
    # 🔥 TICKETS (todos los NO resueltos)
    # =====================================================
    tickets_pendientes = Ticket.objects.exclude(status__iexact="Resuelto").count()

    # =====================================================
    # 🔥 CITAS BL
    # =====================================================
    try:
        from citas_billingue.models import Appointment_bl
        citas_bl = Appointment_bl.objects.exclude(status__iexact="Resuelto").count()
    except:
        citas_bl = 0

    # =====================================================
    # 🔥 CITAS COL
    # =====================================================
    try:
        from citas_colegio.models import Appointment_col
        citas_col = Appointment_col.objects.exclude(status__iexact="Resuelto").count()
    except:
        citas_col = 0

    # =====================================================
    # 🔥 REPORTES DE CONDUCTA — BILINGÜE
    # =====================================================
    try:
        from conducta.models import ReporteInformativo, ReporteConductual, ProgressReport

        reportes_bl = (
            ReporteInformativo.objects.filter(area='bilingue', estado='enviado').count() +
            ReporteConductual.objects.filter(area='bilingue', estado='enviado').count() +
            ProgressReport.objects.filter(estado='enviado').count()
        )
    except:
        reportes_bl = 0

    # =====================================================
    # 🔥 REPORTES DE CONDUCTA — COLEGIO
    # =====================================================
    try:
        from conducta.models import ReporteInformativo, ReporteConductual

        reportes_col = (
            ReporteInformativo.objects.filter(area='colegio', estado='enviado').count() +
            ReporteConductual.objects.filter(area='colegio', estado='enviado').count()
        )
    except:
        reportes_col = 0

    # =====================================================
    # 🔥 RELOJ (compensatorios / permisos)
    # =====================================================
    try:
        from reloj.models import Solicitud
        reloj_pendientes = Solicitud.objects.exclude(estado__iexact="Aprobado").count()
    except:
        reloj_pendientes = 0

    # =====================================================
    # 🔰 ROLES Y PERMISOS
    # =====================================================
    is_admin            = user.is_superuser
    is_administracion   = user.groups.filter(name='administracion').exists()
    is_group_citas_bl   = user.groups.filter(name='citas bilingue').exists()
    is_group_citas_col  = user.groups.filter(name='citas colegio').exists()
    is_group_enfermeria = user.groups.filter(name='enfermeria').exists()
    is_group_inventario = user.groups.filter(name='inventario').exists()
    is_group_reloj      = user.groups.filter(name='reloj').exists()

    is_coord_bilingue   = user.groups.filter(name='coordinador_bilingue').exists()
    is_coord_colegio    = user.groups.filter(name='coordinador_colegio').exists()
    is_maestro_bilingue = user.groups.filter(name='maestros_bilingue').exists()
    is_maestro_colegio  = user.groups.filter(name='maestros_colegio').exists()

    # =====================================================
    # 🔐 PERMISOS
    # =====================================================
    can_view_inventory   = user.has_perm('inventario.view_inventariomedicamento')
    can_view_maintenance = user.has_perm('mantenimiento.view_mantenimiento')
    can_view_tickets     = user.has_perm('tickets.view_ticket')
    can_view_sponsors    = user.has_perm('sponsors.view_sponsor')
    can_view_seguridad   = user.has_perm('seguridad.view_seguridad')

    # =====================================================
    # 🚫 BLOQUEO DE TARJETAS PARA USUARIOS ESPECÍFICOS
    # =====================================================
    # admin2 y admin3 NO deben ver ninguna tarjeta
    blocked_users = ["admin2", "admin3"]
    show_cards = user.username not in blocked_users

    # =====================================================
    # CONTEXTO FINAL PARA EL HTML
    # =====================================================
    todos_usuarios = User.objects.filter(is_active=True).exclude(email='').order_by('first_name', 'last_name')

    context = {
        'year': year,
        'todos_usuarios': todos_usuarios,

        # ---------- Tarjetas del dashboard ----------
        'tickets_pendientes': tickets_pendientes,
        'citas_bl': citas_bl,
        'citas_col': citas_col,
        'reportes_bl': reportes_bl,
        'reportes_col': reportes_col,
        'reloj_pendientes': reloj_pendientes,

        # ---------- Mostrar/ocultar TODAS las tarjetas ----------
        'show_cards': show_cards,

        # ---------- Visibilidad según rol ----------
        'is_administracion': is_administracion,

        'show_inventory':   is_admin or can_view_inventory or is_group_inventario,
        'show_maintenance': is_admin or can_view_maintenance,
        'show_tickets':     is_admin or can_view_tickets or is_administracion,
        'show_sponsors':    is_admin or can_view_sponsors,
        'show_seguridad':   is_admin or can_view_seguridad,
        'show_citas_bl':    is_admin or is_group_citas_bl,
        'show_citas_col':   is_admin or is_group_citas_col,
        'show_enfermeria':  is_admin or is_group_enfermeria or is_coord_bilingue,
        'show_reloj':       is_admin or is_group_reloj,

        'show_coordinador_bilingue': is_admin or is_coord_bilingue,
        'show_coordinador_colegio':  is_admin or is_coord_colegio,
        'show_agendas':      is_admin or is_coord_bilingue or is_coord_colegio or is_maestro_bilingue or is_maestro_colegio,
        'show_directorio':   is_admin or is_coord_bilingue or is_coord_colegio,
    }

    # <--- hecho por claude code: limpiar session welcome después de renderizar
    # para que solo aparezca una vez al entrar, no en cada recarga.
    request.session.pop('show_welcome', None)

    return render(request, 'accounts/menu.html', context)




# =====================================================
# 📧 REENVÍO DE CORREO DE BIENVENIDA (solo superuser)
# =====================================================
@login_required
def reenviar_bienvenida(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    modo = request.POST.get('modo', 'todos')  # 'todos' o 'uno'
    email_destino = request.POST.get('email', '').strip()

    SITE_URL = 'https://servicios.ana-hn.org:437'

    if modo == 'uno':
        usuarios = User.objects.filter(email=email_destino, is_active=True)
    else:
        usuarios = User.objects.filter(is_active=True).exclude(email='')

    enviados = 0
    errores = []
    anio = datetime.datetime.now().year
    for u in usuarios:
        if not u.email:
            continue
        nombre = u.get_full_name() or u.username
        texto_plano = (
            f'Hola {nombre},\n\n'
            f'Este es un recordatorio de tu acceso al Sistema TechCare.\n\n'
            f'Usuario : {u.email}\n\n'
            f'Si no recuerdas tu contraseña, usa el enlace "¿Olvidaste tu contraseña?" en la página de inicio de sesión o contacta al administrador.\n\n'
            f'Accede en: {SITE_URL}'
        )
        html_recordatorio = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.10);">
      <tr>
        <td style="background:linear-gradient(135deg,#1864ab,#228be6);padding:32px 40px;text-align:center;">
          <p style="margin:0;font-size:26px;font-weight:700;color:#fff;letter-spacing:-.5px;">TechCare</p>
          <p style="margin:6px 0 0;font-size:13px;color:rgba(255,255,255,.75);">Asociación Nuevo Amanecer</p>
        </td>
      </tr>
      <tr>
        <td style="padding:36px 40px 24px;">
          <p style="margin:0 0 8px;font-size:20px;font-weight:700;color:#1a1a2e;">Hola, {nombre}</p>
          <p style="margin:0 0 24px;font-size:14px;color:#6c757d;">Este es un recordatorio de tu acceso al Sistema TechCare.</p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f9fa;border-radius:8px;padding:20px;margin-bottom:24px;">
            <tr>
              <td style="padding:6px 0;">
                <span style="font-size:12px;color:#6c757d;text-transform:uppercase;letter-spacing:.5px;">Usuario</span><br>
                <span style="font-size:15px;font-weight:600;color:#1a1a2e;">{u.email}</span>
              </td>
            </tr>
          </table>
          <p style="margin:0 0 20px;font-size:13px;color:#6c757d;">
            Si no recuerdas tu contraseña, usa el enlace <strong>"¿Olvidaste tu contraseña?"</strong> en la página de inicio de sesión o contacta al administrador.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center">
              <a href="{SITE_URL}"
                 style="display:inline-block;background:#228be6;color:#fff;text-decoration:none;padding:13px 36px;border-radius:8px;font-size:15px;font-weight:600;">
                Acceder al sistema
              </a>
            </td></tr>
          </table>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 40px;border-top:1px solid #e9ecef;text-align:center;">
          <p style="margin:0;font-size:12px;color:#adb5bd;">
            © {anio} Soporte Técnico – Asociación Nuevo Amanecer
          </p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body></html>"""
        try:
            msg = EmailMultiAlternatives(
                'Recordatorio de acceso – Sistema TechCare',
                texto_plano,
                settings.DEFAULT_FROM_EMAIL,
                [u.email],
            )
            msg.attach_alternative(html_recordatorio, "text/html")
            msg.send(fail_silently=False)
            enviados += 1
        except Exception:
            errores.append(u.email)

    return JsonResponse({'ok': True, 'enviados': enviados, 'errores': errores})


# =====================================================
# 🔔 NOTIFICACIONES AVANZADAS PARA EL MENÚ
# =====================================================
@login_required
def notify_tickets(request):
    """
    Devuelve tickets pendientes para la campana del menú.
    Se conecta con ticket_notify.js
    """
    abiertos = Ticket.objects.filter(status="pendiente").count()
    recientes = Ticket.objects.filter(status="pendiente").order_by('-id')[:5]

    return JsonResponse({
        "total": abiertos,
        "tickets": [
            {
                "id": t.id,
                "ticket_id": t.ticket_id,
                "name": t.name,
                "fecha": t.created_at.strftime("%d/%m/%Y %H:%M") if t.created_at else ""
            }
            for t in recientes
        ]
    })


# =====================================================
# 🔚 LOGOUT GENERAL
# =====================================================
def logout_view(request):
    inactive = request.GET.get('inactive')
    logout(request)
    messages.info(request, 'Sesión cerrada por inactividad.' if inactive else 'Sesión cerrada correctamente.')
    return redirect('login')


# =====================================================
# 🔚 LOGOUT PARA MAESTROS
# =====================================================
def maestro_logout(request):
    inactive = request.GET.get('inactive')
    logout(request)
    messages.info(request, 'Sesión cerrada por inactividad.' if inactive else 'Sesión cerrada correctamente.')
    return redirect('login')
