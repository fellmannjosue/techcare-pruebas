from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
import datetime

# ⬅️ Nuevo sistema de notificaciones globales
from core.utils_notifications import crear_notificacion

from .forms import MaestroRegisterForm
from .models import RegistroAcceso, PerfilUsuario, CoordPermiso
from tickets.models import Ticket
from reloj.models import RelojPermiso


# =====================================================
# 🔐 LOGIN GENERAL DEL SISTEMA
# =====================================================
# ── Bloqueo de login por intentos fallidos (hecho por claude code) ───────────
# 3 intentos → bloqueo temporal 1 min (cache) · 5 intentos → bloqueo total (perfil)
_LOGIN_MAX_TEMP  = 3      # intentos para el bloqueo temporal
_LOGIN_TEMP_SECS = 60     # duración del bloqueo temporal (1 min)
_LOGIN_MAX_TOTAL = 5      # intentos para el bloqueo total


def _login_key(username):
    return (username or '').strip().lower()


def _perfil_bloqueado(username):
    """(User|None, bloqueado_bool) según perfil.login_bloqueado del usuario real."""
    u = User.objects.filter(username__iexact=(username or '').strip()).first()
    if u:
        try:
            return u, bool(u.perfil.login_bloqueado)
        except Exception:
            return u, False
    return None, False


def _login_temp_lock_left(key):
    """Segundos restantes del bloqueo temporal (0 si no hay)."""
    import time
    from django.core.cache import cache
    ts = cache.get('login_lock:' + key)
    if not ts:
        return 0
    left = int(ts - time.time())
    return left if left > 0 else 0


def _registrar_fallo_login(username, key):
    """Suma un intento fallido y devuelve {intentos, temp_secs, total}."""
    import time
    from django.core.cache import cache
    from django.utils import timezone as _tz
    n = (cache.get('login_fails:' + key, 0) or 0) + 1
    cache.set('login_fails:' + key, n, 15 * 60)   # ventana de 15 min
    estado = {'intentos': n, 'temp_secs': 0, 'total': False}
    if n >= _LOGIN_MAX_TOTAL:
        estado['total'] = True
        u = User.objects.filter(username__iexact=(username or '').strip()).first()
        if u:
            try:
                p = u.perfil
                p.login_bloqueado = True
                p.login_bloqueado_en = _tz.now()
                p.save(update_fields=['login_bloqueado', 'login_bloqueado_en'])
            except Exception:
                pass
    elif n == _LOGIN_MAX_TEMP:   # solo en el 3er intento se aplica el bloqueo de 1 min
        cache.set('login_lock:' + key, time.time() + _LOGIN_TEMP_SECS, _LOGIN_TEMP_SECS)
        estado['temp_secs'] = _LOGIN_TEMP_SECS
    return estado


def _reset_login_fails(key):
    from django.core.cache import cache
    cache.delete('login_fails:' + key)
    cache.delete('login_lock:' + key)


def login_view(request):
    """
    Login unificado para todos los usuarios.
    - Maestros → dashboard maestro
    - Técnicos → dashboard tickets
    - Superuser → menú principal
    """
    # <--- hecho por claude code: si ya está autenticado, redirigir al home correcto
    # (evita que el botón "atrás" del navegador muestre el login cuando ya está logueado)
    if request.user.is_authenticated:
        next_url = request.GET.get('next', '')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('menu')

    year = datetime.datetime.now().year
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        is_maestro = request.POST.get('is_maestro') == 'on'
        key = _login_key(username)

        # Bloqueo total (persistente) o temporal (cache) antes de autenticar
        _u_block, _is_blocked = _perfil_bloqueado(username)
        if _is_blocked:
            return render(request, 'accounts/login.html',
                          {'year': year, 'bloqueo_total': True, 'bloqueo_username': username})
        _lock_left = _login_temp_lock_left(key)
        if _lock_left > 0:
            return render(request, 'accounts/login.html',
                          {'year': year, 'bloqueo_temp': _lock_left})

        user = authenticate(request, username=username, password=password)

        if user:
            _reset_login_fails(key)
            def _registrar_acceso(u):
                ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
                if ip and ',' in ip:
                    ip = ip.split(',')[0].strip()
                RegistroAcceso.objects.create(
                    usuario=u, username=u.username,
                    ip=ip or None,
                    agente=request.META.get('HTTP_USER_AGENT', '')[:500],
                )

            # <--- hecho por claude code: cookie de bienvenida universal (funciona en cualquier página destino)
            def _welcome_redirect(url_name, *args, **kwargs):
                resp = redirect(url_name, *args, **kwargs)
                nombre = user.get_full_name() or user.username
                resp.set_cookie('tc_welcome', nombre, max_age=30, httponly=False, samesite='Lax')
                return resp

            # Superuser: checkbox false → menú, checkbox true → dashboard maestro
            if user.is_superuser:
                login(request, user)
                _registrar_acceso(user)
                return _welcome_redirect('dashboard_maestro' if is_maestro else 'menu')

            # Staff: redirección según usuario/grupo
            if user.is_staff:
                login(request, user)
                _registrar_acceso(user)
                # Multi-rol → Panel General (reemplaza la antigua "selección de rol")
                from .panel_roles import es_multi_panel
                if es_multi_panel(user):
                    return _welcome_redirect('panel_general')
                if user.groups.filter(name='reloj').exists():
                    return _welcome_redirect('reloj_dashboard')
                # Cualquier usuario del área Administración → solo tickets
                if user.groups.filter(name='administracion').exists():
                    return _welcome_redirect('dashboard_administracion')
                # Coord-maestros: el checkbox determina el modo de agendas
                try:
                    _es_coord_maestro = user.perfil.es_coord_maestro
                except Exception:
                    _es_coord_maestro = False
                if _es_coord_maestro:
                    request.session['agenda_modo_maestro'] = is_maestro
                # Coordinadores con restricción de progress — siempre van al dashboard coordinador
                if user.groups.filter(name__in=['coord_progress_bl', 'coordinador_bilingue', 'coordinador_colegio']).exists():
                    if user.groups.filter(name__in=['coordinadores_colegio', 'coordinador_colegio', 'coordinadores']).exists():
                        return _welcome_redirect('dashboard_coordinador', area='colegio')
                    return _welcome_redirect('dashboard_coordinador', area='bilingue')
                if is_maestro:
                    return _welcome_redirect('dashboard_maestro')
                if user.groups.filter(name__in=['coordinadores_colegio', 'coordinador_colegio', 'coordinadores']).exists():
                    return _welcome_redirect('dashboard_coordinador', area='colegio')
                return _welcome_redirect('dashboard_coordinador', area='bilingue')

            # Construir lista de roles a partir de los grupos del usuario (case-insensitive)
            roles_disponibles = [
                _GRUPO_A_ROL[g.name.lower()]
                for g in user.groups.all()
                if g.name.lower() in _GRUPO_A_ROL
            ]
            # El rol maestro solo aparece si tiene el grupo asignado — el checkbox no lo otorga

            if not roles_disponibles:
                messages.error(request, 'checkbox_hint')
                return render(request, 'accounts/login.html', {'year': year})

            login(request, user)
            _registrar_acceso(user)

            if len(roles_disponibles) == 1:
                return _welcome_redirect(roles_disponibles[0]['url'])
            return _welcome_redirect('seleccion_rol')

        # ── Fallo de autenticación: contar intento y (des)bloquear ──
        estado = _registrar_fallo_login(username, key)
        if estado['total']:
            return render(request, 'accounts/login.html',
                          {'year': year, 'bloqueo_total': True, 'bloqueo_username': username})
        if estado['temp_secs']:
            return render(request, 'accounts/login.html',
                          {'year': year, 'bloqueo_temp': estado['temp_secs']})
        restantes = max(0, _LOGIN_MAX_TEMP - estado['intentos'])
        msg = 'Credenciales inválidas.'
        if restantes:
            msg += f' Te queda{"n" if restantes != 1 else ""} {restantes} intento{"s" if restantes != 1 else ""} antes del bloqueo temporal.'
        messages.error(request, msg)

    return render(request, 'accounts/login.html', {'year': year})


# =====================================================
# 🎭 SELECCIÓN DE ROL (usuarios con múltiples roles)
# =====================================================

# Mapeo grupo → tarjeta de rol (para cualquier usuario)
_GRUPO_A_ROL = {
    'maestros_bilingue':    {'titulo': 'Maestro – Bilingüe',    'subtitulo': 'Registrar y ver mis reportes del área BL',           'icon': 'ti-school',          'clase': 'icon-bl',    'url': '/accounts/aplicar-rol/maestro_bl/'},
    'maestros_colegio':     {'titulo': 'Maestro – Colegio',     'subtitulo': 'Registrar y ver mis reportes del área Colegio',      'icon': 'ti-building-school', 'clase': 'icon-col',   'url': '/accounts/aplicar-rol/maestro_col/'},
    'coordinador_bilingue': {'titulo': 'Coordinador Bilingüe',  'subtitulo': 'Ver reportes del área BL · gestionar incidencias',   'icon': 'ti-users-group',     'clase': 'icon-coord', 'url': '/accounts/aplicar-rol/coordinador/'},
    'coordinador_colegio':  {'titulo': 'Coordinador Colegio',   'subtitulo': 'Ver reportes del área Colegio · gestionar incidencias','icon': 'ti-users-group',    'clase': 'icon-coord', 'url': '/accounts/aplicar-rol/coordinador_col/'},
    'administracion':       {'titulo': 'Administración',        'subtitulo': 'Gestión de tickets y solicitudes',                   'icon': 'ti-layout-dashboard','clase': 'icon-admin', 'url': '/tickets/dashboard_administracion/'},
    'tecnicos':             {'titulo': 'Soporte Técnico',       'subtitulo': 'Gestión de tickets técnicos',                       'icon': 'ti-tools',           'clase': 'icon-tech',  'url': '/tickets/dashboard/'},
    'enfermeria':           {'titulo': 'Enfermería',            'subtitulo': 'Atención médica y control de medicamentos',          'icon': 'ti-first-aid-kit',   'clase': 'icon-enf',   'url': '/enfermeria/'},
    'inventario':           {'titulo': 'Inventario',            'subtitulo': 'Control de equipos y recursos',                     'icon': 'ti-package',         'clase': 'icon-inv',   'url': '/inventario/'},
    'reloj':                {'titulo': 'Control de Reloj',      'subtitulo': 'Gestión de asistencia y horarios',                  'icon': 'ti-clock',           'clase': 'icon-reloj', 'url': '/reloj/'},
}

_ROLES_POR_USUARIO = {
    'druiz@ana-hn.org': [
        {'titulo': 'Coordinador Bilingüe',  'subtitulo': 'Ver reportes del área BL · gestionar incidencias',  'icon': 'ti-users-group',     'clase': 'icon-coord', 'url': '/accounts/aplicar-rol/coordinador/'},
        {'titulo': 'Maestro – Bilingüe',    'subtitulo': 'Registrar y ver mis reportes del área BL',          'icon': 'ti-school',          'clase': 'icon-bl',    'url': '/accounts/aplicar-rol/maestro_bl/'},
        {'titulo': 'Maestro – Colegio',     'subtitulo': 'Registrar y ver mis reportes del área Colegio',     'icon': 'ti-building-school', 'clase': 'icon-col',   'url': '/accounts/aplicar-rol/maestro_col/'},
    ],
    'admin2@ana-hn.org': [
        {'titulo': 'Maestro – Bilingüe',    'subtitulo': 'Registrar y ver mis reportes del área BL',          'icon': 'ti-school',          'clase': 'icon-bl',    'url': '/accounts/aplicar-rol/maestro_bl/'},
        {'titulo': 'Maestro – Colegio',     'subtitulo': 'Registrar y ver mis reportes del área Colegio',     'icon': 'ti-building-school', 'clase': 'icon-col',   'url': '/accounts/aplicar-rol/maestro_col/'},
    ],
    'glorenzo@ana-hn.org': [
        {'titulo': 'Control de Reloj',      'subtitulo': 'Gestión de asistencia y horarios',                  'icon': 'ti-clock',           'clase': 'icon-reloj', 'url': '/reloj/'},
        {'titulo': 'Inventario',            'subtitulo': 'Control de equipos y recursos',                     'icon': 'ti-package',         'clase': 'icon-inv',   'url': '/inventario/'},
    ],
}

_ROLES_MAESTRO_DUAL = [
    {'titulo': 'Maestro – Bilingüe', 'subtitulo': 'Registrar y ver mis reportes del área BL',      'icon': 'ti-school',          'clase': 'icon-bl',  'url': '/accounts/aplicar-rol/maestro_bl/'},
    {'titulo': 'Maestro – Colegio',  'subtitulo': 'Registrar y ver mis reportes del área Colegio', 'icon': 'ti-building-school', 'clase': 'icon-col', 'url': '/accounts/aplicar-rol/maestro_col/'},
]

@login_required
def seleccion_rol(request):
    # Ventana retirada: el Panel General reemplaza la selección de rol.
    # Multi-rol → panel general; el resto → su inicio normal.
    from .panel_roles import es_multi_panel
    if es_multi_panel(request.user):
        return redirect('panel_general')
    return redirect('menu')


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
                if cargo == 'docente':
                    group_name = 'maestros_bilingue'
                else:
                    group_name = 'coordinador_bilingue'
                    user.is_staff = True
            elif area == 'colegio':
                if cargo == 'docente':
                    group_name = 'maestros_colegio'
                elif cargo == 'instructor_cfp':
                    group_name = 'instructores'   # solo ve Notas CFP + Tickets
                else:
                    group_name = 'coordinador_colegio'
                    user.is_staff = True
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
    Superusers y administración ven el panel completo.
    Coordinadores, maestros y técnicos son redirigidos a su dashboard.
    """
    user = request.user

    # ── Redirigir a usuarios que tienen su propio dashboard ──────────────────
    if not user.is_superuser:
        # Staff multi-rol → dashboard general (todos sus botones en un solo lugar)
        from .panel_roles import es_multi_panel
        if es_multi_panel(user):
            return redirect('panel_general')

        # Solo Progress → progress report directo
        if user.groups.filter(name='solo_progress').exists():
            return redirect('progress_report_bilingue')

        # Técnicos → tickets
        if user.groups.filter(name='tecnicos').exists():
            return redirect('tickets_dashboard')

        # Reloj → dashboard reloj
        if user.groups.filter(name='reloj').exists() and not user.groups.filter(
            name__in=['administracion', 'coordinador_bilingue', 'coordinadores_colegio',
                      'coordinador_colegio', 'coordinadores', 'maestros_bilingue', 'maestros_colegio']
        ).exists():
            return redirect('reloj_dashboard')

        # Administración → su dashboard
        if user.groups.filter(name='administracion').exists() and not user.groups.filter(
            name__in=['coordinador_bilingue', 'coordinadores_colegio', 'coordinador_colegio',
                      'coordinadores', 'maestros_bilingue', 'maestros_colegio']
        ).exists():
            return redirect('dashboard_administracion')

        # Staff (coordinadores) en modo maestro → dashboard maestro
        if user.is_staff and request.session.get('agenda_modo_maestro'):
            return redirect('dashboard_maestro')

        # Staff (coordinadores) en modo coordinador
        if user.is_staff:
            if user.groups.filter(name__in=['coordinadores_colegio', 'coordinador_colegio', 'coordinadores']).exists():
                return redirect('dashboard_coordinador', area='colegio')
            if user.groups.filter(name__in=['coordinador_bilingue', 'coordinador_bl', 'coord_progress_bl']).exists():
                return redirect('dashboard_coordinador', area='bilingue')

        # Maestros regulares
        in_mbl  = user.groups.filter(name='maestros_bilingue').exists()
        in_mcol = user.groups.filter(name='maestros_colegio').exists()
        if in_mbl or in_mcol:
            # maestro en ambas áreas → panel general (con toggle); si no, su dashboard
            if in_mbl and in_mcol:
                return redirect('panel_general')
            return redirect('dashboard_maestro')
    # ─────────────────────────────────────────────────────────────────────────

    year = datetime.datetime.now().year

    # =====================================================
    # 🔥 TICKETS (todos los NO resueltos)
    # =====================================================
    tickets_pendientes = Ticket.objects.exclude(status__iexact="Resuelto").count()

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
        'reportes_bl': reportes_bl,
        'reportes_col': reportes_col,
        'reloj_pendientes': reloj_pendientes,

        # ---------- Mostrar/ocultar TODAS las tarjetas ----------
        'show_cards': show_cards,

        # ---------- Visibilidad según rol ----------
        'is_administracion': is_administracion,

        'show_inventory':   is_admin or can_view_inventory or is_group_inventario,
        'show_maintenance': is_admin or can_view_maintenance,
        'show_camaras_inv': is_admin or can_view_inventory or can_view_maintenance or is_group_inventario,
        'show_tickets':     is_admin or can_view_tickets or is_administracion or user.groups.filter(name='instructores').exists(),
        'show_sponsors':    is_admin or can_view_sponsors,
        'show_cfp':         user.is_superuser or user.groups.filter(name__in=['director_cfp', 'instructores']).exists(),
        'show_enfermeria':  is_admin or is_group_enfermeria or is_coord_bilingue,
        'show_reloj':       is_admin or is_group_reloj,

        'show_coordinador_bilingue': is_admin or is_coord_bilingue,
        'show_coordinador_colegio':  is_admin or is_coord_colegio,
        'show_agendas':        is_admin or is_coord_bilingue or is_coord_colegio or is_maestro_bilingue or is_maestro_colegio,
        'show_directorio':     is_admin or is_coord_bilingue or is_coord_colegio,
        'show_calculadoras':   is_admin or is_group_reloj,

        # Apps en construcción — solo superuser
        'show_atencion_padres': user.is_superuser,
        'show_salidas_bano':    user.is_superuser or user.groups.filter(
                                    name__in=['control baño coord', 'control baños col']
                                ).exists(),
        'show_camaras':         user.is_superuser,
    }

    # <--- hecho por claude code: pasar show_welcome al contexto antes de limpiar la sesión
    show_welcome = request.session.pop('show_welcome', False)
    context['show_welcome'] = show_welcome
    context['welcome_name']  = request.user.get_full_name() or request.user.username

    # Superusuario: panel acordeón con subdashboards por módulo
    if user.is_superuser:
        return render(request, 'accounts/panel_super.html', {
            'grupos': _grupos_super_con_hrefs(),  # <--- hecho por claude code: hrefs resueltos para el acordeón
            'tickets_pendientes': tickets_pendientes,
            'reportes_bl': reportes_bl,
            'reportes_col': reportes_col,
            'show_welcome': show_welcome,
            'welcome_name': context['welcome_name'],
        })

    return render(request, 'accounts/menu.html', context)


# <--- hecho por claude code: panel del superusuario por 6 grupos
GRUPOS_SUPER = [
    {'key': 'soporte', 'titulo': 'Soporte y TI', 'icon': 'ti-headset', 'color': '#206bc4',
     'desc': 'Tickets, inventario y mantenimiento',
     'cards': [
        {'t': 'Sistema de Tickets', 's': 'Gestión de solicitudes', 'i': 'ti-ticket', 'c': '#206bc4', 'url': 'technician_dashboard'},
        {'t': 'Inventario', 's': 'Control de activos', 'i': 'ti-package', 'c': '#2fb344', 'url': 'inventario:dashboard'},
        {'t': 'Mantenimiento', 's': 'Reportes de mantenimiento', 'i': 'ti-tool', 'c': '#d63939', 'url': 'mantenimiento:maintenance_dashboard'},
        {'t': 'Inventario y Mant. de Cámaras', 's': 'Cámaras, NVRs, gabinetes', 'i': 'ti-camera', 'c': '#4263eb', 'url': 'inventario_camaras:hub'},
     ]},
    {'key': 'academico', 'titulo': 'Académico', 'icon': 'ti-school', 'color': '#0ca678',
     'desc': 'Coordinación, agendas, enfermería y notas',
     'cards': [
        {'t': 'Coordinador BL', 's': 'Bilingüe', 'i': 'ti-chalkboard', 'c': '#0ca678', 'url': 'dashboard_coordinador', 'args': {'area': 'bilingue'}},
        {'t': 'Coordinador Colegio', 's': 'Colegio', 'i': 'ti-user-cog', 'c': '#f08c00', 'url': 'dashboard_coordinador', 'args': {'area': 'colegio'}},
        {'t': 'Agendas', 's': 'Agendas semanales', 'i': 'ti-calendar-week', 'c': '#7048e8', 'url': 'agendas:form_agenda'},
        {'t': 'Enfermería', 's': 'Panel de enfermería', 'i': 'ti-stethoscope', 'c': '#d63939', 'url': 'enfermeria:enfermeria_dashboard'},
        {'t': 'Directorio', 's': 'Teléfonos de alumnos', 'i': 'ti-address-book', 'c': '#2fb344', 'url': 'directorio_telefonos'},
        {'t': 'Notas Mitad de Parcial', 's': 'Revisión / Asignaciones', 'i': 'ti-file-certificate', 'c': '#206bc4', 'url': 'notas_parcial_index'},
        {'t': 'Ruteo Reportes BL', 's': 'Grupos, coordinadores y alumnado (todo en una hoja)', 'i': 'ti-route', 'c': '#4263eb', 'url': 'routing_bl_config'},
     ]},
    # <--- hecho por claude code: grupo propio para salidas (baño y, próximamente, permisos)
    {'key': 'salidas', 'titulo': 'Salidas', 'icon': 'ti-door-exit', 'color': '#0ca678',
     'desc': 'Salidas al baño y con permisos',
     'cards': [
        {'t': 'Salidas al baño', 's': 'Control de salidas al baño', 'i': 'ti-door-exit', 'c': '#0ca678', 'url': 'salidas_bano:index'},
     ]},
    {'key': 'reloj', 'titulo': 'Reloj y Sponsors', 'icon': 'ti-clock', 'color': '#f76707',
     'desc': 'Asistencia y patrocinadores',
     'cards': [
        {'t': 'Reloj', 's': 'Control de asistencia', 'i': 'ti-clock', 'c': '#f76707', 'url': 'reloj_dashboard'},
        {'t': 'Sponsors', 's': 'Gestión de patrocinadores', 'i': 'ti-heart-handshake', 'c': '#d6336c', 'url': 'sponsors:sponsors_dashboard'},
     ]},
    {'key': 'cfp', 'titulo': 'CFP', 'icon': 'ti-school', 'color': '#2fb344',
     'desc': 'Centro de Formación Profesional',
     'cards': [
        {'t': 'Contabilidad CFP', 's': 'Talleres y cursos del CFP', 'i': 'ti-calculator', 'c': '#2fb344', 'url': 'cfp:dashboard'},
        {'t': 'Notas CFP', 's': 'Registro de notas por curso', 'i': 'ti-list-numbers', 'c': '#206bc4', 'url': 'cfp:notas_cursos'},
     ]},
    {'key': 'monitoreo', 'titulo': 'Monitoreo', 'icon': 'ti-chart-histogram', 'color': '#d6336c',
     'desc': 'Auditoría y actividad del sistema',
     'cards': [
        {'t': 'Auditoría', 's': 'Cambios del sistema', 'i': 'ti-shield-check', 'c': '#206bc4', 'url': 'settings_auditoria'},
        {'t': 'Actividad', 's': 'Logs de actividad', 'i': 'ti-activity', 'c': '#0ca678', 'url': 'settings_actividad'},
     ]},
    {'key': 'permisos', 'titulo': 'Permisos', 'icon': 'ti-shield-lock', 'color': '#7048e8',
     'desc': 'Accesos, coordinadores y desbloqueo de login',
     'cards': [
        {'t': 'Permisos Reloj', 's': 'Acceso por usuario', 'i': 'ti-clock-cog', 'c': '#f76707', 'url': 'settings_reloj_permisos'},
        {'t': 'Permisos Coordinadores', 's': 'Acceso coordinadores', 'i': 'ti-users-group', 'c': '#7048e8', 'url': 'settings_coord_permisos'},
        {'t': 'Desbloqueo de accesos', 's': 'Cuentas bloqueadas por login', 'i': 'ti-lock-open', 'c': '#2fb344', 'url': 'settings_desbloqueos'},
     ]},
    {'key': 'config', 'titulo': 'Configuración', 'icon': 'ti-settings', 'color': '#4263eb',
     'desc': 'Configuración de correos',
     'cards': [
        {'t': 'Correos', 's': 'Configuración de correos', 'i': 'ti-mail', 'c': '#d63939', 'url': 'settings_correos'},
     ]},
    {'key': 'construccion', 'titulo': 'Modo Mantenimiento', 'icon': 'ti-tool', 'color': '#f59f00',
     'desc': 'Bloquear el sistema temporalmente',
     'cards': [
        {'t': 'Modo Mantenimiento', 's': 'Bloquear el sistema temporalmente', 'i': 'ti-tool', 'c': '#f59f00', 'url': 'mantenimiento_modo'},
     ]},
]


# <--- hecho por claude code: resuelve los href de cada tarjeta para el panel acordeón
def _reverse_seguro(name, args=None):
    if not name:
        return ''
    try:
        return reverse(name, kwargs=args) if args else reverse(name)
    except Exception:
        return ''


def _grupos_super_con_hrefs():
    return [
        {**g, 'cards': [{**c, 'href': _reverse_seguro(c.get('url'), c.get('args'))} for c in g['cards']]}
        for g in GRUPOS_SUPER
    ]


@login_required
def panel_grupo(request, grupo):
    """Vista de un grupo del panel del superusuario (estilo Panel General)."""
    if not request.user.is_superuser:
        return redirect('menu')
    g = next((x for x in GRUPOS_SUPER if x['key'] == grupo), None)
    if not g:
        from django.http import Http404
        raise Http404('Grupo no encontrado')

    def _u(name, args=None):
        if not name:
            return ''
        try:
            return reverse(name, kwargs=args) if args else reverse(name)
        except Exception:
            return ''
    cards = [{**c, 'href': _u(c.get('url'), c.get('args'))} for c in g['cards']]
    return render(request, 'accounts/panel_grupo.html', {
        'titulo': g['titulo'], 'icon': g['icon'], 'desc': g.get('desc', ''),
        'cards': cards, 'wip': g.get('wip', False),
    })


# ── Modo Mantenimiento (página propia, grupo "En construcción") ──────────────
@login_required
def mantenimiento_modo(request):
    if not request.user.is_superuser:
        return redirect('menu')
    todos_usuarios = User.objects.filter(is_active=True).exclude(email='').order_by('first_name', 'last_name')
    # <--- hecho por claude code: módulos bloqueables (normal | lectura | bloqueado)
    from constance import config as _cfg
    from core.maintenance_modules import modulos_para_ui, ESTADO_LABELS
    return render(request, 'accounts/mantenimiento_modo.html', {
        'todos_usuarios': todos_usuarios,
        'mant_modulos': modulos_para_ui(_cfg),
        'mant_estados': ESTADO_LABELS,
    })


# ── Desbloqueo de accesos (cuentas bloqueadas por intentos de login) ─────────
@login_required
def settings_desbloqueos(request):
    if not request.user.is_superuser:
        return redirect('menu')
    perfiles = (PerfilUsuario.objects
                .filter(login_bloqueado=True).select_related('usuario')
                .order_by('-login_bloqueado_en'))
    bloqueados = [{
        'user_id': p.usuario_id,
        'nombre':  p.usuario.get_full_name() or p.usuario.username,
        'email':   p.usuario.email or p.usuario.username,
        'fecha':   p.login_bloqueado_en,
    } for p in perfiles]
    return render(request, 'accounts/settings_desbloqueos.html', {
        'active_tab': 'desbloqueos',
        'bloqueados': bloqueados,
        'can_manage_users': request.user.is_superuser,
        'can_see_activity': request.user.is_superuser,
    })


@login_required
def desbloquear_usuario(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    try:
        p = PerfilUsuario.objects.select_related('usuario').get(usuario_id=request.POST.get('user_id'))
    except PerfilUsuario.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No encontrado'}, status=404)
    p.login_bloqueado = False
    p.login_bloqueado_en = None
    p.save(update_fields=['login_bloqueado', 'login_bloqueado_en'])
    _reset_login_fails(_login_key(p.usuario.username))   # limpia contadores de cache
    return JsonResponse({'ok': True})


@login_required
def panel_general(request):
    """Dashboard general para staff multi-rol: todos los botones en un solo lugar,
    visibles según el grupo. El toggle Bilingüe/Colegio solo aparece para quien
    es maestro en ambas áreas (maestros_bilingue Y maestros_colegio)."""
    from .panel_roles import maestro_dos_areas, _g, _GRUPOS_COORD_BL, _GRUPOS_COORD_COL
    user = request.user
    ctx = {
        'show_tickets':     user.is_superuser or _g(user, 'administracion') or user.has_perm('tickets.view_ticket'),
        'show_coord_bl':    _g(user, *_GRUPOS_COORD_BL),
        'show_coord_col':   _g(user, *_GRUPOS_COORD_COL),
        'show_maestro_bl':  _g(user, 'maestros_bilingue'),
        'show_maestro_col': _g(user, 'maestros_colegio'),
        'show_enfermeria':  _g(user, *_GRUPOS_COORD_BL),
        'show_reloj':       user.is_superuser or _g(user, 'reloj'),
        'toggle_area':      maestro_dos_areas(user),
        'welcome_name':     user.get_full_name() or user.username,
    }
    return render(request, 'accounts/dashboard_general.html', ctx)




# =====================================================
# 📧 REENVÍO DE CORREO DE BIENVENIDA (solo superuser)
# =====================================================
@login_required
def usuarios_lista_json(request):
    """Devuelve lista de usuarios activos con email como JSON (solo superuser)."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False}, status=403)
    usuarios = (
        User.objects.filter(is_active=True).exclude(email='')
        .order_by('first_name', 'last_name')
        .values('email', 'first_name', 'last_name', 'username')
    )
    data = [
        {
            'email': u['email'],
            'nombre': f"{u['first_name']} {u['last_name']}".strip() or u['username'],
        }
        for u in usuarios
    ]
    return JsonResponse({'ok': True, 'usuarios': data})


@login_required
def reenviar_bienvenida(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    modo = request.POST.get('modo', 'todos')  # 'todos' o 'uno'
    email_destino = request.POST.get('email', '').strip()
    mensaje_extra = request.POST.get('mensaje_extra', '').strip()

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
            + (f'{mensaje_extra}\n\n' if mensaje_extra else '')
            + f'Accede en: {SITE_URL}'
        )
        bloque_mensaje_extra = ""
        if mensaje_extra:
            lineas_html = "".join(
                f'<span style="font-size:14px;color:#1a1a2e;">{linea}</span><br>'
                for linea in mensaje_extra.splitlines()
            )
            bloque_mensaje_extra = f"""
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="background:#fff8e1;border-left:4px solid #f59f00;border-radius:4px;padding:16px 20px;margin-bottom:24px;">
            <tr><td>
              <span style="font-size:12px;color:#f59f00;text-transform:uppercase;letter-spacing:.5px;font-weight:700;">
                Mensaje del administrador
              </span><br><br>
              {lineas_html}
            </td></tr>
          </table>"""
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
          {bloque_mensaje_extra}
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


# =====================================================
# ⚙ ACCOUNT SETTINGS — helpers
# =====================================================
def _settings_ctx(request, tab):
    perfil = getattr(request.user, 'perfil', None)
    can_manage = (
        request.user.is_superuser or
        (request.user.is_staff and perfil is not None and perfil.puede_ver_usuarios)
    )
    return {
        'active_tab':       tab,
        'can_manage_users': can_manage,
        'can_see_activity': request.user.is_superuser,
    }


# ── 1. Mi Perfil ──────────────────────────────────────────────
@login_required
def settings_perfil(request):
    user = request.user
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)

    if request.method == 'POST':
        action = request.POST.get('action', 'perfil')

        if action == 'perfil':
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name  = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            if email and email != user.email:
                if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                    messages.error(request, 'Ese correo ya está en uso por otro usuario.')
                    return redirect('settings_perfil')
                user.email = email
            user.save()
            if 'avatar' in request.FILES:
                if perfil.avatar:
                    perfil.avatar.delete(save=False)
                perfil.avatar = request.FILES['avatar']
                perfil.save()
            messages.success(request, 'Perfil actualizado correctamente.')

        elif action == 'delete_avatar':
            if perfil.avatar:
                perfil.avatar.delete(save=False)
                perfil.avatar = None
                perfil.save()
            messages.success(request, 'Avatar eliminado.')

        elif action == 'password':
            old_pw  = request.POST.get('old_password', '')
            new_pw  = request.POST.get('new_password', '')
            confirm = request.POST.get('confirm_password', '')
            if not user.check_password(old_pw):
                messages.error(request, 'Contraseña actual incorrecta.')
            elif new_pw != confirm:
                messages.error(request, 'Las contraseñas nuevas no coinciden.')
            elif len(new_pw) < 8:
                messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            else:
                from django.contrib.auth import update_session_auth_hash
                user.set_password(new_pw)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña actualizada correctamente.')

        return redirect('settings_perfil')

    ctx = _settings_ctx(request, 'perfil')
    ctx['perfil'] = perfil
    return render(request, 'accounts/settings_perfil.html', ctx)


# ── 2. Mis Notificaciones ─────────────────────────────────────
@login_required
def settings_notificaciones(request):
    from core.models import Notificacion
    notificaciones = Notificacion.objects.filter(
        destinatario=request.user
    ).order_by('-fecha')

    ctx = _settings_ctx(request, 'notificaciones')
    ctx['notificaciones'] = notificaciones
    return render(request, 'accounts/settings_notificaciones.html', ctx)


# ── 3. Usuarios (staff) ───────────────────────────────────────
def _can_manage(user):
    perfil = getattr(user, 'perfil', None)
    return user.is_superuser or (user.is_staff and perfil is not None and perfil.puede_ver_usuarios)


def settings_usuarios(request):
    if not _can_manage(request.user):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('settings_perfil')

    from django.db.models import Q, Subquery, OuterRef

    q            = request.GET.get('q', '').strip()
    grupo_filtro = request.GET.get('grupo', '').strip()

    def _qs(base):
        return base.prefetch_related('groups').order_by('first_name', 'last_name', 'username')

    def _filter(qs):
        if q:
            qs = qs.filter(
                Q(username__icontains=q) | Q(first_name__icontains=q) |
                Q(last_name__icontains=q) | Q(email__icontains=q)
            )
        return qs

    superusers  = _filter(_qs(User.objects.filter(is_superuser=True)))

    reg_base = User.objects.filter(is_staff=False, is_superuser=False)
    if grupo_filtro:
        reg_base = reg_base.filter(groups__name=grupo_filtro)
    reg_users = _filter(_qs(reg_base))

    staff_base = User.objects.filter(is_staff=True, is_superuser=False)
    if grupo_filtro:
        staff_base = staff_base.filter(groups__name=grupo_filtro)
    staff_users = _filter(
        _qs(staff_base).annotate(
            puede_ver=Subquery(
                PerfilUsuario.objects.filter(usuario_id=OuterRef('pk')).values('puede_ver_usuarios')[:1]
            )
        )
    )

    todos_grupos = Group.objects.all().order_by('name')

    ctx = _settings_ctx(request, 'usuarios')
    ctx.update({
        'superusers':    superusers,
        'staff_users':   staff_users,
        'reg_users':     reg_users,
        'q':             q,
        'grupo_filtro':  grupo_filtro,
        'todos_grupos':  todos_grupos,
    })
    return render(request, 'accounts/settings_usuarios.html', ctx)


@login_required
def settings_usuario_crear(request):
    if not _can_manage(request.user):
        return redirect('settings_perfil')

    grupos = Group.objects.all().order_by('name')

    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        password   = request.POST.get('password', '')
        is_staff   = request.POST.get('is_staff') == 'on'
        is_active  = request.POST.get('is_active', 'on') == 'on'
        group_ids  = request.POST.getlist('groups')

        if not username or not password:
            messages.error(request, 'El usuario y la contraseña son obligatorios.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, f'El usuario "{username}" ya existe.')
        else:
            u = User.objects.create_user(
                username=username, email=email, password=password,
                first_name=first_name, last_name=last_name,
                is_staff=is_staff, is_active=is_active,
            )
            if group_ids:
                u.groups.set(Group.objects.filter(pk__in=group_ids))
            messages.success(request, f'Usuario "{username}" creado correctamente.')
            return redirect('settings_usuarios')

    ctx = _settings_ctx(request, 'usuarios')
    ctx.update({'grupos': grupos, 'modo': 'crear'})
    return render(request, 'accounts/settings_usuario_form.html', ctx)


@login_required
def settings_usuario_editar(request, pk):
    if not _can_manage(request.user):
        return redirect('settings_perfil')

    u      = get_object_or_404(User, pk=pk)
    grupos = Group.objects.all().order_by('name')

    if request.method == 'POST':
        u.first_name = request.POST.get('first_name', '').strip()
        u.last_name  = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        if email and email != u.email:
            if not User.objects.filter(email=email).exclude(pk=pk).exists():
                u.email = email
        u.is_staff  = request.POST.get('is_staff') == 'on'
        u.is_active = request.POST.get('is_active') == 'on'
        if request.user.is_superuser:
            u.is_superuser = request.POST.get('is_superuser') == 'on'
        new_pw = request.POST.get('password', '').strip()
        if new_pw:
            u.set_password(new_pw)
        group_ids = request.POST.getlist('groups')
        u.groups.set(Group.objects.filter(pk__in=group_ids))
        u.save()
        # Actualizar permiso puede_ver_usuarios (solo superuser puede otorgarlo)
        if request.user.is_superuser:
            perfil_u, _ = PerfilUsuario.objects.get_or_create(usuario=u)
            perfil_u.puede_ver_usuarios = request.POST.get('puede_ver_usuarios') == 'on'
            perfil_u.save()
        messages.success(request, f'Usuario "{u.username}" actualizado.')
        return redirect('settings_usuarios')

    perfil_u, _ = PerfilUsuario.objects.get_or_create(usuario=u)
    ctx = _settings_ctx(request, 'usuarios')
    ctx.update({'edit_user': u, 'grupos': grupos, 'modo': 'editar', 'perfil_edit': perfil_u})
    return render(request, 'accounts/settings_usuario_form.html', ctx)


@login_required
def settings_usuario_eliminar(request, pk):
    if not _can_manage(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    u = get_object_or_404(User, pk=pk)
    if u == request.user:
        return JsonResponse({'ok': False, 'error': 'No puedes eliminarte a ti mismo.'})
    nombre = u.get_full_name() or u.username
    u.delete()
    return JsonResponse({'ok': True, 'nombre': nombre})


@login_required
def settings_usuario_toggle_perms(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuarios pueden cambiar este permiso.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    u = get_object_or_404(User, pk=pk)
    if not u.is_staff or u.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo aplica a usuarios staff.'})
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=u)
    perfil.puede_ver_usuarios = not perfil.puede_ver_usuarios
    perfil.save()
    return JsonResponse({'ok': True, 'puede_ver': perfil.puede_ver_usuarios})


# ── 4. Grupos (staff) ─────────────────────────────────────────
@login_required
def settings_grupos(request):
    if not _can_manage(request.user):
        return redirect('settings_perfil')

    grupos = Group.objects.prefetch_related('user_set').order_by('name')
    ctx = _settings_ctx(request, 'grupos')
    ctx['grupos'] = grupos
    return render(request, 'accounts/settings_grupos.html', ctx)


@login_required
def settings_grupo_crear(request):
    if not _can_manage(request.user):
        return redirect('settings_perfil')

    if request.method == 'POST':
        nombre = request.POST.get('name', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del grupo es obligatorio.')
        elif Group.objects.filter(name=nombre).exists():
            messages.error(request, f'El grupo "{nombre}" ya existe.')
        else:
            Group.objects.create(name=nombre)
            messages.success(request, f'Grupo "{nombre}" creado correctamente.')
            return redirect('settings_grupos')

    ctx = _settings_ctx(request, 'grupos')
    ctx['modo'] = 'crear'
    return render(request, 'accounts/settings_grupo_form.html', ctx)


@login_required
def settings_grupo_editar(request, pk):
    if not _can_manage(request.user):
        return redirect('settings_perfil')

    g = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        nombre = request.POST.get('name', '').strip()
        if not nombre:
            messages.error(request, 'El nombre es obligatorio.')
        elif Group.objects.filter(name=nombre).exclude(pk=pk).exists():
            messages.error(request, f'El grupo "{nombre}" ya existe.')
        else:
            g.name = nombre
            g.save()
            messages.success(request, f'Grupo actualizado a "{nombre}".')
            return redirect('settings_grupos')

    ctx = _settings_ctx(request, 'grupos')
    ctx.update({'edit_group': g, 'modo': 'editar'})
    return render(request, 'accounts/settings_grupo_form.html', ctx)


@login_required
def settings_grupo_eliminar(request, pk):
    if not _can_manage(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    g = get_object_or_404(Group, pk=pk)
    nombre = g.name
    g.delete()
    return JsonResponse({'ok': True, 'nombre': nombre})


@login_required
def settings_usuarios_asignar_grupos(request):
    if not _can_manage(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    user_pks  = request.POST.getlist('user_pks')
    group_pks = request.POST.getlist('group_pks')
    modo      = request.POST.get('modo', 'agregar')
    if not user_pks or not group_pks:
        return JsonResponse({'ok': False, 'error': 'Selecciona al menos un usuario y un grupo.'})
    users  = User.objects.filter(pk__in=user_pks)
    groups = Group.objects.filter(pk__in=group_pks)
    for u in users:
        if modo == 'reemplazar':
            u.groups.set(groups)
        else:
            u.groups.add(*groups)
    return JsonResponse({'ok': True, 'count': users.count()})


@login_required
def settings_grupo_usuarios(request, pk):
    if not _can_manage(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    g = get_object_or_404(Group, pk=pk)
    usuarios = list(
        g.user_set.values('id', 'username', 'first_name', 'last_name', 'is_active')
        .order_by('username')
    )
    return JsonResponse({'ok': True, 'nombre': g.name, 'usuarios': usuarios})


# ── 5. Actividad (superuser) ──────────────────────────────────
@login_required
def settings_actividad(request):
    if not request.user.is_superuser:
        messages.error(request, 'Solo superusuarios pueden ver la actividad del sistema.')
        return redirect('settings_perfil')

    from core.models import Notificacion
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    import json

    today   = datetime.date.today()
    hace_30 = today - datetime.timedelta(days=29)

    # Logins por día – últimos 30 días
    logins_dia = (
        RegistroAcceso.objects
        .filter(fecha_hora__date__gte=hace_30)
        .annotate(dia=TruncDate('fecha_hora'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )
    dia_map     = {item['dia']: item['total'] for item in logins_dia}
    dias_labels, dias_data = [], []
    for i in range(30):
        d = hace_30 + datetime.timedelta(days=i)
        dias_labels.append(d.strftime('%d/%m'))
        dias_data.append(dia_map.get(d, 0))

    # Top 10 usuarios por accesos
    top_usuarios = list(
        RegistroAcceso.objects
        .filter(fecha_hora__date__gte=hace_30)
        .values('username')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )

    total_users      = User.objects.count()
    active_users     = User.objects.filter(is_active=True).count()
    staff_users      = User.objects.filter(is_staff=True, is_superuser=False).count()
    super_users      = User.objects.filter(is_superuser=True).count()
    total_logins     = RegistroAcceso.objects.count()
    logins_hoy       = RegistroAcceso.objects.filter(fecha_hora__date=today).count()
    total_notifs     = Notificacion.objects.count()
    notifs_no_leidas = Notificacion.objects.filter(leida=False).count()
    accesos_recientes = RegistroAcceso.objects.select_related('usuario').order_by('-fecha_hora')[:50]

    ctx = _settings_ctx(request, 'actividad')
    ctx.update({
        'dias_labels_json': json.dumps(dias_labels),
        'dias_data_json':   json.dumps(dias_data),
        'top_usuarios':     top_usuarios,
        'top_labels_json':  json.dumps([u['username'] for u in top_usuarios]),
        'top_data_json':    json.dumps([u['total']    for u in top_usuarios]),
        'total_users':       total_users,
        'active_users':      active_users,
        'staff_users':       staff_users,
        'super_users':       super_users,
        'total_logins':      total_logins,
        'logins_hoy':        logins_hoy,
        'total_notifs':      total_notifs,
        'notifs_no_leidas':  notifs_no_leidas,
        'accesos_recientes': accesos_recientes,
    })
    return render(request, 'accounts/settings_actividad.html', ctx)


# ── 6. Config. Coordinadores (superuser) ────────────────────
@login_required
def settings_coordinadores(request):
    if not request.user.is_superuser:
        return redirect('settings_perfil')
    from conducta.models import ConfiguracionCoordinador

    if request.method == 'POST':
        pk      = request.POST.get('pk') or None
        area    = request.POST.get('area', '').strip()
        codigo  = request.POST.get('codigo', '').strip()
        nombre  = request.POST.get('nombre', '').strip()
        uid     = request.POST.get('usuario_id') or None
        activo  = request.POST.get('activo') == 'on'
        if not nombre:
            messages.error(request, 'El nombre es obligatorio.')
        elif pk:
            obj = get_object_or_404(ConfiguracionCoordinador, pk=pk)
            obj.area = area; obj.codigo = codigo; obj.nombre = nombre
            obj.usuario_id = uid; obj.activo = activo
            obj.save()
            messages.success(request, f'Coordinador "{nombre}" actualizado.')
        else:
            ConfiguracionCoordinador.objects.create(
                area=area, codigo=codigo, nombre=nombre, usuario_id=uid, activo=activo)
            messages.success(request, f'Coordinador "{nombre}" creado.')
        return redirect('settings_coordinadores')

    ctx = _settings_ctx(request, 'coordinadores')
    ctx.update({
        'coordinadores': ConfiguracionCoordinador.objects.select_related('usuario').order_by('area', 'codigo'),
        'todos_usuarios': User.objects.filter(is_active=True).exclude(email='').order_by('first_name', 'last_name'),
    })
    return render(request, 'accounts/settings_coordinadores.html', ctx)


@login_required
def settings_coordinador_eliminar(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    from conducta.models import ConfiguracionCoordinador
    obj = get_object_or_404(ConfiguracionCoordinador, pk=pk)
    nombre = obj.nombre
    obj.delete()
    return JsonResponse({'ok': True, 'nombre': nombre})


# ── 7. Config. Notificaciones Conducta (superuser) ───────────
@login_required
def settings_notificaciones_conducta(request):
    if not request.user.is_superuser:
        return redirect('settings_perfil')
    from conducta.models import ConfiguracionNotificacion, ConfiguracionCoordinador

    if request.method == 'POST':
        pk   = request.POST.get('pk') or None
        area = request.POST.get('area', '').strip()
        cid  = request.POST.get('coordinador_id') or None
        data = {
            'area': area, 'coordinador_id': cid,
            'recibe_conductual':             request.POST.get('recibe_conductual') == 'on',
            'recibe_informativo_academico':  request.POST.get('recibe_informativo_academico') == 'on',
            'recibe_informativo_conductual': request.POST.get('recibe_informativo_conductual') == 'on',
            'recibe_progress':               request.POST.get('recibe_progress') == 'on',
            'activo':                        request.POST.get('activo') == 'on',
        }
        try:
            if pk:
                obj = get_object_or_404(ConfiguracionNotificacion, pk=pk)
                for k, v in data.items():
                    setattr(obj, k, v)
                obj.save()
                messages.success(request, 'Regla actualizada correctamente.')
            else:
                ConfiguracionNotificacion.objects.create(**data)
                messages.success(request, 'Regla creada correctamente.')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('settings_notificaciones_conducta')

    ctx = _settings_ctx(request, 'notificaciones_conducta')
    ctx.update({
        'reglas':        ConfiguracionNotificacion.objects.select_related('coordinador__usuario').order_by('area', 'coordinador__nombre'),
        'coordinadores': ConfiguracionCoordinador.objects.filter(activo=True).order_by('area', 'codigo', 'nombre'),
    })
    return render(request, 'accounts/settings_notificaciones_conducta.html', ctx)


@login_required
def settings_notificacion_eliminar(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    from conducta.models import ConfiguracionNotificacion
    obj = get_object_or_404(ConfiguracionNotificacion, pk=pk)
    nombre = str(obj)
    obj.delete()
    return JsonResponse({'ok': True, 'nombre': nombre})


# ── 8. Config. Roles coord-maestro (superuser) ───────────────
@login_required
def settings_roles(request):
    if not request.user.is_superuser:
        return redirect('settings_perfil')

    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        uid    = request.POST.get('user_id') or None
        if not uid:
            messages.error(request, 'Usuario no especificado.')
            return redirect('settings_roles')
        target = get_object_or_404(User, pk=uid)
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=target)

        if accion == 'toggle_coord_maestro':
            perfil.es_coord_maestro = not perfil.es_coord_maestro
            perfil.save()
            estado = 'activado' if perfil.es_coord_maestro else 'desactivado'
            messages.success(request, f'Modo coord-maestro {estado} para {target.get_full_name() or target.username}.')

        elif accion == 'toggle_staff':
            if target == request.user:
                messages.error(request, 'No puedes modificar tu propio estado staff.')
            else:
                target.is_staff = not target.is_staff
                target.save()
                estado = 'activado' if target.is_staff else 'desactivado'
                messages.success(request, f'Staff {estado} para {target.get_full_name() or target.username}.')

        elif accion == 'set_grupos':
            grupo_ids = request.POST.getlist('grupos')
            target.groups.set(Group.objects.filter(pk__in=grupo_ids))
            messages.success(request, f'Grupos actualizados para {target.get_full_name() or target.username}.')

        return redirect('settings_roles')

    ctx = _settings_ctx(request, 'roles')
    usuarios = (User.objects
                .prefetch_related('groups', 'perfil')
                .filter(is_active=True)
                .exclude(is_superuser=True)
                .order_by('first_name', 'last_name', 'username'))
    ctx.update({
        'usuarios_roles': usuarios,
        'todos_grupos':   Group.objects.order_by('name'),
    })
    return render(request, 'accounts/settings_roles.html', ctx)


@login_required
def settings_reloj_permisos(request):
    if not request.user.is_superuser:
        return redirect('settings_perfil')

    EMAILS_RELOJ = ['glorenzo@ana-hn.org', 'yzavala@ana-hn.org']
    usuarios = list(
        User.objects.filter(email__in=EMAILS_RELOJ, is_active=True).order_by('first_name', 'last_name')
    )

    for u in usuarios:
        RelojPermiso.objects.get_or_create(user=u)

    # has_edit=True: módulo tiene Ver+Editar+Eliminar. False: solo Ver.
    MODULOS = [
        ('reporte',       'Generar Reporte',        'ti-table',         True),
        ('plantilla',     'Plantilla de Horario',   'ti-stack',         True),
        ('asignacion',    'Asignación de Horario',  'ti-calendar-user', True),
        ('compensatorio', 'Tiempo Compensatorio',   'ti-clock-check',   True),
        ('feriado',       'Feriados',               'ti-calendar',      True),
        ('sabado',        'Sábados Especiales',     'ti-calendar-week', True),
        ('calculo_comp',  'Control Compensatorio',  'ti-calculator',    True),
        ('vacaciones',    'Vacaciones',             'ti-beach',         True),
        ('permisos',      'Permisos Emp.',          'ti-license',       False),
        ('reportes_pdf',  'Reportes PDF',           'ti-file-download', False),
        ('vigilancia',    'Vigilancia',             'ti-shield',        False),
    ]

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        import json as _json
        body    = _json.loads(request.body or b'{}')
        user_id = int(body.get('user_id', 0))
        campo   = body.get('campo', '')
        valor   = bool(body.get('valor', False))
        try:
            u   = User.objects.get(pk=user_id, email__in=EMAILS_RELOJ)
            obj = RelojPermiso.objects.get(user=u)
            # Permiso PROVISIONAL para registrar permisos: guarda fecha/hora límite (o la limpia)
            if campo == 'permisos_registrar_hasta':
                raw = (body.get('valor') or '').strip()
                if raw:
                    from datetime import datetime as _dt
                    try:
                        obj.permisos_registrar_hasta = _dt.strptime(raw, '%Y-%m-%dT%H:%M')
                    except ValueError:
                        return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)
                else:
                    obj.permisos_registrar_hasta = None
                obj.save(update_fields=['permisos_registrar_hasta'])
                prh = obj.permisos_registrar_hasta
                return JsonResponse({'ok': True,
                                     'hasta': prh.strftime('%Y-%m-%dT%H:%M') if prh else '',
                                     'hasta_ms': int(prh.timestamp() * 1000) if prh else 0})
            if hasattr(obj, campo):
                setattr(obj, campo, valor)
                obj.save(update_fields=[campo])
                return JsonResponse({'ok': True})
        except Exception:
            pass
        return JsonResponse({'ok': False}, status=400)

    # Construir matrix transpuesta: usuario-centric
    _AVATAR_COLORS = ['blue','teal','green','orange','red','purple','cyan','pink']
    modulos_info = [
        {'key': k, 'label': l, 'icon': i, 'has_edit': he}
        for k, l, i, he in MODULOS
    ]

    matrix_usuarios = []
    for idx, u in enumerate(usuarios):
        try:
            perms = u.reloj_permiso
        except Exception:
            continue
        nombre = u.get_full_name() or u.username
        partes = nombre.split()
        initials = (partes[0][0] + partes[-1][0]).upper() if len(partes) >= 2 else nombre[:2].upper()
        celdas = []
        for mod_key, mod_label, mod_icon, has_edit in MODULOS:
            celdas.append({
                'key':      mod_key,
                'label':    mod_label,
                'icon':     mod_icon,
                'has_edit': has_edit,
                'ver':      getattr(perms, f'{mod_key}_ver',     False),
                'editar':   getattr(perms, f'{mod_key}_editar',  False) if has_edit else None,
                'eliminar': getattr(perms, f'{mod_key}_eliminar',False) if has_edit else None,
            })
        _prh = perms.permisos_registrar_hasta
        matrix_usuarios.append({
            'user':     u,
            'initials': initials,
            'color':    _AVATAR_COLORS[idx % len(_AVATAR_COLORS)],
            'ver_todos': perms.ver_todos,
            'celdas':   celdas,
            # Permiso provisional para registrar permisos fuera de fecha
            'permisos_hasta':    _prh.strftime('%Y-%m-%dT%H:%M') if _prh else '',
            'permisos_hasta_ms': int(_prh.timestamp() * 1000) if _prh else 0,
        })

    return render(request, 'accounts/settings_reloj_permisos.html', {
        'active_tab':       'reloj_permisos',
        'nav_home_url':     '/',
        'can_manage_users': request.user.is_superuser,
        'can_see_activity': request.user.is_superuser,
        'modulos':          modulos_info,
        'matrix_usuarios':  matrix_usuarios,
    })


@login_required
def settings_coord_permisos(request):
    """Panel de permisos Editar/Eliminar para coordinadores BL y Colegio."""
    from django.utils import timezone as _tz
    import datetime as _dt

    _DURACION_ELIMINAR = _dt.timedelta(hours=24)

    if not request.user.is_superuser:
        return redirect('settings_perfil')

    COORD_GRUPOS = [
        'coordinadores_colegio', 'coordinador_colegio', 'coordinadores', 'coordinador_col',
        'coordinador_bilingue',  'coordinador_bl',      'coord_progress_bl',
        'control baño coord',
    ]

    usuarios = list(
        User.objects.filter(groups__name__in=COORD_GRUPOS, is_active=True)
            .exclude(is_superuser=True)
            .distinct()
            .order_by('first_name', 'last_name')
    )

    for u in usuarios:
        CoordPermiso.objects.get_or_create(user=u)

    MODULOS = [
        ('notas',      'Notas Mitad de Parcial',    'ti-file-certificate'),
        ('salidas',    'Salidas Baño',               'ti-door-exit'),
        ('agenda',     'Agenda',                     'ti-calendar-week'),
        ('dashboard',  'Dashboard Coordinador',      'ti-layout-dashboard'),
    ]

    # Auto-expirar permisos de eliminación vencidos
    ahora = _tz.now()
    for u in usuarios:
        try:
            obj = u.coord_permiso
            changed_fields = []
            for mod_key, _, _ in MODULOS:
                hasta = getattr(obj, f'{mod_key}_eliminar_hasta', None)
                if hasta and hasta < ahora:
                    setattr(obj, f'{mod_key}_eliminar', False)
                    setattr(obj, f'{mod_key}_eliminar_hasta', None)
                    changed_fields += [f'{mod_key}_eliminar', f'{mod_key}_eliminar_hasta']
            if changed_fields:
                obj.save(update_fields=changed_fields)
        except Exception:
            pass

    ids_permitidos = {u.pk for u in usuarios}

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        import json as _json
        body    = _json.loads(request.body or b'{}')
        user_id = int(body.get('user_id', 0))
        campo   = body.get('campo', '')
        valor   = bool(body.get('valor', False))
        try:
            if user_id not in ids_permitidos:
                return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
            u   = User.objects.get(pk=user_id)
            obj = CoordPermiso.objects.get(user=u)
            if not hasattr(obj, campo):
                return JsonResponse({'ok': False}, status=400)
            setattr(obj, campo, valor)
            hasta_iso = None
            if campo.endswith('_eliminar'):
                mod       = campo[:-len('_eliminar')]
                hasta_fld = f'{mod}_eliminar_hasta'
                if hasattr(obj, hasta_fld):
                    nueva_hasta = None
                    if valor:
                        # Fecha+hora elegida por el usuario; si no llega o es inválida, +24h
                        hasta_str = (body.get('hasta') or '').strip()
                        try:
                            nueva_hasta = _dt.datetime.fromisoformat(hasta_str) if hasta_str else None
                        except ValueError:
                            nueva_hasta = None
                        if nueva_hasta is None:
                            nueva_hasta = _tz.now() + _DURACION_ELIMINAR
                    setattr(obj, hasta_fld, nueva_hasta)
                    obj.save(update_fields=[campo, hasta_fld])
                    hasta_iso = nueva_hasta.isoformat() if nueva_hasta else None
                else:
                    obj.save(update_fields=[campo])
            else:
                obj.save(update_fields=[campo])
            return JsonResponse({'ok': True, 'hasta': hasta_iso})
        except Exception:
            pass
        return JsonResponse({'ok': False}, status=400)

    # Construir matrix transpuesta: usuario-centric (filas=usuarios, columnas=módulos)
    _AVATAR_COLORS = ['blue','teal','green','orange','red','purple','cyan','pink','yellow','indigo']
    modulos_info = [{'key': k, 'label': l, 'icon': i} for k, l, i in MODULOS]

    matrix_usuarios = []
    for idx, u in enumerate(usuarios):
        try:
            perms = u.coord_permiso
        except Exception:
            continue
        nombre = u.get_full_name() or u.username
        partes = nombre.split()
        initials = (partes[0][0] + partes[-1][0]).upper() if len(partes) >= 2 else nombre[:2].upper()
        celdas = []
        for mod_key, _, _ in MODULOS:
            hasta     = getattr(perms, f'{mod_key}_eliminar_hasta', None)
            hasta_iso = hasta.isoformat() if hasta else ''
            celdas.append({
                'key':            mod_key,
                'editar':         getattr(perms, f'{mod_key}_editar',   False),
                'eliminar':       getattr(perms, f'{mod_key}_eliminar', False),
                'eliminar_hasta': hasta_iso,
                'eliminar_hasta_local': hasta.strftime('%Y-%m-%dT%H:%M') if hasta else '',
            })
        matrix_usuarios.append({
            'user':     u,
            'initials': initials,
            'color':    _AVATAR_COLORS[idx % len(_AVATAR_COLORS)],
            'celdas':   celdas,
        })

    return render(request, 'accounts/settings_coord_permisos.html', {
        'active_tab':       'coord_permisos',
        'nav_home_url':     '/',
        'can_manage_users': True,
        'can_see_activity': True,
        'modulos':          modulos_info,
        'matrix_usuarios':  matrix_usuarios,
    })


def pwa_service_worker(request):
    sw = """
const CACHE = 'techcare-v2';
const OFFLINE_URL = '/offline/';
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.add(OFFLINE_URL)).then(() => self.skipWaiting())
  );
});
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => clients.claim())
  );
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  // Navegación (abrir páginas): si no hay red, mostrar la página offline cacheada
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }
  // Otros recursos: intenta red, cae a caché si existe
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
"""
    return HttpResponse(sw.strip(), content_type='application/javascript',
                        headers={'Service-Worker-Allowed': '/'})


def pwa_offline(request):
    """Página mostrada por el service worker cuando no hay conexión."""
    return render(request, 'accounts/offline.html')


# ── Visor de Logs del Sistema ────────────────────────────────────────────────
import subprocess as _subprocess
import re as _re

_LOG_FILES = {
    'apache_error':   '/var/log/apache2/servicios_ana_error.log',
    'apache_access':  '/var/log/apache2/servicios_ana_access.log',
    'apache_general': '/var/log/apache2/error.log',
}

def _leer_log(path, lineas=300):
    try:
        result = _subprocess.run(
            ['tail', '-n', str(lineas), path],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip().splitlines()
    except Exception as e:
        return [f'[ERROR leyendo log: {e}]']


@login_required
def settings_logs(request):
    if not request.user.is_superuser:
        messages.error(request, 'Solo superusuarios pueden ver los logs del sistema.')
        return redirect('settings_perfil')

    from django.contrib.admin.models import LogEntry

    # Django LogEntry — últimas 200 entradas
    django_logs = (
        LogEntry.objects
        .select_related('user', 'content_type')
        .order_by('-action_time')[:200]
    )

    # Accesos recientes
    accesos = RegistroAcceso.objects.select_related('usuario').order_by('-fecha_hora')[:100]

    ctx = _settings_ctx(request, 'logs')
    ctx.update({
        'django_logs':  django_logs,
        'accesos':      accesos,
        'log_files':    list(_LOG_FILES.keys()),
    })
    return render(request, 'accounts/settings_logs.html', ctx)


@login_required
def settings_logs_api(request):
    """API endpoint para cargar líneas de un archivo de log vía AJAX."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    log_key = request.GET.get('log', 'apache_error')
    lineas  = min(int(request.GET.get('lineas', 300)), 1000)
    filtro  = request.GET.get('q', '').strip().lower()

    path = _LOG_FILES.get(log_key)
    if not path:
        return JsonResponse({'ok': False, 'error': 'Log no encontrado'}, status=404)

    lines = _leer_log(path, lineas)

    # Invertir para mostrar más recientes arriba
    lines = list(reversed(lines))

    if filtro:
        lines = [l for l in lines if filtro in l.lower()]

    # Detectar nivel para colorear en frontend
    def _nivel(line):
        ll = line.lower()
        if 'error' in ll or 'critical' in ll or 'crit' in ll:
            return 'error'
        if 'warn' in ll or 'notice' in ll:
            return 'warning'
        if '200' in ll or 'info' in ll:
            return 'info'
        return 'default'

    data = [{'text': l, 'nivel': _nivel(l)} for l in lines]
    return JsonResponse({'ok': True, 'lines': data, 'total': len(data)})


# ── Auditoría (django-simple-history: usuario + qué cambió) ──────────────────
# <--- hecho por claude code: visor de auditoría sobre los modelos Historical*
_AUDIT_TIPO = {'+': ('Creó', 'green', 'ti-plus'),
               '~': ('Editó', 'yellow', 'ti-pencil'),
               '-': ('Eliminó', 'red', 'ti-trash')}
_AUDIT_OP_GET = {'creo': '+', 'edito': '~', 'elimino': '-'}


def _audited_models():
    """Devuelve los modelos registrados en django-simple-history, ordenados."""
    from django.apps import apps
    out = []
    for m in apps.get_models():
        mgr = getattr(m, 'history', None)
        if mgr is not None and hasattr(mgr, 'model'):
            out.append(m)
    out.sort(key=lambda m: (m._meta.app_label, m._meta.object_name))
    return out


def _audit_model_key(m):
    return f'{m._meta.app_label}.{m._meta.object_name}'


def _fmt_val(v):
    if v is None or v == '':
        return '—'
    s = str(v)
    return (s[:120] + '…') if len(s) > 120 else s


def _build_audit_event(hr, with_table=False, model=None):
    """Convierte un registro Historical* en un evento legible para la tabla."""
    tipo, color, icon = _AUDIT_TIPO.get(hr.history_type, ('?', 'secondary', 'ti-help'))
    cambios = []
    sin_baseline = False
    if hr.history_type == '~':
        try:
            prev = hr.prev_record
            if prev is not None:
                for c in hr.diff_against(prev).changes:
                    cambios.append({'campo': c.field,
                                    'old': _fmt_val(c.old),
                                    'new': _fmt_val(c.new)})
            else:
                sin_baseline = True
        except Exception:
            pass
    try:
        registro = str(hr.instance)
    except Exception:
        registro = f'#{getattr(hr, "id", "?")}'
    u = hr.history_user
    ev = {
        'fecha':   hr.history_date,
        'usuario': (u.get_full_name() or u.username) if u else None,
        'tipo':    tipo, 'color': color, 'icon': icon,
        'es_edicion': hr.history_type == '~',
        'sin_baseline': sin_baseline,
        'registro': registro,
        'cambios':  cambios,
    }
    if with_table and model is not None:
        ev['tabla'] = model._meta.verbose_name.title()
    return ev


@login_required
def settings_auditoria(request):
    """Auditoría completa vía django-simple-history: quién creó/editó/eliminó
    cada registro, cuándo y qué cambió (valor anterior → nuevo). Solo superuser."""
    if not request.user.is_superuser:
        messages.error(request, 'Solo superusuarios pueden ver la auditoría del sistema.')
        return redirect('settings_perfil')

    from django.core.paginator import Paginator
    from django.db.models import Count

    modelos = _audited_models()
    modelos_ctx = [{'key': _audit_model_key(m),
                    'label': m._meta.verbose_name.title(),
                    'app': m._meta.app_label} for m in modelos]

    f_tabla = (request.GET.get('tabla') or '').strip()
    f_op    = (request.GET.get('op') or '').strip().lower()
    op_db   = _AUDIT_OP_GET.get(f_op)

    # Filtro por rango de fechas (desde / hasta)  <--- hecho por claude code
    import datetime as _dt_aud
    def _parse_d(s):
        try:
            return _dt_aud.date.fromisoformat((s or '').strip())
        except ValueError:
            return None
    f_desde = _parse_d(request.GET.get('desde'))
    f_hasta = _parse_d(request.GET.get('hasta'))

    def _rango(qs):
        if f_desde:
            qs = qs.filter(history_date__date__gte=f_desde)
        if f_hasta:
            qs = qs.filter(history_date__date__lte=f_hasta)
        return qs

    sel_model = next((m for m in modelos if _audit_model_key(m) == f_tabla), None)

    eventos = []
    page_obj = None
    total = creados = editados = eliminados = 0
    es_global = sel_model is None

    if sel_model is not None:
        H = sel_model.history.model
        base = _rango(H.objects.all())
        cnts = {r['history_type']: r['c']
                for r in base.values('history_type').annotate(c=Count('history_id'))}
        creados, editados, eliminados = cnts.get('+', 0), cnts.get('~', 0), cnts.get('-', 0)
        total = creados + editados + eliminados

        qs = base.select_related('history_user').order_by('-history_date')
        if op_db:
            qs = qs.filter(history_type=op_db)
        paginator = Paginator(qs, 40)
        page_obj  = paginator.get_page(request.GET.get('page'))
        eventos   = [_build_audit_event(hr) for hr in page_obj]
    else:
        # Feed global: últimos eventos de cada tabla, mezclados por fecha
        merged = []
        # Con rango de fechas se amplía la ventana por tabla; sin rango, los últimos 8.
        _lim = 60 if (f_desde or f_hasta) else 8
        for m in modelos:
            q = _rango(m.history.model.objects.select_related('history_user').order_by('-history_date'))
            if op_db:
                q = q.filter(history_type=op_db)
            for hr in q[:_lim]:
                merged.append((hr.history_date, hr, m))
        merged.sort(key=lambda t: t[0], reverse=True)
        eventos = [_build_audit_event(hr, with_table=True, model=m)
                   for _, hr, m in merged[:300]]

    ctx = _settings_ctx(request, 'auditoria')
    ctx.update({
        'modelos':    modelos_ctx,
        'eventos':    eventos,
        'page_obj':   page_obj,
        'es_global':  es_global,
        'sel_label':  sel_model._meta.verbose_name.title() if sel_model else '',
        'total':      total,
        'creados':    creados,
        'editados':   editados,
        'eliminados': eliminados,
        'n_tablas':   len(modelos),
        'f_tabla':    f_tabla,
        'f_op':       f_op,
        'f_desde':    f_desde.isoformat() if f_desde else '',
        'f_hasta':    f_hasta.isoformat() if f_hasta else '',
    })
    return render(request, 'accounts/settings_auditoria.html', ctx)


# ── Configuración de Correos ──────────────────────────────────────────────────

@login_required
def settings_correos(request):
    """Página de diagnóstico y configuración del sistema de correo."""
    if not request.user.is_superuser:
        return redirect('menu')

    from django.conf import settings as dj_settings
    from django.contrib.auth.models import User
    from .models import DestinatarioEmail
    from notas_parcial.views import (
        _CORREOS_VALIDOS,
        _DEST_POR_USUARIO, _CORREO_PRUEBAS,
    )
    from core.email_utils import (
        get_enfermeria_from,
        get_coord_bl_from,
        get_coord_col_from,
    )

    email_config = {
        'backend':      dj_settings.EMAIL_BACKEND,
        'host':         dj_settings.EMAIL_HOST,
        'port':         dj_settings.EMAIL_PORT,
        'use_tls':      getattr(dj_settings, 'EMAIL_USE_TLS', False),
        'user':         dj_settings.EMAIL_HOST_USER,
        'password_set': bool(dj_settings.EMAIL_HOST_PASSWORD),
        'from_email':   dj_settings.DEFAULT_FROM_EMAIL,
    }

    def _cfg_modulo(cfg_key, from_fn):
        cfg = getattr(dj_settings, cfg_key, {})
        return {
            'host':         cfg.get('HOST', '—'),
            'port':         cfg.get('PORT', '—'),
            'use_tls':      cfg.get('USE_TLS', False),
            'use_ssl':      cfg.get('USE_SSL', False),
            'user':         cfg.get('USER', ''),
            'password_set': bool(cfg.get('PASSWORD', '')),
            'from_email':   from_fn(),
        }

    email_modulos = {
        'enfermeria': _cfg_modulo('EMAIL_ENFERMERIA',  get_enfermeria_from),
        'bl':         _cfg_modulo('EMAIL_COORD_BL',    get_coord_bl_from),
        'col':        _cfg_modulo('EMAIL_COORD_COL',   get_coord_col_from),
    }

    usuarios = User.objects.filter(is_active=True).prefetch_related('groups').order_by('first_name', 'last_name')
    total_usuarios   = usuarios.count()
    con_email        = usuarios.exclude(email='').count()
    sin_email        = total_usuarios - con_email

    # ── Matriz de destinatarios de correo ──────────────────────────────────
    MODULOS_EMAIL = [
        ('conducta_bl',        'Conducta BL',               'ti-clipboard-text text-blue'),
        ('conducta_col',       'Conducta Colegio',           'ti-clipboard-text text-green'),
        ('progress_bl',        'Progress BL',               'ti-chart-bar text-cyan'),
        ('notas_parcial_bl',   'Notas Parcial BL',          'ti-book text-orange'),
        ('notas_parcial_col',  'Notas Parcial Colegio',     'ti-book text-teal'),
        ('salidas_negro_col',  'Salidas ⚫ Colegio',        'ti-door-exit text-dark'),
        ('salidas_negro_bach', 'Salidas ⚫ Bachillerato',   'ti-door-exit text-secondary'),
        ('enfermeria',         'Enfermería',                'ti-stethoscope text-red'),
        ('tickets',            'Tickets Soporte',           'ti-ticket text-purple'),
    ]

    # Solo usuarios staff con email — candidatos a recibir notificaciones
    # glorenzo y yzavala excluidos de todos los módulos de notificación
    _EXCLUIR_NOTIF = ['glorenzo@ana-hn.org', 'yzavala@ana-hn.org']
    usuarios_con_email = (User.objects
                          .filter(is_active=True, is_staff=True)
                          .exclude(email='')
                          .exclude(username__in=_EXCLUIR_NOTIF)
                          .prefetch_related('groups')
                          .order_by('first_name', 'last_name'))

    # Obtener o crear DestinatarioEmail por usuario
    dest_map = {d.user_id: d for d in DestinatarioEmail.objects.filter(
        user__in=usuarios_con_email
    )}

    matrix_usuarios = []
    for u in usuarios_con_email:
        dest = dest_map.get(u.pk)
        celdas = []
        for campo, _, _ in MODULOS_EMAIL:
            celdas.append({
                'user_id': u.pk,
                'campo':   campo,
                'activo':  getattr(dest, campo, False) if dest else False,
            })
        matrix_usuarios.append({'user': u, 'celdas': celdas})

    matrix_modulos = [
        {'key': k, 'label': l, 'icon': i}
        for k, l, i in MODULOS_EMAIL
    ]

    def _build_tab_data(campos_list):
        """Construye lista de dicts {user, **campos} para tabs de módulo."""
        result = []
        for u in usuarios_con_email:
            d = dest_map.get(u.pk)
            entry = {'user': u}
            for campo in campos_list:
                entry[campo] = getattr(d, campo, False) if d else False
            result.append(entry)
        return result

    conducta_data   = _build_tab_data(['conducta_bl', 'conducta_col'])
    progress_data   = _build_tab_data(['progress_bl'])
    notas_data      = _build_tab_data(['notas_parcial_bl', 'notas_parcial_col'])
    enfermeria_data = _build_tab_data(['enfermeria'])

    # ── Tickets — solo soporte técnico (usuario admin) ──────────────────────
    tickets_user_qs = User.objects.filter(username='admin', is_active=True)
    tickets_dest_map = {d.user_id: d for d in DestinatarioEmail.objects.filter(
        user__in=tickets_user_qs
    )}
    tickets_data = []
    for u in tickets_user_qs:
        d = tickets_dest_map.get(u.pk)
        tickets_data.append({
            'user':    u,
            'tickets': getattr(d, 'tickets', False) if d else False,
        })

    # ── Salidas Baño — datos para panel de 4 usuarios específicos ─────────
    _SALIDAS_USERNAMES = ['flicona@ana-hn.org', 'kgarcia@ana-hn.org',
                          'bespino@ana-hn.org',  'fvalladares@ana-hn.org']
    salidas_users_qs = (User.objects
                        .filter(username__in=_SALIDAS_USERNAMES, is_active=True)
                        .order_by('first_name', 'last_name'))
    salidas_dest_map = {d.user_id: d for d in DestinatarioEmail.objects.filter(
        user__in=salidas_users_qs
    )}
    salidas_bano_data = []
    for u in salidas_users_qs:
        d = salidas_dest_map.get(u.pk)
        salidas_bano_data.append({
            'user':        u,
            'negro_col':   getattr(d, 'salidas_negro_col',  False) if d else False,
            'negro_bach':  getattr(d, 'salidas_negro_bach', False) if d else False,
        })

    ctx = _settings_ctx(request, 'correos')
    ctx.update({
        'nav_home_url':          '/',
        'email_config':          email_config,
        'email_modulos':         email_modulos,
        'usuarios':              usuarios,
        'total_usuarios':        total_usuarios,
        'con_email':             con_email,
        'sin_email':             sin_email,
        'correos_validos_pdf':   sorted(_CORREOS_VALIDOS),
        'correo_pruebas':        _CORREO_PRUEBAS,
        'dest_por_usuario':      _DEST_POR_USUARIO,
        # Matriz destinatarios (tab Notificaciones)
        'matrix_usuarios':       matrix_usuarios,
        'matrix_modulos':        matrix_modulos,
        # Tabs por módulo
        'conducta_data':         conducta_data,
        'progress_data':         progress_data,
        'notas_data':            notas_data,
        'enfermeria_data':       enfermeria_data,
        'tickets_data':          tickets_data,
        # Salidas Baño
        'salidas_bano_data':     salidas_bano_data,
    })
    return render(request, 'accounts/settings_correos.html', ctx)


@login_required
@require_POST
def settings_correos_notif_toggle(request):
    """AJAX: activa/desactiva un módulo de email para un usuario."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    try:
        from django.contrib.auth.models import User as AuthUser
        from .models import DestinatarioEmail
        import json
        data    = json.loads(request.body)
        user_id = int(data.get('user_id', 0))
        campo   = data.get('campo', '')
        valor   = bool(data.get('valor', False))

        CAMPOS_VALIDOS = {
            'conducta_bl', 'conducta_col', 'progress_bl',
            'notas_parcial_bl', 'notas_parcial_col',
            'salidas_negro_col', 'salidas_negro_bach',
            'enfermeria', 'tickets',
        }
        if campo not in CAMPOS_VALIDOS:
            return JsonResponse({'ok': False, 'error': 'Campo inválido'}, status=400)

        user = AuthUser.objects.get(pk=user_id)
        dest, _ = DestinatarioEmail.objects.get_or_create(user=user)
        setattr(dest, campo, valor)
        dest.save(update_fields=[campo])
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
def settings_correos_smtp(request):
    """Verifica la conexión SMTP y retorna JSON."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    try:
        from django.core.mail import get_connection
        conn = get_connection()
        conn.open()
        conn.close()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
def settings_correos_test(request):
    """Envía un correo de prueba y retorna JSON."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    import json as _json
    from django.core.mail import EmailMultiAlternatives as _EMA
    try:
        data = _json.loads(request.body)
        dest = data.get('dest', '').strip()
    except Exception:
        dest = ''

    if not dest:
        return JsonResponse({'ok': False, 'error': 'Correo de destino vacío'})

    try:
        asunto = '[TechCare] Correo de prueba del sistema'
        texto  = f'Este es un correo de prueba enviado desde TechCare por {request.user.get_full_name() or request.user.username}.'
        html   = f'''<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f0f4f8;padding:32px;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:28px;box-shadow:0 4px 24px rgba(0,0,0,.1);">
  <p style="font-size:22px;font-weight:700;color:#1864ab;margin:0 0 12px;">✅ TechCare — Prueba de correo</p>
  <p style="color:#495057;">{texto}</p>
  <p style="color:#adb5bd;font-size:12px;margin-top:24px;">Enviado desde Configuración › Correos</p>
</div></body></html>'''
        msg = _EMA(asunto, texto, None, [dest])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
def settings_correos_modulo_test(request):
    """Prueba SMTP de un módulo específico y opcionalmente envía un correo de prueba."""
    # <--- hecho por claude code: prueba SMTP por módulo (enfermeria / bl / col / gmail)
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    import json as _json
    from django.core.mail import EmailMultiAlternatives as _EMA
    from core.email_utils import (
        get_enfermeria_connection, get_enfermeria_from,
        get_coord_bl_connection,   get_coord_bl_from,
        get_coord_col_connection,  get_coord_col_from,
    )
    from django.core.mail import get_connection as _get_default_conn
    from django.conf import settings as _s

    try:
        data   = _json.loads(request.body)
    except Exception:
        data = {}

    modulo = data.get('modulo', '').strip()   # gmail | enfermeria | bl | col
    dest   = data.get('dest',   '').strip()
    solo_ping = data.get('ping', False)       # True → solo verificar conexión, no enviar

    _MAP = {
        'gmail':      (lambda: _get_default_conn(),       lambda: _s.DEFAULT_FROM_EMAIL),
        'enfermeria': (get_enfermeria_connection,          get_enfermeria_from),
        'bl':         (get_coord_bl_connection,            get_coord_bl_from),
        'col':        (get_coord_col_connection,           get_coord_col_from),
    }
    if modulo not in _MAP:
        return JsonResponse({'ok': False, 'error': f'Módulo desconocido: {modulo}'})

    conn_fn, from_fn = _MAP[modulo]

    # ── Solo ping (verificar conexión sin enviar) ────────────────────────────
    if solo_ping:
        try:
            conn = conn_fn()
            if conn is None:
                return JsonResponse({'ok': False, 'error': 'Sin credenciales configuradas → usando Gmail fallback'})
            conn.open(); conn.close()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})

    # ── Envío de prueba ──────────────────────────────────────────────────────
    if not dest:
        return JsonResponse({'ok': False, 'error': 'Correo de destino vacío'})

    try:
        conn     = conn_fn()
        from_addr = from_fn()
        asunto = f'[TechCare] Prueba SMTP – módulo {modulo.upper()}'
        texto  = f'Prueba de correo enviada desde TechCare.\nMódulo: {modulo.upper()}\nCuenta: {from_addr}'
        html   = f'''<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#f0f4f8;padding:32px;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:28px;box-shadow:0 4px 24px rgba(0,0,0,.1);">
  <p style="font-size:20px;font-weight:700;color:#1864ab;margin:0 0 12px;">✅ Prueba SMTP – {modulo.upper()}</p>
  <p style="color:#495057;">{texto}</p>
  <p style="color:#adb5bd;font-size:12px;margin-top:24px;">Enviado desde Configuración › Correos › SMTP Módulos</p>
</div></body></html>'''
        msg = _EMA(asunto, texto, from_addr, [dest], connection=conn)
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
        return JsonResponse({'ok': True, 'from': from_addr})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


# ── Envío de instrucciones de login ────────────────────────────────────────────
# <--- hecho por claude code

_LOGIN_EMAIL_DEFAULTS = {
    'asunto':   'Nuevo método de inicio de sesión – TechCare',
    'intro':    'Hemos actualizado la pantalla de acceso a TechCare. A continuación puedes ver los pasos según tu rol para ingresar sin problemas.',
    'paso_m1':  'En el campo Usuario escribe solo tu nombre (ej: jmartinez), sin el @ana-hn.org — el sistema lo agrega automáticamente.',
    'paso_m2':  'Escribe tu contraseña de siempre.',
    'paso_m3':  'Marca la casilla "Soy maestro" antes de hacer clic en Iniciar Sesión. Sin este paso el sistema no te reconocerá como docente.',
    'paso_m4':  'Haz clic en Iniciar Sesión. ¡Listo!',
    'paso_c1':  'En el campo Usuario escribe solo tu nombre (ej: jmartinez).',
    'paso_c2':  'Escribe tu contraseña.',
    'paso_c3':  'Haz clic en Iniciar Sesión — no es necesario marcar el checkbox.',
    'paso_a1':  'En la pantalla de login, haz clic en el enlace "Acceso admin" (arriba a la derecha del campo usuario).',
    'paso_a2':  'Escribe tu nombre de usuario completo y tu contraseña.',
    'paso_a3':  'Haz clic en Iniciar Sesión.',
    'tip':      'En la pantalla de login encontrarás el enlace "Olvidé mi contraseña" para restablecerla por correo electrónico.',
}


def _build_login_email_html(d, nombre_dest=''):
    """Construye el HTML del correo de instrucciones de login (compatible con Outlook)."""
    import html as _h
    import datetime as _dt

    def esc(s):
        return _h.escape(str(s or ''))

    anio  = _dt.datetime.now().year
    saludo = f'Hola, {nombre_dest}' if nombre_dest else 'Hola,'

    def _paso_row(num, texto, color, importante=False):
        bg  = '#dc2626' if importante else color
        pre = '<strong style="color:#dc2626;">Importante: </strong>' if importante else ''
        return f"""
        <tr>
          <td width="26" valign="top" style="padding-top:2px;padding-bottom:10px;">
            <table cellpadding="0" cellspacing="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
              <tr><td width="24" height="24" align="center" valign="middle"
                      bgcolor="{bg}" style="background:{bg};width:24px;height:24px;">
                <span style="color:#ffffff;font-size:12px;font-weight:700;
                             font-family:Arial,sans-serif;line-height:24px;">{num}</span>
              </td></tr>
            </table>
          </td>
          <td style="padding-left:10px;padding-bottom:10px;color:#1e293b;font-size:14px;
                     line-height:1.6;font-family:Arial,sans-serif;">
            {pre}{esc(texto)}
          </td>
        </tr>"""

    pasos_m = (
        _paso_row('1', d.get('paso_m1',''), '#1d4ed8') +
        _paso_row('2', d.get('paso_m2',''), '#1d4ed8') +
        _paso_row('3', d.get('paso_m3',''), '#1d4ed8', importante=True) +
        _paso_row('4', d.get('paso_m4',''), '#1d4ed8')
    )
    pasos_c = (
        _paso_row('1', d.get('paso_c1',''), '#16a34a') +
        _paso_row('2', d.get('paso_c2',''), '#16a34a') +
        _paso_row('3', d.get('paso_c3',''), '#16a34a')
    )
    pasos_a = (
        _paso_row('1', d.get('paso_a1',''), '#7c3aed') +
        _paso_row('2', d.get('paso_a2',''), '#7c3aed') +
        _paso_row('3', d.get('paso_a3',''), '#7c3aed')
    )

    return f"""<!DOCTYPE html>
<html xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office" lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <!--[if mso]><noscript><xml>
    <o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings>
  </xml></noscript><![endif]-->
  <title>{esc(d.get('asunto','TechCare'))}</title>
</head>
<body style="margin:0;padding:0;background:#f0f4f8;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">

<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#f0f4f8;mso-table-lspace:0pt;mso-table-rspace:0pt;">
<tr><td align="center" style="padding:32px 16px;">

  <table width="600" cellpadding="0" cellspacing="0" align="center"
         style="mso-table-lspace:0pt;mso-table-rspace:0pt;">

    <!-- HEADER -->
    <tr>
      <td align="center" bgcolor="#1a56db"
          style="background:#1a56db;padding:32px 24px 24px;">
        <p style="margin:0 0 4px;font-size:26px;font-weight:700;color:#ffffff;
                  font-family:Arial,sans-serif;">TechCare</p>
        <p style="margin:0;font-size:13px;color:#bfdbfe;font-family:Arial,sans-serif;">
          Asociaci&oacute;n Nuevo Amanecer
        </p>
      </td>
    </tr>

    <!-- BODY -->
    <tr>
      <td bgcolor="#ffffff"
          style="background:#ffffff;padding:36px 36px 28px;
                 border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">

        <p style="margin:0 0 4px;font-size:20px;font-weight:700;color:#1e293b;
                  font-family:Arial,sans-serif;">{esc(saludo)}</p>
        <p style="margin:0 0 24px;font-size:14px;color:#475569;line-height:1.6;
                  font-family:Arial,sans-serif;">{esc(d.get('intro',''))}</p>

        <!-- ─ MAESTROS ─ -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="mso-table-lspace:0pt;mso-table-rspace:0pt;margin-bottom:20px;">
          <tr>
            <td bgcolor="#eff6ff"
                style="background:#eff6ff;border:1px solid #bfdbfe;padding:18px 20px;">
              <p style="margin:0 0 14px;font-size:15px;font-weight:700;color:#1d4ed8;
                        font-family:Arial,sans-serif;">
                Si eres
                <span style="background:#1d4ed8;color:#ffffff;padding:2px 10px;
                             font-size:13px;font-family:Arial,sans-serif;">Maestro/a</span>
              </p>
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
                {pasos_m}
              </table>
              <!-- mockup formulario -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="mso-table-lspace:0pt;mso-table-rspace:0pt;margin-top:14px;">
                <tr><td align="center">
                  <table cellpadding="0" cellspacing="0" width="300"
                         style="mso-table-lspace:0pt;mso-table-rspace:0pt;
                                background:#ffffff;border:1px solid #cbd5e1;">
                    <tr><td style="padding:12px 16px 4px;" align="center">
                      <p style="margin:0 0 8px;font-size:10px;color:#94a3b8;
                                text-transform:uppercase;letter-spacing:.05em;
                                font-weight:600;font-family:Arial,sans-serif;">
                        Vista previa del formulario
                      </p>
                    </td></tr>
                    <tr><td style="padding:0 16px 8px;">
                      <p style="margin:0 0 3px;font-size:11px;color:#475569;
                                font-weight:600;font-family:Arial,sans-serif;">Usuario</p>
                      <table width="100%" cellpadding="0" cellspacing="0"
                             style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
                        <tr>
                          <td width="30" bgcolor="#f1f5f9"
                              style="background:#f1f5f9;border:1px solid #cbd5e1;
                                     padding:7px 6px;text-align:center;
                                     font-size:13px;font-family:Arial,sans-serif;">&#128100;</td>
                          <td bgcolor="#f8fafc"
                              style="background:#f8fafc;border:1px solid #cbd5e1;
                                     border-left:none;padding:7px 10px;font-size:13px;
                                     color:#334155;font-family:Arial,sans-serif;">jmartinez</td>
                          <td bgcolor="#f1f5f9"
                              style="background:#f1f5f9;border:1px solid #cbd5e1;
                                     border-left:none;padding:7px 8px;font-size:12px;
                                     color:#64748b;white-space:nowrap;
                                     font-family:Arial,sans-serif;">@ana-hn.org</td>
                        </tr>
                      </table>
                    </td></tr>
                    <tr><td style="padding:0 16px 8px;">
                      <p style="margin:0 0 3px;font-size:11px;color:#475569;
                                font-weight:600;font-family:Arial,sans-serif;">Contrase&ntilde;a</p>
                      <table width="100%" cellpadding="0" cellspacing="0"
                             style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
                        <tr>
                          <td width="30" bgcolor="#f1f5f9"
                              style="background:#f1f5f9;border:1px solid #cbd5e1;
                                     padding:7px 6px;text-align:center;
                                     font-size:13px;font-family:Arial,sans-serif;">&#128274;</td>
                          <td bgcolor="#f8fafc"
                              style="background:#f8fafc;border:1px solid #cbd5e1;
                                     border-left:none;padding:7px 10px;font-size:14px;
                                     color:#94a3b8;letter-spacing:4px;
                                     font-family:Arial,sans-serif;">
                            &#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;
                          </td>
                        </tr>
                      </table>
                    </td></tr>
                    <tr><td style="padding:6px 16px 10px;">
                      <table cellpadding="0" cellspacing="0"
                             style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
                        <tr>
                          <td width="18" height="18" bgcolor="#1d4ed8"
                              style="background:#1d4ed8;text-align:center;
                                     vertical-align:middle;">
                            <span style="color:#ffffff;font-size:11px;font-weight:700;
                                         font-family:Arial,sans-serif;">&#10003;</span>
                          </td>
                          <td style="padding-left:8px;font-size:13px;color:#1e293b;
                                     font-weight:600;font-family:Arial,sans-serif;">
                            Soy maestro
                          </td>
                          <td style="padding-left:8px;font-size:10px;color:#b45309;
                                     font-weight:600;font-family:Arial,sans-serif;
                                     background:#fef9c3;">&nbsp;&#8592; &#161;No olvidar!&nbsp;</td>
                        </tr>
                      </table>
                    </td></tr>
                    <tr><td style="padding:0 16px 14px;" align="center">
                      <table width="100%" cellpadding="0" cellspacing="0"
                             style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
                        <tr>
                          <td align="center" bgcolor="#1d4ed8"
                              style="background:#1d4ed8;padding:10px;">
                            <span style="color:#ffffff;font-size:13px;font-weight:700;
                                         font-family:Arial,sans-serif;">Iniciar Sesi&oacute;n</span>
                          </td>
                        </tr>
                      </table>
                    </td></tr>
                  </table>
                </td></tr>
              </table>
            </td>
          </tr>
        </table>

        <!-- ─ COORDINADORES ─ -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="mso-table-lspace:0pt;mso-table-rspace:0pt;margin-bottom:20px;">
          <tr>
            <td bgcolor="#f0fdf4"
                style="background:#f0fdf4;border:1px solid #bbf7d0;padding:18px 20px;">
              <p style="margin:0 0 14px;font-size:15px;font-weight:700;color:#166534;
                        font-family:Arial,sans-serif;">
                Si eres
                <span style="background:#16a34a;color:#ffffff;padding:2px 10px;
                             font-size:13px;font-family:Arial,sans-serif;">Coordinador/a</span>
              </p>
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
                {pasos_c}
              </table>
            </td>
          </tr>
        </table>

        <!-- ─ ADMINISTRADORES ─ -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="mso-table-lspace:0pt;mso-table-rspace:0pt;margin-bottom:20px;">
          <tr>
            <td bgcolor="#faf5ff"
                style="background:#faf5ff;border:1px solid #e9d5ff;padding:18px 20px;">
              <p style="margin:0 0 14px;font-size:15px;font-weight:700;color:#6b21a8;
                        font-family:Arial,sans-serif;">
                Si eres
                <span style="background:#7c3aed;color:#ffffff;padding:2px 10px;
                             font-size:13px;font-family:Arial,sans-serif;">Administrador</span>
              </p>
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
                {pasos_a}
              </table>
            </td>
          </tr>
        </table>

        <!-- ─ TIP ─ -->
        <table width="100%" cellpadding="0" cellspacing="0"
               style="mso-table-lspace:0pt;mso-table-rspace:0pt;">
          <tr>
            <td bgcolor="#fff7ed"
                style="background:#fff7ed;border-left:4px solid #f97316;padding:14px 18px;">
              <p style="margin:0;font-size:14px;color:#431407;line-height:1.6;
                        font-family:Arial,sans-serif;">
                <strong>&#128161; &iquest;Olvidaste tu contrase&ntilde;a?</strong><br>
                {esc(d.get('tip',''))}
              </p>
            </td>
          </tr>
        </table>

      </td>
    </tr>

    <!-- FOOTER -->
    <tr>
      <td bgcolor="#1e293b"
          style="background:#1e293b;padding:20px 24px;text-align:center;">
        <p style="margin:0 0 4px;color:#94a3b8;font-size:13px;
                  font-family:Arial,sans-serif;">
          Si tienes alguna duda o problema para ingresar, contacta a soporte t&eacute;cnico.
        </p>
        <p style="margin:0;color:#64748b;font-size:12px;font-family:Arial,sans-serif;">
          &copy; {anio} Soporte T&eacute;cnico &ndash; Asociaci&oacute;n Nuevo Amanecer
        </p>
      </td>
    </tr>

  </table>

</td></tr>
</table>
</body>
</html>"""


@login_required
def settings_envio_login(request):
    """Página para redactar y enviar el correo de instrucciones de login."""
    if not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'POST':
        data    = {k: request.POST.get(k, v) for k, v in _LOGIN_EMAIL_DEFAULTS.items()}
        ids     = request.POST.getlist('usuario_ids')
        asunto  = data.get('asunto', 'Nuevo método de inicio de sesión – TechCare')
        enviados = 0
        errores  = []

        if not ids:
            return JsonResponse({'ok': False, 'error': 'No se seleccionó ningún usuario.'})

        usuarios = User.objects.filter(id__in=ids, is_active=True).exclude(email='')

        for u in usuarios:
            nombre = u.get_full_name() or u.username
            html   = _build_login_email_html(data, nombre_dest=nombre)
            texto  = (
                f'Hola {nombre},\n\n'
                f'{data.get("intro","")}\n\n'
                f'Accede en: https://servicios.ana-hn.org:437'
            )
            try:
                msg = EmailMultiAlternatives(asunto, texto,
                                             settings.DEFAULT_FROM_EMAIL, [u.email])
                msg.attach_alternative(html, 'text/html')
                msg.send(fail_silently=False)
                enviados += 1
            except Exception:
                errores.append(u.email)

        return JsonResponse({'ok': True, 'enviados': enviados, 'errores': errores})

    # GET — lista de usuarios activos con email
    ctx = _settings_ctx(request, 'envio_login')
    ctx['defaults'] = _LOGIN_EMAIL_DEFAULTS
    ctx['usuarios_lista'] = (
        User.objects
        .filter(is_active=True)
        .exclude(email='')
        .order_by('first_name', 'last_name', 'username')
        .values('id', 'first_name', 'last_name', 'username', 'email')
    )
    return render(request, 'accounts/settings_envio_login.html', ctx)


@login_required
def settings_envio_login_preview(request):
    """Devuelve el HTML renderizado del correo para la vista previa (POST)."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    data = {k: request.POST.get(k, v) for k, v in _LOGIN_EMAIL_DEFAULTS.items()}
    html = _build_login_email_html(data, nombre_dest='[Nombre del usuario]')
    return JsonResponse({'html': html})
