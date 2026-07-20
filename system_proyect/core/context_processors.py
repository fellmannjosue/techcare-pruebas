# core/context_processors.py

from datetime import datetime
from django.urls import reverse

def current_year(request):
    return {'year': datetime.now().year}


def version_context(request):
    """<--- hecho por claude code: versión en el footer + modal de novedades (una vez por versión)."""
    from core.version import version_actual, novedades
    v = version_actual()
    mostrar = False
    u = getattr(request, 'user', None)
    if u is not None and u.is_authenticated:
        try:
            mostrar = (u.perfil.version_vista or '') != v
        except Exception:
            mostrar = False
    return {'app_version': v, 'novedades': novedades(), 'mostrar_novedades': mostrar}


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
    # 'administracion' va de último: solo es el inicio cuando el usuario NO tiene
    # otro rol con dashboard propio. Si tiene otro rol, su inicio es el de ese rol
    # y Tickets aparece solo en el sidebar (nav_tickets).
    elif grp('administracion'):
        nav_home_url = reverse('dashboard_administracion')
    else:
        nav_home_url = reverse('menu')

    is_salidas_bano = is_admin or grp('control baño coord', 'control baños col')

    return {
        'nav_tickets':          is_admin or can('tickets.view_ticket') or grp('administracion', 'instructores'),
        'nav_reloj':            is_admin or grp('reloj'),
        'nav_calculadoras':     is_admin or grp('reloj'),
        'nav_inventory':        is_admin or can('inventario.view_item') or grp('inventario'),
        'nav_sponsors':         is_admin or can('sponsors.view_sponsor'),
        'nav_cfp':              is_admin or grp('director_cfp', 'instructores'),
        'nav_maintenance':      is_admin or can('mantenimiento.view_reportemantenimiento'),
        'nav_enfermeria':       is_admin or grp('enfermeria'),
        'nav_coord_bl':         nav_coord_bl,
        'nav_coord_col':        nav_coord_col,
        'nav_maestro_bl':       nav_mbl,
        'nav_maestro_col':      nav_mcol,
        'nav_es_coord_maestro': es_coord_maestro,
        'nav_modo_maestro':     modo_maestro,
        'nav_home_url':         nav_home_url,
        'nav_solo_progress':    is_solo_progress,
        'nav_progress_only':    is_progress_only,
        'nav_salidas_bano':     is_salidas_bano,
        # <--- hecho por claude code: enlace a Ruteo BL para coordinadores C1/C2/C4 (si el toggle está activo)
        'nav_ruteo_bl':         _puede_ver_ruteo_bl(request),
    }


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
