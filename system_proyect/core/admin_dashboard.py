from datetime import date, timedelta
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncDate
from accounts.models import RegistroAcceso

User = get_user_model()
DAYS = 14


def _labels_and_zeros():
    today = date.today()
    labels = [(today - timedelta(days=i)).strftime('%d/%m') for i in range(DAYS - 1, -1, -1)]
    dates  = [(today - timedelta(days=i)) for i in range(DAYS - 1, -1, -1)]
    return labels, dates


def _chart_logins():
    labels, dates = _labels_and_zeros()
    qs = (
        User.objects
        .filter(last_login__date__gte=dates[0])
        .annotate(day=TruncDate('last_login'))
        .values('day')
        .annotate(total=Count('id'))
    )
    by_day = {row['day']: row['total'] for row in qs}
    data = [by_day.get(d, 0) for d in dates]
    return {'labels': labels, 'data': data}


def _chart_activity():
    labels, dates = _labels_and_zeros()
    qs = (
        LogEntry.objects
        .filter(action_time__date__gte=dates[0])
        .annotate(day=TruncDate('action_time'))
        .values('day')
        .annotate(total=Count('id'))
    )
    by_day = {row['day']: row['total'] for row in qs}
    data = [by_day.get(d, 0) for d in dates]
    return {'labels': labels, 'data': data}


def dashboard_callback(request, context):
    logins   = _chart_logins()
    activity = _chart_activity()

    total_users   = User.objects.count()
    active_users  = User.objects.filter(is_active=True).count()
    total_actions = LogEntry.objects.count()
    today_actions = LogEntry.objects.filter(action_time__date=date.today()).count()

    accesos_recientes = RegistroAcceso.objects.select_related('usuario')[:10]
    context.update(_indicadores())   # <--- hecho por claude code (16-oct-2026): inicio práctico del panel admin

    context.update({
        'chart_logins_labels':   logins['labels'],
        'chart_logins_data':     logins['data'],
        'chart_activity_labels': activity['labels'],
        'chart_activity_data':   activity['data'],
        'stat_total_users':      total_users,
        'stat_active_users':     active_users,
        'stat_total_actions':    total_actions,
        'stat_today_actions':    today_actions,
        'accesos_recientes':     accesos_recientes,
    })
    return context


# ─────────────────────────────────────────────────────────────
# <--- hecho por claude code (16-oct-2026): indicadores del inicio del panel admin (tickets, préstamos, agendas,
# Moodle, usuarios), últimos cambios de la auditoría (simple_history) y accesos a los módulos por programa.
# Cada bloque se protege por separado: si una app falla, el inicio igual carga.
# ─────────────────────────────────────────────────────────────
def _seguro(fn, defecto=None):
    try:
        return fn()
    except Exception:
        return defecto


def _kpi_tickets():
    from django.utils import timezone
    from tickets.models import Ticket
    abiertos = Ticket.objects.exclude(status__in=['Resuelto', 'Cerrado'])
    return {'abiertos': abiertos.count(), 'nuevos': abiertos.filter(status__in=['Nuevo', 'Pendiente']).count(),
            'vencidos': abiertos.filter(sin_sla=False, vence_en__lt=timezone.now())
                                .exclude(status__in=['En espera del usuario', 'Incompleto']).count()}


def _kpi_prestamos():
    from mantenimiento.models import MaintenanceRecord
    q = MaintenanceRecord.objects.filter(tipo_equipo='prestamo')
    return {'prestados': q.filter(status='En Proceso').count(),
            'vencidos': q.filter(status='En Proceso', prest_hasta__lt=date.today()).count(),
            'por_firmar': q.filter(status='Pendiente').count()}


def _kpi_agendas():
    from agendas.models import Agenda
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    q = Agenda.objects.filter(semana_inicio__gte=lunes, semana_inicio__lte=lunes + timedelta(days=6))
    out = {'semana': q.count(), 'con_imagen': q.exclude(imagen_final='').exclude(imagen_final__isnull=True).count(),
           'lunes': lunes, 'viernes': lunes + timedelta(days=4), 'en_moodle': 0}
    try:
        from moodle_upload.models import PublicacionMoodle
        out['en_moodle'] = PublicacionMoodle.objects.filter(ok=True, agenda__in=q).values('agenda').distinct().count()
    except Exception:
        pass
    return out


def _kpi_moodle():
    from django.utils import timezone
    from moodle_upload.models import ConexionMoodle, PublicacionMoodle
    hace7 = timezone.now() - timedelta(days=7)
    con = ConexionMoodle.objects.filter(activa=True).first()
    dias = (con.vence - timezone.now()).days if con and con.vence else None
    return {'ok7': PublicacionMoodle.objects.filter(ok=True, fecha__gte=hace7).count(),
            'err7': PublicacionMoodle.objects.filter(ok=False, fecha__gte=hace7).count(),
            'conexion': con.nombre if con else '', 'token_dias': dias}


def _ultimos_cambios(n=12):
    """Últimos cambios de TODAS las tablas con historial (últimos 7 días), los más recientes primero."""
    from django.apps import apps
    from django.core.cache import cache
    datos = cache.get('tc_admin_ultimos_cambios')
    if datos is not None:
        return datos
    desde = date.today() - timedelta(days=7)
    filas = []
    for m in apps.get_models():
        if not m.__name__.startswith('Historical') or not hasattr(m, 'history_date'):
            continue
        try:
            for h in m.objects.filter(history_date__date__gte=desde).select_related('history_user').order_by('-history_date')[:n]:
                filas.append({'fecha': h.history_date, 'tipo': h.history_type,
                              'usuario': (h.history_user.get_full_name() or h.history_user.username) if h.history_user_id else 'Sistema',
                              'modelo': m.instance_type._meta.verbose_name.capitalize() if hasattr(m, 'instance_type') else m.__name__[10:],
                              'app': m._meta.app_label, 'objeto': str(h).rsplit(' as of ', 1)[0][:90]})
        except Exception:
            continue
    filas.sort(key=lambda f: f['fecha'], reverse=True)
    datos = filas[:n]
    cache.set('tc_admin_ultimos_cambios', datos, 120)
    return datos


def _indicadores():
    from core.admin_nav import PROGRAMAS, MODULOS
    from django.contrib import admin
    from django.urls import reverse
    modulos = {}
    for m in admin.site._registry:
        modulos.setdefault(m._meta.app_label, 0)
        modulos[m._meta.app_label] += 1
    programas = []
    for clave, titulo in PROGRAMAS:
        items = []
        for label, n in modulos.items():
            prog, nombre, icono = MODULOS.get(label, ('otros', label.replace('_', ' ').capitalize(), 'widgets'))
            if prog == clave:
                items.append({'nombre': nombre, 'icono': icono, 'tablas': n, 'url': reverse('admin:app_list', args=[label])})
        if items:
            programas.append({'titulo': titulo, 'items': sorted(items, key=lambda i: i['nombre'].lower())})
    return {
        'k_tickets': _seguro(_kpi_tickets, {}), 'k_prestamos': _seguro(_kpi_prestamos, {}),
        'k_agendas': _seguro(_kpi_agendas, {}), 'k_moodle': _seguro(_kpi_moodle, {}),
        'k_accesos_hoy': _seguro(lambda: RegistroAcceso.objects.filter(fecha_hora__date=date.today()).count(), 0),
        'ultimos_cambios': _seguro(_ultimos_cambios, []), 'programas_admin': programas,
        'url_tickets': _seguro(lambda: reverse('admin:tickets_ticket_changelist'), '#'),
        'url_prestamos': _seguro(lambda: reverse('admin:mantenimiento_maintenancerecord_changelist') + '?tipo_equipo__exact=prestamo', '#'),
        'url_agendas': _seguro(lambda: reverse('admin:agendas_agenda_changelist'), '#'),
        'url_moodle': _seguro(lambda: reverse('admin:moodle_upload_publicacionmoodle_changelist'), '#'),
    }
