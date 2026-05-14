# core/context_processors.py

from datetime import datetime

def current_year(request):
    return {'year': datetime.now().year}


_COORD_MAESTROS_NAV = frozenset([
    'cvarela@ana-hn.org', 'druiz@ana-hn.org',
    'ialcerro@ana-hn.org', 'jmartinez@ana-hn.org',
])

def nav_context(request):
    """Provee variables nav_* a todos los templates para el sidebar unificado."""
    if not request.user.is_authenticated:
        return {}

    user     = request.user
    is_admin = user.is_superuser

    def grp(*names):
        return user.groups.filter(name__in=names).exists()

    is_coord_bl    = grp('coordinador_bilingue')
    is_coord_col   = grp('coordinadores_colegio', 'coordinador_colegio', 'coordinadores')
    is_maestro_bl  = grp('maestros_bilingue')
    is_maestro_col = grp('maestros_colegio')

    can = lambda p: user.has_perm(p)

    es_coord_maestro = user.email.lower() in _COORD_MAESTROS_NAV
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
    else:
        nav_coord_bl  = is_admin or is_coord_bl
        nav_coord_col = is_admin or is_coord_col
        nav_mbl       = is_maestro_bl
        nav_mcol      = is_maestro_col

    return {
        'nav_tickets':          is_admin or can('tickets.view_ticket') or grp('administracion'),
        'nav_reloj':            is_admin or grp('reloj'),
        'nav_calculadoras':     is_admin or grp('reloj'),
        'nav_inventory':        is_admin or can('inventario.view_item') or grp('inventario'),
        'nav_sponsors':         is_admin or can('sponsors.view_sponsor'),
        'nav_seguridad':        is_admin or can('seguridad.view_registro'),
        'nav_maintenance':      is_admin or can('mantenimiento.view_reportemantenimiento'),
        'nav_enfermeria':       is_admin or grp('enfermeria'),
        'nav_coord_bl':         nav_coord_bl,
        'nav_coord_col':        nav_coord_col,
        'nav_maestro_bl':       nav_mbl,
        'nav_maestro_col':      nav_mcol,
        'nav_es_coord_maestro': es_coord_maestro,
        'nav_modo_maestro':     modo_maestro,
    }
