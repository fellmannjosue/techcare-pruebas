# <--- hecho por claude code (16-oct-2026): MENÚ LATERAL del panel admin (Unfold) por PROGRAMA, igual que el Panel de
# TechCare: Soporte y TI · Académico · Administración · Sistema. Se arma en cada petición desde los modelos
# REGISTRADOS (admin.site), así un módulo nuevo aparece solo (en su programa o en "Otros"). Cada módulo enlaza a su
# página del admin (/admin/<app>/) con la lista de sus tablas. Contadores en Tickets y Préstamos.
from django.contrib import admin
from django.urls import reverse

# app_label → (programa, título, ícono Material Symbols)
MODULOS = {
    # Soporte y TI
    'tickets': ('soporte', 'Tickets', 'confirmation_number'),
    'inventario': ('soporte', 'Inventario', 'inventory_2'),
    'mantenimiento': ('soporte', 'Mantenimiento de equipos', 'build'),
    'inventario_camaras': ('soporte', 'Cámaras', 'videocam'),
    'red': ('soporte', 'Red (IPAM)', 'lan'),
    'desarrollo': ('soporte', 'Gestión de Desarrollo', 'code'),
    'calculadoras': ('soporte', 'Calculadoras', 'calculate'),
    # Académico
    'conducta': ('academico', 'Conducta', 'menu_book'),
    'agendas': ('academico', 'Agendas', 'calendar_month'),
    'moodle_upload': ('academico', 'Moodle', 'cloud_upload'),
    'notas_parcial': ('academico', 'Notas mitad de parcial', 'grading'),
    'ingresos_notas': ('academico', 'Ingreso de notas', 'edit_note'),
    'salidas_bano': ('academico', 'Salidas al baño', 'wc'),
    'enfermeria': ('academico', 'Enfermería', 'medical_services'),
    'cfp': ('academico', 'CFP', 'school'),
    # Administración
    'reloj': ('admin', 'Reloj', 'schedule'),
    'contabilidad': ('admin', 'Contabilidad', 'account_balance'),
    'mantenimiento_mecanico': ('admin', 'Mantenimiento mecánico', 'local_gas_station'),
    'sponsors': ('admin', 'Sponsors', 'volunteer_activism'),
    # Sistema
    'auth': ('sistema', 'Usuarios y grupos', 'group'),
    'accounts': ('sistema', 'Cuentas y seguridad', 'manage_accounts'),
    'core': ('sistema', 'Núcleo (auditoría, avisos)', 'settings'),
    'constance': ('sistema', 'Configuración del sistema', 'tune'),
    'authtoken': ('sistema', 'Tokens de la API', 'key'),
    'portal_super': ('sistema', 'Portal', 'dashboard'),
}
PROGRAMAS = [('soporte', 'Soporte y TI'), ('academico', 'Académico'), ('admin', 'Administración'),
             ('sistema', 'Sistema'), ('otros', 'Otros')]
BADGES = {'tickets': 'core.admin_nav.badge_tickets', 'mantenimiento': 'core.admin_nav.badge_prestamos'}


def _activo(prefijo):
    return lambda request: request.path.startswith(prefijo)


def navegacion(request):
    apps = sorted({m._meta.app_label for m in admin.site._registry})
    por_programa = {k: [] for k, _ in PROGRAMAS}
    for label in apps:
        prog, titulo, icono = MODULOS.get(label, ('otros', label.replace('_', ' ').capitalize(), 'widgets'))
        try:
            enlace = reverse('admin:app_list', args=[label])
        except Exception:
            continue
        item = {'title': titulo, 'icon': icono, 'link': enlace, 'active': _activo(enlace),
                'permission': (lambda lbl: lambda req: req.user.has_module_perms(lbl))(label)}
        if label in BADGES:
            item['badge'] = BADGES[label]
        por_programa[prog].append(item)
    menu = [{
        'title': None, 'separator': False, 'items': [
            {'title': 'Inicio del panel', 'icon': 'space_dashboard', 'link': reverse('admin:index'),
             'active': lambda req: req.path == reverse('admin:index')},
            {'title': 'Volver a TechCare', 'icon': 'arrow_back', 'link': '/'},
            {'title': 'Código del sistema', 'icon': 'data_object', 'link': reverse('settings_codigo'),
             'permission': lambda req: req.user.is_superuser},
        ]}]
    for clave, titulo in PROGRAMAS:
        items = sorted(por_programa[clave], key=lambda i: i['title'].lower())
        if items:
            menu.append({'title': titulo, 'separator': True, 'collapsible': True, 'items': items})
    return menu


def badge_tickets(request):
    from tickets.models import Ticket
    n = Ticket.objects.exclude(status__in=['Resuelto', 'Cerrado']).count()
    return n or None


def badge_prestamos(request):
    """Préstamos de equipo vencidos (siguen prestados después de la fecha de devolución)."""
    import datetime
    from mantenimiento.models import MaintenanceRecord
    n = MaintenanceRecord.objects.filter(tipo_equipo='prestamo', status='En Proceso',
                                         prest_hasta__lt=datetime.date.today()).count()
    return n or None
