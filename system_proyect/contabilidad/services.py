# <--- hecho por claude code: lógica de negocio del módulo Contabilidad.
# FASE 2: registrar movimientos de inventario con valuación PROMEDIO PONDERADO.
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from django.utils import timezone

from .models import (ProductoUniforme, MovimientoUniforme, ClaseMovimiento, TipoSalida,
                     CLASES_ENTRADA, CompraProveedor, DetalleCompra, EstadoCompra)


def _q2(x):
    return Decimal(x).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _q4(x):
    return Decimal(x).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


@transaction.atomic
def registrar_movimiento(producto_id, *, clase, cantidad, fecha, usuario,
                         costo_unitario=None, concepto='', motivo='', observaciones='',
                         tipo_salida='', precio_unitario=None, compra=None):
    """Registra un movimiento y actualiza existencia + costo promedio del producto.
    - Entradas/saldo inicial: recalculan el promedio ponderado con su costo unitario.
    - Ajuste (+): entra al costo promedio actual (no altera el promedio).
    - Salidas/ajuste (−): salen al costo promedio actual; el promedio NO cambia.
    Todo dentro de una transacción con bloqueo del producto (sin negativos)."""
    prod = ProductoUniforme.objects.select_for_update().get(pk=producto_id)
    cantidad = int(cantidad)
    if cantidad <= 0:
        raise ValidationError('La cantidad debe ser mayor a cero.')

    exist = int(prod.existencia_actual)
    prom = prod.costo_promedio or Decimal('0')
    es_entrada = clase in CLASES_ENTRADA

    if es_entrada:
        if clase in (ClaseMovimiento.SALDO_INICIAL, ClaseMovimiento.ENTRADA):
            if costo_unitario is None or Decimal(costo_unitario) < 0:
                raise ValidationError('El costo unitario es obligatorio (y ≥ 0) en entradas.')
            cu = _q4(costo_unitario)
        else:  # AJUSTE_POS entra al costo promedio actual
            cu = prom
        valor_previo = Decimal(exist) * prom
        valor_nuevo = valor_previo + (Decimal(cantidad) * cu)
        nueva_exist = exist + cantidad
        nuevo_prom = _q4(valor_nuevo / nueva_exist) if nueva_exist > 0 else Decimal('0')
        importe = _q2(Decimal(cantidad) * cu)
    else:  # SALIDA / AJUSTE_NEG
        if cantidad > exist:
            raise ValidationError(f'No hay existencia suficiente (disponible: {exist}).')
        cu = prom
        nueva_exist = exist - cantidad
        nuevo_prom = prom  # el promedio ponderado no cambia en salidas
        importe = _q2(Decimal(cantidad) * prom)   # importe = costo de la salida (al promedio)

    # <--- FASE 2.1: solo las salidas tipo VENTA generan ingreso.
    ingreso = Decimal('0')
    pu = Decimal('0')
    if not es_entrada and clase == ClaseMovimiento.SALIDA and tipo_salida == TipoSalida.VENTA:
        base_precio = precio_unitario if precio_unitario is not None else (prod.precio_venta or Decimal('0'))
        pu = _q4(base_precio)
        ingreso = _q2(Decimal(cantidad) * pu)

    mov = MovimientoUniforme.objects.create(
        producto=prod, fecha=fecha, clase=clase,
        concepto=concepto or dict(ClaseMovimiento.choices)[clase],
        cantidad=cantidad, costo_unitario=_q4(cu), importe=importe,
        existencia_despues=nueva_exist, costo_promedio_despues=nuevo_prom,
        motivo=motivo, observaciones=observaciones,
        tipo_salida=(tipo_salida if not es_entrada else ''),
        precio_unitario=pu, ingreso=ingreso, compra=compra,
        creado_por=usuario, modificado_por=usuario,
    )
    prod.existencia_actual = nueva_exist
    prod.costo_promedio = nuevo_prom
    prod.modificado_por = usuario
    prod.save(update_fields=['existencia_actual', 'costo_promedio', 'modificado_por', 'fecha_modificado'])
    return mov


# ═══════════════════════ FASE 2.1 · Compras a proveedores ═══════════════════════
@transaction.atomic
def registrar_compra(*, proveedor, fecha, usuario, documento='', observaciones='', lineas):
    """Crea una compra en BORRADOR con sus líneas. 'lineas' = lista de dicts:
    {producto (obj/id), cantidad, costo_unitario, tipo_impuesto (obj/id/None)}.
    NO afecta inventario todavía (eso ocurre al confirmar)."""
    if not lineas:
        raise ValidationError('La compra debe tener al menos una línea.')
    compra = CompraProveedor(proveedor=proveedor, fecha=fecha, documento=documento,
                             observaciones=observaciones, estado=EstadoCompra.BORRADOR,
                             creado_por=usuario, modificado_por=usuario)
    compra.save()
    compra.codigo = f'CP-{compra.pk:05d}'
    compra.save(update_fields=['codigo'])
    for ln in lineas:
        d = DetalleCompra(
            compra=compra,
            producto_id=getattr(ln['producto'], 'pk', ln['producto']),
            cantidad=int(ln['cantidad']),
            costo_unitario=Decimal(ln['costo_unitario']),
            tipo_impuesto_id=(getattr(ln.get('tipo_impuesto'), 'pk', ln.get('tipo_impuesto')) or None),
        )
        if d.cantidad <= 0 or d.costo_unitario < 0:
            raise ValidationError('Cantidad debe ser > 0 y costo ≥ 0 en cada línea.')
        d.calcular()
        d.save()
    compra.recalcular_totales()
    return compra


@transaction.atomic
def confirmar_compra(compra_id, usuario):
    """Confirma la compra: genera UNA entrada de inventario por línea (fuente única).
    Idempotente: si ya está confirmada no vuelve a generar existencias."""
    compra = CompraProveedor.objects.select_for_update().get(pk=compra_id)
    if compra.estado == EstadoCompra.CONFIRMADA:
        return compra  # ya afectó inventario; no duplicar
    if compra.estado == EstadoCompra.ANULADA:
        raise ValidationError('La compra está anulada; no puede confirmarse.')
    detalles = list(compra.detalles.select_related('producto'))
    if not detalles:
        raise ValidationError('La compra no tiene líneas.')
    for d in detalles:
        registrar_movimiento(
            d.producto_id, clase=ClaseMovimiento.ENTRADA, cantidad=d.cantidad,
            fecha=compra.fecha, usuario=usuario, costo_unitario=d.costo_unitario,
            concepto=f'Compra {compra.codigo} · {compra.proveedor.nombre}',
            compra=compra)
    compra.estado = EstadoCompra.CONFIRMADA
    compra.confirmada_por = usuario
    compra.confirmada_en = timezone.now()
    compra.modificado_por = usuario
    compra.save(update_fields=['estado', 'confirmada_por', 'confirmada_en', 'modificado_por', 'fecha_modificado'])
    return compra


@transaction.atomic
def anular_compra(compra_id, usuario, motivo=''):
    """Anula una compra CONFIRMADA generando movimientos inversos (ajuste −) por cada línea.
    Si la existencia ya fue consumida (no alcanza), no permite anular (evita negativos)."""
    compra = CompraProveedor.objects.select_for_update().get(pk=compra_id)
    if compra.estado != EstadoCompra.CONFIRMADA:
        raise ValidationError('Solo se puede anular una compra confirmada.')
    for d in compra.detalles.select_related('producto'):
        registrar_movimiento(
            d.producto_id, clase=ClaseMovimiento.AJUSTE_NEG, cantidad=d.cantidad,
            fecha=timezone.now().date(), usuario=usuario,
            concepto=f'Anulación de compra {compra.codigo}',
            motivo=(motivo or 'Anulación de compra'))
    compra.estado = EstadoCompra.ANULADA
    compra.anulada_por = usuario
    compra.anulada_en = timezone.now()
    compra.motivo_anulacion = motivo
    compra.modificado_por = usuario
    compra.save(update_fields=['estado', 'anulada_por', 'anulada_en', 'motivo_anulacion',
                               'modificado_por', 'fecha_modificado'])
    return compra
