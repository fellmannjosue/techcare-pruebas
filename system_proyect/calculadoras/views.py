from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from datetime import date
from functools import wraps
import logging
import urllib.request
import json as _json
from .models import TasaCambio, MONEDA_CHOICES

API_URL = 'https://open.exchangerate-api.com/v6/latest/USD'

def _candado(prueba):
    """<--- hecho por claude code (seguridad 05-nov-2026): con sesión pero sin permiso → a su menú (como antes).
    Sin sesión lo para LoginRequiredMiddleware y va DIRECTO al login: el login_url='menu' de user_passes_test
    lo mandaba primero al menú (y de ahí al login, perdiendo el ?next)."""
    def deco(vista):
        @wraps(vista)
        def _envuelta(request, *args, **kwargs):
            if not prueba(request.user):
                return redirect('menu')
            return vista(request, *args, **kwargs)
        return _envuelta
    return deco


# <--- hecho por claude code: Calculadoras es SOLO para el superusuario (nadie más)…
solo_super = _candado(lambda u: u.is_authenticated and u.is_superuser)
# …salvo las 5 calculadoras de TIEMPO (sumar horas, entre dos horas, horas→días, fecha a fecha, minutos→horas),
# que también las usa el grupo `calculadoras_tiempo` (30-sep-2026, pedido para yzavala). Divisas, MB→GB, IPs y
# Lorem siguen siendo solo del superusuario.
GRUPO_TIEMPO = 'calculadoras_tiempo'


def puede_tiempo(u):
    return u.is_authenticated and (u.is_superuser or u.groups.filter(name=GRUPO_TIEMPO).exists())


tiempo_o_super = _candado(puede_tiempo)


@tiempo_o_super
def dashboard(request):
    tasas = {t.moneda: t for t in TasaCambio.objects.all()}
    return render(request, 'calculadoras/dashboard.html', {'tasas': tasas, 'es_super': request.user.is_superuser})


@solo_super
def divisas(request):
    tasas = {t.moneda: t for t in TasaCambio.objects.all()}
    return render(request, 'calculadoras/divisas.html', {
        'tasas': tasas,
        'monedas': MONEDA_CHOICES,
    })


@tiempo_o_super
def tiempo(request):
    return render(request, 'calculadoras/tiempo.html', {})


# <--- hecho por claude code: una sola vista para las 4 calculadoras de tiempo como paginas individuales.
TIEMPO_META = {
    'sumar_horas': {'titulo': 'Sumar horas y minutos', 'icono': 'ti-sum'},
    'entre_horas': {'titulo': 'Entre dos horas', 'icono': 'ti-clock-bolt'},
    'horas_dias': {'titulo': 'Horas → Días', 'icono': 'ti-clock-hour-4'},
    'minutos_horas': {'titulo': 'Minutos → Horas', 'icono': 'ti-hourglass'},
    'fecha_fecha': {'titulo': 'Fecha a Fecha', 'icono': 'ti-calendar-stats'},
}


@tiempo_o_super
def tiempo_calc(request, calc):
    meta = TIEMPO_META.get(calc)
    if meta is None:
        return redirect('calculadoras_dashboard')
    return render(request, 'calculadoras/tiempo_calc.html', {
        'calc': calc,
        'titulo': meta['titulo'],
        'icono': meta['icono'],
    })


@solo_super
def almacenamiento(request):
    return render(request, 'calculadoras/almacenamiento.html', {})


@solo_super
def ip_calculator(request):
    return render(request, 'calculadoras/ip.html', {})


@solo_super
def lorem_ipsum(request):
    return render(request, 'calculadoras/lorem.html', {})


@require_POST
@solo_super
def actualizar_tasa(request):
    moneda = request.POST.get('moneda', '').strip().upper()
    tasa_str = request.POST.get('tasa', '').strip().replace(',', '.')
    fecha_str = request.POST.get('fecha', str(date.today()))

    monedas_validas = {m[0] for m in MONEDA_CHOICES}
    if moneda not in monedas_validas:
        return JsonResponse({'ok': False, 'error': 'Moneda inválida'})
    try:
        tasa = float(tasa_str)
        if tasa <= 0:
            raise ValueError
        fecha = date.fromisoformat(fecha_str)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'})

    obj, _ = TasaCambio.objects.update_or_create(
        moneda=moneda,
        defaults={'tasa': tasa, 'fecha_actualizacion': fecha, 'actualizado_por': request.user}
    )
    return JsonResponse({'ok': True, 'tasa': str(obj.tasa), 'fecha': str(obj.fecha_actualizacion)})


@require_POST   # <--- hecho por claude code (seguridad 05-nov-2026): GUARDA en la BD → solo POST (con CSRF); antes bastaba un GET
@solo_super
def fetch_tasas_auto(request):
    """Obtiene tasas USD/EUR/CHF → HNL desde open.exchangerate-api.com y las guarda."""
    try:
        with urllib.request.urlopen(API_URL, timeout=8) as resp:
            data = _json.load(resp)
        if not isinstance(data, dict):
            raise ValueError('respuesta inesperada')
    except Exception:
        # <--- hecho por claude code (seguridad 05-nov-2026): el detalle va al log, no al navegador (antes se devolvía la excepción cruda)
        logging.getLogger(__name__).exception('calculadoras: no se pudo consultar %s', API_URL)
        return JsonResponse({'ok': False, 'error': 'No se pudo conectar al servicio de tasas. Intenta más tarde o ingrésalas a mano.'})

    rates = data.get('rates', {})
    hnl = rates.get('HNL')
    eur = rates.get('EUR')
    chf = rates.get('CHF')

    if not hnl:
        return JsonResponse({'ok': False, 'error': 'La API no devolvió tasa para HNL'})

    hoy = date.today()
    resultados = {}

    conversiones = {
        'USD': round(hnl, 4),
        'EUR': round(hnl / eur, 4) if eur else None,
        'CHF': round(hnl / chf, 4) if chf else None,
    }

    for moneda, tasa in conversiones.items():
        if tasa:
            TasaCambio.objects.update_or_create(
                moneda=moneda,
                defaults={'tasa': tasa, 'fecha_actualizacion': hoy,
                          'actualizado_por': request.user}
            )
            resultados[moneda] = {'tasa': str(tasa), 'fecha': str(hoy)}

    return JsonResponse({'ok': True, 'tasas': resultados, 'fuente': 'open.exchangerate-api.com'})
