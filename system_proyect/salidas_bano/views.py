# <--- hecho por claude code: Sistema Salidas Baño — vistas completas
import json
from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connections
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import PeriodoEscolar, MaestroClase, SalidaBano, NotificacionSalida
from .forms import PeriodoEscolarForm, MaestroClaseForm

User = get_user_model()

# ── Colores de semáforo ───────────────────────────────────────────────────────
SEMAFORO_BADGE = {
    'verde':    ('bg-success',  'text-white', 'Verde'),
    'amarillo': ('bg-yellow',   'text-white', 'Amarillo'),
    'rojo':     ('bg-danger',   'text-white', 'Rojo'),
    'negro':    ('bg-dark',     'text-white', 'Negro'),
}

# ── Semáforo automático: 1ª salida=verde, 2ª=amarillo, 3ª=rojo, 4ª=negro ────
SEMAFORO_AUTO = ['verde', 'amarillo', 'rojo', 'negro']

# ── Mapeo área → descripción SQL Server ──────────────────────────────────────
_AREA_SQL = {
    'colegio':      "N'Colegio'",
    'bachillerato': "N'Bachillerato'",
}

# ── Nombres modernos de grado por área ───────────────────────────────────────
# CrsoNumero en SQL Server devuelve "1ero", "2do", etc.
# Los mostramos con la nomenclatura oficial (7mo–11vo)
GRADO_DISPLAY = {
    'colegio': {
        '1': '7mo', '1ero': '7mo',
        '2': '8vo', '2do': '8vo',
        '3': '9no', '3ero': '9no',
    },
    'bachillerato': {
        '1': '10mo', '1ero': '10mo',
        '2': '11vo', '2do': '11vo',
    },
}


def _get_periodo_activo(area):
    """Retorna el periodo activo para el área dada (o None)."""
    # Busca periodo activo que aplique al área o sea 'ambos'
    q = PeriodoEscolar.objects.filter(activo=True)
    # Filtra por area: exacto o 'ambos'
    periodo = q.filter(area=area).first() or q.filter(area='ambos').first()
    return periodo


def _alumnos_sqlserver(area):
    """Retorna lista de alumnos de SQL Server para el area dado."""
    desc = _AREA_SQL.get(area)
    if not desc:
        return []
    try:
        with connections['padres_sqlserver'].cursor() as cursor:
            sql = f"""
              SELECT
                t.IngrEgrID,
                ISNULL(d.Nombre1,'')
                  + CASE WHEN d.Nombre2 IS NOT NULL AND d.Nombre2 <> '' THEN ' '+d.Nombre2 ELSE '' END
                  + ' '
                  + ISNULL(d.Apellido1,'')
                  + CASE WHEN d.Apellido2 IS NOT NULL AND d.Apellido2 <> '' THEN ' '+d.Apellido2 ELSE '' END
                  AS NombreCompl,
                c.CrsoNumero,
                c.GrupoNumero
              FROM dbo.tblPrsDtosGen   AS d
              JOIN dbo.tblPrsTipo           AS t  ON d.PersonaID = t.PersonaID
              JOIN dbo.tblEdcArea           AS a  ON t.IngrEgrID = a.IngrEgrID
              JOIN dbo.tblEdcEjecCrso       AS ec ON a.AreaID    = ec.AreaID
              JOIN dbo.tblEdcCrso           AS c  ON ec.CrsoID   = c.CrsoID
              JOIN dbo.tblEdcDescripAreaEdc AS da ON a.DescrAreaEdcID = da.DescrAreaEdcID
              WHERE d.Alum = 1
                AND DATEPART(yy, c.FechaInicio) = DATEPART(yyyy, GETDATE())
                AND da.Descripcion IN ({desc})
                AND ec.Desertor    = 0
                AND ec.TrasladoPer = 0
              ORDER BY c.CrsoNumero, c.GrupoNumero, NombreCompl
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
        return [
            {
                'ingr_egr_id': row[0],
                'nombre':      (row[1] or '').strip(),
                'grado':       str(row[2] or '').strip(),
                'grupo':       str(row[3] or '').strip(),
            }
            for row in rows
        ]
    except Exception as e:
        print(f'[salidas_bano] ERROR SQL Server ({area}):', e)
        return []


def _notif_no_leidas(user):
    return NotificacionSalida.objects.filter(usuario=user, leida=False).count()


# ── Helpers de acceso ─────────────────────────────────────────────────────────

GRP_MAESTRO = 'control baños col'
GRP_COORD   = 'control baño coord'


def _puede_acceder(user):
    """Superuser, staff, control baños col o control baño coord."""
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=[GRP_MAESTRO, GRP_COORD]).exists()


def _es_coordinador_sb(user):
    """¿Puede gestionar períodos y maestros-clases?"""
    if user.is_superuser:
        return True
    return user.groups.filter(name=GRP_COORD).exists()


def _puede_editar_salidas(user):
    """Superuser y coordinadores con salidas_editar=True (o sin registro CoordPermiso)."""
    if user.is_superuser:
        return True
    try:
        return user.coord_permiso.salidas_editar
    except Exception:
        return True  # sin registro = sin restricción (compatibilidad)


def _puede_eliminar_salidas(user):
    """Superuser y coordinadores con salidas_eliminar=True y dentro del plazo."""
    if user.is_superuser:
        return True
    try:
        p = user.coord_permiso
        if p.salidas_eliminar_hasta and p.salidas_eliminar_hasta < timezone.now():
            return False
        return p.salidas_eliminar
    except Exception:
        return True  # sin registro = sin restricción


# ══════════════════════════════════════════════════════════════════════════════
# Vista principal
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def index(request):
    if not _puede_acceder(request.user):
        return HttpResponseForbidden()

    es_coord   = _es_coordinador_sb(request.user)
    tab_activo = request.GET.get('tab', 'salidas')   # salidas | periodos | maestros

    # ── Grados disponibles para el form Maestros-Clases (agrupados por área) ────
    _AREA_LABELS = [('colegio', 'Colegio'), ('bachillerato', 'Bachillerato')]
    grados_para_mc = {}   # {'Colegio': ['1ero','2do','3ero'], 'Bachillerato': [...]}
    for _ak, _alabel in _AREA_LABELS:
        _gs = sorted(set(a['grado'] for a in _alumnos_sqlserver(_ak) if a['grado']))
        # Agrega grados ya guardados en MaestroClase para ese área
        _gs_extra = list(MaestroClase.objects.filter(area=_ak)
                         .values_list('grado', flat=True).distinct())
        _gs = sorted(set(_gs) | set(_gs_extra))
        if _gs:
            _dm = GRADO_DISPLAY.get(_ak, {})
            grados_para_mc[_alabel] = [(_g, _dm.get(_g, _g)) for _g in _gs]

    # ── Manejar POSTs del coordinador ──────────────────────────────────────────
    periodo_form = PeriodoEscolarForm()
    mc_form      = MaestroClaseForm(grado_choices=grados_para_mc)

    if request.method == 'POST' and es_coord:
        accion = request.POST.get('accion', '')

        if accion == 'guardar_periodo':
            edit_pid = request.POST.get('edit_id')
            inst = PeriodoEscolar.objects.filter(pk=edit_pid).first() if edit_pid else None
            periodo_form = PeriodoEscolarForm(request.POST, instance=inst)
            if periodo_form.is_valid():
                periodo_form.save()
                messages.success(request, 'Período guardado.')
                return redirect(f'{request.path}?tab=periodos')
            tab_activo = 'periodos'

        elif accion == 'eliminar_periodo':
            PeriodoEscolar.objects.filter(pk=request.POST.get('obj_id')).delete()
            messages.success(request, 'Período eliminado.')
            return redirect(f'{request.path}?tab=periodos')

        elif accion == 'guardar_mc':
            edit_mid = request.POST.get('edit_id')
            inst = MaestroClase.objects.filter(pk=edit_mid).first() if edit_mid else None
            mc_form = MaestroClaseForm(request.POST, instance=inst, grado_choices=grados_para_mc)
            if mc_form.is_valid():
                mc_form.save()
                messages.success(request, 'Asignación guardada.')
                return redirect(f'{request.path}?tab=maestros')
            tab_activo = 'maestros'

        elif accion == 'eliminar_mc':
            MaestroClase.objects.filter(pk=request.POST.get('obj_id')).delete()
            messages.success(request, 'Asignación eliminada.')
            return redirect(f'{request.path}?tab=maestros')

    # Editar desde GET
    if request.GET.get('editar_periodo') and es_coord:
        inst = PeriodoEscolar.objects.filter(pk=request.GET['editar_periodo']).first()
        if inst:
            periodo_form = PeriodoEscolarForm(instance=inst)
        tab_activo = 'periodos'

    if request.GET.get('editar_mc') and es_coord:
        inst = MaestroClase.objects.filter(pk=request.GET['editar_mc']).first()
        if inst:
            mc_form = MaestroClaseForm(instance=inst, grado_choices=grados_para_mc)
        tab_activo = 'maestros'

    # ── Datos de salidas (tab principal) ───────────────────────────────────────
    area      = request.GET.get('area', 'colegio')
    grado_sel = request.GET.get('grado', '')
    areas = [('colegio', 'Colegio'), ('bachillerato', 'Bachillerato')]

    periodo = None
    alumnos_por_grado = {}
    grados            = []
    salidas_hoy       = {}
    clases_por_grado  = {}
    error             = ''

    periodo = _get_periodo_activo(area)
    if not periodo:
        error = f'No hay período activo para {dict(areas).get(area, area)}. Configúralo en la pestaña Períodos.'

    todos = _alumnos_sqlserver(area)
    for a in todos:
        g = a['grado']
        if g not in alumnos_por_grado:
            alumnos_por_grado[g] = []
        alumnos_por_grado[g].append(a)
    grados = sorted(alumnos_por_grado.keys())
    if grados and not grado_sel:
        grado_sel = grados[0]

    if periodo:
        # Agrupar todas las salidas de hoy por alumno; key = str(ingr_egr_id)
        _raw = {}
        for s in (SalidaBano.objects
                  .filter(periodo=periodo, area=area, fecha=date.today())
                  .select_related('maestro')
                  .order_by('id')):
            _raw.setdefault(s.ingr_egr_id, []).append(s)
        for _iid, _exits in _raw.items():
            _last   = _exits[-1]
            _nombre = (_last.maestro.get_full_name() or _last.maestro.username) if _last.maestro else '—'
            salidas_hoy[str(_iid)] = {
                'count':             len(_exits),
                'semaforo':          _last.semaforo,
                'last_id':           _last.id,
                'last_clase':        _last.clase,
                'last_maestro':      _nombre,
                'last_hora_salida':  _last.hora_salida.strftime('%H:%M') if _last.hora_salida else '',
                'last_hora_regreso': _last.hora_regreso.strftime('%H:%M') if _last.hora_regreso else '',
                'last_comentario':   _last.comentario or '',
            }

    # Incluye registros del área exacta + los marcados como 'ambos'
    for mc in (MaestroClase.objects
               .filter(area__in=[area, 'ambos'])
               .select_related('maestro')
               .order_by('grado', 'maestro__first_name', 'clase')):
        nombre  = mc.maestro.get_full_name() or mc.maestro.username
        entrada = {'value': mc.clase, 'label': f"{nombre} — {mc.clase}"}
        # Soporta: "todos", "1ero", "1ero,2do", "1ero,2do,3ero"
        grados_mc = [g.strip() for g in mc.grado.split(',')]
        targets   = grados if 'todos' in grados_mc else grados_mc
        for g in targets:
            if g not in clases_por_grado:
                clases_por_grado[g] = []
            clases_por_grado[g].append(entrada)

    # ── Datos para tabs de coordinador ─────────────────────────────────────────
    periodos_lista = PeriodoEscolar.objects.all().order_by('-anio', '-parcial') if es_coord else []
    mc_lista       = (MaestroClase.objects.select_related('maestro')
                      .order_by('area', 'grado', 'maestro__first_name') if es_coord else [])

    ctx = {
        'areas':             areas,
        'area_sel':          area,
        'grado_sel':         grado_sel,
        'grados':            grados,
        'alumnos_por_grado': json.dumps(alumnos_por_grado),
        'salidas_hoy':       json.dumps(salidas_hoy),
        'clases_por_grado':  json.dumps(clases_por_grado),
        'periodo':           periodo,
        'periodo_id':        periodo.id if periodo else '',
        'error':             error,
        'notif_count':       _notif_no_leidas(request.user),
        'nav_home_url':      '/',
        'es_coordinador':    es_coord,
        'fecha_hoy':         date.today().strftime('%Y-%m-%d'),
        'tab_activo':        tab_activo,
        # Nombres modernos de grado (7mo-11vo): lista de (raw, label)
        'grados_display':    [(g, GRADO_DISPLAY.get(area, {}).get(g, g)) for g in grados],
        # Coordinador
        'periodo_form':      periodo_form,
        'mc_form':           mc_form,
        'periodos_lista':    periodos_lista,
        'mc_lista':          mc_lista,
        'editar_periodo_id': request.GET.get('editar_periodo', ''),
        'editar_mc_id':      request.GET.get('editar_mc', ''),
    }
    return render(request, 'salidas_bano/index.html', ctx)


# ══════════════════════════════════════════════════════════════════════════════
# API: guardar salida
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def guardar_salida(request):
    """Registra una nueva salida al baño. Semáforo asignado automáticamente."""
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    periodo_id  = data.get('periodo_id')
    ingr_egr_id = data.get('ingr_egr_id')
    alumno      = data.get('alumno', '')
    grado       = data.get('grado', '')
    grupo       = data.get('grupo', '')
    area        = data.get('area', '')
    clase        = data.get('clase', '')
    hora_salida  = data.get('hora_salida', '')
    hora_regreso = data.get('hora_regreso', '').strip()
    comentario   = data.get('comentario', '')

    if not all([periodo_id, ingr_egr_id, alumno, area, clase, hora_salida]):
        return JsonResponse({'ok': False, 'error': 'Faltan campos requeridos.'}, status=400)

    periodo = get_object_or_404(PeriodoEscolar, pk=periodo_id)

    # Parsear hora
    try:
        hs = datetime.strptime(hora_salida.strip(), '%H:%M').time()
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Formato de hora inválido.'}, status=400)

    # ── Auto-semáforo: contar salidas de hoy para este alumno ─────────────────
    count_hoy = SalidaBano.objects.filter(
        ingr_egr_id=int(ingr_egr_id), area=area, fecha=date.today()
    ).count()

    # Bloquear si ya alcanzó Negro (count >= 3) y no es coordinador
    if count_hoy >= 3 and not _es_coordinador_sb(request.user):
        nombre_corto = alumno.split()[0] if alumno else 'El alumno'
        return JsonResponse({
            'ok':    False,
            'error': f'{nombre_corto} ya está en Negro hoy. Solo el coordinador puede registrar más salidas.',
        }, status=400)

    # Índice 0→verde, 1→amarillo, 2→rojo, 3→negro
    semaforo = SEMAFORO_AUTO[min(count_hoy, 3)]

    # Parsear hora_regreso (opcional)
    hr = None
    if hora_regreso:
        try:
            hr = datetime.strptime(hora_regreso, '%H:%M').time()
        except ValueError:
            hr = None

    salida = SalidaBano.objects.create(
        ingr_egr_id  = int(ingr_egr_id),
        alumno       = alumno,
        grado        = grado,
        grupo        = grupo,
        area         = area,
        periodo      = periodo,
        clase        = clase,
        semaforo     = semaforo,
        hora_salida  = hs,
        hora_regreso = hr,
        comentario   = comentario,
        maestro      = request.user,
    )

    # ── Notificaciones solo cuando llega a Negro ──────────────────────────────
    if semaforo == 'negro':
        _crear_notificaciones(salida, request.user)
        _enviar_email_negro(salida, request)

    nombre_maestro = request.user.get_full_name() or request.user.username

    return JsonResponse({
        'ok':          True,
        'id':          salida.id,
        'semaforo':    semaforo,
        'count':       count_hoy + 1,
        'maestro':     nombre_maestro,
        'hora_salida': hs.strftime('%H:%M'),
        'hora_regreso': hr.strftime('%H:%M') if hr else '',
    })


# ══════════════════════════════════════════════════════════════════════════════
# API: registrar regreso
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def marcar_regreso(request, pk):
    salida = get_object_or_404(SalidaBano, pk=pk)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    hora_regreso = data.get('hora_regreso', '')
    try:
        hr = datetime.strptime(hora_regreso.strip(), '%H:%M').time()
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Formato de hora inválido.'}, status=400)
    salida.hora_regreso = hr
    salida.save(update_fields=['hora_regreso'])
    duracion = salida.duracion_minutos
    return JsonResponse({'ok': True, 'duracion': duracion})


# ══════════════════════════════════════════════════════════════════════════════
# API: eliminar salida (solo coordinadores)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def eliminar_salida(request, pk):
    """Elimina una salida registrada. Solo coordinadores con permiso activo."""
    if not _es_coordinador_sb(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    if not _puede_eliminar_salidas(request.user):
        return JsonResponse({'ok': False, 'error': 'Permiso de eliminación no activo o expirado.'}, status=403)

    salida = get_object_or_404(SalidaBano, pk=pk)
    ingr_egr_id = salida.ingr_egr_id
    area        = salida.area
    salida.delete()

    # Recalcular estado actual del alumno para este día
    exits_hoy = (SalidaBano.objects
                 .filter(ingr_egr_id=ingr_egr_id, area=area, fecha=date.today())
                 .select_related('maestro')
                 .order_by('id'))
    count = exits_hoy.count()

    if count == 0:
        return JsonResponse({'ok': True, 'count': 0, 'semaforo': '',
                             'last_id': '', 'last_clase': '',
                             'last_maestro': '', 'last_hora_salida': ''})

    last   = exits_hoy.last()
    nombre = (last.maestro.get_full_name() or last.maestro.username) if last.maestro else '—'
    return JsonResponse({
        'ok':              True,
        'count':           count,
        'semaforo':        last.semaforo,
        'last_id':         last.id,
        'last_clase':      last.clase,
        'last_maestro':    nombre,
        'last_hora_salida': last.hora_salida.strftime('%H:%M') if last.hora_salida else '',
        'last_hora_regreso': last.hora_regreso.strftime('%H:%M') if last.hora_regreso else '',
        'last_comentario': last.comentario or '',
    })


# ══════════════════════════════════════════════════════════════════════════════
# API: notificaciones
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
def notif_count(request):
    count = _notif_no_leidas(request.user)
    return JsonResponse({'count': count})


@login_required
@require_GET
def notif_list(request):
    notifs = (
        NotificacionSalida.objects
        .filter(usuario=request.user, leida=False)
        .select_related('salida', 'salida__maestro')
        .order_by('-creada_en')[:20]
    )
    items = []
    for n in notifs:
        s = n.salida
        semaforo_info = SEMAFORO_BADGE.get(s.semaforo, ('bg-secondary', 'text-white', s.semaforo))
        items.append({
            'id':         n.id,
            'alumno':     s.alumno,
            'grado':      s.grado,
            'grupo':      s.grupo,
            'semaforo':   s.semaforo,
            'bg_class':   semaforo_info[0],
            'hora':       s.hora_salida.strftime('%H:%M') if s.hora_salida else '',
            'clase':      s.clase,
            'maestro':    s.maestro.get_full_name() if s.maestro else '',
            'fecha':      s.fecha.strftime('%d/%m/%Y'),
        })
    return JsonResponse({'items': items})


@login_required
@require_POST
def notif_leer(request, pk):
    """Marca una notificación como leída."""
    notif = get_object_or_404(NotificacionSalida, pk=pk, usuario=request.user)
    notif.leida = True
    notif.save(update_fields=['leida'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def notif_leer_todas(request):
    """Marca todas las notificaciones del usuario como leídas."""
    NotificacionSalida.objects.filter(usuario=request.user, leida=False).update(leida=True)
    return JsonResponse({'ok': True})


# ══════════════════════════════════════════════════════════════════════════════
# API: historial alumno
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_GET
def historial_alumno(request, ingr_egr_id):
    """Retorna el historial de salidas de un alumno en el período activo."""
    area     = request.GET.get('area', '')
    periodo  = _get_periodo_activo(area) if area else None

    qs = SalidaBano.objects.filter(ingr_egr_id=ingr_egr_id)
    if periodo:
        qs = qs.filter(periodo=periodo)
    qs = qs.select_related('maestro').order_by('-fecha', '-hora_salida')

    items = []
    for s in qs:
        items.append({
            'id':           s.id,
            'fecha':        s.fecha.strftime('%d/%m/%Y'),
            'clase':        s.clase,
            'semaforo':     s.semaforo,
            'hora_salida':  s.hora_salida.strftime('%H:%M') if s.hora_salida else '',
            'hora_regreso': s.hora_regreso.strftime('%H:%M') if s.hora_regreso else '—',
            'duracion':     s.duracion_minutos,
            'comentario':   s.comentario or '',
            'maestro':      s.maestro.get_full_name() if s.maestro else '',
        })
    return JsonResponse({'alumno': items[0]['id'] if items else ingr_egr_id, 'salidas': items})


# ══════════════════════════════════════════════════════════════════════════════
# Helpers internos
# ══════════════════════════════════════════════════════════════════════════════

def _crear_notificaciones(salida, registrado_por):
    """
    Crea notificaciones de campana para todos los maestros que dan clase
    al mismo grado y área (excepto el propio registrador).
    """
    maestros_grado = User.objects.filter(
        clases_bano__grado=salida.grado,
        clases_bano__area=salida.area,
    ).exclude(pk=registrado_por.pk).distinct()

    for maestro in maestros_grado:
        NotificacionSalida.objects.get_or_create(
            salida=salida,
            usuario=maestro,
            defaults={'leida': False},
        )


def _enviar_email_negro(salida, request):
    """Envía correo HTML al coordinador cuando el semáforo es negro."""
    try:
        from django.core.mail import EmailMultiAlternatives

        area_label  = 'Colegio' if salida.area == 'colegio' else 'Bachillerato'
        hora_str    = salida.hora_salida.strftime('%H:%M') if salida.hora_salida else '—'
        maestro_str = salida.maestro.get_full_name() or salida.maestro.username if salida.maestro else '—'
        comentario  = salida.comentario or '—'
        from accounts.models import DestinatarioEmail
        from core.utils_notifications import crear_notificacion as _crear_notif_global
        campo_mod = 'salidas_negro_bach' if salida.area == 'bachillerato' else 'salidas_negro_col'
        dest_qs = DestinatarioEmail.objects.filter(**{campo_mod: True}).select_related('user')
        extras    = [d.user.email for d in dest_qs if d.user.email]
        to_email  = list(set(extras))
        from_email = settings.DEFAULT_FROM_EMAIL

        asunto = f'⚫ ALERTA NEGRA — {salida.alumno}  |  {area_label} {salida.grado} Grupo {salida.grupo}'

        # ── Texto plano ───────────────────────────────────────────────────────
        texto = (
            f'ALERTA NEGRA — SISTEMA SALIDAS AL BAÑO\n'
            f'{"="*45}\n\n'
            f'El/la siguiente estudiante ha alcanzado su 4ª salida al baño el día de hoy.\n\n'
            f'  Alumno/a    : {salida.alumno}\n'
            f'  Grado/Grupo : {area_label} {salida.grado} — Grupo {salida.grupo}\n'
            f'  Clase       : {salida.clase}\n'
            f'  Hora salida : {hora_str}\n'
            f'  Registrado  : {maestro_str}\n'
            f'  Comentario  : {comentario}\n\n'
            f'Por favor tome las acciones correspondientes.\n\n'
            f'TechCare — servicios.ana-hn.org\n'
            f'(Mensaje automático, no responder)'
        )

        # ── HTML ─────────────────────────────────────────────────────────────
        def row(icon, label, value, shade=False):
            bg = 'background:#f8f9fa;' if shade else ''
            return (
                f'<tr style="{bg}">'
                f'<td style="padding:10px 18px;color:#666;font-weight:600;width:155px;'
                f'border-bottom:1px solid #e9ecef;">{icon}&nbsp;{label}</td>'
                f'<td style="padding:10px 18px;color:#1a1a1a;border-bottom:1px solid #e9ecef;">'
                f'{value}</td></tr>'
            )

        tabla_rows = (
            row('👤', 'Alumno/a',       f'<strong style="font-size:15px;">{salida.alumno}</strong>', shade=True)
          + row('🏫', 'Grado / Grupo',  f'{area_label} <strong>{salida.grado}</strong> — Grupo {salida.grupo}')
          + row('📖', 'Clase / Maestro', salida.clase,          shade=True)
          + row('🕐', 'Hora de salida', hora_str)
          + row('👩‍🏫', 'Registrado por', maestro_str,            shade=True)
          + row('💬', 'Comentario',     comentario)
        )

        html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:32px 16px;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:10px;overflow:hidden;
                  box-shadow:0 4px 18px rgba(0,0,0,.13);max-width:560px;">

      <!-- HEADER -->
      <tr>
        <td style="background:#1a1a1a;padding:30px 32px;text-align:center;">
          <div style="font-size:42px;margin-bottom:10px;">⚫</div>
          <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700;letter-spacing:1px;">
            ALERTA NEGRA — SALIDAS AL BAÑO
          </h1>
          <p style="color:#999;margin:8px 0 0;font-size:13px;">
            4ª salida registrada el día de hoy — acción requerida
          </p>
        </td>
      </tr>

      <!-- BODY -->
      <tr>
        <td style="padding:28px 32px;">
          <p style="margin:0 0 22px;color:#444;font-size:15px;line-height:1.6;">
            Se ha registrado la <strong>cuarta (4ª) salida al baño</strong> del día para el/la
            siguiente estudiante. Esto activa el <span style="color:#1a1a1a;font-weight:700;">semáforo NEGRO</span>
            en el sistema.
          </p>

          <!-- Tabla de datos -->
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e9ecef;border-radius:8px;overflow:hidden;font-size:14px;">
            {tabla_rows}
          </table>

          <!-- Aviso -->
          <div style="margin-top:22px;background:#fff3cd;border-left:4px solid #ffc107;
                      border-radius:0 6px 6px 0;padding:14px 18px;">
            <strong style="color:#856404;">⚠️ Acción requerida:</strong>
            <span style="color:#665010;">
              Este estudiante ha alcanzado el nivel máximo de salidas al baño el día de hoy.
              Por favor tome las medidas correspondientes.
            </span>
          </div>
        </td>
      </tr>

      <!-- FOOTER -->
      <tr>
        <td style="padding:14px 32px;background:#f8f9fa;border-top:1px solid #e9ecef;text-align:center;">
          <p style="margin:0;color:#aaa;font-size:12px;">
            TechCare —
            <a href="https://servicios.ana-hn.org:437" style="color:#aaa;text-decoration:none;">
              servicios.ana-hn.org
            </a>
            &nbsp;·&nbsp; Mensaje automático, no responder.
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""

        msg = EmailMultiAlternatives(
            subject    = asunto,
            body       = texto,
            from_email = from_email,
            to         = to_email,
        )
        msg.attach_alternative(html, 'text/html')
        msg.send()

        salida.notificado = True
        salida.save(update_fields=['notificado'])

        # Campanita global (toast) para los mismos destinatarios del email
        msg_bell = f"⚫ Alerta Negra — {salida.alumno} ({salida.grado} Grupo {salida.grupo})"
        for dest in dest_qs:
            try:
                _crear_notif_global(dest.user, msg_bell, modulo='salidas_bano', tipo='alerta', enviar_correo=False)
            except Exception:
                pass
    except Exception as e:
        print(f'[salidas_bano] ERROR email negro:', e)


# ══════════════════════════════════════════════════════════════════════════════
# Vistas de coordinador: Períodos Escolares
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def periodos_view(request):
    if not _es_coordinador_sb(request.user):
        return HttpResponseForbidden()

    edit_id = request.GET.get('editar')
    instancia = get_object_or_404(PeriodoEscolar, pk=edit_id) if edit_id else None

    if request.method == 'POST':
        accion = request.POST.get('accion', '')

        if accion == 'eliminar':
            if not _puede_eliminar_salidas(request.user):
                messages.error(request, 'Permiso de eliminación no activo o expirado.')
                return redirect('salidas_bano:periodos')
            pid = request.POST.get('periodo_id')
            PeriodoEscolar.objects.filter(pk=pid).delete()
            messages.success(request, 'Período eliminado.')
            return redirect('salidas_bano:periodos')

        if not _puede_editar_salidas(request.user):
            messages.error(request, 'No tienes permiso de edición en Salidas Baño.')
            return redirect('salidas_bano:periodos')
        form = PeriodoEscolarForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Período guardado correctamente.')
            return redirect('salidas_bano:periodos')
    else:
        form = PeriodoEscolarForm(instance=instancia)

    periodos = PeriodoEscolar.objects.all().order_by('-anio', '-parcial')
    return render(request, 'salidas_bano/periodos.html', {
        'form':        form,
        'periodos':    periodos,
        'instancia':   instancia,
        'nav_home_url': '/',
        'es_coordinador': True,
    })


# ══════════════════════════════════════════════════════════════════════════════
# Vistas de coordinador: Maestros – Clases
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def maestros_clases_view(request):
    if not _es_coordinador_sb(request.user):
        return HttpResponseForbidden()

    # Construir opciones de grado con etiquetas modernas (7mo–11vo)
    _AREA_LABELS = [('colegio', 'Colegio'), ('bachillerato', 'Bachillerato')]
    grados_para_mc = {}
    for _ak, _alabel in _AREA_LABELS:
        _gs = sorted(set(a['grado'] for a in _alumnos_sqlserver(_ak) if a['grado']))
        _gs_extra = list(MaestroClase.objects.filter(area=_ak)
                         .values_list('grado', flat=True).distinct())
        _gs = sorted(set(_gs) | set(_gs_extra))
        if _gs:
            _dm = GRADO_DISPLAY.get(_ak, {})
            grados_para_mc[_alabel] = [(_g, _dm.get(_g, _g)) for _g in _gs]

    edit_id = request.GET.get('editar')
    instancia = get_object_or_404(MaestroClase, pk=edit_id) if edit_id else None

    if request.method == 'POST':
        accion = request.POST.get('accion', '')

        if accion == 'eliminar':
            if not _puede_eliminar_salidas(request.user):
                messages.error(request, 'Permiso de eliminación no activo o expirado.')
                return redirect('salidas_bano:maestros_clases')
            mid = request.POST.get('mc_id')
            MaestroClase.objects.filter(pk=mid).delete()
            messages.success(request, 'Asignación eliminada.')
            return redirect('salidas_bano:maestros_clases')

        if not _puede_editar_salidas(request.user):
            messages.error(request, 'No tienes permiso de edición en Salidas Baño.')
            return redirect('salidas_bano:maestros_clases')
        form = MaestroClaseForm(request.POST, instance=instancia, grado_choices=grados_para_mc)
        if form.is_valid():
            form.save()
            messages.success(request, 'Asignación guardada correctamente.')
            return redirect('salidas_bano:maestros_clases')
    else:
        form = MaestroClaseForm(instance=instancia, grado_choices=grados_para_mc)

    # Mapeo combinado para mostrar etiquetas en la tabla
    _display_all = {}
    for _ak in ('colegio', 'bachillerato'):
        _display_all.update(GRADO_DISPLAY.get(_ak, {}))

    asignaciones = list(
        MaestroClase.objects.select_related('maestro').order_by('area', 'grado', 'maestro__first_name')
    )
    for mc in asignaciones:
        parts = [g.strip() for g in mc.grado.split(',')]
        mc.grado_display = ', '.join(_display_all.get(p, p) for p in parts)

    return render(request, 'salidas_bano/maestros_clases.html', {
        'form':          form,
        'asignaciones':  asignaciones,
        'instancia':     instancia,
        'nav_home_url':  '/',
        'es_coordinador': True,
    })
