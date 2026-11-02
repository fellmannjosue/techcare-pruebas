# datashow/services.py
# <--- hecho por claude code (02-nov-2026): lógica de conflictos de horario y disponibilidad.
from django.db.models import Q

from inventario.models import DataShow
from .models import ReservaDataShow


def reservas_en_conflicto(datashow_id, fecha, hora_inicio, hora_fin, excluir_id=None):
    """Reservas ACTIVAS del MISMO datashow, el MISMO día, cuya franja se solapa con la dada.
    Dos franjas [a,b) y [c,d) se solapan si a < d y c < b."""
    qs = ReservaDataShow.objects.filter(
        datashow_id=datashow_id,
        fecha=fecha,
        estado__in=ReservaDataShow.ESTADOS_ACTIVOS,
        hora_inicio__lt=hora_fin,
        hora_fin__gt=hora_inicio,
    )
    if excluir_id:
        qs = qs.exclude(pk=excluir_id)
    return qs.select_related('solicitante', 'datashow')


def datashows_libres(fecha, hora_inicio, hora_fin):
    """DataShows sin reserva activa que se solape con la franja dada."""
    ocupados = ReservaDataShow.objects.filter(
        fecha=fecha,
        estado__in=ReservaDataShow.ESTADOS_ACTIVOS,
        hora_inicio__lt=hora_fin,
        hora_fin__gt=hora_inicio,
    ).values_list('datashow_id', flat=True)
    return DataShow.objects.exclude(pk__in=list(ocupados)).order_by('asset_id')


def datashows_para_seleccionar():
    """Catálogo de DataShows para el formulario (todos, en orden)."""
    return DataShow.objects.all().order_by('asset_id')
