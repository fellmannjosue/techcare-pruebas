# <--- hecho por claude code: motor de SLA para tickets (horas LABORALES L-V 07:00-16:00)
from datetime import timedelta, time as _time

from django.utils import timezone

# Tiempo objetivo de resolución por urgencia (en HORAS LABORALES)
SLA_HORAS = {'urgente': 2, 'alto': 8, 'medio': 24, 'bajo': 72}

URGENCIA_CHOICES = (
    ('bajo',    'Bajo'),
    ('medio',   'Medio'),
    ('alto',    'Alto'),
    ('urgente', 'Urgente'),
)

# Ventana laboral
_LAB_INI = _time(7, 0)    # 07:00
_LAB_FIN = _time(16, 0)   # 16:00


def _local(dt):
    """Normaliza a hora local. Soporta USE_TZ=False (naive) y True (aware)."""
    if dt is not None and timezone.is_aware(dt):
        return timezone.localtime(dt)
    return dt


def _es_laborable(d):
    """Lunes a viernes (0=lunes ... 4=viernes)."""
    return d.weekday() < 5


def _siguiente_apertura(dt):
    """Próximo día laborable a las 07:00 después de dt."""
    d = (dt + timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
    while not _es_laborable(d):
        d += timedelta(days=1)
    return d


def sumar_horas_laborales(inicio, horas):
    """Suma 'horas' de tiempo laboral (L-V 07:00-16:00) a 'inicio' → datetime de vencimiento."""
    restante = timedelta(hours=float(horas))
    cur = _local(inicio)
    while restante.total_seconds() > 0:
        if not _es_laborable(cur) or cur.time() >= _LAB_FIN:
            cur = _siguiente_apertura(cur)
            continue
        if cur.time() < _LAB_INI:
            cur = cur.replace(hour=7, minute=0, second=0, microsecond=0)
        fin_dia = cur.replace(hour=16, minute=0, second=0, microsecond=0)
        disp = fin_dia - cur
        if restante <= disp:
            return cur + restante
        restante -= disp
        cur = _siguiente_apertura(fin_dia)
    return cur


def minutos_laborales_entre(a, b):
    """Minutos de tiempo laboral entre a y b (0 si b <= a)."""
    a = _local(a)
    b = _local(b)
    if b <= a:
        return 0
    total = 0
    cur = a
    while cur < b:
        if not _es_laborable(cur) or cur.time() >= _LAB_FIN:
            cur = _siguiente_apertura(cur)
            continue
        if cur.time() < _LAB_INI:
            cur = cur.replace(hour=7, minute=0, second=0, microsecond=0)
            continue
        fin_dia = cur.replace(hour=16, minute=0, second=0, microsecond=0)
        tramo_fin = min(fin_dia, b)
        total += (tramo_fin - cur).total_seconds()
        cur = _siguiente_apertura(fin_dia)
    return int(total // 60)
