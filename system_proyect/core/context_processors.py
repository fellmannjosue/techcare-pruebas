# core/context_processors.py

from datetime import datetime
from django.urls import reverse

def current_year(request):
    return {'year': datetime.now().year}


def version_context(request):
    """<--- hecho por claude code: versión en el footer + modal de novedades (una vez por versión).

    Regla del usuario: un release **menor** (< 50 archivos, versión tipo 6.0.1.3.001)
    solo le muestra las novedades al superusuario; los demás no reciben la ventana
    por cada arreglito. Un release normal se le anuncia a todos.
    """
    from core.version import version_actual, novedades
    v = version_actual()
    ent = novedades()
    es_menor = bool(ent and ent[0].get('menor'))
    mostrar = False
    u = getattr(request, 'user', None)
    if u is not None and u.is_authenticated:
        try:
            no_vista = (u.perfil.version_vista or '') != v
            mostrar = no_vista and (not es_menor or u.is_superuser)
        except Exception:
            mostrar = False
    from core.middleware import SesionInactividadMiddleware
    return {'app_version': v, 'novedades': ent, 'mostrar_novedades': mostrar,
            'version_menor': es_menor,
            'sesion_inactividad_min': SesionInactividadMiddleware.minutos()}   # <--- hecho por claude code (28-sep-2026): lo lee idle_logout


def nav_context(request):
    """Provee variables nav_* a todos los templates para el sidebar unificado."""
    if not request.user.is_authenticated:
        return {}

    user     = request.user
    is_admin = user.is_superuser

    def grp(*names):
        return user.groups.filter(name__in=names).exists()

    is_coord_bl      = grp('coordinador_bilingue', 'coordinador_bl', 'coord_progress_bl')
    is_coord_col     = grp('coordinadores_colegio', 'coordinador_colegio', 'coordinadores', 'coordinador_col')
    is_maestro_bl    = grp('maestros_bilingue')
    is_maestro_col   = grp('maestros_colegio')
    is_solo_progress = grp('solo_progress')
    is_progress_only = grp('coord_progress_bl')

    can = lambda p: user.has_perm(p)

    try:
        es_coord_maestro = user.perfil.es_coord_maestro
    except Exception:
        es_coord_maestro = False
    modo_maestro     = es_coord_maestro and bool(
        request.session.get('agenda_modo_maestro', False)
    )
    area_maestro = request.session.get('agenda_area_maestro', 'bilingue')

    # Para coord-maestros: mostrar solo el nav del rol activo en sesión
    if es_coord_maestro:
        if not modo_maestro:
            nav_coord_bl  = is_coord_bl
            nav_coord_col = is_coord_col
            nav_mbl       = False
            nav_mcol      = False
        elif area_maestro == 'colegio':
            nav_coord_bl  = False
            nav_coord_col = False
            nav_mbl       = False
            nav_mcol      = True
        else:
            nav_coord_bl  = False
            nav_coord_col = False
            nav_mbl       = True
            nav_mcol      = False
    elif is_solo_progress:
        nav_coord_bl  = False
        nav_coord_col = False
        nav_mbl       = False
        nav_mcol      = False
    else:
        nav_coord_bl  = is_admin or is_coord_bl
        nav_coord_col = is_admin or is_coord_col
        nav_mbl       = is_maestro_bl
        nav_mcol      = is_maestro_col

    # URL de "home" para cada tipo de usuario (usada en sidebar y breadcrumbs)
    from accounts.panel_roles import es_multi_panel
    if is_admin:
        nav_home_url = reverse('menu')
    elif es_multi_panel(user):
        nav_home_url = reverse('panel_general')
    elif is_solo_progress:
        nav_home_url = reverse('progress_report_bilingue')
    # <--- hecho por claude code: quien es maestro en las DOS áreas entra al Panel
    # General (así lo hace el login), así que su "Panel Principal" debe volver ahí y
    # no al dashboard de un área suelta.
    elif is_maestro_bl and is_maestro_col:
        nav_home_url = reverse('panel_general')
    elif nav_mbl or nav_mcol:
        nav_home_url = reverse('dashboard_maestro')
    elif nav_coord_col and not nav_coord_bl:
        nav_home_url = reverse('dashboard_coordinador', kwargs={'area': 'colegio'})
    elif nav_coord_bl:
        nav_home_url = reverse('dashboard_coordinador', kwargs={'area': 'bilingue'})
    elif grp('tecnicos'):
        nav_home_url = reverse('tickets_dashboard')
    elif grp('reloj'):
        nav_home_url = reverse('reloj_dashboard')
    elif grp('enfermeria'):   # <--- hecho por claude code: inicio de enfermería = su dashboard
        nav_home_url = reverse('enfermeria:enfermeria_dashboard')
    # 'administracion' va de último: solo es el inicio cuando el usuario NO tiene
    # otro rol con dashboard propio. Si tiene otro rol, su inicio es el de ese rol
    # y Tickets aparece solo en el sidebar (nav_tickets).
    elif grp('administracion'):
        nav_home_url = reverse('dashboard_administracion')
    else:
        nav_home_url = reverse('menu')

    is_salidas_bano = is_admin or grp('control baño coord', 'control baños col')
    # <--- hecho por claude code: CFP tiene sus propios grupos, independientes del colegio
    is_salidas_bano_cfp = is_admin or grp('control baño coord cfp', 'control baños cfp')

    ctx = {
        # <--- hecho por claude code: 'instructores' salió de aquí; los instructores CFP van en 'administracion'
        'nav_tickets':          is_admin or can('tickets.view_ticket') or grp('administracion'),
        # <--- hecho por claude code: True solo para quien gestiona tickets ajenos (panel de técnico)
        'nav_tickets_tecnico':  is_admin or can('tickets.view_ticket'),
        'nav_reloj':            is_admin or grp('reloj'),
        # <--- hecho por claude code (16-sep-2026): botón "Pruebas" del Reloj solo para quien tiene el permiso pruebas_comp
        'nav_reloj_pruebas':    is_admin or _puede_reloj_pruebas(user),
        'nav_calculadoras':     is_admin or grp('calculadoras_tiempo'),  # <--- hecho por claude code: superuser + grupo calculadoras_tiempo (solo las de tiempo)
        'nav_inventory':        is_admin or can('inventario.view_item') or grp('inventario'),
        'nav_sponsors':         is_admin or can('sponsors.view_sponsor'),
        'nav_cfp':              is_admin or grp('director_cfp', 'instructores', 'contabilidad_cfp'),
        # <--- hecho por claude code: el permiso 'view_reportemantenimiento' no existe (el modelo
        # es maintenancerecord) — con eso el menú jamás salía para no-admins. Se corrige y se
        # acepta también el grupo 'mantenimiento' (Yeny Lagos, auditora de Control de equipo).
        'nav_maintenance':      is_admin or can('mantenimiento.view_maintenancerecord') or grp('mantenimiento'),
        # <--- hecho por claude code (28-sep-2026): hub Control y Servicio Técnico = Inventario ∪ Mantenimiento
        'nav_servicio':         is_admin or can('inventario.view_item') or grp('inventario') or can('mantenimiento.view_maintenancerecord') or grp('mantenimiento'),
        'nav_mm_insumos':       is_admin or grp('mantenimiento_mecanico') or grp('mantenimiento_mecanico_lectura'),   # <--- hecho por claude code (12-oct-2026): combustibles y aceites
        'nav_mant_mecanico':    is_admin or grp('mantenimiento_mecanico') or grp('mantenimiento_mecanico_lectura') or grp('vehiculos_registro') or grp('vehiculos_kilometraje') or grp('vehiculos_auditoria'),   # módulo completo (hub)
        'nav_vehiculos':        is_admin or grp('vehiculos_registro') or grp('vehiculos_kilometraje') or grp('vehiculos_auditoria'),   # <--- hecho por claude code (12-oct-2026)   # <--- hecho por claude code (01-oct-2026): combustibles y aceites
        'nav_enfermeria':       is_admin or grp('enfermeria'),
        'nav_coord_bl':         nav_coord_bl,
        'nav_coord_col':        nav_coord_col,
        'nav_maestro_bl':       nav_mbl,
        'nav_maestro_col':      nav_mcol,
        # <--- hecho por claude code (16-sep-2026): un coordinador de notas que también da clase
        # (druiz) no tenía "Mis notas" en el sidebar; estas flags van por GRUPO, sin depender del modo.
        'nav_notas_maestro_bl':  is_maestro_bl,
        'nav_notas_maestro_col': is_maestro_col,
        'nav_es_coord_maestro': es_coord_maestro,
        'nav_modo_maestro':     modo_maestro,
        'nav_home_url':         nav_home_url,
        'nav_solo_progress':    is_solo_progress,
        'nav_progress_only':    is_progress_only,
        'nav_salidas_bano':     is_salidas_bano,
        'nav_salidas_bano_cfp': is_salidas_bano_cfp,
        # <--- hecho por claude code: Ingreso de Notas al sistema academico
        'nav_ingresos_notas':   is_admin or grp('ingreso notas', 'ingreso notas bilingue', 'ingreso notas colegio'),
        # <--- hecho por claude code: enlace a Ruteo BL para coordinadores C1/C2/C4 (si el toggle está activo)
        'nav_ruteo_bl':         _puede_ver_ruteo_bl(request),
        # <--- hecho por claude code: Gestión de Desarrollo para admin/dev + staff solicitante
        'nav_desarrollo':       is_admin or grp('desarrollo_admin', 'desarrollo_dev', 'desarrollo_solicitante'),
        # <--- hecho por claude code: Contabilidad gated por permiso (no por is_staff)
        'nav_contabilidad':     is_admin or request.user.has_perm('contabilidad.ver_contabilidad'),
        # <--- hecho por claude code: Red (ANA Network Manager) por permiso; grupos `red` (lectura) y `red_admin`
        'nav_red':              is_admin or request.user.has_perm('red.ver_red'),
        'nav_red_admin':        is_admin or request.user.has_perm('red.administrar_red'),
    }
    # <--- hecho por claude code (10-sep-2026): programas ocultos a todos (Configuración → Seguridad):
    # se apagan sus nav_* y se expone `programas_ocultos` para los enlaces sueltos de las plantillas.
    try:
        from constance import config as _cfg
        from core.programas import ocultos, aplicar_ocultos
        aplicar_ocultos(ctx, ocultos(_cfg))
    except Exception:
        ctx.setdefault('programas_ocultos', {})
    return ctx


def _puede_ver_ruteo_bl(request):
    """True si el usuario puede ver la pantalla de Ruteo BL (admin, o coord C1/C2/C4 con toggle activo)."""
    u = getattr(request, 'user', None)
    if not (u and u.is_authenticated):
        return False
    if u.is_superuser:
        return True
    try:
        from conducta.views import _permiso_ruteo_email
        # <--- hecho por claude code: puede ver si su permiso es 'lectura' o 'edit'
        return _permiso_ruteo_email(u.email) in ('lectura', 'edit')
    except Exception:
        return False


def _puede_reloj_pruebas(user):
    """<--- hecho por claude code (16-sep-2026): permiso `pruebas_comp` del Reloj (RelojPermiso)."""
    try:
        from reloj.views import _reloj_can_ver
        return bool(_reloj_can_ver(user, 'pruebas_comp'))
    except Exception:
        return False
