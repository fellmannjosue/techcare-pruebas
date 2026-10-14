# <--- hecho por claude code (14-oct-2026): pantalla "Subir a Moodle" (solo superusuario, solo en pruebas).
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
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
    return render(request, 'moodle_upload/index.html', {
        'con': con, 'tiene_token': bool(con.token), 'estado': estado, 'cursos': cursos,
        'historial': PublicacionMoodle.objects.select_related('usuario')[:30], 'max_mb': MAX_MB,
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
    return redirect('moodle_upload:index')


@login_required
@require_POST
def publicar(request):
    _solo_super(request)
    con = ConexionMoodle.actual()
    f = request.FILES.get('imagen')
    curso_id = request.POST.get('curso', '')
    alt = (request.POST.get('alt') or '').strip()[:200]
    if not f or not curso_id.isdigit():
        messages.error(request, 'Elige el curso y la imagen.')
        return redirect('moodle_upload:index')
    if os.path.splitext(f.name)[1].lower() not in EXT_OK:
        messages.error(request, 'Solo imágenes PNG o JPG.')
        return redirect('moodle_upload:index')
    if f.size > MAX_MB * 1024 * 1024:
        messages.error(request, f'La imagen pesa más de {MAX_MB} MB.')
        return redirect('moodle_upload:index')
    nombres = {str(c['id']): c['nombre'] for c in (cache.get('moodle_upload_cursos') or [])}
    reg = PublicacionMoodle(curso_id=int(curso_id), curso_nombre=nombres.get(curso_id, ''), archivo=f.name[:255],
                            tamano_kb=round(f.size / 1024), alt=alt, usuario=request.user)
    try:
        r = services.publicar(con, curso_id, f.name, f.read(), alt)
        reg.ok, reg.creada, reg.cmid = True, bool(r.get('creado')), r.get('cmid')
        reg.mensaje = r.get('url', '')
        messages.success(request, ('Agenda CREADA' if reg.creada else 'Agenda REEMPLAZADA') +
                         f" en «{reg.curso_nombre or curso_id}». Abre el curso para verla.")
    except services.MoodleError as e:
        reg.mensaje = str(e)
        messages.error(request, f'No se publicó: {e}')
    reg.save()
    return redirect('moodle_upload:index')
