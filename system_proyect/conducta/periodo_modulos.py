"""<--- hecho por claude code (06-nov-2026, pedido del usuario): qué módulos quedan ABIERTOS en cada Período Escolar.

Cada período general (conducta.PeriodoEscolarConducta) guarda en `modulos` un interruptor por módulo.
Apagado = CERRADO en ese período: no se puede llenar (lo ya registrado se sigue viendo).
Sin período activo en el área = no se cambia nada (cada módulo sigue como antes).
El superusuario nunca queda bloqueado. CFP no tiene período por ahora.
"""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect

# clave, etiqueta, áreas donde aplica
MODULOS = [
    ('inf', 'Reportes informativos',   ('bilingue', 'colegio')),
    ('con', 'Reportes conductuales',   ('bilingue', 'colegio')),
    ('age', 'Agendas',                 ('bilingue', 'colegio')),
    ('not', 'Notas mitad de parcial',  ('bilingue', 'colegio')),
    ('sal', 'Salidas al Baño',         ('colegio',)),
    ('pro', 'Progress Report',         ('bilingue',)),
    ('tut', 'Convocatoria / Tutorías', ('bilingue',)),
]
ETIQUETA = {k: t for k, t, _a in MODULOS}
CORTO = {'inf': 'Inf', 'con': 'Con', 'age': 'Age', 'not': 'Not', 'sal': 'Sal', 'pro': 'PR', 'tut': 'Tut'}


def modulos_de_area(area):
    """Módulos que le corresponden a un período de esa área ('ambas' = Bilingüe + Colegio)."""
    if area == 'ambas':
        return [m for m in MODULOS]
    return [m for m in MODULOS if area in m[2]]


def periodo_activo(area):
    from .models import PeriodoEscolarConducta
    return (PeriodoEscolarConducta.objects.filter(activo=True, area__in=[area, 'ambas'])
            .order_by('-anio', '-parcial').first())


def periodo_que_cierra(modulo, area, user=None):
    """Devuelve el período activo que tiene CERRADO ese módulo en esa área, o None si está abierto."""
    if user is not None and user.is_superuser:
        return None
    p = periodo_activo(area)
    if p and not p.modulo_abierto(modulo):
        return p
    return None


def mensaje_cerrado(modulo, periodo):
    return ('%s está cerrado en el %s. Lo abre el administrador en Configuración Académica → Período Escolar.'
            % (ETIQUETA.get(modulo, modulo), periodo.nombre))


def respuesta_si_cerrado(request, modulo, area, json=False, volver='menu'):
    """Para las vistas: None si está abierto; si está cerrado, la respuesta lista (JSON 409 o aviso + redirección)."""
    p = periodo_que_cierra(modulo, area, request.user)
    if not p:
        return None
    msg = mensaje_cerrado(modulo, p)
    if json or request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        return JsonResponse({'ok': False, 'error': msg, 'cerrado': True}, status=409)
    messages.error(request, msg)
    return redirect(volver)
