# <--- hecho por claude code (06-nov-2026): TC-PRY-0005 Convocatoria a reforzamiento (Bilingüe, como Tutorías). Alumnos y clases REALES del sistema académico (solo lectura); lo convocado se guarda en MySQL.
import json
import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (ReforzamientoConfig, ReforzamientoMarca, ReforzamientoDocenteGrado,
                     PeriodoEscolarConducta, GRADO_TUTORIA_LABEL)

AREA = 'bilingue'
MAX_ASIGNATURAS = 8
DIRECCION = 'Angela Cruz'            # V° B° Dirección: persona fija (decisión del usuario)
COORD_C1 = 'cvarela@ana-hn.org'      # 1.1 a 3.2
COORD_C2 = 'druiz@ana-hn.org'        # 4.1 a 9
_ORD = {1: '1ero', 2: '2do', 3: '3ero', 4: '4to', 5: '5to', 6: '6to', 7: '7mo', 8: '8vo', 9: '9no'}
_MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
        'octubre', 'noviembre', 'diciembre']
_DIA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']


def _puede(user):
    from .views import puede_ver_reforzamiento
    return puede_ver_reforzamiento(user)


def _gate(request):
    return None if _puede(request.user) else HttpResponseForbidden('Sin permiso.')


def _periodo(request, data=None):
    from .views import _periodo_activo
    src = data if data is not None else request.GET
    act = _periodo_activo(AREA)
    try:
        parcial = int(src.get('parcial') or (act.parcial if act else 1))
        anio = int(src.get('anio') or (act.anio if act else timezone.now().year))
    except (TypeError, ValueError):
        parcial, anio = (act.parcial if act else 1), (act.anio if act else timezone.now().year)
    if parcial not in (1, 2, 3, 4) or not (2020 <= anio <= 2100):
        parcial, anio = 1, timezone.now().year
    return parcial, anio


def _alumnos():
    """Alumnos BL reales (SQL Server). [] si el sistema académico no responde."""
    from .views import obtener_alumnos_bilingue, _parse_grado_num
    try:
        out = []
        for a in obtener_alumnos_bilingue():
            g, s = _parse_grado_num(a['grado'])
            if g:
                out.append({'id': str(a['id']), 'nombre': a['label'], 'g': g, 's': s})
        return out
    except Exception:
        return []


def _grados(alumnos):
    agg = {}
    for a in alumnos:
        agg[(a['g'], a['s'])] = agg.get((a['g'], a['s']), 0) + 1
    return [{'g': g, 's': s, 'label': f"{GRADO_TUTORIA_LABEL.get(g, g)} {g}.{s}", 'n': n}
            for (g, s), n in sorted(agg.items())]


def _clases(g, s, anio):
    """Clases REALES del grado-sección (tblEdcMaterias, solo lectura), con caché de 1 h."""
    key = f'reforz:clases:{anio}:{g}:{s}'
    val = cache.get(key)
    if val is None:
        try:
            from ingresos_notas.views import _clases as _cls
            area = 'primaria_bl' if g <= 6 else 'colegio_bl'
            val = sorted({(c.get('nombre') or c.get('label') or '').strip() for c in _cls(area, anio, _ORD[g], '_' + s)} - {''})
            if val:                      # nunca se cachea una lista vacía (un fallo del académico no deja el grado sin clases 1 h)
                cache.set(key, val, 3600)
        except Exception:
            val = []
    return val


def _coord(g):
    u = User.objects.filter(username=COORD_C1 if g <= 3 else COORD_C2).first()
    return {'k': 'C1' if g <= 3 else 'C2', 'nombre': (u.get_full_name() or u.username) if u else ''}


def _maestros():
    return [u.get_full_name() or u.username for u in User.objects.filter(
        is_active=True, groups__name='maestros_bilingue').distinct().order_by('first_name', 'last_name')]


def _fecha_larga(d):
    return f"{d.day:02d} de {_MES[d.month - 1]} de {d.year}" if d else ''


def _dia_fecha(d):
    return f"{_DIA[d.weekday()]} {d.day:02d} de {_MES[d.month - 1]}" if d else ''


def _desde(cfg):
    d = cfg.refuerzo_desde if cfg else None
    if not d:
        return ''
    h = cfg.refuerzo_hasta
    txt = _dia_fecha(d)
    return txt.rsplit(' de ', 1)[0] if (h and h.month == d.month) else txt


@login_required
def reforzamiento(request):
    """Pantalla única: tabla por grado (marcar), panel de convocados y fechas del parcial."""
    no = _gate(request)
    if no:
        return no
    parcial, anio = _periodo(request)
    alumnos = _alumnos()
    grados = _grados(alumnos)
    try:
        sel_g = int(request.GET.get('g') or 0)
    except ValueError:
        sel_g = 0
    sel_s = (request.GET.get('s') or '').strip()
    marcas = ReforzamientoMarca.objects.filter(area=AREA, parcial=parcial, anio=anio)

    tabla = None
    if sel_g and any(x['g'] == sel_g and x['s'] == sel_s for x in grados):
        clases = _clases(sel_g, sel_s, anio)
        del_grado = {(m.alumno_id, m.asignatura): m for m in marcas.filter(grado_num=sel_g, seccion=sel_s)}
        extra = sorted({a for (_, a) in del_grado} - set(clases))     # asignaturas ya marcadas que hoy no vienen del académico
        cols = clases + extra
        filas = []
        for a in [x for x in alumnos if x['g'] == sel_g and x['s'] == sel_s]:
            cels = []
            for c in cols:
                m = del_grado.get((a['id'], c))
                cels.append({'asig': c, 'on': bool(m), 'nota': '' if (not m or m.nota is None) else m.nota})
            filas.append({'id': a['id'], 'nombre': a['nombre'], 'cels': cels, 'n': sum(1 for x in cels if x['on'])})
        tabla = {'g': sel_g, 's': sel_s, 'label': f"{GRADO_TUTORIA_LABEL.get(sel_g, sel_g)} {sel_g}.{sel_s}",
                 'cols': cols, 'filas': filas, 'sin_clases': not clases}

    # panel: un renglón por alumno convocado
    docentes = {(d.grado_num, d.seccion): d.docente for d in
                ReforzamientoDocenteGrado.objects.filter(area=AREA, parcial=parcial, anio=anio)}
    conv = {}
    for m in marcas.order_by('grado_num', 'seccion', 'alumno_nombre'):
        r = conv.setdefault(m.alumno_id, {'id': m.alumno_id, 'nombre': m.alumno_nombre, 'g': m.grado_num,
                                          's': m.seccion, 'n': 0, 'por': set()})
        r['n'] += 1
        if m.marcado_por_id:
            r['por'].add(m.marcado_por.get_full_name() or m.marcado_por.username)
    panel = []
    for r in conv.values():
        c = _coord(r['g'])
        panel.append({**r, 'por': ', '.join(sorted(r['por'])), 'grado': f"{r['g']}.{r['s']}",
                      'docente': docentes.get((r['g'], r['s']), ''), 'coord_k': c['k'], 'coord': c['nombre']})
    panel.sort(key=lambda x: (x['g'], x['s'], x['nombre']))

    cfg = ReforzamientoConfig.objects.filter(area=AREA, parcial=parcial, anio=anio).first()
    periodos = list(PeriodoEscolarConducta.objects.filter(area__in=['bilingue', 'ambas']).order_by('-anio', '-parcial'))
    return render(request, 'conducta/reforzamiento.html', {
        'parcial': parcial, 'anio': anio, 'periodos': periodos, 'grados': grados,
        'sel_g': sel_g, 'sel_s': sel_s, 'tabla': tabla, 'panel': panel, 'cfg': cfg,
        'maestros': _maestros(), 'max_asig': MAX_ASIGNATURAS, 'sin_academico': not alumnos,
        'tab': request.GET.get('tab') or ('grado' if sel_g else 'panel'),
    })


def _json(request):
    try:
        d = json.loads(request.body or b'{}')
        return d if isinstance(d, dict) else None
    except (ValueError, TypeError):
        return None


@login_required
@require_POST
def reforzamiento_marcar(request):
    """Marca/desmarca una asignatura o guarda la nota (opcional). Valida alumno y grado contra el académico."""
    no = _gate(request)
    if no:
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    d = _json(request)
    if d is None:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)
    parcial, anio = _periodo(request, d)
    try:
        g = int(d.get('g'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Grado inválido.'}, status=400)
    s = str(d.get('s') or '').strip()
    alumno_id = str(d.get('alumno_id') or '').strip()
    asig = str(d.get('asignatura') or '').strip()[:80]
    accion = d.get('accion')
    alumno = next((a for a in _alumnos() if a['id'] == alumno_id and a['g'] == g and a['s'] == s), None)
    if not alumno:
        return JsonResponse({'ok': False, 'error': 'El alumno no pertenece a ese grado.'}, status=400)
    if not asig:
        return JsonResponse({'ok': False, 'error': 'Falta la asignatura.'}, status=400)
    base = dict(area=AREA, parcial=parcial, anio=anio, alumno_id=alumno_id)
    with transaction.atomic():
        qs = ReforzamientoMarca.objects.select_for_update().filter(**base)
        actual = qs.filter(asignatura=asig).first()
        if accion == 'off':
            if actual:
                actual.delete()
        elif accion in ('on', 'nota'):
            nota = None
            if accion == 'nota':
                crudo = str(d.get('nota') if d.get('nota') is not None else '').strip()
                if crudo != '':
                    if not crudo.isdecimal() or not (0 <= int(crudo) <= 100):
                        return JsonResponse({'ok': False, 'error': 'La nota va de 0 a 100.'}, status=400)
                    nota = int(crudo)
            if not actual:
                if asig not in _clases(g, s, anio) and _clases(g, s, anio):
                    return JsonResponse({'ok': False, 'error': 'Esa clase no es del grado.'}, status=400)
                if qs.count() >= MAX_ASIGNATURAS:
                    return JsonResponse({'ok': False, 'error': f'Máximo {MAX_ASIGNATURAS} asignaturas por alumno.'}, status=409)
                actual = ReforzamientoMarca(**base, grado_num=g, seccion=s, alumno_nombre=alumno['nombre'][:200],
                                            asignatura=asig, marcado_por=request.user)
            if accion == 'nota':
                actual.nota = nota
            actual.grado_num, actual.seccion = g, s
            actual.save()
        else:
            return JsonResponse({'ok': False, 'error': 'Acción inválida.'}, status=400)
        total = qs.count()
    return JsonResponse({'ok': True, 'total': total})


@login_required
@require_POST
def reforzamiento_docente(request):
    """Docente de grado de un grado-sección (sale en la firma de sus cartas)."""
    no = _gate(request)
    if no:
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    d = _json(request)
    if d is None:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)
    parcial, anio = _periodo(request, d)
    try:
        g = int(d.get('g'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Grado inválido.'}, status=400)
    s = str(d.get('s') or '').strip()
    docente = str(d.get('docente') or '').strip()
    if docente and docente not in _maestros():
        return JsonResponse({'ok': False, 'error': 'Docente no válido.'}, status=400)
    ReforzamientoDocenteGrado.objects.update_or_create(
        area=AREA, parcial=parcial, anio=anio, grado_num=g, seccion=s, defaults={'docente': docente})
    return JsonResponse({'ok': True})


@login_required
@require_POST
def reforzamiento_config(request):
    """Fechas del parcial (salen en todas las cartas)."""
    no = _gate(request)
    if no:
        return no
    parcial, anio = _periodo(request, request.POST)
    vals = {}
    for campo in ('fecha_carta', 'fecha_examenes', 'refuerzo_desde', 'refuerzo_hasta'):
        crudo = (request.POST.get(campo) or '').strip()
        try:
            vals[campo] = datetime.date.fromisoformat(crudo) if crudo else None
        except ValueError:
            vals[campo] = None
    ReforzamientoConfig.objects.update_or_create(area=AREA, parcial=parcial, anio=anio, defaults=vals)
    return redirect(f"{request.path.rsplit('fechas/', 1)[0]}?parcial={parcial}&anio={anio}&tab=config&ok=1")


@login_required
def reforzamiento_pdf(request):
    """Carta(s) con el formato aprobado: ?alumno=<id> (una) o ?g=&s= (todas las del grado)."""
    no = _gate(request)
    if no:
        return no
    parcial, anio = _periodo(request)
    qs = ReforzamientoMarca.objects.filter(area=AREA, parcial=parcial, anio=anio)
    alumno = (request.GET.get('alumno') or '').strip()
    if alumno:
        qs = qs.filter(alumno_id=alumno)
    else:
        try:
            qs = qs.filter(grado_num=int(request.GET.get('g')), seccion=(request.GET.get('s') or '').strip())
        except (TypeError, ValueError):
            qs = qs.none()
    cartas = {}
    for m in qs.order_by('alumno_nombre', 'pk'):
        cartas.setdefault(m.alumno_id, {'nombre': m.alumno_nombre, 'g': m.grado_num, 's': m.seccion, 'filas': []})['filas'].append(m)
    if not cartas:
        return HttpResponse('No hay convocados para generar cartas.', status=404)
    cfg = ReforzamientoConfig.objects.filter(area=AREA, parcial=parcial, anio=anio).first()
    docentes = {(d.grado_num, d.seccion): d.docente for d in
                ReforzamientoDocenteGrado.objects.filter(area=AREA, parcial=parcial, anio=anio)}
    lista = []
    for c in cartas.values():
        filas = c['filas'][:MAX_ASIGNATURAS]
        con_nota = any(f.nota is not None for f in filas)
        lista.append({
            'alumno': f"{c['nombre']} · {GRADO_TUTORIA_LABEL.get(c['g'], c['g'])} {c['g']}.{c['s']}",
            'filas': [{'n': i + 1, 'asig': f.asignatura, 'nota': '' if f.nota is None else f.nota} for i, f in enumerate(filas)]
                     + [{'n': i + 1, 'asig': '', 'nota': ''} for i in range(len(filas), MAX_ASIGNATURAS)],
            'con_nota': con_nota, 'docente': docentes.get((c['g'], c['s']), ''), 'coord': _coord(c['g'])['nombre'],
        })
    html = render_to_string('conducta/reforzamiento_carta_pdf.html', {
        'cartas': lista, 'direccion': DIRECCION,
        'parcial_rom': {1: 'I', 2: 'II', 3: 'III', 4: 'IV'}.get(parcial, parcial),
        'fecha_carta': _fecha_larga(cfg.fecha_carta if cfg else None),
        'fecha_examenes': _dia_fecha(cfg.fecha_examenes if cfg else None),
        'desde': _desde(cfg),
        'hasta': _dia_fecha(cfg.refuerzo_hasta if cfg else None),
    })
    from weasyprint import HTML, CSS
    css = finders.find('conducta/css/reforzamiento_carta.css')
    pdf = HTML(string=html).write_pdf(stylesheets=[CSS(filename=css)] if css else None)
    nombre = 'convocatoria_reforzamiento.pdf'
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{nombre}"'
    resp['Cache-Control'] = 'private, no-store'
    return resp
