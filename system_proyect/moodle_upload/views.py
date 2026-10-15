# <--- hecho por claude code (14-oct-2026): pantalla "Subir a Moodle" (solo superusuario, solo en pruebas).
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import services
from .models import ConexionMoodle, PublicacionMoodle

MAX_MB = 15
EXT_OK = ('.png', '.jpg', '.jpeg')


def _solo_super(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        raise PermissionDenied('Solo el superusuario.')


@login_required
def index(request):
    _solo_super(request)
    con = ConexionMoodle.actual()
    estado, cursos = None, []
    if con.token:
        try:
            i = services.info(con)
            estado = {'ok': True, 'texto': f"Conectado a «{i.get('sitename')}» como {i.get('username')} · Moodle {i.get('release', '')}"}
            cursos = cache.get('moodle_upload_cursos')
            if cursos is None:
                cursos = [{'id': c['id'], 'nombre': c.get('fullname') or c.get('shortname'), 'corto': c.get('shortname', '')}
                          for c in services.cursos(con)]
                cache.set('moodle_upload_cursos', cursos, 60)
        except services.MoodleError as e:
            estado = {'ok': False, 'texto': str(e)}
    import datetime as _dt
    from django.utils import timezone
    pubs = PublicacionMoodle.objects
    hace7 = timezone.now() - _dt.timedelta(days=7)
    tab = request.GET.get('tab', 'publicar')
    return render(request, 'moodle_upload/index.html', {
        'con': con, 'tiene_token': bool(con.token), 'estado': estado, 'cursos': cursos,
        'grupos': services.agrupar(cursos),   # <--- hecho por claude code (15-oct-2026)
        'historial': pubs.select_related('usuario', 'agenda__grado')[:100], 'max_mb': MAX_MB,
        'tab': tab if tab in ('publicar', 'historial', 'conexion') else 'publicar',
        'kpi_total': pubs.filter(ok=True).count(), 'kpi_semana': pubs.filter(ok=True, fecha__gte=hace7).count(),
        'kpi_agendas': pubs.filter(ok=True, agenda__isnull=False).count(), 'kpi_errores': pubs.filter(ok=False).count(),
        'ultima': pubs.filter(ok=True).first(),
    })


@login_required
@require_POST
def guardar_conexion(request):
    _solo_super(request)
    con = ConexionMoodle.actual()
    url = (request.POST.get('url') or '').strip().rstrip('/')
    if not url.startswith(('http://', 'https://')):
        messages.error(request, 'La dirección debe empezar con http:// o https://')
        return redirect('moodle_upload:index')
    con.url = url
    token = (request.POST.get('token') or '').strip()
    if token:                       # vacío = conservar el token guardado
        con.set_token(token)
    con.actualizado_por = request.user
    con.save()
    cache.delete('moodle_upload_cursos')
    messages.success(request, 'Conexión guardada.')
    return redirect(reverse('moodle_upload:index') + '?tab=conexion')


@login_required
@require_POST
def publicar(request):
    """Publica una imagen en UN curso. Con ?ajax=1 responde JSON (la pestaña Publicar llama una vez por curso marcado)."""
    _solo_super(request)
    ajax = request.GET.get('ajax') == '1'   # <--- hecho por claude code (15-oct-2026): selección múltiple agrupada

    def fallo(texto, status=400):
        if ajax:
            return JsonResponse({'ok': False, 'error': texto}, status=status)
        messages.error(request, texto)
        return redirect('moodle_upload:index')

    con = ConexionMoodle.actual()
    f = request.FILES.get('imagen')
    curso_id = request.POST.get('curso', '')
    alt = (request.POST.get('alt') or '').strip()[:200]
    if not f or not curso_id.isdigit():
        return fallo('Elige el curso y la imagen.')
    if os.path.splitext(f.name)[1].lower() not in EXT_OK:
        return fallo('Solo imágenes PNG o JPG.')
    if f.size > MAX_MB * 1024 * 1024:
        return fallo(f'La imagen pesa más de {MAX_MB} MB.')
    nombres = {str(c['id']): c['nombre'] for c in (cache.get('moodle_upload_cursos') or [])}
    reg = PublicacionMoodle(curso_id=int(curso_id), curso_nombre=nombres.get(curso_id, ''), archivo=f.name[:255],
                            tamano_kb=round(f.size / 1024), alt=alt, usuario=request.user)
    try:
        r = services.publicar(con, curso_id, f.name, f.read(), alt)
        reg.ok, reg.creada, reg.cmid = True, bool(r.get('creado')), r.get('cmid')
        reg.mensaje = r.get('url', '')
    except services.MoodleError as e:
        reg.mensaje = str(e)
    reg.save()
    if not reg.ok:
        return fallo(f'No se publicó: {reg.mensaje}' if not ajax else reg.mensaje, status=502)
    if ajax:
        return JsonResponse({'ok': True, 'creada': reg.creada, 'curso': reg.curso_nombre or curso_id, 'url': reg.mensaje,
                             'fecha': reg.fecha.strftime('%d/%m/%Y %H:%M')})
    messages.success(request, ('Agenda CREADA' if reg.creada else 'Agenda REEMPLAZADA') +
                     f" en «{reg.curso_nombre or curso_id}». Abre el curso para verla.")
    return redirect('moodle_upload:index')


# ── Desde el Dashboard de Agendas (hecho por claude code, 14-oct-2026) ─────────────────────────────
from django.shortcuts import get_object_or_404


def _puede_publicar_agendas(user):
    from agendas.views import _es_coordinador   # misma regla que el Dashboard de Agendas
    return user.is_authenticated and _es_coordinador(user)


def _cursos_cache(con):
    cursos = cache.get('moodle_upload_cursos')
    if cursos is None:
        cursos = [{'id': c['id'], 'nombre': c.get('fullname') or c.get('shortname'), 'corto': c.get('shortname', '')}
                  for c in services.cursos(con)]
        cache.set('moodle_upload_cursos', cursos, 60)
    return cursos


@login_required
def cursos_json(request):
    if not _puede_publicar_agendas(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    con = ConexionMoodle.actual()
    try:
        cursos = _cursos_cache(con)
        # <--- hecho por claude code (15-oct-2026): agrupados por grado-sección + el grupo que corresponde a la agenda
        grupos = services.agrupar(cursos)
        sugerido = ''
        if (request.GET.get('agenda') or '').isdigit():
            from agendas.models import Agenda
            ag = Agenda.objects.select_related('grado').filter(pk=request.GET['agenda']).first()
            if ag and ag.grado_id:
                sugerido = services.grupo_sugerido(grupos, ag.grado.area, ag.grado.nombre)
        return JsonResponse({'ok': True, 'cursos': cursos, 'grupos': grupos, 'sugerido': sugerido})
    except services.MoodleError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=502)


@login_required
@require_POST
def publicar_agenda(request, pk):
    if not _puede_publicar_agendas(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    from agendas.models import Agenda
    agenda = get_object_or_404(Agenda.objects.select_related('grado'), pk=pk)
    f = request.FILES.get('imagen')
    curso_id = request.POST.get('curso', '')
    if not f or not curso_id.isdigit():
        return JsonResponse({'ok': False, 'error': 'Elige el curso y la imagen.'}, status=400)
    if os.path.splitext(f.name)[1].lower() not in EXT_OK:
        return JsonResponse({'ok': False, 'error': 'Solo imágenes PNG o JPG.'}, status=400)
    if f.size > MAX_MB * 1024 * 1024:
        return JsonResponse({'ok': False, 'error': f'La imagen pesa más de {MAX_MB} MB.'}, status=400)
    con = ConexionMoodle.actual()
    try:
        nombres = {str(c['id']): c['nombre'] for c in _cursos_cache(con)}
    except services.MoodleError:
        nombres = {}
    alt = f"Agenda semanal {agenda.grado.nombre} · {agenda.semana_inicio:%d/%m} – {agenda.semana_fin:%d/%m/%Y}"
    reg = PublicacionMoodle(agenda=agenda, curso_id=int(curso_id), curso_nombre=nombres.get(curso_id, ''),
                            archivo=f.name[:255], tamano_kb=round(f.size / 1024), alt=alt[:200], usuario=request.user)
    try:
        r = services.publicar(con, curso_id, f.name, f.read(), alt)
        reg.ok, reg.creada, reg.cmid, reg.mensaje = True, bool(r.get('creado')), r.get('cmid'), r.get('url', '')
    except services.MoodleError as e:
        reg.mensaje = str(e)
    reg.save()
    if not reg.ok:
        return JsonResponse({'ok': False, 'error': reg.mensaje}, status=502)
    return JsonResponse({'ok': True, 'creada': reg.creada, 'curso': reg.curso_nombre or curso_id,
                         'url': reg.mensaje, 'fecha': reg.fecha.strftime('%d/%m/%Y %H:%M')})
