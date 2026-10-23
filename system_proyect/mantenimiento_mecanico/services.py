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
                                  f'(mínimo {minimo:.2f}). Registrar {insumo.etiqueta_entrada.lower()}.'
                                  + texto_limpieza(insumo),   # <--- 19-oct-2026: en el tanque, dentro de cuánto toca la limpieza
                               modulo='mantenimiento_mecanico', tipo='advertencia', extra=url, enviar_correo=False)
            n += 1
        except Exception as e:   # nunca romper el guardado por un aviso
            print('[mantenimiento_mecanico] no se pudo notificar a', u, e)
    return n


# ─────────────────────────────────────────────────────────────
# <--- hecho por claude code (19-oct-2026): MANTENIMIENTO DEL TANQUE (limpieza del tanque y del filtro).
# 3 veces al año = cada LIMPIEZA_MESES meses desde la última limpieza registrada. Antes de la primera, la fecha
# programada es LIMPIEZA_INICIAL (decidida por el usuario: el 20-oct-2026 se llena el tanque y se limpia).
# ─────────────────────────────────────────────────────────────
import datetime as _dt
import calendar as _cal

LIMPIEZA_MESES = 4
LIMPIEZA_INICIAL = _dt.date(2026, 10, 20)
LIMPIEZA_AVISO_DIAS = 15   # "pronto" = faltan 15 días o menos


def sumar_meses(d, meses):
    m = d.month - 1 + meses
    anio, mes = d.year + m // 12, m % 12 + 1
    return d.replace(year=anio, month=mes, day=min(d.day, _cal.monthrange(anio, mes)[1]))


def estado_limpieza(insumo, hoy=None):
    """{ultima, proxima, dias, estado: al_dia|pronto|hoy|vencido, texto} — solo para insumos en TANQUE."""
    if insumo.presentacion != 'tanque':
        return None
    from .models import LimpiezaTanque
    hoy = hoy or _dt.date.today()
    ultima = LimpiezaTanque.objects.filter(insumo=insumo).order_by('-fecha', '-id').first()
    proxima = sumar_meses(ultima.fecha, LIMPIEZA_MESES) if ultima else LIMPIEZA_INICIAL
    dias = (proxima - hoy).days
    if dias < 0:
        estado, texto = 'vencido', f'vencida hace {-dias} día{"s" if dias != -1 else ""}'
    elif dias == 0:
        estado, texto = 'hoy', 'toca hoy'
    elif dias <= LIMPIEZA_AVISO_DIAS:
        estado, texto = 'pronto', f'en {dias} día{"s" if dias != 1 else ""}'
    else:
        estado, texto = 'al_dia', f'en {dias} días'
    return {'ultima': ultima, 'proxima': proxima, 'dias': dias, 'estado': estado, 'texto': texto,
            'programada': ultima is None, 'cada_meses': LIMPIEZA_MESES}


def texto_limpieza(insumo):
    e = estado_limpieza(insumo)
    if not e:
        return ''
    return f' Limpieza del tanque: {e["texto"]} ({e["proxima"]:%d/%m/%Y}).'


def siguiente_codigo_limpieza():
    from .models import LimpiezaTanque
    ultimo = (LimpiezaTanque.objects.select_for_update().filter(codigo__startswith='LTQ-')
              .order_by('-codigo').values_list('codigo', flat=True).first())
    try:
        n = int(ultimo[4:]) if ultimo else 0
    except ValueError:
        n = 0
    return f'LTQ-{n + 1:04d}'


def avisar_limpieza(insumo, url=''):
    """Aviso por la campana cuando la limpieza está PRONTO / HOY / VENCIDA — una sola vez por etapa y fecha."""
    e = estado_limpieza(insumo)
    if not e or e['estado'] == 'al_dia':
        return 0
    marca = f'{e["estado"]}:{e["proxima"]:%Y-%m-%d}'
    if insumo.aviso_limpieza == marca:
        return 0
    from core.utils_notifications import crear_notificacion
    User = get_user_model()
    msg = {'pronto': f'Mantenimiento del tanque de {insumo.nombre}: la limpieza (tanque y filtro) toca {e["texto"]}, el {e["proxima"]:%d/%m/%Y}.',
           'hoy': f'Mantenimiento del tanque de {insumo.nombre}: la limpieza (tanque y filtro) toca HOY ({e["proxima"]:%d/%m/%Y}).',
           'vencido': f'Mantenimiento del tanque de {insumo.nombre}: la limpieza está {e["texto"]} (tocaba el {e["proxima"]:%d/%m/%Y}).'}[e['estado']]
    n = 0
    for u in User.objects.filter(groups__name=GRUPO_ALERTAS, is_active=True).distinct():
        try:
            crear_notificacion(u, msg, modulo='mantenimiento_mecanico',
                               tipo='alerta' if e['estado'] == 'vencido' else 'advertencia', extra=url, enviar_correo=False)
            n += 1
        except Exception as ex:
            print('[mantenimiento_mecanico] no se pudo notificar la limpieza a', u, ex)
    insumo.aviso_limpieza = marca
    insumo.save(update_fields=['aviso_limpieza'])
    return n
