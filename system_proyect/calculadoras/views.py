from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from datetime import date
import urllib.request
import json as _json
from .models import TasaCambio, MONEDA_CHOICES

API_URL = 'https://open.exchangerate-api.com/v6/latest/USD'


@login_required
def dashboard(request):
    tasas = {t.moneda: t for t in TasaCambio.objects.all()}
    return render(request, 'calculadoras/dashboard.html', {'tasas': tasas})


@login_required
def divisas(request):
    tasas = {t.moneda: t for t in TasaCambio.objects.all()}
    return render(request, 'calculadoras/divisas.html', {
        'tasas': tasas,
        'monedas': MONEDA_CHOICES,
    })


@login_required
def tiempo(request):
    return render(request, 'calculadoras/tiempo.html', {})


@login_required
def almacenamiento(request):
    return render(request, 'calculadoras/almacenamiento.html', {})


@login_required
def ip_calculator(request):
    return render(request, 'calculadoras/ip.html', {})


@require_POST
@login_required
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


@login_required
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
