import json
from decimal import Decimal
from datetime import date
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.conf import settings

_FINANZAS_EMAIL = 'cvalle@ana-hn.org'


def finanzas_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        if not (request.user.is_superuser or request.user.email == _FINANZAS_EMAIL):
            if request.content_type == 'application/json' or request.headers.get('Accept') == 'application/json':
                return JsonResponse({'error': 'Acceso no autorizado.'}, status=403)
            return HttpResponseForbidden('No tienes permiso para acceder a este módulo.')
        return view_func(request, *args, **kwargs)
    return _wrapped

from .models import (
    Categoria, Transaccion, Pendiente, EntradaRapida,
    Presupuesto, PresupuestoCategoria, MetaAhorro, ConfiguracionUsuario,
)

SEED_CATEGORIAS = [
    {'name': 'Salario',         'type': 'income',  'color': '#2A7A4F'},
    {'name': 'Ventas',          'type': 'income',  'color': '#C9A84C'},
    {'name': 'Alimentación',    'type': 'expense', 'color': '#B84040'},
    {'name': 'Transporte',      'type': 'expense', 'color': '#3A6FA8'},
    {'name': 'Servicios',       'type': 'expense', 'color': '#7B5EA7'},
    {'name': 'Entretenimiento', 'type': 'expense', 'color': '#D4843C'},
]


def _body(request):
    try:
        return json.loads(request.body)
    except Exception:
        return {}


def _cat(user, cat_id):
    if not cat_id:
        return None
    return Categoria.objects.filter(pk=cat_id, user=user).first()


# ─── PÁGINA PRINCIPAL ──────────────────────────────────────────────────────────

@finanzas_required
def index(request):
    return render(request, 'finanzas_personales/index.html')


# ─── API: ESTADO COMPLETO ──────────────────────────────────────────────────────

@finanzas_required
@require_http_methods(['GET'])
def api_data(request):
    user = request.user
    if not Categoria.objects.filter(user=user).exists():
        for c in SEED_CATEGORIAS:
            Categoria.objects.create(user=user, nombre=c['name'], tipo=c['type'], color=c['color'])
    config, _ = ConfiguracionUsuario.objects.get_or_create(user=user)
    return JsonResponse({
        'categories':   [c.to_dict() for c in Categoria.objects.filter(user=user)],
        'transactions': [t.to_dict() for t in Transaccion.objects.filter(user=user)],
        'pendings':     [p.to_dict() for p in Pendiente.objects.filter(user=user)],
        'budgets':      [b.to_dict() for b in Presupuesto.objects.filter(user=user).prefetch_related('items')],
        'quickEntries': [e.to_dict() for e in EntradaRapida.objects.filter(user=user)],
        'goals':        [g.to_dict() for g in MetaAhorro.objects.filter(user=user)],
        'settings':     config.to_dict(),
    })


# ─── API: CATEGORÍAS ──────────────────────────────────────────────────────────

@finanzas_required
@require_http_methods(['POST'])
def api_categoria_crear(request):
    b = _body(request)
    cat = Categoria.objects.create(
        user=request.user,
        nombre=b.get('name', '').strip(),
        tipo=b.get('type', 'expense'),
        color=b.get('color', '#999999'),
    )
    return JsonResponse(cat.to_dict(), status=201)


@finanzas_required
@require_http_methods(['PUT', 'DELETE'])
def api_categoria_detalle(request, pk):
    cat = get_object_or_404(Categoria, pk=pk, user=request.user)
    if request.method == 'DELETE':
        cat.delete()
        return JsonResponse({'ok': True})
    b = _body(request)
    cat.nombre = b.get('name', cat.nombre).strip()
    cat.tipo   = b.get('type', cat.tipo)
    cat.color  = b.get('color', cat.color)
    cat.save()
    return JsonResponse(cat.to_dict())


# ─── API: TRANSACCIONES ───────────────────────────────────────────────────────

@finanzas_required
@require_http_methods(['POST'])
def api_transaccion_crear(request):
    b = _body(request)
    txn = Transaccion.objects.create(
        user=request.user,
        tipo=b.get('type', 'expense'),
        monto=b.get('amount', 0),
        descripcion=b.get('description', '').strip(),
        categoria=_cat(request.user, b.get('categoryId')),
        fecha=b.get('date', str(date.today())),
    )
    return JsonResponse(txn.to_dict(), status=201)


@finanzas_required
@require_http_methods(['PUT', 'DELETE'])
def api_transaccion_detalle(request, pk):
    txn = get_object_or_404(Transaccion, pk=pk, user=request.user)
    if request.method == 'DELETE':
        txn.delete()
        return JsonResponse({'ok': True})
    b = _body(request)
    txn.tipo        = b.get('type', txn.tipo)
    txn.monto       = b.get('amount', float(txn.monto))
    txn.descripcion = b.get('description', txn.descripcion).strip()
    txn.categoria   = _cat(request.user, b.get('categoryId'))
    txn.fecha       = b.get('date', str(txn.fecha))
    txn.save()
    return JsonResponse(txn.to_dict())


# ─── API: PENDIENTES ──────────────────────────────────────────────────────────

@finanzas_required
@require_http_methods(['POST'])
def api_pendiente_crear(request):
    b = _body(request)
    p = Pendiente.objects.create(
        user=request.user,
        tipo=b.get('type', 'income'),
        nombre=b.get('name', '').strip(),
        monto=b.get('amount', 0),
        fecha=b.get('date', str(date.today())),
    )
    return JsonResponse(p.to_dict(), status=201)


@finanzas_required
@require_http_methods(['DELETE'])
def api_pendiente_eliminar(request, pk):
    get_object_or_404(Pendiente, pk=pk, user=request.user).delete()
    return JsonResponse({'ok': True})


@finanzas_required
@require_http_methods(['POST'])
def api_pendiente_confirmar(request, pk):
    p = get_object_or_404(Pendiente, pk=pk, user=request.user)
    cat = Categoria.objects.filter(user=request.user, tipo=p.tipo).first()
    txn = Transaccion.objects.create(
        user=request.user, tipo=p.tipo, monto=p.monto,
        descripcion=p.nombre, categoria=cat, fecha=date.today(),
    )
    p.delete()
    return JsonResponse(txn.to_dict(), status=201)


# ─── API: ENTRADAS RÁPIDAS ────────────────────────────────────────────────────

@finanzas_required
@require_http_methods(['POST'])
def api_qe_crear(request):
    b = _body(request)
    qe = EntradaRapida.objects.create(
        user=request.user,
        nombre=b.get('name', '').strip(),
        monto=b.get('amount', 0),
        tipo=b.get('type', 'expense'),
        categoria=_cat(request.user, b.get('categoryId')),
    )
    return JsonResponse(qe.to_dict(), status=201)


@finanzas_required
@require_http_methods(['DELETE'])
def api_qe_eliminar(request, pk):
    get_object_or_404(EntradaRapida, pk=pk, user=request.user).delete()
    return JsonResponse({'ok': True})


@finanzas_required
@require_http_methods(['POST'])
def api_qe_ejecutar(request, pk):
    qe = get_object_or_404(EntradaRapida, pk=pk, user=request.user)
    txn = Transaccion.objects.create(
        user=request.user, tipo=qe.tipo, monto=qe.monto,
        descripcion=qe.nombre, categoria=qe.categoria, fecha=date.today(),
    )
    return JsonResponse(txn.to_dict(), status=201)


# ─── API: PRESUPUESTOS ────────────────────────────────────────────────────────

@finanzas_required
@require_http_methods(['POST'])
def api_presupuesto_crear(request):
    b = _body(request)
    pres = Presupuesto.objects.create(
        user=request.user,
        nombre=b.get('name', '').strip(),
        limite=b.get('limit', 0),
    )
    for item in b.get('items', []):
        cat = _cat(request.user, item.get('catId'))
        if cat:
            PresupuestoCategoria.objects.create(presupuesto=pres, categoria=cat)
    return JsonResponse(pres.to_dict(), status=201)


@finanzas_required
@require_http_methods(['DELETE'])
def api_presupuesto_eliminar(request, pk):
    get_object_or_404(Presupuesto, pk=pk, user=request.user).delete()
    return JsonResponse({'ok': True})


# ─── API: METAS DE AHORRO ────────────────────────────────────────────────────

@finanzas_required
@require_http_methods(['POST'])
def api_meta_crear(request):
    b = _body(request)
    meta = MetaAhorro.objects.create(
        user=request.user,
        nombre=b.get('name', '').strip(),
        objetivo=b.get('target', 0),
        fecha_limite=b.get('deadline') or None,
        emoji=b.get('emoji', '🎯'),
    )
    return JsonResponse(meta.to_dict(), status=201)


@finanzas_required
@require_http_methods(['PUT', 'DELETE'])
def api_meta_detalle(request, pk):
    meta = get_object_or_404(MetaAhorro, pk=pk, user=request.user)
    if request.method == 'DELETE':
        meta.delete()
        return JsonResponse({'ok': True})
    b = _body(request)
    meta.nombre       = b.get('name', meta.nombre).strip()
    meta.objetivo     = b.get('target', float(meta.objetivo))
    meta.fecha_limite = b.get('deadline') or None
    meta.emoji        = b.get('emoji', meta.emoji)
    meta.save()
    return JsonResponse(meta.to_dict())


@finanzas_required
@require_http_methods(['POST'])
def api_meta_ahorrar(request, pk):
    meta = get_object_or_404(MetaAhorro, pk=pk, user=request.user)
    b = _body(request)
    amount = float(b.get('amount', 0))
    if amount <= 0:
        return JsonResponse({'error': 'Monto inválido'}, status=400)
    meta.ahorrado = min(meta.ahorrado + Decimal(str(amount)), meta.objetivo)
    meta.save()
    cat = Categoria.objects.filter(user=request.user, tipo='income').first()
    txn = Transaccion.objects.create(
        user=request.user, tipo='income', monto=amount,
        descripcion=f'Ahorro: {meta.nombre}', categoria=cat, fecha=date.today(),
    )
    return JsonResponse({'meta': meta.to_dict(), 'txn': txn.to_dict()})


# ─── API: CONFIGURACIÓN ───────────────────────────────────────────────────────

@finanzas_required
@require_http_methods(['POST'])
def api_configuracion(request):
    b = _body(request)
    config, _ = ConfiguracionUsuario.objects.get_or_create(user=request.user)
    if 'currency' in b:
        config.moneda = b['currency']
    if 'theme' in b:
        config.tema = b['theme']
    config.save()
    return JsonResponse(config.to_dict())


# ─── API: IMPORTAR / LIMPIAR ──────────────────────────────────────────────────

@finanzas_required
@require_http_methods(['POST'])
def api_importar(request):
    b = _body(request)
    user = request.user
    Transaccion.objects.filter(user=user).delete()
    Categoria.objects.filter(user=user).delete()
    Pendiente.objects.filter(user=user).delete()
    EntradaRapida.objects.filter(user=user).delete()
    Presupuesto.objects.filter(user=user).delete()
    MetaAhorro.objects.filter(user=user).delete()

    cat_map = {}
    for c in b.get('categories', []):
        obj = Categoria.objects.create(user=user, nombre=c['name'], tipo=c['type'], color=c.get('color', '#999999'))
        cat_map[str(c['id'])] = obj

    for t in b.get('transactions', []):
        Transaccion.objects.create(
            user=user, tipo=t['type'], monto=t['amount'],
            descripcion=t.get('description', ''), fecha=t.get('date', str(date.today())),
            categoria=cat_map.get(str(t.get('categoryId', ''))),
        )

    for p in b.get('pendings', []):
        Pendiente.objects.create(
            user=user, tipo=p['type'], nombre=p['name'],
            monto=p['amount'], fecha=p.get('date', str(date.today())),
        )

    for qe in b.get('quickEntries', []):
        EntradaRapida.objects.create(
            user=user, nombre=qe['name'], monto=qe['amount'], tipo=qe['type'],
            categoria=cat_map.get(str(qe.get('categoryId', ''))),
        )

    for bud in b.get('budgets', []):
        pres = Presupuesto.objects.create(user=user, nombre=bud['name'], limite=bud['limit'])
        for item in bud.get('items', []):
            cat = cat_map.get(str(item.get('catId', '')))
            if cat:
                PresupuestoCategoria.objects.create(presupuesto=pres, categoria=cat)

    for g in b.get('goals', []):
        MetaAhorro.objects.create(
            user=user, nombre=g['name'], objetivo=g['target'],
            ahorrado=g.get('saved', 0), fecha_limite=g.get('deadline') or None,
            emoji=g.get('emoji', '🎯'),
        )

    if 'settings' in b:
        config, _ = ConfiguracionUsuario.objects.get_or_create(user=user)
        config.moneda = b['settings'].get('currency', config.moneda)
        config.tema   = b['settings'].get('theme', config.tema)
        config.save()

    return JsonResponse({'ok': True})


@finanzas_required
@require_http_methods(['POST'])
def api_limpiar(request):
    user = request.user
    Transaccion.objects.filter(user=user).delete()
    Categoria.objects.filter(user=user).delete()
    Pendiente.objects.filter(user=user).delete()
    EntradaRapida.objects.filter(user=user).delete()
    Presupuesto.objects.filter(user=user).delete()
    MetaAhorro.objects.filter(user=user).delete()
    for c in SEED_CATEGORIAS:
        Categoria.objects.create(user=user, nombre=c['name'], tipo=c['type'], color=c['color'])
    return JsonResponse({'ok': True})
