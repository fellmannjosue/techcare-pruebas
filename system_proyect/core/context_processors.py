# core/context_processors.py

from datetime import datetime
from django.urls import reverse

def current_year(request):
    return {'year': datetime.now().year}


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
    if is_admin:
        nav_home_url = reverse('menu')
    elif is_solo_progress:
        nav_home_url = reverse('progress_report_bilingue')
    elif nav_mbl or nav_mcol:
        nav_home_url = reverse('dashboard_maestro')
    elif nav_coord_col and not nav_coord_bl:
        nav_home_url = reverse('dashboard_coordinador', kwargs={'area': 'colegio'})
    elif nav_coord_bl:
        nav_home_url = reverse('dashboard_coordinador', kwargs={'area': 'bilingue'})
    elif grp('administracion'):
        nav_home_url = reverse('dashboard_administracion')
    elif grp('tecnicos'):
        nav_home_url = reverse('tickets_dashboard')
    elif grp('reloj'):
        nav_home_url = reverse('reloj_dashboard')
    else:
        nav_home_url = reverse('menu')

    is_salidas_bano = is_admin or grp('control baño coord', 'control baños col')

    return {
        'nav_tickets':          is_admin or can('tickets.view_ticket') or grp('administracion'),
        'nav_reloj':            is_admin or grp('reloj'),
        'nav_calculadoras':     is_admin or grp('reloj'),
        'nav_inventory':        is_admin or can('inventario.view_item') or grp('inventario'),
        'nav_sponsors':         is_admin or can('sponsors.view_sponsor'),
        'nav_finanzas':         request.user.is_superuser or request.user.email == 'cvalle@ana-hn.org',
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
    }
