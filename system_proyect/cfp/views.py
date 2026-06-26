from datetime import date
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.conf import settings

from .models import (
    EjecucionCurso, InformeContable,
    TALLER_CHOICES, TALLER_LABEL, EGRESO_GRUPOS,
)


def cfp_required(view):
    @wraps(view)
    def _w(request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        if not (u.is_superuser or u.groups.filter(name='director_cfp').exists()):
            return HttpResponseForbidden('No tienes permiso para el módulo CFP.')
        return view(request, *args, **kwargs)
    return _w


def _anio(request):
    try:
        return int(request.GET.get('anio') or request.POST.get('anio') or date.today().year)
    except (TypeError, ValueError):
        return date.today().year


def _anios_disponibles(anio_actual):
    ys = set(EjecucionCurso.objects.values_list('anio', flat=True))
    ys.add(anio_actual)
    ys.add(date.today().year)
    return sorted(ys, reverse=True)


# ─── DASHBOARD: tarjetas por taller ───────────────────────────────────────────
@cfp_required
def dashboard(request):
    anio = _anio(request)
    qs = list(EjecucionCurso.objects.filter(anio=anio))
    talleres = []
    for key, label in TALLER_CHOICES:
        ejs = [e for e in qs if e.taller == key]
        talleres.append({
            'key': key, 'label': label, 'n': len(ejs),
            'monto': round(sum(e.monto_cfp for e in ejs), 2),
        })
    return render(request, 'cfp/dashboard.html', {
        'anio': anio, 'anios': _anios_disponibles(anio),
        'talleres': talleres,
        'total': round(sum(e.monto_cfp for e in qs), 2),
    })


# ─── SUBDASHBOARD por taller (3 tabs) ─────────────────────────────────────────
@cfp_required
def taller(request, taller):
    if taller not in TALLER_LABEL:
        return redirect('cfp:dashboard')
    anio = _anio(request)
    ejecuciones = list(EjecucionCurso.objects.filter(anio=anio, taller=taller)
                       .select_related('informe'))

    tot = {
        'horas': sum(e.horas for e in ejecuciones),
        'part': sum(e.part_pago for e in ejecuciones),
        'contrato': round(sum(e.monto_contrato for e in ejecuciones), 2),
        'perdida': round(sum(e.perdida for e in ejecuciones), 2),
        'anticipo': round(sum(e.anticipo for e in ejecuciones), 2),
        'cancelacion': round(sum(e.cancelacion for e in ejecuciones), 2),
        'costo_real': round(sum(e.costo_real for e in ejecuciones), 2),
        'cfp': round(sum(e.monto_cfp for e in ejecuciones), 2),
    }

    # Tab 2: distribución agrupada por nombre de curso
    grupos = {}
    for e in ejecuciones:
        g = grupos.setdefault(e.nombre_curso, {'curso': e.nombre_curso, 'monto': 0.0})
        g['monto'] += e.monto_cfp
    dist = []
    for g in grupos.values():
        m = round(g['monto'], 2)
        dist.append({'curso': g['curso'], 'monto': m,
                     'seguro': round(m * 0.6, 2), 'instr': round(m * 0.2, 2), 'admin': round(m * 0.2, 2)})
    dist.sort(key=lambda x: x['curso'])
    dist_tot = {
        'monto': round(sum(d['monto'] for d in dist), 2),
        'seguro': round(sum(d['seguro'] for d in dist), 2),
        'instr': round(sum(d['instr'] for d in dist), 2),
        'admin': round(sum(d['admin'] for d in dist), 2),
    }

    return render(request, 'cfp/taller.html', {
        'taller_key': taller, 'taller_label': TALLER_LABEL[taller],
        'anio': anio, 'anios': _anios_disponibles(anio),
        'ejecuciones': ejecuciones, 'tot': tot,
        'dist': dist, 'dist_tot': dist_tot,
        'es_mecanica': taller == 'mecanica',
    })


def _to_int(v, d=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


def _to_dec(v, d=0):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return d


@cfp_required
def ejecucion_guardar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    pk = request.POST.get('pk')
    taller = request.POST.get('taller')
    if taller not in TALLER_LABEL:
        return JsonResponse({'ok': False, 'error': 'Taller inválido'}, status=400)
    obj = get_object_or_404(EjecucionCurso, pk=pk) if pk else EjecucionCurso()
    obj.anio         = _to_int(request.POST.get('anio'), date.today().year)
    obj.taller       = taller
    obj.taller_anio  = _to_int(request.POST.get('taller_anio')) or None
    obj.no_ejecucion = (request.POST.get('no_ejecucion') or '').strip()
    obj.no_curso     = (request.POST.get('no_curso') or '').strip()
    obj.no_contrato  = (request.POST.get('no_contrato') or '').strip()
    obj.nombre_curso = (request.POST.get('nombre_curso') or '').strip()
    obj.horas        = _to_int(request.POST.get('horas'))
    obj.part_inicial = _to_int(request.POST.get('part_inicial'))
    obj.part_pago    = _to_int(request.POST.get('part_pago'))
    obj.costo_hora   = _to_dec(request.POST.get('costo_hora'))
    obj.horario      = (request.POST.get('horario') or '').strip()
    if not obj.nombre_curso:
        return JsonResponse({'ok': False, 'error': 'El nombre del curso es obligatorio'}, status=400)
    obj.save()
    return JsonResponse({'ok': True})


@cfp_required
def ejecucion_detalle(request, pk):
    e = get_object_or_404(EjecucionCurso, pk=pk)
    return JsonResponse({
        'pk': e.id, 'anio': e.anio, 'taller': e.taller, 'taller_anio': e.taller_anio or '',
        'no_ejecucion': e.no_ejecucion, 'no_curso': e.no_curso, 'no_contrato': e.no_contrato,
        'nombre_curso': e.nombre_curso, 'horas': e.horas,
        'part_inicial': e.part_inicial, 'part_pago': e.part_pago, 'costo_hora': float(e.costo_hora),
        'horario': e.horario,
    })


@cfp_required
def ejecucion_eliminar(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    get_object_or_404(EjecucionCurso, pk=pk).delete()
    return JsonResponse({'ok': True})


# ─── Tab 3: Informe contable (form + PDF) ─────────────────────────────────────
def _datos_generales():
    """Registro único (compartido por todos los cursos) de datos generales."""
    from .models import CfpDatosGenerales
    dg, _ = CfpDatosGenerales.objects.get_or_create(id=1)
    return dg


def _informe_ctx(ej, inf):
    # Sugerir la división del 20% (Instructores y Director) en los 3 gastos de
    # personal: cada campo vacío muestra su tercio (para que se vea y cuadre).
    instr20 = ej.dist_instr
    if instr20:
        tercio = round(instr20 / 3, 2)
        defaults = {
            'personal_instructor': tercio,
            'personal_encargado':  tercio,
            'personal_apoyo':      round(instr20 - 2 * tercio, 2),
        }
        eg = dict(inf.egresos or {})
        for k, v in defaults.items():
            if not eg.get(k):           # vacío / ausente → sugerir división
                eg[k] = v
        inf.egresos = eg  # solo en memoria (no se guarda salvo POST)

    grupos = []
    for g, lbl, items in EGRESO_GRUPOS:
        filas = [{'key': f'{g}_{k}', 'label': il, 'valor': inf.egresos.get(f'{g}_{k}', '')} for k, il in items]
        grupos.append({'key': g, 'label': lbl, 'filas': filas, 'subtotal': inf.grupo_subtotal(g),
                       'nota': '↳ 20% Instructores y Director dividido en 3' if g == 'personal' else ''})

    # Datos generales COMPARTIDOS: sobrescriben los del informe (en memoria, para mostrar/PDF)
    dg = _datos_generales()
    inf.localidad   = dg.localidad
    inf.direccion   = dg.direccion
    inf.instructor  = dg.instructor
    inf.horario     = dg.horario
    inf.lugar       = dg.lugar
    inf.fecha_lugar = dg.fecha_lugar

    # Opciones de los selects agregables (catálogo + valor guardado actual)
    from .models import CfpOpcion
    actuales = {'localidad': inf.localidad, 'direccion': inf.direccion,
                'instructor': inf.instructor, 'horario': inf.horario or ej.horario,
                'lugar': inf.lugar}
    opciones = {}
    for campo, cur in actuales.items():
        vals = set(CfpOpcion.objects.filter(campo=campo).values_list('valor', flat=True))
        if cur:
            vals.add(cur)
        opciones[campo] = sorted(vals)

    # "Lugar y fecha" combinado para el PDF
    _MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
              'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    lugar = inf.lugar or inf.lugar_fecha
    if inf.fecha_lugar:
        f = inf.fecha_lugar
        fstr = f"{f.day:02d} de {_MESES[f.month - 1]} del año {f.year}"
    else:
        fstr = ''
    lugar_fecha_str = '; '.join(p for p in (lugar, fstr) if p)

    return {'ej': ej, 'inf': inf, 'grupos': grupos, 'opciones': opciones,
            'lugar_fecha_str': lugar_fecha_str,
            'taller_label': TALLER_LABEL.get(ej.taller, ej.taller)}


@cfp_required
def informe_form(request, pk):
    ej = get_object_or_404(EjecucionCurso, pk=pk)
    inf, _ = InformeContable.objects.get_or_create(ejecucion=ej)
    if request.method == 'POST':
        from .models import CfpOpcion
        def _opcion(campo):
            """Resuelve un select agregable: si es '__nueva__' toma el texto y lo cataloga."""
            val = (request.POST.get(campo) or '').strip()
            if val == '__nueva__':
                val = (request.POST.get(campo + '_nueva') or '').strip()
            if val:
                CfpOpcion.objects.get_or_create(campo=campo, valor=val)
            return val
        # Datos generales COMPARTIDOS por todos los cursos (registro único)
        dg = _datos_generales()
        dg.localidad   = _opcion('localidad')
        dg.direccion   = _opcion('direccion')
        dg.instructor  = _opcion('instructor')
        dg.horario     = _opcion('horario')
        dg.lugar       = _opcion('lugar')
        dg.fecha_lugar = request.POST.get('fecha_lugar') or None
        dg.save()

        inf.fecha_inicio    = request.POST.get('fecha_inicio') or None
        inf.fecha_fin       = request.POST.get('fecha_fin') or None
        inf.convenio        = (request.POST.get('convenio') or '').strip()
        inf.regional        = (request.POST.get('regional') or '').strip()
        inf.centro_programa = (request.POST.get('centro_programa') or '').strip()
        inf.egresados       = _to_int(request.POST.get('egresados'))
        egresos = {}
        for g, _lbl, items in EGRESO_GRUPOS:
            for k, _il in items:
                val = _to_dec(request.POST.get(f'{g}_{k}'))
                if val:
                    egresos[f'{g}_{k}'] = val
        inf.egresos = egresos
        inf.save()
        messages.success(request, 'Informe guardado.')
        return redirect(request.path)
    return render(request, 'cfp/informe_form.html', _informe_ctx(ej, inf))


@cfp_required
def informe_pdf(request, pk):
    ej = get_object_or_404(EjecucionCurso, pk=pk)
    inf, _ = InformeContable.objects.get_or_create(ejecucion=ej)
    from weasyprint import HTML
    html = render(request, 'cfp/informe_pdf.html', _informe_ctx(ej, inf)).content.decode('utf-8')
    pdf = HTML(string=html).write_pdf()
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="informe_{ej.no_ejecucion or ej.id}.pdf"'
    return resp
