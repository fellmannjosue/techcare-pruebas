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

    accesos_recientes = RegistroAcceso.objects.select_related('usuario')[:50]

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
