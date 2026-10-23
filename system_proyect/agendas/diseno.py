# <--- hecho por claude code (15-oct-2026): Agendas · pestaña "Crear agenda" y EDITOR DE DISEÑO del coordinador.
# Flujo: el coordinador crea la agenda (grado + semana) → los maestros llenan sus clases → el coordinador abre el
# editor (réplica del PowerPoint BL / Word de Colegio), ajusta letra, filas, columnas y textos, y descarga el PNG,
# que además queda guardado como IMAGEN FINAL (la que se publica en Moodle).
import io
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Agenda, GradoAgenda

DIAS = ('lunes', 'martes', 'miercoles', 'jueves', 'viernes')
MAX_PNG_MB = 15

# Valores de partida = los del generador de PowerPoint (BL) y de Word (Colegio). Anchos BL en pulgadas, Colegio en cm.
DISENO_BASE = {
    'bl': {'letra_celda': 9, 'letra_encabezado': 16, 'letra_clase': 16, 'letra_nota': 9,
           'alto_fila': 1.8, 'auto_alto': True, 'ocultar_vacias': False,
           'anchos': [1.3, 1.55, 1.55, 1.55, 1.55, 1.55, 1.75], 'celdas': {}},
    'col': {'letra_celda': 9, 'letra_encabezado': 10, 'letra_clase': 9, 'letra_nota': 9,
            'alto_fila': 1.2, 'auto_alto': True, 'ocultar_vacias': False,
            'anchos': [4.2, 4.5, 4.5, 4.5, 4.5, 4.5], 'celdas': {}},
}


def tipo_diseno(agenda):
    return 'col' if agenda.grado.area == 'colegio' else 'bl'


def _num(v, lo, hi, defecto):
    try:
        n = float(v)
    except (TypeError, ValueError):
        return defecto
    if n != n:   # NaN
        return defecto
    return round(max(lo, min(hi, n)), 2)


def limpiar_diseno(tipo, datos):
    """Ajustes recibidos del navegador → valores acotados (nunca se guarda lo que venga sin revisar)."""
    base = DISENO_BASE[tipo]
    datos = datos if isinstance(datos, dict) else {}
    out = {}
    for k in ('letra_celda', 'letra_encabezado', 'letra_clase', 'letra_nota'):
        out[k] = _num(datos.get(k), 5, 40, base[k])
    out['alto_fila'] = _num(datos.get('alto_fila'), 0.5, 6, base['alto_fila'])
    out['auto_alto'] = bool(datos.get('auto_alto', base['auto_alto']))
    out['ocultar_vacias'] = bool(datos.get('ocultar_vacias', False))
    anchos = datos.get('anchos') if isinstance(datos.get('anchos'), list) else []
    out['anchos'] = [_num(anchos[i] if i < len(anchos) else None, 0.3, 12, w) for i, w in enumerate(base['anchos'])]
    celdas = datos.get('celdas') if isinstance(datos.get('celdas'), dict) else {}
    out['celdas'] = {str(k)[:120]: _num(v, 5, 40, base['letra_celda']) for k, v in list(celdas.items())[:400]}
    return out


def diseno_efectivo(agenda):
    """Ajustes guardados completados con los de partida (lo usan el editor, el PowerPoint y el Word)."""
    return limpiar_diseno(tipo_diseno(agenda), agenda.diseno_json or {})


def _areas(request):
    from .views import _areas_para_usuario
    return _areas_para_usuario(request.user, request)


def _puede(request, agenda=None):
    from .views import _es_coord_efectivo
    if not _es_coord_efectivo(request):
        return False
    areas = _areas(request)
    return agenda is None or areas is None or agenda.grado.area in areas


_MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
          'noviembre', 'diciembre']


def _fecha_es(d):
    return f'{d.day} de {_MESES[d.month - 1]}'


# ── Pestaña "Crear agenda" ────────────────────────────────────────────────────
def contexto_crear(request):
    """Grados del coordinador agrupados por área + la próxima semana (lunes) y lo que ya existe en ella."""
    areas = _areas(request)
    grados = GradoAgenda.objects.filter(activo=True)
    if areas is not None:
        grados = grados.filter(area__in=areas)
    hoy = timezone.now().date()
    lunes = hoy - timedelta(days=hoy.weekday())   # lunes a miércoles: esta semana; jueves en adelante: la próxima
    if hoy.weekday() >= 3:
        lunes += timedelta(days=7)
    existentes = set(Agenda.objects.filter(semana_inicio__gte=lunes, semana_inicio__lte=lunes + timedelta(days=6))
                     .values_list('grado_id', flat=True))
    por_area = {}
    for g in grados:
        por_area.setdefault(g.get_area_display(), []).append({'id': g.pk, 'nombre': g.nombre, 'existe': g.pk in existentes})
    return {'crear_grupos': por_area, 'crear_lunes': lunes}


@login_required
@require_POST
def crear_semana(request):
    """Crea la agenda VACÍA (solo grado + semana) de cada grado marcado; los maestros la llenan después."""
    if not _puede(request):
        return HttpResponseForbidden()
    from .views import _clases_core, _clases_orden
    destino = reverse('agendas:dashboard_coordinador') + '?tab=crear'
    try:
        d = date.fromisoformat(request.POST.get('semana', ''))
    except ValueError:
        messages.error(request, 'Elige la semana.')
        return redirect(destino)
    lunes = d - timedelta(days=d.weekday())
    viernes = lunes + timedelta(days=4)
    ids = [int(x) for x in request.POST.getlist('grados') if x.isdigit()]
    areas = _areas(request)
    grados = GradoAgenda.objects.filter(pk__in=ids, activo=True)
    if areas is not None:
        grados = grados.filter(area__in=areas)
    if not grados:
        messages.error(request, 'Marca al menos un grado.')
        return redirect(destino)
    creadas, ya = [], []
    for g in grados.order_by('area', 'orden', 'nombre'):
        existe = Agenda.objects.filter(grado=g).filter(
            Q(semana_inicio__lte=viernes, semana_fin__gte=lunes)
            | Q(semana_inicio__gte=lunes, semana_inicio__lte=lunes + timedelta(days=6))).exists()
        if existe:
            ya.append(g.nombre)
            continue
        core = _clases_core(g)
        filas = [{'materia': m, **{dia: '' for dia in DIAS}, 'nota': '', 'docente': '', 'es_asociada': False}
                 for m in _clases_orden(g) if m in core]
        Agenda.objects.create(usuario=request.user, grado=g, semana_inicio=lunes, semana_fin=viernes,
                              materias_json=filas, creado_por=request.user)
        creadas.append(g.nombre)
    sem = f'{lunes:%d/%m/%Y} – {viernes:%d/%m/%Y}'
    if creadas:
        messages.success(request, f'Semana {sem}: se crearon {len(creadas)} agenda(s) ({", ".join(creadas)}). '
                                  'Los maestros ya pueden llenarlas.')
    if ya:
        messages.warning(request, f'Ya existían y no se tocaron: {", ".join(ya)}.')
    return redirect(reverse('agendas:dashboard_coordinador'))


# ── Editor de diseño ──────────────────────────────────────────────────────────
@login_required
def editor(request, pk):
    agenda = get_object_or_404(Agenda.objects.select_related('grado'), pk=pk)
    if not _puede(request, agenda):
        return HttpResponseForbidden('Solo la coordinación del área puede diseñar esta agenda.')
    from django.templatetags.static import static
    from .views import _rol_ctx
    tipo = tipo_diseno(agenda)
    filas = [{'materia': m.get('materia', ''), **{dia: (m.get(dia) or '').replace('\r\n', '\n').replace('\r', '')
                                                   for dia in DIAS}}
             for m in (agenda.materias_json or [])]
    datos = {
        'tipo': tipo, 'filas': filas, 'nota': agenda.nota_general or '', 'diseno': diseno_efectivo(agenda),
        'base': DISENO_BASE[tipo], 'grado': agenda.grado.nombre,
        'semana': f'{_fecha_es(agenda.semana_inicio)} al {_fecha_es(agenda.semana_fin)}',
        'semana_col': f'Semana del {_fecha_es(agenda.semana_inicio)} al {_fecha_es(agenda.semana_fin)} de {agenda.semana_fin.year}',
        'fondo': static('agendas/img/plantilla agendas.png'),
        'archivo': f"agenda_{agenda.grado.nombre.replace(' ', '_')}_{agenda.semana_inicio}.png",
    }
    return render(request, 'agendas/diseno_agenda.html', {
        'agenda': agenda, 'datos': datos, 'tipo': tipo, **_rol_ctx(request),
    })


@login_required
@require_POST
def guardar(request, pk):
    """Guarda ajustes de diseño y los textos corregidos (JSON). Conserva quién llenó cada clase."""
    agenda = get_object_or_404(Agenda.objects.select_related('grado'), pk=pk)
    if not _puede(request, agenda):
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    try:
        datos = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)
    agenda.diseno_json = limpiar_diseno(tipo_diseno(agenda), datos.get('diseno'))
    nuevos = {str(f.get('materia', '')): f for f in (datos.get('filas') or []) if isinstance(f, dict)}
    quien = request.user.get_full_name() or request.user.username
    filas = []
    for m in (agenda.materias_json or []):
        m = dict(m)
        n = nuevos.get(m.get('materia', ''))
        if n:
            cambio = False
            for dia in DIAS:
                txt = str(n.get(dia, ''))[:2000].replace('\r\n', '\n').replace('\r', '')
                if txt != (m.get(dia) or '').replace('\r\n', '\n').replace('\r', ''):
                    m[dia] = txt
                    cambio = True
            if cambio and not (m.get('docente') or '').strip() and any(m.get(d) for d in DIAS):
                m['docente'] = quien
        filas.append(m)
    agenda.materias_json = filas
    if 'nota' in datos:
        agenda.nota_general = str(datos.get('nota') or '').strip()[:200]
    agenda.modificado_por = request.user
    agenda.save()
    return JsonResponse({'ok': True, 'hora': timezone.now().strftime('%H:%M')})


@login_required
@require_POST
def imagen_final_guardar(request, pk):
    """Recibe el PNG generado en el navegador y lo guarda como imagen final de la agenda."""
    agenda = get_object_or_404(Agenda.objects.select_related('grado'), pk=pk)
    if not _puede(request, agenda):
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    f = request.FILES.get('imagen')
    if not f or f.size > MAX_PNG_MB * 1024 * 1024:
        return JsonResponse({'ok': False, 'error': f'Falta la imagen o pesa más de {MAX_PNG_MB} MB.'}, status=400)
    contenido = f.read()
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(contenido))
        img.verify()
        if img.format != 'PNG' or img.size[0] > 5000 or img.size[1] > 5000:
            raise ValueError
    except Exception:
        return JsonResponse({'ok': False, 'error': 'No es una imagen PNG válida.'}, status=400)
    anterior = agenda.imagen_final.name if agenda.imagen_final else ''
    nombre = f"agenda_{agenda.pk}_{timezone.now():%Y%m%d_%H%M%S}.png"
    agenda.imagen_final.save(nombre, ContentFile(contenido), save=False)
    agenda.imagen_final_en = timezone.now()
    agenda.imagen_final_por = request.user
    agenda.save(update_fields=['imagen_final', 'imagen_final_en', 'imagen_final_por', 'fecha_modificado'])
    if anterior and anterior != agenda.imagen_final.name:
        agenda.imagen_final.storage.delete(anterior)
    return JsonResponse({'ok': True, 'fecha': agenda.imagen_final_en.strftime('%d/%m/%Y %H:%M'),
                         'url': reverse('agendas:imagen_final', args=[agenda.pk])})


@login_required
def imagen_final_ver(request, pk):
    """Sirve la imagen final (sin depender de cómo se publique /media/)."""
    agenda = get_object_or_404(Agenda.objects.select_related('grado'), pk=pk)
    from .views import _es_coordinador
    areas = _areas(request)
    if not _es_coordinador(request.user) or (areas is not None and agenda.grado.area not in areas):
        return HttpResponseForbidden()
    if not agenda.imagen_final:
        raise Http404
    try:
        return FileResponse(agenda.imagen_final.open('rb'), content_type='image/png')
    except FileNotFoundError:
        raise Http404
