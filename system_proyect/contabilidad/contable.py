# <--- hecho por claude code (23-sep-2026): servicios del núcleo contable (partida doble).
# Toda la lógica dura vive aquí; las vistas solo capturan datos y llaman a estas funciones.
from collections import OrderedDict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Q, Max
from datetime import timedelta
from django.utils import timezone

from .models import (CuentaContable, CentroCosto, PeriodoContable, Asiento, DetalleAsiento,
                     TipoCuenta, TipoAsiento, EstadoAsiento, NATURALEZA_POR_TIPO)

CERO = Decimal('0.00')


# ─────────────────────────── Períodos ───────────────────────────
def periodo_de(fecha, crear=True):
    """Período (año, mes) de una fecha. Se crea abierto si no existe (y `crear`)."""
    p = PeriodoContable.objects.filter(anio=fecha.year, mes=fecha.month).first()
    if p is None and crear:
        p = PeriodoContable.objects.create(anio=fecha.year, mes=fecha.month)
    return p


def exigir_periodo_abierto(fecha):
    p = periodo_de(fecha)
    if not p.abierto:
        raise ValidationError(f'El período {p} está cerrado: no admite partidas ni cambios.')
    return p


# ─────────────────────────── Numeración ───────────────────────────
def siguiente_numero(fecha):
    """Correlativo anual P-AAAA-0001 (se asigna al CONTABILIZAR, para no dejar huecos con borradores)."""
    pref = f'P-{fecha.year}-'
    ultimo = (Asiento.objects.filter(numero__startswith=pref)
              .aggregate(m=Max('numero'))['m'])
    n = int(ultimo.split('-')[-1]) + 1 if ultimo else 1
    return f'{pref}{n:04d}'


# ─────────────────────────── Partidas ───────────────────────────
def _dec(v):
    try:
        return Decimal(str(v or '0')).quantize(Decimal('0.01'))
    except Exception:
        raise ValidationError(f'Importe no válido: {v!r}')


def validar_lineas(lineas):
    """`lineas` = lista de dicts {cuenta, centro_costo, descripcion, debe, haber}.
    Devuelve (lineas_limpias, total_debe, total_haber) o lanza ValidationError."""
    limpias, td, th = [], CERO, CERO
    for i, l in enumerate(lineas, 1):
        cuenta = l.get('cuenta')
        if cuenta is None:
            continue
        debe, haber = _dec(l.get('debe')), _dec(l.get('haber'))
        if debe < 0 or haber < 0:
            raise ValidationError(f'Línea {i}: los importes no pueden ser negativos.')
        if debe == 0 and haber == 0:
            continue
        if debe > 0 and haber > 0:
            raise ValidationError(f'Línea {i}: una línea va en el Debe O en el Haber, no en ambos.')
        if not cuenta.es_detalle:
            raise ValidationError(f'Línea {i}: la cuenta {cuenta.codigo} es de agrupación; usa una cuenta de detalle.')
        if not cuenta.activo:
            raise ValidationError(f'Línea {i}: la cuenta {cuenta.codigo} está inactiva.')
        limpias.append({'cuenta': cuenta, 'centro_costo': l.get('centro_costo'),
                        'descripcion': (l.get('descripcion') or '')[:200], 'debe': debe, 'haber': haber})
        td += debe; th += haber
    if len(limpias) < 2:
        raise ValidationError('La partida necesita al menos dos líneas con importe.')
    if td != th:
        raise ValidationError(f'La partida no cuadra: Debe L {td:,.2f} ≠ Haber L {th:,.2f}.')
    return limpias, td, th


@transaction.atomic
def guardar_asiento(asiento, lineas, usuario, contabilizar=False):
    """Crea/actualiza un asiento en BORRADOR con sus líneas; opcionalmente lo contabiliza."""
    if asiento.pk and not asiento.editable:
        raise ValidationError('Solo se pueden modificar partidas en borrador.')
    periodo = exigir_periodo_abierto(asiento.fecha)
    limpias, td, th = validar_lineas(lineas)
    asiento.periodo = periodo
    asiento.total_debe, asiento.total_haber = td, th
    if not asiento.pk:
        asiento.creado_por = usuario
    asiento.modificado_por = usuario
    asiento.save()
    asiento.detalles.all().delete()
    DetalleAsiento.objects.bulk_create([
        DetalleAsiento(asiento=asiento, orden=i, **l) for i, l in enumerate(limpias, 1)])
    if contabilizar:
        contabilizar_asiento(asiento, usuario)
    return asiento


@transaction.atomic
def contabilizar_asiento(asiento, usuario):
    """Pasa un borrador a CONTABILIZADO: valida cuadre y período, asigna el número definitivo."""
    asiento = Asiento.objects.select_for_update().get(pk=asiento.pk)
    if asiento.estado != EstadoAsiento.BORRADOR:
        raise ValidationError('Solo se contabilizan partidas en borrador.')
    exigir_periodo_abierto(asiento.fecha)
    lineas = [{'cuenta': d.cuenta, 'centro_costo': d.centro_costo, 'descripcion': d.descripcion,
               'debe': d.debe, 'haber': d.haber} for d in asiento.detalles.select_related('cuenta')]
    validar_lineas(lineas)
    if not asiento.numero:
        asiento.numero = siguiente_numero(asiento.fecha)
    asiento.estado = EstadoAsiento.CONTABILIZADO
    asiento.contabilizado_por, asiento.contabilizado_en = usuario, timezone.now()
    asiento.modificado_por = usuario
    asiento.save()
    return asiento


@transaction.atomic
def anular_asiento(asiento, usuario, motivo):
    """Anula una partida contabilizada (deja de afectar saldos; se conserva para auditoría).
    Si el período ya está cerrado, no se puede anular."""
    asiento = Asiento.objects.select_for_update().get(pk=asiento.pk)
    if asiento.estado != EstadoAsiento.CONTABILIZADO:
        raise ValidationError('Solo se anulan partidas contabilizadas.')
    if not (motivo or '').strip() or len(motivo.strip()) < 5:
        raise ValidationError('Indica el motivo de la anulación (mínimo 5 caracteres).')
    exigir_periodo_abierto(asiento.fecha)
    asiento.estado = EstadoAsiento.ANULADO
    asiento.anulado_por, asiento.anulado_en, asiento.motivo_anulacion = usuario, timezone.now(), motivo.strip()[:250]
    asiento.modificado_por = usuario
    asiento.save()
    return asiento


@transaction.atomic
def cerrar_periodo(periodo, usuario):
    if Asiento.objects.filter(periodo=periodo, estado=EstadoAsiento.BORRADOR).exists():
        raise ValidationError(f'Hay partidas en borrador en {periodo}: contabilízalas o elimínalas antes de cerrar.')
    periodo.estado, periodo.cerrado_por, periodo.cerrado_en = 'cerrado', usuario, timezone.now()
    periodo.modificado_por = usuario
    periodo.save()


@transaction.atomic
def reabrir_periodo(periodo, usuario):
    periodo.estado, periodo.cerrado_por, periodo.cerrado_en = 'abierto', None, None
    periodo.modificado_por = usuario
    periodo.save()


# ─────────────────────────── Saldos y reportes ───────────────────────────
def _mov_contabilizados(desde=None, hasta=None, centro=None):
    qs = DetalleAsiento.objects.filter(asiento__estado=EstadoAsiento.CONTABILIZADO)
    if desde:
        qs = qs.filter(asiento__fecha__gte=desde)
    if hasta:
        qs = qs.filter(asiento__fecha__lte=hasta)
    if centro:
        qs = qs.filter(centro_costo=centro)
    return qs


def saldo_natural(cuenta, debe, haber):
    """Saldo con el signo de la naturaleza de la cuenta (positivo = saldo normal)."""
    return (debe - haber) if cuenta.naturaleza == 'deudora' else (haber - debe)


def movimientos_por_cuenta(desde=None, hasta=None, centro=None):
    """{cuenta_id: (debe, haber)} de cuentas de DETALLE con movimiento en el rango."""
    filas = (_mov_contabilizados(desde, hasta, centro).values('cuenta_id')
             .annotate(d=Sum('debe'), h=Sum('haber')))
    return {f['cuenta_id']: (f['d'] or CERO, f['h'] or CERO) for f in filas}


def acumular_arbol(mov, cuentas=None):
    """Suma los movimientos de detalle hacia sus cuentas padre. Devuelve {cuenta_id: (debe, haber)}."""
    cuentas = cuentas or list(CuentaContable.objects.all())
    por_id = {c.pk: c for c in cuentas}
    acum = {}
    for cid, (d, h) in mov.items():
        c = por_id.get(cid)
        while c is not None:
            dd, hh = acum.get(c.pk, (CERO, CERO))
            acum[c.pk] = (dd + d, hh + h)
            c = por_id.get(c.padre_id) if c.padre_id else None
    return acum


def balanza_comprobacion(desde, hasta, centro=None, solo_detalle=False):
    """Filas [{cuenta, saldo_inicial, debe, haber, saldo_final}] ordenadas por código + totales.
    saldo_inicial = movimientos antes de `desde` (en cuentas de resultados se incluye igual; el cierre anual los lleva a cero)."""
    cuentas = list(CuentaContable.objects.filter(activo=True))
    ini = acumular_arbol(movimientos_por_cuenta(None, desde - timedelta(days=1), centro) if desde else {}, cuentas)
    per = acumular_arbol(movimientos_por_cuenta(desde, hasta, centro), cuentas)
    filas, tot = [], {'ini_d': CERO, 'ini_h': CERO, 'debe': CERO, 'haber': CERO, 'fin_d': CERO, 'fin_h': CERO}
    for c in cuentas:
        if solo_detalle and not c.es_detalle:
            continue
        di, hi = ini.get(c.pk, (CERO, CERO)); dp, hp = per.get(c.pk, (CERO, CERO))
        if di == hi == dp == hp == CERO:
            continue
        s_ini = di - hi; s_fin = s_ini + dp - hp          # signo contable: + deudor, − acreedor
        filas.append({'cuenta': c, 'ini_d': max(s_ini, CERO), 'ini_h': max(-s_ini, CERO), 'debe': dp, 'haber': hp,
                      'fin_d': max(s_fin, CERO), 'fin_h': max(-s_fin, CERO)})
        if c.es_detalle:
            tot['ini_d'] += max(s_ini, CERO); tot['ini_h'] += max(-s_ini, CERO); tot['debe'] += dp; tot['haber'] += hp
            tot['fin_d'] += max(s_fin, CERO); tot['fin_h'] += max(-s_fin, CERO)
    return filas, tot


def _seccion(tipos, desde, hasta, centro=None):
    """Árbol de cuentas de unos tipos con saldo natural acumulado: [{cuenta, saldo}] + total."""
    cuentas = list(CuentaContable.objects.filter(activo=True, tipo__in=tipos))
    todas = list(CuentaContable.objects.all())
    acum = acumular_arbol(movimientos_por_cuenta(desde, hasta, centro), todas)
    filas, total = [], CERO
    for c in cuentas:
        d, h = acum.get(c.pk, (CERO, CERO))
        if d == h == CERO:
            continue
        s = saldo_natural(c, d, h)
        filas.append({'cuenta': c, 'saldo': s})
        if c.nivel == 1:
            total += s
    return filas, total


def estado_resultados(desde, hasta, centro=None):
    ing, t_ing = _seccion([TipoCuenta.INGRESO], desde, hasta, centro)
    cos, t_cos = _seccion([TipoCuenta.COSTO], desde, hasta, centro)
    gas, t_gas = _seccion([TipoCuenta.GASTO], desde, hasta, centro)
    return {'ingresos': ing, 'total_ingresos': t_ing, 'costos': cos, 'total_costos': t_cos,
            'gastos': gas, 'total_gastos': t_gas, 'utilidad_bruta': t_ing - t_cos,
            'resultado': t_ing - t_cos - t_gas}


def balance_general(hasta, centro=None):
    """Balance a una fecha. El resultado del ejercicio (acumulado de ingresos−costos−gastos hasta la fecha)
    se muestra como línea de patrimonio para que Activo = Pasivo + Patrimonio."""
    act, t_act = _seccion([TipoCuenta.ACTIVO], None, hasta, centro)
    pas, t_pas = _seccion([TipoCuenta.PASIVO], None, hasta, centro)
    pat, t_pat = _seccion([TipoCuenta.PATRIMONIO], None, hasta, centro)
    er = estado_resultados(None, hasta, centro)
    return {'activo': act, 'total_activo': t_act, 'pasivo': pas, 'total_pasivo': t_pas,
            'patrimonio': pat, 'total_patrimonio': t_pat, 'resultado': er['resultado'],
            'total_pasivo_patrimonio': t_pas + t_pat + er['resultado'],
            'cuadra': t_act == t_pas + t_pat + er['resultado']}


def mayor_cuenta(cuenta, desde=None, hasta=None, centro=None):
    """Libro mayor de una cuenta (si es de agrupación, incluye sus descendientes): saldo inicial + movimientos con saldo corrido."""
    ids = [cuenta.pk]
    if not cuenta.es_detalle:
        pend = [cuenta.pk]
        while pend:
            hijas = list(CuentaContable.objects.filter(padre_id__in=pend).values_list('pk', flat=True))
            ids += hijas; pend = hijas
    base = _mov_contabilizados(None, None, centro).filter(cuenta_id__in=ids)
    ini = base.filter(asiento__fecha__lt=desde).aggregate(d=Sum('debe'), h=Sum('haber')) if desde else {'d': CERO, 'h': CERO}
    saldo = saldo_natural(cuenta, ini['d'] or CERO, ini['h'] or CERO)
    saldo_inicial = saldo
    qs = base
    if desde:
        qs = qs.filter(asiento__fecha__gte=desde)
    if hasta:
        qs = qs.filter(asiento__fecha__lte=hasta)
    filas = []
    for d in qs.select_related('asiento', 'cuenta', 'centro_costo').order_by('asiento__fecha', 'asiento__numero', 'orden'):
        saldo += saldo_natural(cuenta, d.debe, d.haber)
        filas.append({'d': d, 'saldo': saldo})
    tot = qs.aggregate(d=Sum('debe'), h=Sum('haber'))
    return {'saldo_inicial': saldo_inicial, 'filas': filas, 'debe': tot['d'] or CERO, 'haber': tot['h'] or CERO, 'saldo_final': saldo}


# ─────────────────────────── Catálogo base ───────────────────────────
# Catálogo inicial para una asociación sin fines de lucro en Honduras (ISV 15 %, IHSS, RAP, 13º/14º).
# Es un punto de partida EDITABLE: la contadora lo ajusta desde el catálogo (agregar/renombrar/desactivar).
CATALOGO_BASE = [
    ('1', 'ACTIVO', 'activo'),
    ('1.1', 'Activo corriente', 'activo'),
    ('1.1.01', 'Caja', 'activo'),
    ('1.1.01.001', 'Caja general', 'activo'),
    ('1.1.01.002', 'Caja chica', 'activo'),
    ('1.1.02', 'Bancos', 'activo'),
    ('1.1.02.001', 'Banco · cuenta principal', 'activo'),
    ('1.1.02.002', 'Banco · cuenta de donaciones', 'activo'),
    ('1.1.03', 'Cuentas por cobrar', 'activo'),
    ('1.1.03.001', 'Colegiaturas por cobrar', 'activo'),
    ('1.1.03.002', 'Clientes (ventas)', 'activo'),
    ('1.1.03.003', 'Anticipos y préstamos a empleados', 'activo'),
    ('1.1.03.004', 'Donaciones prometidas por cobrar', 'activo'),
    ('1.1.04', 'Inventarios', 'activo'),
    ('1.1.04.001', 'Inventario de uniformes', 'activo'),
    ('1.1.04.002', 'Materia prima CFP', 'activo'),
    ('1.1.04.003', 'Suministros y papelería', 'activo'),
    ('1.1.05', 'Impuestos a favor', 'activo'),
    ('1.1.05.001', 'ISV crédito fiscal (15 %)', 'activo'),
    ('1.1.06', 'Gastos pagados por anticipado', 'activo'),
    ('1.1.06.001', 'Seguros pagados por anticipado', 'activo'),
    ('1.2', 'Activo no corriente', 'activo'),
    ('1.2.01', 'Propiedad, planta y equipo', 'activo'),
    ('1.2.01.001', 'Terrenos', 'activo'),
    ('1.2.01.002', 'Edificios e instalaciones', 'activo'),
    ('1.2.01.003', 'Mobiliario y equipo de oficina', 'activo'),
    ('1.2.01.004', 'Equipo de cómputo y tecnología', 'activo'),
    ('1.2.01.005', 'Vehículos', 'activo'),
    ('1.2.01.006', 'Maquinaria y equipo CFP', 'activo'),
    ('1.2.02', 'Depreciación acumulada', 'activo'),
    ('1.2.02.001', 'Depreciación acumulada · edificios', 'activo'),
    ('1.2.02.002', 'Depreciación acumulada · mobiliario y equipo', 'activo'),
    ('1.2.02.003', 'Depreciación acumulada · equipo de cómputo', 'activo'),
    ('1.2.02.004', 'Depreciación acumulada · vehículos', 'activo'),
    ('2', 'PASIVO', 'pasivo'),
    ('2.1', 'Pasivo corriente', 'pasivo'),
    ('2.1.01', 'Cuentas por pagar', 'pasivo'),
    ('2.1.01.001', 'Proveedores', 'pasivo'),
    ('2.1.01.002', 'Acreedores varios', 'pasivo'),
    ('2.1.02', 'Impuestos y retenciones por pagar', 'pasivo'),
    ('2.1.02.001', 'ISV por pagar (15 %)', 'pasivo'),
    ('2.1.02.002', 'ISR retenido a empleados', 'pasivo'),
    ('2.1.02.003', 'Retenciones a terceros (12.5 % honorarios)', 'pasivo'),
    ('2.1.03', 'Obligaciones laborales', 'pasivo'),
    ('2.1.03.001', 'Sueldos por pagar', 'pasivo'),
    ('2.1.03.002', 'IHSS por pagar', 'pasivo'),
    ('2.1.03.003', 'RAP por pagar', 'pasivo'),
    ('2.1.03.004', 'Provisión décimo tercer mes', 'pasivo'),
    ('2.1.03.005', 'Provisión décimo cuarto mes', 'pasivo'),
    ('2.1.03.006', 'Provisión vacaciones', 'pasivo'),
    ('2.1.04', 'Fondos de donantes restringidos', 'pasivo'),
    ('2.1.04.001', 'Fondos de proyectos por ejecutar', 'pasivo'),
    ('2.1.05', 'Anticipos recibidos', 'pasivo'),
    ('2.1.05.001', 'Matrículas y cursos cobrados por anticipado', 'pasivo'),
    ('2.2', 'Pasivo no corriente', 'pasivo'),
    ('2.2.01', 'Préstamos bancarios a largo plazo', 'pasivo'),
    ('2.2.01.001', 'Préstamo bancario', 'pasivo'),
    ('3', 'PATRIMONIO', 'patrimonio'),
    ('3.1', 'Patrimonio institucional', 'patrimonio'),
    ('3.1.01', 'Fondo social', 'patrimonio'),
    ('3.1.01.001', 'Fondo social / aportes fundacionales', 'patrimonio'),
    ('3.2', 'Resultados', 'patrimonio'),
    ('3.2.01', 'Superávit (déficit) acumulado', 'patrimonio'),
    ('3.2.01.001', 'Superávit (déficit) de ejercicios anteriores', 'patrimonio'),
    ('3.2.02', 'Resultado del ejercicio', 'patrimonio'),
    ('3.2.02.001', 'Superávit (déficit) del ejercicio', 'patrimonio'),
    ('4', 'INGRESOS', 'ingreso'),
    ('4.1', 'Donaciones', 'ingreso'),
    ('4.1.01', 'Donaciones de padrinos (sponsors)', 'ingreso'),
    ('4.1.01.001', 'Apadrinamientos', 'ingreso'),
    ('4.1.02', 'Donaciones generales', 'ingreso'),
    ('4.1.02.001', 'Donaciones en efectivo', 'ingreso'),
    ('4.1.02.002', 'Donaciones en especie', 'ingreso'),
    ('4.1.02.003', 'Donaciones de proyectos (restringidas)', 'ingreso'),
    ('4.2', 'Ingresos educativos', 'ingreso'),
    ('4.2.01', 'Matrículas y colegiaturas', 'ingreso'),
    ('4.2.01.001', 'Matrículas', 'ingreso'),
    ('4.2.01.002', 'Colegiaturas mensuales', 'ingreso'),
    ('4.2.02', 'Cursos CFP', 'ingreso'),
    ('4.2.02.001', 'Ingresos por cursos de formación', 'ingreso'),
    ('4.3', 'Ventas', 'ingreso'),
    ('4.3.01', 'Venta de uniformes', 'ingreso'),
    ('4.3.01.001', 'Venta de uniformes', 'ingreso'),
    ('4.3.02', 'Venta de productos CFP', 'ingreso'),
    ('4.3.02.001', 'Venta de productos elaborados', 'ingreso'),
    ('4.4', 'Otros ingresos', 'ingreso'),
    ('4.4.01', 'Otros ingresos', 'ingreso'),
    ('4.4.01.001', 'Intereses bancarios', 'ingreso'),
    ('4.4.01.002', 'Ingresos varios', 'ingreso'),
    ('5', 'COSTOS', 'costo'),
    ('5.1', 'Costo de ventas', 'costo'),
    ('5.1.01', 'Costo de uniformes vendidos', 'costo'),
    ('5.1.01.001', 'Costo de uniformes vendidos', 'costo'),
    ('5.2', 'Costo de cursos CFP', 'costo'),
    ('5.2.01', 'Materia prima y mantenimiento (60 %)', 'costo'),
    ('5.2.01.001', 'Materia prima consumida', 'costo'),
    ('5.2.01.002', 'Mantenimiento de equipo CFP', 'costo'),
    ('5.2.02', 'Personal instructor (20 %)', 'costo'),
    ('5.2.02.001', 'Pago a instructores', 'costo'),
    ('6', 'GASTOS', 'gasto'),
    ('6.1', 'Gastos de personal', 'gasto'),
    ('6.1.01', 'Sueldos y salarios', 'gasto'),
    ('6.1.01.001', 'Sueldos personal docente', 'gasto'),
    ('6.1.01.002', 'Sueldos personal administrativo', 'gasto'),
    ('6.1.01.003', 'Horas extra y bonos', 'gasto'),
    ('6.1.02', 'Prestaciones y cargas sociales', 'gasto'),
    ('6.1.02.001', 'Décimo tercer mes', 'gasto'),
    ('6.1.02.002', 'Décimo cuarto mes', 'gasto'),
    ('6.1.02.003', 'Vacaciones', 'gasto'),
    ('6.1.02.004', 'IHSS aporte patronal', 'gasto'),
    ('6.1.02.005', 'RAP aporte patronal', 'gasto'),
    ('6.1.02.006', 'Capacitación del personal', 'gasto'),
    ('6.2', 'Gastos administrativos', 'gasto'),
    ('6.2.01', 'Servicios', 'gasto'),
    ('6.2.01.001', 'Energía eléctrica', 'gasto'),
    ('6.2.01.002', 'Agua', 'gasto'),
    ('6.2.01.003', 'Teléfono e internet', 'gasto'),
    ('6.2.01.004', 'Honorarios profesionales', 'gasto'),
    ('6.2.01.005', 'Seguros', 'gasto'),
    ('6.2.01.006', 'Vigilancia y seguridad', 'gasto'),
    ('6.2.02', 'Materiales y suministros', 'gasto'),
    ('6.2.02.001', 'Papelería y útiles de oficina', 'gasto'),
    ('6.2.02.002', 'Materiales de limpieza', 'gasto'),
    ('6.2.02.003', 'Combustible y lubricantes', 'gasto'),
    ('6.2.03', 'Mantenimiento y reparaciones', 'gasto'),
    ('6.2.03.001', 'Mantenimiento de edificios', 'gasto'),
    ('6.2.03.002', 'Mantenimiento de equipo y tecnología', 'gasto'),
    ('6.2.03.003', 'Mantenimiento de vehículos', 'gasto'),
    ('6.2.04', 'Viáticos y transporte', 'gasto'),
    ('6.2.04.001', 'Viáticos', 'gasto'),
    ('6.2.04.002', 'Transporte', 'gasto'),
    ('6.2.05', 'Otros gastos administrativos', 'gasto'),
    ('6.2.05.001', 'Alimentación y atenciones', 'gasto'),
    ('6.2.05.002', 'Impuestos y tasas municipales', 'gasto'),
    ('6.2.05.003', 'Gastos varios', 'gasto'),
    ('6.3', 'Gastos de programas', 'gasto'),
    ('6.3.01', 'Programa educativo', 'gasto'),
    ('6.3.01.001', 'Material didáctico', 'gasto'),
    ('6.3.01.002', 'Becas y ayudas a alumnos', 'gasto'),
    ('6.3.01.003', 'Actividades y eventos escolares', 'gasto'),
    ('6.3.02', 'Programa de nutrición y salud', 'gasto'),
    ('6.3.02.001', 'Alimentación de alumnos', 'gasto'),
    ('6.3.02.002', 'Enfermería y medicamentos', 'gasto'),
    ('6.4', 'Depreciación', 'gasto'),
    ('6.4.01', 'Gasto por depreciación', 'gasto'),
    ('6.4.01.001', 'Depreciación de activos fijos', 'gasto'),
    ('6.5', 'Gastos financieros', 'gasto'),
    ('6.5.01', 'Gastos bancarios', 'gasto'),
    ('6.5.01.001', 'Comisiones bancarias', 'gasto'),
    ('6.5.01.002', 'Intereses sobre préstamos', 'gasto'),
]


@transaction.atomic
def cargar_catalogo_base(usuario):
    """Carga el catálogo base solo si el catálogo está vacío. Devuelve cuántas cuentas creó."""
    if CuentaContable.objects.exists():
        raise ValidationError('El catálogo ya tiene cuentas; el catálogo base solo se carga sobre un catálogo vacío.')
    por_codigo, n = {}, 0
    codigos = {c for c, _, _ in CATALOGO_BASE}
    hijos = {c for c, _, _ in CATALOGO_BASE if any(o != c and o.startswith(c + '.') for o in codigos)}
    for codigo, nombre, tipo in CATALOGO_BASE:
        padre = por_codigo.get(codigo.rsplit('.', 1)[0]) if '.' in codigo else None
        c = CuentaContable(codigo=codigo, nombre=nombre, tipo=tipo, naturaleza=NATURALEZA_POR_TIPO[tipo],
                           padre=padre, es_detalle=codigo not in hijos, creado_por=usuario, modificado_por=usuario)
        c.save(); por_codigo[codigo] = c; n += 1
    return n
