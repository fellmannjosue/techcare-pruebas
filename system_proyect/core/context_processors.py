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


def _puede_reforzamiento(user):
    try:
        from conducta.views import puede_ver_reforzamiento
        return puede_ver_reforzamiento(user)
    except Exception:
        return False


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
    # <--- hecho por claude code (04-nov-2026): druiz es COORDINADOR BL + MAESTRO en AMBAS áreas,
    # pero tenía perfil.es_coord_maestro en False, así que "Coordinador BL" se colaba en la barra.
    # Su coordinación se ve en el "Panel Principal"; la barra superior solo debe mostrar "Maestros COL/BL".
    # Esto va ANTES del flag es_coord_maestro para no depender de que esté bien marcado.
    if (is_coord_bl or is_coord_col) and is_maestro_bl and is_maestro_col:
        nav_coord_bl  = False
        nav_coord_col = False
        nav_mbl       = True
        nav_mcol      = True
    elif es_coord_maestro:
        # <--- hecho por claude code (03-nov-2026): coordinador(a) que ADEMÁS es maestro en las DOS
        # áreas (druiz) ve su coordinación + ambos roles de maestro a la vez (la barra los combina
        # en "Maestro BL/COL"); no depende del interruptor de modo.
        if is_maestro_bl and is_maestro_col:
            # <--- hecho por claude code (03-nov-2026): la COORDINACIÓN (druiz) se ve en
            # "Panel Principal" (panel_general); en la barra superior solo queda
            # "Maestros COL/BL". Por eso NO mostramos el grupo Coordinador en el menú.
            nav_coord_bl  = False
            nav_coord_col = False
            nav_mbl       = True
            nav_mcol      = True
        elif not modo_maestro:
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
        # <--- hecho por claude code (03-nov-2026): Solicitud de DataShow — solo el grupo "datashow" (Config → Acceso a DataShow) o superusuario
        'nav_datashow':         is_admin or grp('datashow'),
        'nav_reforzamiento':    _puede_reforzamiento(request.user),   # <--- hecho por claude code (06-nov-2026): por ahora solo druiz y superusuario
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

    # <--- hecho por claude code (30-oct-2026): menú superior horizontal del superusuario por CATEGORÍAS
    # (las mismas del Panel Principal). Reutiliza GRUPOS_SUPER; el .js no reconstruye si ya hay items.
    if user.is_superuser:
        try:
            from accounts.views import (_grupos_super_con_hrefs, _PANEL_CAT,
                                        _PANEL_KEYS_SOLO_SIDEBAR)
            _labels = {'soporte': 'Soporte y TI', 'academico': 'Académico', 'notas': 'Notas',
                       'cfp': 'CFP', 'admin': 'Administración', 'mantenimiento': 'Mantenimiento'}
            _icons = {'soporte': 'ti-headset', 'academico': 'ti-school', 'notas': 'ti-file-certificate',
                      'cfp': 'ti-briefcase', 'admin': 'ti-report-money', 'mantenimiento': 'ti-engine'}
            _order = ['soporte', 'academico', 'notas', 'cfp', 'admin', 'mantenimiento']
            buckets = {k: [] for k in _order}
            for g in _grupos_super_con_hrefs():
                if g['key'] in _PANEL_KEYS_SOLO_SIDEBAR:
                    continue
                cat = _PANEL_CAT.get(g['key'], 'admin')
                if cat in buckets:
                    buckets[cat].extend(g.get('cards', []))
            # <--- hecho por claude code (02-nov-2026): Académico con sub-grupos (acordeón) pedidos por el usuario
            _ACAD_CONFIG = ('Directorio', 'Período Escolar', 'Ruteo Reportes BL')
            _ACAD_UPLOAD = ('Upload Moodle', 'Moodle')
            cats = []
            for k in _order:
                acc = buckets[k]
                if not acc:
                    continue
                entry = {'key': k, 'label': _labels[k], 'icon': _icons[k], 'accesos': acc}
                if k == 'academico':
                    _es_sal = lambda a: a['t'].startswith('Salidas al baño')   # <--- 02-nov-2026: acordeón "Salidas al baño"
                    sub_cfg = [a for a in acc if a['t'] in _ACAD_CONFIG]
                    sub_upl = [a for a in acc if a['t'] in _ACAD_UPLOAD]
                    sub_sal = [a for a in acc if _es_sal(a)]
                    directos = [a for a in acc if a['t'] not in _ACAD_CONFIG and a['t'] not in _ACAD_UPLOAD and not _es_sal(a)]
                    subs = []
                    if sub_cfg:
                        subs.append({'label': 'Configuración Académica', 'icon': 'ti-settings', 'accesos': sub_cfg})
                    if sub_upl:
                        subs.append({'label': 'Upload', 'icon': 'ti-cloud-upload', 'accesos': sub_upl})
                    if sub_sal:
                        subs.append({'label': 'Salidas al baño', 'icon': 'ti-door-exit', 'accesos': sub_sal})
                    entry['accesos'] = directos
                    entry['subgrupos'] = subs
                elif k == 'mantenimiento':
                    # <--- hecho por claude code (02-nov-2026): Aceites agrupados (acordeón), como Académico
                    _MM_ACEITES = ('Aceite 40', 'Aceite 50', 'Aceite hidráulico')
                    # <--- hecho por claude code (04-nov-2026): Flota de vehículos + Hojas de la flota en su propio acordeón
                    _MM_FLOTA = ('Flota de vehículos', 'Hojas de la flota')
                    entry['accesos'] = [a for a in acc if a['t'] not in _MM_ACEITES and a['t'] not in _MM_FLOTA]
                    subs = []
                    sub_ac = [a for a in acc if a['t'] in _MM_ACEITES]
                    if sub_ac:
                        subs.append({'label': 'Aceites', 'icon': 'ti-droplet', 'accesos': sub_ac})
                    sub_fl = [a for a in acc if a['t'] in _MM_FLOTA]
                    if sub_fl:
                        subs.append({'label': 'Flota', 'icon': 'ti-car', 'accesos': sub_fl})
                    if subs:
                        entry['subgrupos'] = subs
                cats.append(entry)
            ctx['nav_cats_super'] = cats
        except Exception:
            ctx['nav_cats_super'] = []
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
