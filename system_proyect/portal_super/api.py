# portal_super/api.py
# <--- hecho por claude code: API JSON del portal nuevo del superusuario.
# Mismo patrón que inventario_camaras/api.py: sesión de Django (mismo dominio),
# sin CORS ni JWT. Reúsa las MISMAS consultas que ya existen en el sistema
# (accounts.views.settings_actividad, menu_view, core.maintenance_modules) para
# no duplicar lógica ni inventar números nuevos.
import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count
from django.db.models.functions import TruncDate
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.models import RegistroAcceso

User = get_user_model()


class SoloSuperuser(permissions.BasePermission):
    """Solo el superusuario entra a esta API (a diferencia de SoloStaff de cámaras)."""
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_superuser)


def _pendientes():
    """tickets/reportes pendientes — mismas queries que accounts.views.menu_view."""
    datos = {'tickets': 0, 'reportes_bl': 0, 'reportes_col': 0}
    try:
        from tickets.models import Ticket
        datos['tickets'] = Ticket.objects.exclude(status__iexact='Resuelto').count()
    except Exception:
        pass
    try:
        from conducta.models import ReporteInformativo, ReporteConductual, ProgressReport
        datos['reportes_bl'] = (
            ReporteInformativo.objects.filter(area='bilingue', estado='enviado').count()
            + ReporteConductual.objects.filter(area='bilingue', estado='enviado').count()
            + ProgressReport.objects.filter(estado='enviado').count()
        )
        datos['reportes_col'] = (
            ReporteInformativo.objects.filter(area='colegio', estado='enviado').count()
            + ReporteConductual.objects.filter(area='colegio', estado='enviado').count()
        )
    except Exception:
        pass
    return datos


def _estado_modulos():
    """Estado de mantenimiento por módulo — reúsa core.maintenance_modules."""
    try:
        from constance import config
        from core.maintenance_modules import modulos_para_ui, hay_restricciones
        modulos = modulos_para_ui(config)
        return {
            'mantenimiento_activo': bool(getattr(config, 'MAINTENANCE_MODE', False)),
            'con_restricciones': hay_restricciones(config),
            'modulos': [{'key': m['key'], 'label': m['label'], 'estado': m['estado'],
                         'icon': m.get('icon', ''), 'color': m.get('color', '')} for m in modulos],
        }
    except Exception:
        return {'mantenimiento_activo': False, 'con_restricciones': False, 'modulos': []}


@api_view(['GET'])
@permission_classes([SoloSuperuser])
def resumen(request):
    """Todo el dashboard en una sola llamada."""
    today = datetime.date.today()
    hace_30 = today - datetime.timedelta(days=29)

    # Logins por día (30d) — patrón de settings_actividad
    logins_dia = (RegistroAcceso.objects
                  .filter(fecha_hora__date__gte=hace_30)
                  .annotate(dia=TruncDate('fecha_hora'))
                  .values('dia').annotate(total=Count('id')).order_by('dia'))
    dia_map = {i['dia']: i['total'] for i in logins_dia}
    serie_logins = []
    for i in range(30):
        d = hace_30 + datetime.timedelta(days=i)
        serie_logins.append({'label': d.strftime('%d/%m'), 'valor': dia_map.get(d, 0)})

    top_usuarios = list(RegistroAcceso.objects
                        .filter(fecha_hora__date__gte=hace_30)
                        .values('username').annotate(total=Count('id'))
                        .order_by('-total')[:8])

    accesos = (RegistroAcceso.objects.select_related('usuario')
               .order_by('-fecha_hora')[:15])
    accesos_recientes = [{
        'usuario': (a.usuario.get_full_name() or a.usuario.username) if a.usuario else a.username,
        'username': a.username,
        'ip': a.ip or '',
        'fecha': a.fecha_hora.strftime('%d/%m/%Y %H:%M') if a.fecha_hora else '',
    } for a in accesos]

    # Roles (grupos) con cuántos usuarios tienen
    roles = list(Group.objects.annotate(n=Count('user')).order_by('-n', 'name')
                 .values('name', 'n')[:10])

    return Response({
        'usuario': {
            'nombre': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
        },
        'conteos': {
            'usuarios': User.objects.count(),
            'activos': User.objects.filter(is_active=True).count(),
            'inactivos': User.objects.filter(is_active=False).count(),
            'staff': User.objects.filter(is_staff=True, is_superuser=False).count(),
            'superusers': User.objects.filter(is_superuser=True).count(),
            'roles': Group.objects.count(),
            'logins_hoy': RegistroAcceso.objects.filter(fecha_hora__date=today).count(),
            'logins_total': RegistroAcceso.objects.count(),
        },
        'pendientes': _pendientes(),
        'sistema': _estado_modulos(),
        'serie_logins': serie_logins,
        'top_usuarios': [{'username': u['username'], 'total': u['total']} for u in top_usuarios],
        'roles': [{'nombre': r['name'], 'usuarios': r['n']} for r in roles],
        'accesos_recientes': accesos_recientes,
    })


# Navegación del portal: secciones + items con href RESUELTO por Django (nunca rompe).
# 'spa': True → lo maneja la propia SPA (Dashboard, Usuarios); si no, abre la página clásica.
_NAV = [
    {'key': 'principal', 'titulo': '', 'items': [
        {'label': 'Dashboard', 'icon': 'ti-layout-dashboard', 'spa': 'dashboard'},
    ]},
    {'key': 'admin', 'titulo': 'Administración', 'items': [
        {'label': 'Usuarios y Roles', 'icon': 'ti-users', 'spa': 'usuarios'},
        {'label': 'Correos', 'icon': 'ti-mail', 'url': 'settings_correos'},
        {'label': 'Modo Mantenimiento', 'icon': 'ti-tool', 'url': 'mantenimiento_modo'},
    ]},
    {'key': 'monitoreo', 'titulo': 'Monitoreo', 'items': [
        {'label': 'Actividad', 'icon': 'ti-activity', 'url': 'settings_actividad'},
        {'label': 'Auditoría', 'icon': 'ti-shield-check', 'url': 'settings_auditoria'},
    ]},
    {'key': 'permisos', 'titulo': 'Permisos', 'items': [
        {'label': 'Permisos Reloj', 'icon': 'ti-clock-cog', 'url': 'settings_reloj_permisos'},
        {'label': 'Permisos Coordinadores', 'icon': 'ti-users-group', 'url': 'settings_coord_permisos'},
        {'label': 'Desbloqueo de accesos', 'icon': 'ti-lock-open', 'url': 'settings_desbloqueos'},
    ]},
    {'key': 'soporte', 'titulo': 'Soporte y TI', 'items': [
        {'label': 'Tickets', 'icon': 'ti-ticket', 'url': 'technician_dashboard'},
        {'label': 'Inventario', 'icon': 'ti-package', 'url': 'inventario:dashboard'},
        {'label': 'Mantenimiento', 'icon': 'ti-tool', 'url': 'mantenimiento:maintenance_dashboard'},
        {'label': 'Inventario Cámaras', 'icon': 'ti-camera', 'url': 'inventario_camaras:hub'},
    ]},
    {'key': 'academico', 'titulo': 'Académico', 'items': [
        {'label': 'Coordinador BL', 'icon': 'ti-chalkboard', 'url': 'dashboard_coordinador', 'args': {'area': 'bilingue'}},
        {'label': 'Coordinador Colegio', 'icon': 'ti-user-cog', 'url': 'dashboard_coordinador', 'args': {'area': 'colegio'}},
        {'label': 'Notas Mitad de Parcial', 'icon': 'ti-file-certificate', 'url': 'notas_parcial_index'},
        {'label': 'Agendas', 'icon': 'ti-calendar-week', 'url': 'agendas:form_agenda'},
        {'label': 'Enfermería', 'icon': 'ti-stethoscope', 'url': 'enfermeria:enfermeria_dashboard'},
        {'label': 'Ruteo Reportes BL', 'icon': 'ti-route', 'url': 'routing_bl_config'},
        {'label': 'Directorio', 'icon': 'ti-address-book', 'url': 'directorio_telefonos'},
    ]},
    {'key': 'operacion', 'titulo': 'Operación', 'items': [
        {'label': 'Reloj', 'icon': 'ti-clock', 'url': 'reloj_dashboard'},
        {'label': 'Sponsors', 'icon': 'ti-heart-handshake', 'url': 'sponsors:sponsors_dashboard'},
        {'label': 'Calculadoras', 'icon': 'ti-calculator', 'url': 'calculadoras_dashboard'},
        {'label': 'Salidas al baño', 'icon': 'ti-door-exit', 'url': 'salidas_bano:index'},
        {'label': 'CFP', 'icon': 'ti-school', 'url': 'cfp:dashboard'},
    ]},
]


@api_view(['GET'])
@permission_classes([SoloSuperuser])
def nav(request):
    """Sidebar con hrefs resueltos por Django (mismo criterio que _grupos_super_con_hrefs)."""
    from django.urls import reverse

    def href(item):
        if item.get('spa'):
            return ''
        try:
            return reverse(item['url'], kwargs=item.get('args')) if item.get('args') else reverse(item['url'])
        except Exception:
            return ''

    grupos = []
    for g in _NAV:
        items = [{'label': it['label'], 'icon': it['icon'],
                  'spa': it.get('spa', ''), 'href': href(it)} for it in g['items']]
        items = [it for it in items if it['spa'] or it['href']]  # descartar rutas rotas
        if items:
            grupos.append({'key': g['key'], 'titulo': g['titulo'], 'items': items})
    return Response({'grupos': grupos})


@api_view(['GET'])
@permission_classes([SoloSuperuser])
def usuarios(request):
    """Listado de usuarios con sus roles (para el módulo de administración).
    Multi-admin 'solo UI': el nivel se deriva de is_superuser / is_staff / grupos."""
    q = (request.query_params.get('q') or '').strip()
    qs = User.objects.prefetch_related('groups').order_by('first_name', 'last_name', 'username')
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q)
                       | Q(last_name__icontains=q) | Q(email__icontains=q))
    filtro = request.query_params.get('nivel')  # superuser | staff | usuario | inactivo
    out = []
    for u in qs[:500]:
        if u.is_superuser:
            nivel = 'superuser'
        elif u.is_staff:
            nivel = 'staff'
        else:
            nivel = 'usuario'
        if filtro == 'inactivo' and u.is_active:
            continue
        if filtro in ('superuser', 'staff', 'usuario') and filtro != nivel:
            continue
        out.append({
            'id': u.id,
            'nombre': u.get_full_name() or u.username,
            'username': u.username,
            'email': u.email,
            'nivel': nivel,
            'activo': u.is_active,
            'ultimo_acceso': u.last_login.strftime('%d/%m/%Y %H:%M') if u.last_login else '—',
            'roles': [g.name for g in u.groups.all()],
        })
    return Response({'total': len(out), 'usuarios': out})
