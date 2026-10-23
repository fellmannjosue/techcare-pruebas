# <--- hecho por claude code (28-sep-2026): sub-dashboard "Control y Servicio Técnico".
# Une en una sola pantalla el Inventario (equipos) y Mantenimiento (fichas): KPIs, accesos,
# alertas y actividad reciente. No tiene modelos propios: solo LEE de las dos apps.
# Acceso: quien puede ver Inventario o Mantenimiento (mismas reglas que nav_inventory / nav_maintenance).
import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse

from inventario.models import Computadora, Monitor, Televisor, Impresora, Router, DataShow, ItemGeneral
from mantenimiento.models import MaintenanceRecord


def _puede_inventario(u):
    return u.is_superuser or u.has_perm('inventario.view_item') or u.groups.filter(name='inventario').exists()


def _puede_mantenimiento(u):
    return (u.is_superuser or u.has_perm('mantenimiento.view_maintenancerecord')
            or u.groups.filter(name='mantenimiento').exists())


@login_required
def hub(request):
    u = request.user
    ver_inv, ver_mant = _puede_inventario(u), _puede_mantenimiento(u)
    if not (ver_inv or ver_mant):
        raise PermissionDenied('No tienes acceso a Control y Servicio Técnico.')
    hoy = datetime.date.today()
    inicio_mes = hoy.replace(day=1)

    # ── Inventario ──
    inventario = []
    if ver_inv:
        inventario = [
            {'t': 'Computadoras', 's': 'Inventario y gestión', 'i': 'ti-device-desktop', 'c': '#3b82f6', 'n': Computadora.objects.count(), 'url': reverse('inventario:inventario_computadoras')},
            {'t': 'Monitores',    's': 'Control de monitores', 'i': 'ti-device-imac',    'c': '#64748b', 'n': Monitor.objects.count(),     'url': reverse('inventario:inventario_monitores')},
            {'t': 'Televisores',  's': 'Registro y control',   'i': 'ti-device-tv',      'c': '#06b6d4', 'n': Televisor.objects.count(),   'url': reverse('inventario:inventario_televisores')},
            {'t': 'Impresoras',   's': 'Gestión e insumos',    'i': 'ti-printer',        'c': '#f97316', 'n': Impresora.objects.count(),   'url': reverse('inventario:inventario_impresoras')},
            {'t': 'Routers',      's': 'Inventario de red',    'i': 'ti-wifi',           'c': '#22c55e', 'n': Router.objects.count(),      'url': reverse('inventario:inventario_routers')},
            {'t': 'DataShows',    's': 'Proyectores',          'i': 'ti-video',          'c': '#a855f7', 'n': DataShow.objects.count(),    'url': reverse('inventario:inventario_datashows')},
            # <--- hecho por claude code (22-oct-2026): Inventario General salió a su propio grupo (Panel Principal)
        ]
    total_equipos = sum(x['n'] for x in inventario)

    # ── Mantenimiento ──
    fichas = []
    fichas_control = []   # <--- hecho por claude code (22-oct-2026): familia del Control en grupo aparte
    por_tipo = {}
    if ver_mant:
        por_tipo = dict(MaintenanceRecord.objects.values_list('tipo_equipo').annotate(n=Count('id')).values_list('tipo_equipo', 'n'))
        fichas = [
            {'t': 'Computadoras',       's': 'Fichas de reparación',       'i': 'ti-device-desktop', 'c': '#206bc4', 'n': por_tipo.get('computadora', 0),   'url': reverse('mantenimiento:fichas', args=['computadoras'])},
            {'t': 'Impresoras',         's': 'Tinta y sistema',            'i': 'ti-printer',        'c': '#f76707', 'n': por_tipo.get('impresora', 0),     'url': reverse('mantenimiento:fichas', args=['impresoras'])},
        ]
        # <--- hecho por claude code (22-oct-2026): grupo APARTE — la familia del Control de equipo (todas se registran desde el formulario único de Control)
        fichas_control = [
            {'t': 'Control de equipos', 's': 'Evaluación del maestro',     'i': 'ti-clipboard-check','c': '#0ca678', 'n': por_tipo.get('control', 0),       'url': reverse('mantenimiento:fichas', args=['control'])},
            {'t': 'Inspecciones',       's': 'Espacio de trabajo',         'i': 'ti-zoom-check',     'c': '#f59f00', 'n': por_tipo.get('inspeccion', 0),    'url': reverse('mantenimiento:fichas', args=['inspecciones'])},
            {'t': 'Entregas',           's': 'Soporte entrega al usuario', 'i': 'ti-package-export', 'c': '#2fb344', 'n': por_tipo.get('entrega', 0),       'url': reverse('mantenimiento:fichas', args=['entregas'])},
            {'t': 'Recogidas',          's': 'Soporte recibe del usuario', 'i': 'ti-package-import', 'c': '#ae3ec9', 'n': por_tipo.get('recogida', 0),      'url': reverse('mantenimiento:fichas', args=['recogidas'])},
            {'t': 'Casos especiales',   's': 'Recogidas desde un control', 'i': 'ti-alert-octagon',  'c': '#d6336c', 'n': por_tipo.get('caso_especial', 0), 'url': reverse('mantenimiento:fichas', args=['casos-especiales'])},
            {'t': 'Cambios de equipo',  's': 'Equipo anterior → nuevo',    'i': 'ti-replace',        'c': '#4263eb', 'n': por_tipo.get('cambio_equipo', 0), 'url': reverse('mantenimiento:fichas', args=['cambios-equipo'])},
            {'t': 'Reasignaciones',     's': 'Computadora: maestro A → B', 'i': 'ti-arrows-exchange', 'c': '#0891b2', 'n': por_tipo.get('reasignacion', 0), 'url': reverse('mantenimiento:fichas', args=['reasignaciones'])},   # <--- hecho por claude code (12-oct-2026)
            # <--- hecho por claude code (22-oct-2026): Préstamo de equipo salió a su propio grupo (Panel Principal)
            {'t': 'Mantenimientos',     's': 'Mantenimiento del equipo',  'i': 'ti-tool',  'c': '#0ca678', 'n': por_tipo.get('mantenimiento', 0), 'url': reverse('mantenimiento:fichas', args=['mantenimientos'])},   # <--- hecho por claude code (21-oct-2026)
            {'t': 'Reparaciones',       's': 'Reparación · 3 firmas',     'i': 'ti-tools', 'c': '#e8590c', 'n': por_tipo.get('reparacion', 0),    'url': reverse('mantenimiento:fichas', args=['reparaciones'])},
        ]
    total_fichas = sum(por_tipo.values())
    fichas_mes = MaintenanceRecord.objects.filter(date__gte=inicio_mes).count() if ver_mant else 0
    pendientes = MaintenanceRecord.objects.exclude(status='Completado').count() if ver_mant else 0

    # ── Launcher "＋ Registrar" (modal con sub-modales) ─── <--- hecho por claude code (22-oct-2026)
    # Cada botón lleva a la pantalla de alta que YA existe y la auto-abre (router, no duplica formularios).
    # Inventario General y Préstamo NO van aquí (se mueven a programas aparte).
    _mf = lambda slug, nuevo: reverse('mantenimiento:fichas', args=[slug]) + (f'?nuevo={nuevo}' if nuevo else '')
    reg_inv = ([
        {'t': 'Computadora', 'i': 'ti-device-desktop', 'c': '#3b82f6', 'url': reverse('inventario:inventario_computadoras') + '?nuevo=1'},
        {'t': 'Monitor',     'i': 'ti-device-imac',    'c': '#64748b', 'url': reverse('inventario:inventario_monitores') + '?nuevo=1'},
        {'t': 'Televisor',   'i': 'ti-device-tv',      'c': '#06b6d4', 'url': reverse('inventario:inventario_televisores') + '?nuevo=1'},
        {'t': 'Impresora',   'i': 'ti-printer',        'c': '#f97316', 'url': reverse('inventario:inventario_impresoras') + '?nuevo=1'},
        {'t': 'Router',      'i': 'ti-wifi',           'c': '#22c55e', 'url': reverse('inventario:inventario_routers') + '?nuevo=1'},
        {'t': 'DataShow',    'i': 'ti-video',          'c': '#a855f7', 'url': reverse('inventario:inventario_datashows') + '?nuevo=1'},
    ] if ver_inv else [])
    reg_mant = ([
        {'t': 'Computadora', 'i': 'ti-device-desktop', 'c': '#206bc4', 'url': _mf('computadoras', '1')},
        {'t': 'Impresora',   'i': 'ti-printer',        'c': '#f76707', 'url': _mf('impresoras', '1')},
    ] if ver_mant else [])
    # <--- hecho por claude code (22-oct-2026): Inspección/Entrega/Recogida entran por el FORMULARIO ÚNICO de Control
    # (abren el Control con su toggle de acción ya activo). Caso/Cambio/Reasignación/Mantenimiento = switches del Control.
    reg_control = ([
        {'t': 'Control de equipo', 'i': 'ti-clipboard-check', 'c': '#0ca678', 'url': _mf('control', '1')},
        {'t': 'Inspección',        'i': 'ti-zoom-check',      'c': '#f59f00', 'url': _mf('control', 'inspeccion')},
        {'t': 'Entrega',           'i': 'ti-package-export',  'c': '#2fb344', 'url': _mf('control', 'entrega')},
        {'t': 'Recogida',          'i': 'ti-package-import',  'c': '#ae3ec9', 'url': _mf('control', 'recogida')},
        {'t': 'Caso especial',     'i': 'ti-alert-octagon',   'c': '#d6336c', 'url': _mf('control', 'caso_especial')},
        {'t': 'Cambio de equipo',  'i': 'ti-replace',         'c': '#4263eb', 'url': _mf('control', 'cambio_equipo')},
        {'t': 'Reasignación',      'i': 'ti-arrows-exchange', 'c': '#0891b2', 'url': _mf('control', 'reasignacion')},
        {'t': 'Mantenimiento',     'i': 'ti-tool',            'c': '#0ca678', 'url': _mf('control', 'mantenimiento')},
    ] if ver_mant else [])

    # ── Alertas (solo con datos reales) ──
    alertas = []
    if ver_inv:
        tinta_baja = Impresora.objects.filter(Q(nivel_tinta__iexact='Vacío') | Q(nivel_tinta__iexact='Vacio') | Q(nivel_tinta__iexact='Media'))
        for imp in tinta_baja[:5]:
            alertas.append({'nivel': 'warning', 'i': 'ti-droplet-half-2', 't': f'Impresora {imp.asset_id} · {imp.nombre}', 's': f'Nivel de tinta: {imp.nivel_tinta}', 'url': reverse('inventario:inventario_impresoras')})
    if ver_mant:
        malos = (MaintenanceRecord.objects.filter(tipo_equipo='control', estado_equipo__in=['malo', 'fuera'])
                 .select_related('computadora').order_by('-date')[:5])
        for r in malos:
            alertas.append({'nivel': 'danger', 'i': 'ti-alert-triangle', 't': f'{r.computadora.asset_id if r.computadora else r.model} · {r.teacher_name or "—"}',
                            's': f'Control {r.record_id}: {r.get_estado_equipo_display()}', 'url': reverse('mantenimiento:fichas', args=['control'])})
        if ver_inv:
            con_control = set(MaintenanceRecord.objects.filter(tipo_equipo='control', computadora__isnull=False).values_list('computadora_id', flat=True))
            sin_control = Computadora.objects.exclude(asset_id__icontains='LAB').exclude(pk__in=con_control).count()
            if sin_control:
                alertas.append({'nivel': 'info', 'i': 'ti-clipboard-x', 't': f'{sin_control} computadoras sin Control de equipo',
                                's': 'Equipos de general que aún no tienen evaluación registrada', 'url': reverse('mantenimiento:fichas', args=['control'])})
        pend = MaintenanceRecord.objects.exclude(status='Completado').count()
        if pend:
            alertas.append({'nivel': 'warning', 'i': 'ti-clock', 't': f'{pend} fichas pendientes o en proceso', 's': 'Mantenimientos sin cerrar', 'url': reverse('mantenimiento:maintenance_dashboard')})

    recientes = (MaintenanceRecord.objects.select_related('computadora', 'impresora').order_by('-date', '-id')[:8]) if ver_mant else []

    return render(request, 'servicio_tecnico/hub.html', {
        'ver_inv': ver_inv, 'ver_mant': ver_mant,
        'inventario': inventario, 'fichas': fichas, 'fichas_control': fichas_control, 'alertas': alertas, 'recientes': recientes,
        'reg_inv': reg_inv, 'reg_mant': reg_mant, 'reg_control': reg_control,   # <--- hecho por claude code (22-oct-2026): launcher
        'kpis': [
            {'t': 'Equipos en inventario', 'v': total_equipos, 'i': 'ti-package',        'c': '#206bc4'},
            {'t': 'Fichas de mantenimiento', 'v': total_fichas, 'i': 'ti-tool',          'c': '#0ca678'},
            {'t': 'Fichas este mes',        'v': fichas_mes,   'i': 'ti-calendar-event', 'c': '#f59f00'},
            {'t': 'Pendientes / en proceso', 'v': pendientes,  'i': 'ti-clock',           'c': '#d63939'},
        ],
        'url_inv_dashboard': reverse('inventario:dashboard') if ver_inv else '',
        'url_inv_registros': reverse('inventario:inventario_registros') if ver_inv else '',
        'url_inv_categoria': reverse('inventario:inventario_por_categoria') if ver_inv else '',
        'url_mant': reverse('mantenimiento:maintenance_dashboard') if ver_mant else '',
        'nav_home_url': '/',
    })
