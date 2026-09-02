# <--- hecho por claude code: vistas del módulo Contabilidad.
# FASE 1: dashboard gated. FASE 2: inventario de uniformes (kardex, promedio ponderado).
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Sum, F, Count, ProtectedError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .utils import puede, puede_ver_contabilidad, es_admin_contabilidad
from .models import (ProductoUniforme, MovimientoUniforme, AreaUniforme, TipoUniforme,
                     ClaseMovimiento, CLASES_ENTRADA, TipoSalida,
                     Proveedor, CompraProveedor, DetalleCompra, TipoImpuesto, EstadoCompra,
                     RegaliaProveedor, PrecioProveedor)
from .forms import (ProductoUniformeForm, MovimientoUniformeForm, ProveedorForm, CompraHeaderForm,
                    VentaForm, RegaliaForm, PrecioVentaForm)
from . import services


# Submódulos del programa contable. 'listo=True' cuando la fase que lo implementa
# ya está desplegada; hasta entonces se muestra como "Próximamente" (sin números inventados).
_SUBMODULOS = [
    {'nombre': 'Inventarios',          'icono': 'ti-package',        'color': '#2fb344', 'perm': 'ver_inventario',      'listo': True,  'url': 'contabilidad:inventario_dashboard'},
    {'nombre': 'Cobros',               'icono': 'ti-cash',           'color': '#206bc4', 'perm': 'ver_cobros',          'listo': False},
    {'nombre': 'Deudas',               'icono': 'ti-receipt',        'color': '#d63939', 'perm': 'ver_deudas',          'listo': False},
    {'nombre': 'SAR / Declaraciones',  'icono': 'ti-file-invoice',   'color': '#f59f00', 'perm': 'ver_declaraciones',   'listo': False},
    {'nombre': 'Conciliaciones',       'icono': 'ti-arrows-shuffle', 'color': '#ae3ec9', 'perm': 'ver_conciliaciones',  'listo': False},
    {'nombre': 'Catálogo de Cuentas',  'icono': 'ti-list-numbers',   'color': '#0ca678', 'perm': 'ver_cuentas',         'listo': False},
    {'nombre': 'Partidas Contables',   'icono': 'ti-book',           'color': '#4263eb', 'perm': 'ver_partidas',        'listo': False},
    {'nombre': 'Mayor de Cuentas',     'icono': 'ti-report',         'color': '#7048e8', 'perm': 'ver_cuentas',         'listo': False},
    {'nombre': 'Reportes',             'icono': 'ti-chart-bar',      'color': '#d6336c', 'perm': 'ver_reportes',        'listo': False},
]


@login_required
def dashboard(request):
    """Dashboard del módulo. Acceso validado en backend (no basta ocultar el botón)."""
    if not puede_ver_contabilidad(request.user):
        raise PermissionDenied('No tienes acceso al módulo de Contabilidad.')
    u = request.user
    submodulos = []
    for s in _SUBMODULOS:
        item = dict(s)
        item['visible'] = puede(u, s['perm'])
        submodulos.append(item)
    return render(request, 'contabilidad/dashboard.html', {
        'submodulos': submodulos,
        'es_admin': es_admin_contabilidad(u),
        'ver_regalias': puede(u, 'ver_regalias'),  # <--- hecho por claude code: acceso a Regalías (aparte)
        'nav_home_url': '/',
    })


# <--- hecho por claude code: hub de Inventario por ROL — cada tarjeta se muestra según el permiso del usuario
# A (Ventas) → registrar_venta · B (Abastecimiento) → administrar_inventario/proveedores/compras · C (Supervisión) → reportes/auditoría
# <--- hecho por claude code: Proveedores y Compras ya NO son tarjetas del hub — viven DENTRO de "Inventario de Uniformes"
_INV_TARJETAS = [
    {'t': 'Nueva venta',             's': 'Vender uniformes (descuenta stock)',      'i': 'ti-cash',      'c': '#2fb344', 'url': 'contabilidad:venta_nueva',        'perm': 'registrar_venta'},
    {'t': 'Inventario de Uniformes', 's': 'Existencias, kardex, proveedores y compras', 'i': 'ti-shirt',   'c': '#206bc4', 'url': 'contabilidad:inventario_lista',   'perm': 'ver_inventario'},
    {'t': 'Reporte de Inventario',   's': 'Valuación y existencias',                 'i': 'ti-chart-bar', 'c': '#0ca678', 'url': 'contabilidad:inventario_reporte', 'perm': 'ver_reportes'},
    {'t': 'Auditoría',               's': 'Quién hizo cada venta/compra',            'i': 'ti-history',   'c': '#7048e8', 'url': 'contabilidad:auditoria_lista',    'perm': 'ver_auditoria'},
]


@login_required
def inventario_dashboard(request):
    """Dashboard de Inventario: reúne las herramientas visibles según el rol del usuario."""
    u = request.user
    tarjetas = [t for t in _INV_TARJETAS if puede(u, t['perm'])]
    # <--- hecho por claude code: tarjeta de LECTURA del Inventario institucional (SQL Server).
    # Apagada hasta autorización explícita (settings.INVENTARIO_SQL_TARJETA, env INV_TEST2_MOSTRAR_TARJETA=1).
    from django.conf import settings as _settings
    from .sqlserver_inventory.connection import alias_configurado
    if getattr(_settings, 'INVENTARIO_SQL_TARJETA', False) and puede(u, 'ver_inventario') and alias_configurado():
        tarjetas = tarjetas + [{
            't': 'Inventario institucional', 's': 'Lectura desde SQL Server (Test2)',
            'i': 'ti-database', 'c': '#4263eb', 'url': 'contabilidad:inv_sql_estado', 'perm': 'ver_inventario'}]
    if not tarjetas:
        raise PermissionDenied('No tienes acceso a Inventario.')
    return render(request, 'contabilidad/inventario_dashboard.html', {
        'tarjetas': tarjetas,
        # <--- hecho por claude code: puede iniciar el flujo guiado (necesita crear proveedor + productos)
        'puede_guia':        puede(u, 'crear_proveedor') and puede(u, 'administrar_inventario'),
        'ver_kpis':          puede(u, 'ver_inventario'),
        'total_productos':   ProductoUniforme.objects.count(),
        'total_proveedores': Proveedor.objects.count(),
        'total_compras':     CompraProveedor.objects.count(),
        'es_admin': es_admin_contabilidad(u),
        'nav_home_url': '/',
    })


# <--- hecho por claude code: form dedicado de PRECIOS (precio del proveedor + precio de venta; ISV 15% auto)
@login_required
def producto_precio(request, pk):
    _gate(request.user, 'administrar_inventario')
    import json
    prod = get_object_or_404(ProductoUniforme.objects.select_related('area', 'tipo'), pk=pk)
    pid = request.GET.get('proveedor')

    # <--- hecho por claude code: precio por proveedor = último costo de compra, sobrescrito por precio manual
    precios_map = {}
    for d in (DetalleCompra.objects
              .filter(producto=prod, compra__estado=EstadoCompra.CONFIRMADA)
              .select_related('compra__proveedor')
              .order_by('compra__fecha', 'compra__id')):
        precios_map[str(d.compra.proveedor_id)] = f'{d.costo_unitario:.2f}'   # el último gana (orden asc)
    for pp in prod.precios_proveedor.all():
        precios_map[str(pp.proveedor_id)] = f'{pp.precio:.2f}'

    if request.method == 'POST':
        form = PrecioVentaForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            PrecioProveedor.objects.update_or_create(
                producto=prod, proveedor=cd['proveedor'],
                defaults={'precio': cd['precio_proveedor'],
                          'modificado_por': request.user, 'creado_por': request.user})
            prod.precio_venta = cd['precio_venta']
            prod.modificado_por = request.user
            prod.save(update_fields=['precio_venta', 'modificado_por', 'fecha_modificado'])
            messages.success(request, f'Precio de {cd["proveedor"].nombre} guardado.')
            return redirect('contabilidad:producto_kardex', pk=prod.pk)
    else:
        inicial = {'precio_venta': prod.precio_venta}
        if pid:
            inicial['proveedor'] = pid
            if pid in precios_map:
                inicial['precio_proveedor'] = precios_map[pid]
        form = PrecioVentaForm(initial=inicial)

    precios = prod.precios_proveedor.select_related('proveedor').all()
    return render(request, 'contabilidad/producto_precio_form.html', {
        'form': form, 'prod': prod, 'precios': precios,
        'precios_json': json.dumps(precios_map), 'nav_home_url': '/'})


# <--- hecho por claude code: VENTA de uniformes (rol A). Salida tipo VENTA: descuenta stock y genera ingreso.
@login_required
def venta_nueva(request):
    _gate(request.user, 'registrar_venta')
    import json
    qs = ProductoUniforme.objects.filter(activo=True)
    pid = request.GET.get('producto') or request.POST.get('producto')
    if request.method == 'POST':
        form = VentaForm(request.POST, producto_qs=qs)
        if form.is_valid():
            cd = form.cleaned_data
            cli = (cd.get('cliente') or '').strip()
            try:
                services.registrar_movimiento(
                    cd['producto'].pk, clase=ClaseMovimiento.SALIDA, cantidad=cd['cantidad'],
                    fecha=cd['fecha'], usuario=request.user,
                    tipo_salida=TipoSalida.VENTA, precio_unitario=cd.get('precio_unitario'),
                    concepto=('Venta' + (f' · {cli}' if cli else '')),
                    motivo=cli, observaciones=cd.get('observaciones', ''))
                messages.success(request, 'Venta registrada correctamente.')
                if _guia_activa(request):
                    return _guia_next(request, 'venta')   # fin del flujo → hub
                return redirect('contabilidad:venta_nueva')
            except ValidationError as e:
                messages.error(request, '; '.join(e.messages))
    else:
        inicial = {'fecha': timezone.now().date()}
        if pid:
            inicial['producto'] = pid
        form = VentaForm(initial=inicial, producto_qs=qs)
    # precio de venta por producto (para autollenar en el form)
    precios = {str(p.pk): (str(p.precio_venta) if p.precio_venta is not None else '') for p in qs}
    return render(request, 'contabilidad/venta_form.html', {
        'form': form, 'precios_json': json.dumps(precios),
        'guia': _guia_activa(request), 'paso': _guia_paso('venta'), 'nav_home_url': '/'})


# <--- hecho por claude code: AUDITORÍA del módulo (rol C). Bitácora derivada de datos reales (AuditModel):
# movimientos (ventas/entradas/ajustes), compras y productos. Sin modelo nuevo, sin inventar datos.
@login_required
def auditoria_lista(request):
    _gate(request.user, 'ver_auditoria')
    eventos = []
    for m in (MovimientoUniforme.objects.select_related('producto', 'creado_por')
              .order_by('-fecha_creado')[:200]):
        if m.clase == ClaseMovimiento.SALIDA and m.tipo_salida == TipoSalida.VENTA:
            accion, icono, color = 'Venta', 'ti-cash', '#2fb344'
            detalle = f'{m.cantidad} und · ingreso L {m.ingreso}'
        elif m.es_entrada:
            accion, icono, color = m.get_clase_display(), 'ti-arrow-down-circle', '#206bc4'
            detalle = f'{m.cantidad} und'
        else:
            accion, icono, color = m.get_clase_display(), 'ti-arrow-up-circle', '#f76707'
            detalle = f'{m.cantidad} und'
        eventos.append({'fecha': m.fecha_creado, 'usuario': m.creado_por, 'accion': accion,
                        'objeto': str(m.producto), 'detalle': detalle, 'icono': icono, 'color': color})
    for c in (CompraProveedor.objects.select_related('proveedor', 'creado_por')
              .order_by('-fecha_creado')[:100]):
        eventos.append({'fecha': c.fecha_creado, 'usuario': c.creado_por,
                        'accion': f'Compra ({c.get_estado_display()})',
                        'objeto': f'{c.codigo} · {c.proveedor.nombre}', 'detalle': f'L {c.total}',
                        'icono': 'ti-shopping-cart', 'color': '#4263eb'})
    for p in (ProductoUniforme.objects.select_related('area', 'creado_por')
              .order_by('-fecha_creado')[:100]):
        eventos.append({'fecha': p.fecha_creado, 'usuario': p.creado_por, 'accion': 'Producto creado',
                        'objeto': str(p), 'detalle': p.area.nombre, 'icono': 'ti-shirt', 'color': '#7048e8'})
    eventos = [e for e in eventos if e['fecha']]
    eventos.sort(key=lambda e: e['fecha'], reverse=True)
    return render(request, 'contabilidad/auditoria_lista.html', {
        'eventos': eventos[:150], 'nav_home_url': '/'})


# ═══════════════════════ REGALÍAS DE PROVEEDORES (informe aparte) ═══════════════════════
# <--- hecho por claude code: NO afecta inventario ni contabilidad; solo lleva el conteo por proveedor.
@login_required
def regalias_lista(request):
    _gate(request.user, 'ver_regalias')
    regalias = RegaliaProveedor.objects.select_related('proveedor', 'creado_por').order_by('-fecha', '-id')
    resumen = (RegaliaProveedor.objects
               .values('proveedor__id', 'proveedor__nombre', 'proveedor__color')
               .annotate(entregas=Count('id'), unidades=Sum('cantidad'))
               .order_by('-unidades'))
    return render(request, 'contabilidad/regalias_lista.html', {
        'regalias': regalias, 'resumen': resumen,
        'total_unidades': regalias.aggregate(s=Sum('cantidad'))['s'] or 0,
        'puede_registrar': puede(request.user, 'registrar_regalia'),
        'nav_home_url': '/'})


@login_required
def regalia_nueva(request):
    _gate(request.user, 'registrar_regalia')
    if request.method == 'POST':
        form = RegaliaForm(request.POST)
        if form.is_valid():
            r = form.save(commit=False)
            r.creado_por = request.user
            r.modificado_por = request.user
            r.save()
            messages.success(request, 'Regalía registrada.')
            return redirect('contabilidad:regalias_lista')
    else:
        form = RegaliaForm(initial={'fecha': timezone.now().date()})
    return render(request, 'contabilidad/regalia_form.html', {'form': form, 'nav_home_url': '/'})


# ═══════════════════════ FASE 2 · Inventario de uniformes ═══════════════════════
def _gate(user, codename):
    if not puede(user, codename):
        raise PermissionDenied('No tienes permiso para esta acción de inventario.')


# <--- hecho por claude code: flujo GUIADO de inventario (3 pasos: Proveedor → Producto → Compra)
# La ENTRADA al inventario la registra CONFIRMAR la compra; NO se hace un Movimiento aparte
# (eso duplicaba el stock). "Movimiento" y "Venta" ya NO forman parte del guiado.
_GUIA_PASOS = {
    'proveedor':  (1, 'contabilidad:producto_nuevo'),
    'producto':   (2, 'contabilidad:compra_nueva'),
    'compra':     (3, None),   # fin del guiado → se confirma la compra en su detalle
    'movimiento': (0, None),   # fuera del guiado (saldo inicial / ajustes / mermas / donaciones)
    'venta':      (0, None),   # fuera del guiado (rol de Ventas)
}


def _guia_activa(request):
    return bool(request.GET.get('guia') or request.POST.get('guia'))


def _guia_paso(clave):
    return _GUIA_PASOS[clave][0]


def _guia_next(request, clave, producto_id=None):
    """Redirige al siguiente paso del flujo guiado (arrastrando el producto por la URL)."""
    from django.urls import reverse as _rev
    nxt = _GUIA_PASOS[clave][1]
    # si el siguiente paso es Venta y el usuario no puede vender, termina el flujo
    if nxt == 'contabilidad:venta_nueva' and not puede(request.user, 'registrar_venta'):
        nxt = None
    if not nxt:
        return redirect('contabilidad:inventario_dashboard')
    pid = producto_id or request.GET.get('producto') or request.POST.get('producto')
    url = _rev(nxt) + '?guia=1'
    if pid:
        url += f'&producto={pid}'
    return redirect(url)


@login_required
def inventario_lista(request):
    """Listado de productos con existencia y valor; filtros por área/tipo/búsqueda."""
    _gate(request.user, 'ver_inventario')
    qs = ProductoUniforme.objects.select_related('area', 'tipo')
    g = request.GET
    buscar = (g.get('q') or '').strip()
    if buscar:
        qs = qs.filter(Q(nombre__icontains=buscar) | Q(codigo__icontains=buscar) |
                       Q(talla__icontains=buscar) | Q(color__icontains=buscar))
    if g.get('area'):
        qs = qs.filter(area_id=g['area'])
    if g.get('tipo'):
        qs = qs.filter(tipo_id=g['tipo'])
    if g.get('estado') == 'bajo':
        qs = qs.filter(stock_minimo__gt=0, existencia_actual__lte=F('stock_minimo'))
    productos = list(qs)
    total_valor = sum((p.valor_total for p in productos), Decimal('0'))
    total_unid = sum(p.existencia_actual for p in productos)
    # <--- FASE 2.1: indicadores reales (proveedores, compras, ventas, ingresos)
    ventas = MovimientoUniforme.objects.filter(clase=ClaseMovimiento.SALIDA, tipo_salida=TipoSalida.VENTA)
    ind = {
        'proveedores': Proveedor.objects.filter(activo=True).count(),
        'compras': CompraProveedor.objects.filter(estado=EstadoCompra.CONFIRMADA).count(),
        'compradas': DetalleCompra.objects.filter(compra__estado=EstadoCompra.CONFIRMADA).aggregate(s=Sum('cantidad'))['s'] or 0,
        'vendidas': ventas.aggregate(s=Sum('cantidad'))['s'] or 0,
        'ingresos': ventas.aggregate(s=Sum('ingreso'))['s'] or Decimal('0'),
    }
    return render(request, 'contabilidad/inventario_lista.html', {
        'productos': productos, 'filtros': g,
        'areas': AreaUniforme.objects.filter(activo=True),
        'tipos': TipoUniforme.objects.filter(activo=True),
        'total_valor': total_valor, 'total_unid': total_unid, 'total_prod': len(productos),
        'ind': ind,
        'ver_ingresos': puede(request.user, 'ver_ingresos'),
        'puede_admin': puede(request.user, 'administrar_inventario'),
        'ver_proveedores': puede(request.user, 'ver_proveedores'),
        'ver_compras': puede(request.user, 'ver_compras'),
        'nav_home_url': '/',
    })


@login_required
def producto_kardex(request, pk):
    """Kardex de un producto: tabla estilo Excel (Entradas | Salidas | Existencia)."""
    _gate(request.user, 'ver_inventario')
    prod = get_object_or_404(ProductoUniforme.objects.select_related('area', 'tipo'), pk=pk)
    movimientos = prod.movimientos.select_related('creado_por', 'compra__proveedor').order_by('fecha', 'id')
    # <--- hecho por claude code: FIFO por lotes SOLO para atribuir proveedor a cada salida
    # (el costo sigue siendo promedio ponderado; esto es únicamente trazabilidad de origen).
    from collections import deque
    cola = deque()   # lotes en orden de llegada: [etiqueta_proveedor, cantidad_restante]
    filas = []
    for m in movimientos:
        valor_saldo = (Decimal(m.existencia_despues) * m.costo_promedio_despues).quantize(Decimal('0.01'))
        es_entrada = m.clase in CLASES_ENTRADA
        prov_txt = ''
        if es_entrada:
            if m.compra_id and m.compra and m.compra.proveedor_id:
                etiqueta = m.compra.proveedor.nombre
            elif m.clase == ClaseMovimiento.SALDO_INICIAL:
                etiqueta = 'Saldo inicial'
            else:
                etiqueta = 'Entrada/Ajuste'
            cola.append([etiqueta, m.cantidad])
            prov_txt = etiqueta
        else:
            restante = m.cantidad
            orden, consumido = [], {}
            while restante > 0 and cola:
                lote = cola[0]
                toma = min(lote[1], restante)
                if lote[0] not in consumido:
                    consumido[lote[0]] = 0
                    orden.append(lote[0])
                consumido[lote[0]] += toma
                lote[1] -= toma
                restante -= toma
                if lote[1] == 0:
                    cola.popleft()
            prov_txt = ', '.join(f'{lab} ×{consumido[lab]}' for lab in orden) or '—'
        filas.append({'m': m, 'es_entrada': es_entrada, 'valor_saldo': valor_saldo, 'proveedor': prov_txt})

    # <--- FASE 2.1: indicadores + proveedores del producto (desde datos reales)
    det = DetalleCompra.objects.filter(producto=prod, compra__estado=EstadoCompra.CONFIRMADA).select_related('compra__proveedor')
    unidades_compradas = det.aggregate(s=Sum('cantidad'))['s'] or 0
    ventas = prod.movimientos.filter(clase=ClaseMovimiento.SALIDA, tipo_salida=TipoSalida.VENTA)
    unidades_vendidas = ventas.aggregate(s=Sum('cantidad'))['s'] or 0
    ingresos = ventas.aggregate(s=Sum('ingreso'))['s'] or Decimal('0')
    costo_ventas = ventas.aggregate(s=Sum('importe'))['s'] or Decimal('0')  # al costo promedio (mismo método)
    margen = (ingresos - costo_ventas)
    # proveedores que lo han suministrado
    prov_map = {}
    for d in det:
        pr = d.compra.proveedor
        m = prov_map.setdefault(pr.id, {'prov': pr, 'unidades': 0, 'ultimo_costo': d.costo_unitario, 'ultima_fecha': d.compra.fecha})
        m['unidades'] += d.cantidad
        if d.compra.fecha >= m['ultima_fecha']:
            m['ultima_fecha'] = d.compra.fecha
            m['ultimo_costo'] = d.costo_unitario
    proveedores = sorted(prov_map.values(), key=lambda x: x['prov'].nombre)

    return render(request, 'contabilidad/producto_kardex.html', {
        'prod': prod, 'filas': filas,
        'ind': {'compradas': unidades_compradas, 'vendidas': unidades_vendidas,
                'ingresos': ingresos, 'costo_ventas': costo_ventas, 'margen': margen},
        'proveedores': proveedores,
        'ver_costos': puede(request.user, 'ver_costos'),
        'ver_ingresos': puede(request.user, 'ver_ingresos'),
        'puede_admin': puede(request.user, 'administrar_inventario'),
        'nav_home_url': '/',
    })


@login_required
@require_POST
def catalogo_agregar(request):
    """Agrega un Área o Tipo de uniforme desde el formulario (AJAX). Devuelve JSON."""
    _gate(request.user, 'administrar_inventario')
    grupo = (request.POST.get('grupo') or '').strip()
    nombre = (request.POST.get('nombre') or '').strip()
    if grupo not in ('area', 'tipo'):
        return JsonResponse({'ok': False, 'error': 'Grupo inválido.'}, status=400)
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'Escribe un nombre.'}, status=400)
    if len(nombre) > 60:
        return JsonResponse({'ok': False, 'error': 'Nombre demasiado largo.'}, status=400)
    Model = AreaUniforme if grupo == 'area' else TipoUniforme
    obj, _creado = Model.objects.get_or_create(nombre__iexact=nombre, defaults={'nombre': nombre})
    if not obj.activo:
        obj.activo = True
        obj.save(update_fields=['activo'])
    return JsonResponse({'ok': True, 'value': obj.pk, 'label': obj.nombre})


@login_required
def producto_nuevo(request):
    _gate(request.user, 'administrar_inventario')
    if request.method == 'POST':
        form = ProductoUniformeForm(request.POST)
        if form.is_valid():
            prod = form.save(commit=False)
            prod.creado_por = request.user
            prod.modificado_por = request.user
            prod.save()
            messages.success(request, f'Producto "{prod}" creado. Registra su saldo inicial o una entrada.')
            if _guia_activa(request):
                return _guia_next(request, 'producto', producto_id=prod.pk)
            return redirect('contabilidad:producto_kardex', pk=prod.pk)
    else:
        form = ProductoUniformeForm()
    return render(request, 'contabilidad/producto_form.html',
                  {'form': form, 'modo': 'nuevo',
                   'guia': _guia_activa(request), 'paso': _guia_paso('producto'), 'nav_home_url': '/'})


@login_required
def producto_editar(request, pk):
    _gate(request.user, 'administrar_inventario')
    prod = get_object_or_404(ProductoUniforme, pk=pk)
    if request.method == 'POST':
        form = ProductoUniformeForm(request.POST, instance=prod)
        if form.is_valid():
            prod = form.save(commit=False)
            prod.modificado_por = request.user
            prod.save()
            messages.success(request, f'"{prod}" actualizado.')
            return redirect('contabilidad:producto_kardex', pk=prod.pk)
    else:
        form = ProductoUniformeForm(instance=prod)
    return render(request, 'contabilidad/producto_form.html',
                  {'form': form, 'modo': 'editar', 'prod': prod, 'nav_home_url': '/'})


@login_required
def movimiento_nuevo(request):
    """Formulario simple: registra un movimiento; el sistema calcula existencia/promedio."""
    _gate(request.user, 'administrar_inventario')
    pid = request.GET.get('producto') or request.POST.get('producto')
    if request.method == 'POST':
        form = MovimientoUniformeForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                services.registrar_movimiento(
                    cd['producto'].pk, clase=cd['clase'], cantidad=cd['cantidad'],
                    fecha=cd['fecha'], usuario=request.user,
                    costo_unitario=cd.get('costo_unitario'),
                    concepto=cd.get('concepto', ''), motivo=cd.get('motivo', ''),
                    observaciones=cd.get('observaciones', ''),
                    tipo_salida=cd.get('tipo_salida', ''),
                    precio_unitario=cd.get('precio_unitario'))
                messages.success(request, 'Movimiento registrado.')
                if _guia_activa(request):
                    return _guia_next(request, 'movimiento', producto_id=cd['producto'].pk)
                return redirect('contabilidad:producto_kardex', pk=cd['producto'].pk)
            except ValidationError as e:
                messages.error(request, '; '.join(e.messages))
    else:
        inicial = {'fecha': timezone.now().date()}
        if pid:
            inicial['producto'] = pid
        form = MovimientoUniformeForm(initial=inicial)
    return render(request, 'contabilidad/movimiento_form.html', {
        'form': form, 'guia': _guia_activa(request), 'paso': _guia_paso('movimiento'), 'nav_home_url': '/'})


@login_required
def inventario_reporte(request):
    """Resumen de existencias y valor por área y tipo."""
    _gate(request.user, 'ver_inventario')
    filas = (ProductoUniforme.objects.values('area__nombre', 'tipo__nombre')
             .annotate(unidades=Sum('existencia_actual'), productos=Count('id'))
             .order_by('area__nombre', 'tipo__nombre'))
    # valor total (existencia × promedio) se calcula en Python por precisión decimal
    valor_por_grupo = {}
    for p in ProductoUniforme.objects.all():
        key = (p.area.nombre if p.area else '—', p.tipo.nombre if p.tipo else '—')
        valor_por_grupo[key] = valor_por_grupo.get(key, Decimal('0')) + p.valor_total
    resumen = []
    for f in filas:
        key = (f['area__nombre'], f['tipo__nombre'])
        resumen.append({'area': f['area__nombre'], 'tipo': f['tipo__nombre'],
                        'unidades': f['unidades'] or 0, 'productos': f['productos'] or 0,
                        'valor': valor_por_grupo.get(key, Decimal('0'))})
    total_valor = sum((r['valor'] for r in resumen), Decimal('0'))
    total_unid = sum(r['unidades'] for r in resumen)
    return render(request, 'contabilidad/inventario_reporte.html', {
        'resumen': resumen, 'total_valor': total_valor, 'total_unid': total_unid,
        'nav_home_url': '/'})


# ═══════════════════════ FASE 2.1 · Proveedores ═══════════════════════
def _resumen_proveedor(prov):
    """Resumen calculado desde compras confirmadas (nunca contadores manuales)."""
    det = DetalleCompra.objects.filter(compra__proveedor=prov, compra__estado=EstadoCompra.CONFIRMADA)
    return {
        'compras': prov.compras.filter(estado=EstadoCompra.CONFIRMADA).count(),
        'unidades': det.aggregate(s=Sum('cantidad'))['s'] or 0,
        'productos': det.values('producto').distinct().count(),
        'ultima': prov.compras.filter(estado=EstadoCompra.CONFIRMADA).order_by('-fecha').values_list('fecha', flat=True).first(),
    }


@login_required
def proveedor_lista(request):
    _gate(request.user, 'ver_proveedores')
    qs = Proveedor.objects.all()
    g = request.GET
    if g.get('q'):
        qs = qs.filter(Q(nombre__icontains=g['q']) | Q(nombre_comercial__icontains=g['q']) | Q(contacto__icontains=g['q']))
    if g.get('estado') == 'activo':
        qs = qs.filter(activo=True)
    elif g.get('estado') == 'inactivo':
        qs = qs.filter(activo=False)
    proveedores = []
    for p in qs:
        proveedores.append({'p': p, 'r': _resumen_proveedor(p)})
    return render(request, 'contabilidad/proveedor_lista.html', {
        'proveedores': proveedores, 'filtros': g,
        'puede_crear': puede(request.user, 'crear_proveedor'), 'nav_home_url': '/'})


@login_required
def proveedor_nuevo(request):
    _gate(request.user, 'crear_proveedor')
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            pr = form.save(commit=False)
            pr.creado_por = request.user
            pr.modificado_por = request.user
            pr.save()
            messages.success(request, f'Proveedor "{pr.nombre}" creado.')
            if _guia_activa(request):
                return _guia_next(request, 'proveedor')
            return redirect('contabilidad:proveedor_detalle', pk=pr.pk)
    else:
        form = ProveedorForm()
    return render(request, 'contabilidad/proveedor_form.html', {
        'form': form, 'modo': 'nuevo',
        'guia': _guia_activa(request), 'paso': _guia_paso('proveedor'), 'nav_home_url': '/'})


@login_required
def proveedor_editar(request, pk):
    _gate(request.user, 'editar_proveedor')
    pr = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=pr)
        if form.is_valid():
            pr = form.save(commit=False)
            pr.modificado_por = request.user
            pr.save()
            messages.success(request, f'"{pr.nombre}" actualizado.')
            return redirect('contabilidad:proveedor_detalle', pk=pr.pk)
    else:
        form = ProveedorForm(instance=pr)
    return render(request, 'contabilidad/proveedor_form.html', {'form': form, 'modo': 'editar', 'prov': pr, 'nav_home_url': '/'})


@login_required
def proveedor_detalle(request, pk):
    _gate(request.user, 'ver_proveedores')
    prov = get_object_or_404(Proveedor, pk=pk)
    resumen = _resumen_proveedor(prov)
    # Productos suministrados (desde detalles confirmados)
    det = (DetalleCompra.objects.filter(compra__proveedor=prov, compra__estado=EstadoCompra.CONFIRMADA)
           .select_related('producto', 'compra'))
    prod_map = {}
    for d in det:
        m = prod_map.setdefault(d.producto_id, {'producto': d.producto, 'unidades': 0,
                                                'ultimo_costo': d.costo_unitario, 'ultima_fecha': d.compra.fecha})
        m['unidades'] += d.cantidad
        if d.compra.fecha >= m['ultima_fecha']:
            m['ultima_fecha'] = d.compra.fecha
            m['ultimo_costo'] = d.costo_unitario
    productos = sorted(prod_map.values(), key=lambda x: str(x['producto']))
    historial = prov.compras.order_by('-fecha', '-id')[:50]
    return render(request, 'contabilidad/proveedor_detalle.html', {
        'prov': prov, 'resumen': resumen, 'productos': productos, 'historial': historial,
        'puede_editar': puede(request.user, 'editar_proveedor'),
        'puede_compras': puede(request.user, 'ver_compras'), 'nav_home_url': '/'})


# ═══════════════════════ FASE 2.1 · Compras ═══════════════════════
@login_required
def compra_lista(request):
    _gate(request.user, 'ver_compras')
    qs = CompraProveedor.objects.select_related('proveedor').prefetch_related('detalles')
    g = request.GET
    if g.get('proveedor'):
        qs = qs.filter(proveedor_id=g['proveedor'])
    if g.get('estado'):
        qs = qs.filter(estado=g['estado'])
    if g.get('desde'):
        qs = qs.filter(fecha__gte=g['desde'])
    if g.get('hasta'):
        qs = qs.filter(fecha__lte=g['hasta'])
    if g.get('documento'):
        qs = qs.filter(documento__icontains=g['documento'])
    compras = list(qs[:200])
    return render(request, 'contabilidad/compra_lista.html', {
        'compras': compras, 'filtros': g,
        'proveedores': Proveedor.objects.filter(activo=True),
        'estados': EstadoCompra.choices,
        'puede_registrar': puede(request.user, 'registrar_compra'), 'nav_home_url': '/'})


@login_required
def compra_nueva(request):
    _gate(request.user, 'registrar_compra')
    if request.method == 'POST':
        form = CompraHeaderForm(request.POST)
        prod_ids = request.POST.getlist('linea_producto')
        cants = request.POST.getlist('linea_cantidad')
        costos = request.POST.getlist('linea_costo')
        impuestos = request.POST.getlist('linea_impuesto')
        lineas = []
        for i, pid in enumerate(prod_ids):
            if not pid or not (cants[i] if i < len(cants) else ''):
                continue
            lineas.append({'producto': int(pid), 'cantidad': int(cants[i]),
                           'costo_unitario': costos[i] or '0',
                           'tipo_impuesto': (int(impuestos[i]) if i < len(impuestos) and impuestos[i] else None)})
        if form.is_valid() and lineas:
            cd = form.cleaned_data
            try:
                compra = services.registrar_compra(
                    proveedor=cd['proveedor'], fecha=cd['fecha'], usuario=request.user,
                    documento=cd.get('documento', ''), observaciones=cd.get('observaciones', ''),
                    lineas=lineas)
                # <--- hecho por claude code: fin del guiado en Compra. Al confirmar la compra
                # (en su detalle) entra el stock; NO se hace Movimiento aparte.
                messages.success(request, f'Compra {compra.codigo} en borrador. '
                                          f'Revísala y CONFÍRMALA para que entre al inventario.')
                return redirect('contabilidad:compra_detalle', pk=compra.pk)
            except ValidationError as e:
                messages.error(request, '; '.join(e.messages))
        elif not lineas:
            messages.error(request, 'Agrega al menos una línea de producto.')
    else:
        form = CompraHeaderForm(initial={'fecha': timezone.now().date()})
    return render(request, 'contabilidad/compra_form.html', {
        'form': form,
        'productos': ProductoUniforme.objects.filter(activo=True).select_related('area', 'tipo'),
        'impuestos': TipoImpuesto.objects.filter(activo=True),
        'guia': _guia_activa(request), 'paso': _guia_paso('compra'), 'nav_home_url': '/'})


@login_required
def compra_detalle(request, pk):
    _gate(request.user, 'ver_compras')
    compra = get_object_or_404(CompraProveedor.objects.select_related('proveedor'), pk=pk)
    return render(request, 'contabilidad/compra_detalle.html', {
        'compra': compra, 'detalles': compra.detalles.select_related('producto', 'tipo_impuesto'),
        'puede_confirmar': puede(request.user, 'registrar_compra'),
        'puede_anular': puede(request.user, 'anular_compra'), 'nav_home_url': '/'})


@login_required
@require_POST
def compra_confirmar(request, pk):
    _gate(request.user, 'registrar_compra')
    try:
        services.confirmar_compra(pk, request.user)
        messages.success(request, 'Compra confirmada. Entradas aplicadas al inventario.')
    except ValidationError as e:
        messages.error(request, '; '.join(e.messages))
    return redirect('contabilidad:compra_detalle', pk=pk)


@login_required
@require_POST
def compra_anular(request, pk):
    _gate(request.user, 'anular_compra')
    try:
        services.anular_compra(pk, request.user, motivo=(request.POST.get('motivo') or '').strip())
        messages.success(request, 'Compra anulada (movimientos inversos aplicados).')
    except ValidationError as e:
        messages.error(request, '; '.join(e.messages))
    return redirect('contabilidad:compra_detalle', pk=pk)


# ═══════════════════════ FASE 2.1 · Eliminar (SOLO superusuario) ═══════════════════════
def _solo_super(user):
    if not user.is_superuser:
        raise PermissionDenied('Solo el superusuario puede eliminar registros de Contabilidad.')


@login_required
@require_POST
@transaction.atomic
def producto_eliminar(request, pk):
    """Solo superusuario. Elimina el producto y SU KARDEX (movimientos). Se bloquea únicamente
    si el producto aparece en compras (integridad con CompraProveedor): primero elimina/anula
    esas compras, o desactiva el producto."""
    _solo_super(request.user)
    prod = get_object_or_404(ProductoUniforme, pk=pk)
    nombre = str(prod)
    if prod.detalles_compra.exists():
        messages.error(request, 'No se puede eliminar: el producto aparece en compras. Elimina o anula esas compras primero, o desactívalo.')
        return redirect('contabilidad:producto_kardex', pk=pk)
    prod.movimientos.all().delete()   # el superusuario borra también el kardex del producto
    prod.delete()
    messages.success(request, f'Producto "{nombre}" eliminado (junto con su kardex).')
    return redirect('contabilidad:inventario_lista')


@login_required
@require_POST
def proveedor_eliminar(request, pk):
    _solo_super(request.user)
    prov = get_object_or_404(Proveedor, pk=pk)
    nombre = prov.nombre
    try:
        prov.delete()
    except ProtectedError:
        messages.error(request, 'No se puede eliminar: el proveedor tiene compras registradas. Desactívalo en su lugar.')
        return redirect('contabilidad:proveedor_detalle', pk=pk)
    messages.success(request, f'Proveedor "{nombre}" eliminado.')
    return redirect('contabilidad:proveedor_lista')


@login_required
@require_POST
def compra_eliminar(request, pk):
    _solo_super(request.user)
    compra = get_object_or_404(CompraProveedor, pk=pk)
    if compra.estado != EstadoCompra.BORRADOR:
        messages.error(request, 'Solo se puede eliminar una compra en BORRADOR. Las confirmadas se anulan (deja trazabilidad).')
        return redirect('contabilidad:compra_detalle', pk=pk)
    codigo = compra.codigo
    compra.delete()   # cascade elimina sus detalles (no afectó inventario por ser borrador)
    messages.success(request, f'Compra {codigo} (borrador) eliminada.')
    return redirect('contabilidad:compra_lista')
