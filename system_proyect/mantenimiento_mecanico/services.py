# <--- hecho por claude code (01-oct-2026): lógica de inventario de Mantenimiento Mecánico.
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max, Sum

from .models import Entrada, Entrega, Insumo, GRUPO_ALERTAS

_D0 = Decimal('0')


def saldo(insumo):
    e = Entrada.objects.filter(insumo=insumo).aggregate(t=Sum('cantidad'))['t'] or _D0
    s = Entrega.objects.filter(insumo=insumo).aggregate(t=Sum('galones'))['t'] or _D0
    return e - s


def resumen(insumo):
    """Saldo y métricas de presentación: % del tanque, barriles equivalentes, bandera de saldo bajo."""
    e = Entrada.objects.filter(insumo=insumo).aggregate(t=Sum('cantidad'))['t'] or _D0
    s = Entrega.objects.filter(insumo=insumo).aggregate(t=Sum('galones'))['t'] or _D0
    sal = e - s
    r = {'entradas': e, 'entregas': s, 'saldo': sal, 'pct': None, 'barriles': None,
         'bajo': sal < (insumo.minimo_alerta or _D0)}
    cap = insumo.capacidad_envase or _D0
    if insumo.presentacion == 'tanque' and cap > 0:
        r['pct'] = max(0, min(100, int(sal * 100 / cap)))
    if insumo.presentacion == 'barril' and cap > 0:
        r['barriles'] = (sal / cap).quantize(Decimal('0.01'))
    ult = Entrada.objects.filter(insumo=insumo).order_by('-fecha', '-id').first()
    r['ultima_entrada'] = ult
    return r


def siguiente_numero(insumo):
    """Correlativo por insumo, con bloqueo para no repetir números en guardados simultáneos."""
    with transaction.atomic():
        Insumo.objects.select_for_update().get(pk=insumo.pk)
        m = Entrega.objects.filter(insumo=insumo).aggregate(m=Max('numero'))['m'] or 0
        return m + 1


def kilometraje_anterior(maquinaria, excluir_pk=None):
    if not maquinaria:
        return None
    qs = Entrega.objects.filter(maquinaria=maquinaria, kilometraje__isnull=False)
    if excluir_pk:
        qs = qs.exclude(pk=excluir_pk)
    e = qs.order_by('-fecha', '-hora', '-id').first()
    return e.kilometraje if e else None


def alertar_si_bajo(insumo, saldo_antes, saldo_despues, url=''):
    """Avisa (campana + toast) al grupo de alertas solo al CRUZAR el mínimo hacia abajo, no en cada entrega."""
    minimo = insumo.minimo_alerta or _D0
    if not (saldo_antes >= minimo and saldo_despues < minimo):
        return 0
    from core.utils_notifications import crear_notificacion
    User = get_user_model()
    n = 0
    for u in User.objects.filter(groups__name=GRUPO_ALERTAS, is_active=True).distinct():
        try:
            crear_notificacion(u, f'Saldo bajo de {insumo.nombre}: quedan {saldo_despues:.2f} gal '
                                  f'(mínimo {minimo:.2f}). Registrar {insumo.etiqueta_entrada.lower()}.',
                               modulo='mantenimiento_mecanico', tipo='advertencia', extra=url, enviar_correo=False)
            n += 1
        except Exception as e:   # nunca romper el guardado por un aviso
            print('[mantenimiento_mecanico] no se pudo notificar a', u, e)
    return n
