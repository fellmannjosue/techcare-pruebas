from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from datetime import date
import urllib.request
import json as _json
from .models import TasaCambio, MONEDA_CHOICES

API_URL = 'https://open.exchangerate-api.com/v6/latest/USD'

# <--- hecho por claude code: Calculadoras es SOLO para el superusuario (nadie más).
solo_super = user_passes_test(lambda u: u.is_superuser, login_url='menu')


@solo_super
def dashboard(request):
    tasas = {t.moneda: t for t in TasaCambio.objects.all()}
    return render(request, 'calculadoras/dashboard.html', {'tasas': tasas})


@solo_super
def divisas(request):
    tasas = {t.moneda: t for t in TasaCambio.objects.all()}
    return render(request, 'calculadoras/divisas.html', {
        'tasas': tasas,
        'monedas': MONEDA_CHOICES,
    })


@solo_super
def tiempo(request):
    return render(request, 'calculadoras/tiempo.html', {})


# <--- hecho por claude code: una sola vista para las 4 calculadoras de tiempo como paginas individuales.
TIEMPO_META = {
    'entre_horas': {'titulo': 'Entre dos horas', 'icono': 'ti-clock-bolt'},
    'horas_dias': {'titulo': 'Horas → Días', 'icono': 'ti-clock-hour-4'},
    'minutos_horas': {'titulo': 'Minutos → Horas', 'icono': 'ti-hourglass'},
    'fecha_fecha': {'titulo': 'Fecha a Fecha', 'icono': 'ti-calendar-stats'},
}


@solo_super
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


@solo_super
def fetch_tasas_auto(request):
    """Obtiene tasas USD/EUR/CHF → HNL desde open.exchangerate-api.com y las guarda."""
    try:
        with urllib.request.urlopen(API_URL, timeout=8) as resp:
            data = _json.load(resp)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'No se pudo conectar a la API: {e}'})

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
