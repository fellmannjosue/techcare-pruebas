# <--- hecho por claude code: Sistema Salidas Baño — vistas completas
import json
from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections
from django.db.models import Q
from django.utils.html import escape
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import MaestroClase, SalidaBano, NotificacionSalida
from conducta.models import PeriodoEscolarConducta   # <--- hecho por claude code (06-nov-2026): Período Escolar GENERAL
from .forms import MaestroClaseForm

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

# ── Ámbitos: dos pantallas independientes sobre el mismo módulo ──────────────
# <--- hecho por claude code: el Colegio (7mo-11vo) y el CFP comparten sistema
# (semáforo, notificaciones, historial) pero NO comparten alumnos ni permisos.
# En CFP el eje no es el grado sino el CURSO, y la llave del alumno es PersonaID.
AMBITOS = {
    'colegio': {
        'label':       'Colegio',
        'areas':       [('colegio', 'Colegio'), ('bachillerato', 'Bachillerato')],
        'grp_maestro': 'control baños col',
        'grp_coord':   'control baño coord',
        'label_grado': 'Grado',
        'label_grupo': 'Grupo',
        'url_name':    'salidas_bano:index',
    },
    'cfp': {
        'label':       'CFP',
        'areas':       [('cfp', 'CFP')],
        'grp_maestro': 'control baños cfp',
        'grp_coord':   'control baño coord cfp',
        'label_grado': 'Curso',
        'label_grupo': 'Jornada',
        'url_name':    'salidas_bano:index_cfp',
    },
}


def _ambito_de_area(area):
    """El área dice a qué pantalla pertenece un registro."""
    return 'cfp' if area == 'cfp' else 'colegio'


def _alumnos_cfp():
    """Participantes de CFP desde SQL Server, con el MISMO shape que los del colegio.

    Sale de la misma BD (`padres_sqlserver`) que usa Notas CFP, pero por curso:
    la llave es PersonaID y el 'grado' es el curso (tc.Descripcion).
    """
    from cfp.views import CURSOS_CFP          # importado aquí para no acoplar al importar el módulo
    if not CURSOS_CFP:
        return []
    try:
        marcas = ','.join(['%s'] * len(CURSOS_CFP))
        sql = f"""
          SELECT
            ip.PersonaID,
            LTRIM(RTRIM(
              ISNULL(d.Nombre1,'')   + ' ' + ISNULL(d.Nombre2,'') + ' ' +
              ISNULL(d.Apellido1,'') + ' ' + ISNULL(d.Apellido2,''))) AS Nombre,
            tc.Descripcion AS Curso
          FROM tblEdcIngrPrevisto ip
            INNER JOIN tblPrsDtosGen  d  ON d.PersonaID  = ip.PersonaID
            INNER JOIN tblEdcTipoCrso tc ON tc.TipoCrsoID = ip.TipoCursoID
          WHERE ip.Año = %s AND tc.Descripcion IN ({marcas})
          ORDER BY tc.Descripcion, Nombre
        """
        with connections['padres_sqlserver'].cursor() as cursor:
            cursor.execute(sql, [date.today().year] + CURSOS_CFP)
            rows = cursor.fetchall()
        return [
            {
                'ingr_egr_id': int(row[0]),
                'nombre':      ' '.join((row[1] or '').split()),
                'grado':       (row[2] or '').strip(),   # el curso hace de "grado"
                'grupo':       '',                       # CFP no separa grupos en SQL Server
            }
            for row in rows
        ]
    except Exception as e:
        print('[salidas_bano] ERROR SQL Server (cfp):', e)
        return []


def _alumnos_area(area):
    """Alumnos del área, venga del colegio o del CFP."""
    return _alumnos_cfp() if area == 'cfp' else _alumnos_sqlserver(area)


def _display_grados(area):
    """Mapa {valor: etiqueta} para mostrar el grado (colegio) o el curso (CFP)."""
    if area == 'cfp':
        from cfp.views import CURSO_LABEL
        return CURSO_LABEL
    return GRADO_DISPLAY.get(area, {})


def _get_periodo_activo(area):
    """Retorna el periodo activo para el área dada (o None)."""
    # Busca periodo activo que aplique al área o sea 'ambos'
    # <--- hecho por claude code (06-nov-2026, pedido del usuario): el período sale del Período Escolar GENERAL
    # (Configuración Académica, solo superusuario). Colegio y Bachillerato usan el de 'colegio' o 'ambas'; CFP solo 'cfp'.
    p = _periodos_del_area(area).filter(activo=True).order_by('-anio', '-parcial').first()
    # <--- hecho por claude code (06-nov-2026): con «Salidas al Baño» cerrado en el período, no hay período para registrar
    return p if (p and p.modulo_abierto('sal')) else None


def _areas_periodo(area):
    """Áreas del Período Escolar general que le sirven a un área de Salidas."""
    return ['cfp'] if area == 'cfp' else ['colegio', 'ambas']


def _periodos_del_area(area):
    return PeriodoEscolarConducta.objects.filter(area__in=_areas_periodo(area))


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

# <--- hecho por claude code (seguridad 05-nov-2026): únicas áreas que existen en SalidaBano; lo que mande el navegador fuera de esta lista se rechaza.
_AREAS_VALIDAS = ('colegio', 'bachillerato', 'cfp')


def _pk(valor):
    """<--- hecho por claude code (seguridad 05-nov-2026): id del navegador como entero (antes 'abc' en ?editar= u obj_id daba 500)."""
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return None


def _puede_acceder(user, ambito='colegio'):
    """Superusuario o los grupos del ámbito (colegio y CFP son independientes)."""
    # <--- hecho por claude code (seguridad 05-nov-2026): sin is_staff — es el MISMO criterio del menú (nav_salidas_bano / nav_salidas_bano_cfp en core/context_processors.py). Antes cualquier staff de otro módulo veía la nómina de menores de los dos ámbitos y el coordinador de un ámbito operaba en el otro.
    if user.is_superuser:
        return True
    if ambito == 'cfp':
        # <--- hecho por claude code (05-nov-2026): con «Salidas al baño CFP» oculto en Programas activos, tampoco pasan las rutas compartidas (guardar, regreso, pendientes) con área CFP.
        from constance import config as _cfg
        from core.programas import ocultos
        if 'salidas_cfp' in ocultos(_cfg):
            return False
    cfg = AMBITOS.get(ambito, AMBITOS['colegio'])
    return user.groups.filter(name__in=[cfg['grp_maestro'], cfg['grp_coord']]).exists()


def _cursos_cfp_permitidos(user, es_coord):
    """<--- hecho por claude code (seguridad 05-nov-2026): cursos CFP que puede tocar el usuario (None = todos), la MISMA regla con la que index filtra la nómina: coordinador de salidas CFP, director CFP y superusuario ven todo; el instructor, solo sus InstructorCurso."""
    if es_coord:
        return None
    from cfp.views import _cursos_instructor          # importado aquí para no acoplar al importar el módulo
    return _cursos_instructor(user)


def _es_coordinador_sb(user, ambito='colegio'):
    """¿Puede gestionar períodos y maestros-clases de ESE ámbito?"""
    if user.is_superuser:
        return True
    cfg = AMBITOS.get(ambito, AMBITOS['colegio'])
    return user.groups.filter(name=cfg['grp_coord']).exists()


def _puede_editar_salidas(user):
    """Superuser y coordinadores con salidas_editar=True (o sin registro CoordPermiso)."""
    if user.is_superuser:
        return True
    try:
        return user.coord_permiso.salidas_editar
    except ObjectDoesNotExist:   # <--- hecho por claude code (seguridad 05-nov-2026): solo "sin fila" conserva la compatibilidad; antes CUALQUIER error daba permiso
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
    except ObjectDoesNotExist:   # <--- hecho por claude code (seguridad 05-nov-2026): solo "sin fila" conserva la compatibilidad; antes CUALQUIER error daba permiso
        return True  # sin registro = sin restricción


# ══════════════════════════════════════════════════════════════════════════════
# Vista principal
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def index(request, ambito='colegio'):
    # <--- hecho por claude code: misma pantalla para dos ámbitos (Colegio y CFP);
    # cada uno con sus propios alumnos, períodos, maestros-clases y permisos.
    cfg = AMBITOS.get(ambito, AMBITOS['colegio'])
    if not _puede_acceder(request.user, ambito):
        return HttpResponseForbidden()

    es_coord   = _es_coordinador_sb(request.user, ambito)
    # <--- hecho por claude code (seguridad 05-nov-2026): las pestañas Períodos / Maestros-Clases solo las opera la coordinación del ámbito; antes el POST de un maestro se ignoraba con un 200 silencioso (y además consultaba SQL Server).
    if request.method == 'POST' and not es_coord:
        return HttpResponseForbidden()
    tab_activo = request.GET.get('tab', 'salidas')   # salidas | maestros | historial

    # Áreas que existen en este ámbito (Colegio+Bachillerato, o solo CFP)
    areas       = cfg['areas']
    areas_claves = [a for a, _ in areas]

    # ── Grados/cursos disponibles para el form Maestros-Clases ─────────────────
    grados_para_mc = {}   # {'Colegio': ['1ero','2do',...], 'CFP': ['Panadero',...]}
    for _ak, _alabel in areas:
        _gs = sorted(set(a['grado'] for a in _alumnos_area(_ak) if a['grado']))
        # Agrega grados ya guardados en MaestroClase para ese área
        _gs_extra = list(MaestroClase.objects.filter(area=_ak)
                         .values_list('grado', flat=True).distinct())
        _gs = sorted(set(_gs) | set(_gs_extra))
        if _gs:
            _dm = _display_grados(_ak)
            grados_para_mc[_alabel] = [(_g, _dm.get(_g, _g)) for _g in _gs]

    # ── Manejar POSTs del coordinador ──────────────────────────────────────────
    # <--- hecho por claude code: el ámbito acota tanto las áreas elegibles como los
    # objetos editables ('ambos' = Colegio+Bachillerato, no existe en CFP).
    areas_admin  = areas_claves + ([] if ambito == 'cfp' else ['ambos'])
    area_choices = [(a, l) for a, l in MaestroClase.AREA_CHOICES if a in areas_admin]

    mc_form      = MaestroClaseForm(grado_choices=grados_para_mc, area_choices=area_choices)

    if request.method == 'POST' and es_coord:
        accion = request.POST.get('accion', '')

        # <--- hecho por claude code (06-nov-2026): los períodos ya no se administran aquí (Período Escolar general, solo superusuario)
        if accion == 'eliminar_mc' and not _puede_eliminar_salidas(request.user):
            messages.error(request, 'Permiso de eliminación no activo o expirado.')
            return redirect(f"{request.path}?tab=maestros")

        if accion == 'guardar_mc':
            edit_mid = _pk(request.POST.get('edit_id'))   # <--- hecho por claude code (seguridad 05-nov-2026): id no numérico ya no da 500
            inst = (MaestroClase.objects.filter(pk=edit_mid, area__in=areas_admin).first()
                    if edit_mid else None)
            mc_form = MaestroClaseForm(request.POST, instance=inst,
                                       grado_choices=grados_para_mc, area_choices=area_choices)
            if mc_form.is_valid():
                mc_form.save()
                messages.success(request, 'Asignación guardada.')
                return redirect(f'{request.path}?tab=maestros')
            tab_activo = 'maestros'

        elif accion == 'eliminar_mc':
            MaestroClase.objects.filter(pk=_pk(request.POST.get('obj_id')),
                                        area__in=areas_admin).delete()
            messages.success(request, 'Asignación eliminada.')
            return redirect(f'{request.path}?tab=maestros')

    # Editar desde GET
    if request.GET.get('editar_mc') and es_coord:
        inst = MaestroClase.objects.filter(pk=_pk(request.GET['editar_mc']),
                                           area__in=areas_admin).first()
        if inst:
            mc_form = MaestroClaseForm(instance=inst, grado_choices=grados_para_mc,
                                       area_choices=area_choices)
        tab_activo = 'maestros'

    # ── Datos de salidas (tab principal) ───────────────────────────────────────
    # <--- hecho por claude code: el área pedida tiene que pertenecer al ámbito, si no
    # desde /salidas-bano/cfp/?area=colegio se verían los alumnos del colegio.
    area      = request.GET.get('area', areas_claves[0])
    if area not in areas_claves:
        area = areas_claves[0]
    grado_sel = request.GET.get('grado', '')

    periodo = None
    alumnos_por_grado = {}
    grados            = []
    salidas_hoy       = {}
    clases_por_grado  = {}
    error             = ''

    periodo = _get_periodo_activo(area)
    if not periodo:
        # <--- hecho por claude code (06-nov-2026): el período es el general (o el módulo está cerrado en él)
        from conducta.periodo_modulos import periodo_que_cierra, mensaje_cerrado
        _pc = periodo_que_cierra('sal', 'colegio') if area != 'cfp' else None
        error = (mensaje_cerrado('sal', _pc) if _pc else
                 f'No hay Período Escolar activo para {dict(areas).get(area, area)}.')

    todos = _alumnos_area(area)
    # <--- hecho por claude code: en CFP un instructor ve SOLO sus cursos asignados
    # (InstructorCurso). El coordinador de salidas, el director CFP y el superusuario
    # siguen viendo todos los cursos. Antes las instructoras veían los 5 cursos.
    # <--- hecho por claude code (seguridad 05-nov-2026): la regla se calcula UNA vez con _cursos_cfp_permitidos (la misma de guardar, pendientes, regreso e historial) y se aplica a la nómina y a salidas_hoy (abajo).
    _mis_cursos = _cursos_cfp_permitidos(request.user, es_coord) if area == 'cfp' else None   # None = ve todos
    if _mis_cursos is not None:
        todos = [a for a in todos if a['grado'] in _mis_cursos]
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
        _hoy_qs = SalidaBano.objects.filter(periodo=periodo, area=area, fecha=date.today())
        # <--- hecho por claude code (seguridad 05-nov-2026): en CFP el instructor recibe solo las salidas de hoy de SUS cursos, como su nómina; antes data-v11 traía la clase, el comentario, el maestro y el id de la última salida de hoy de TODOS los participantes del CFP.
        if _mis_cursos is not None:
            _hoy_qs = _hoy_qs.filter(grado__in=_mis_cursos)
        _raw = {}
        for s in (_hoy_qs
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
    # <--- hecho por claude code: 'ambos' es Colegio+Bachillerato; en CFP no aplica.
    _areas_mc = [area] if area == 'cfp' else [area, 'ambos']
    _mc_qs = MaestroClase.objects.filter(area__in=_areas_mc)
    # <--- hecho por claude code: SOLO en Colegio un maestro normal ve únicamente SUS
    # clases; el coordinador ve todas. CFP es caso aparte: ahí las instructoras siguen
    # viendo todas las clases (así lo pidió el usuario).
    if not es_coord and area != 'cfp':
        _mc_qs = _mc_qs.filter(maestro=request.user)
    for mc in (_mc_qs
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
    # <--- hecho por claude code: cada ámbito solo administra SUS áreas (ver areas_admin)
    mc_lista       = (MaestroClase.objects.filter(area__in=areas_admin)
                      .select_related('maestro')
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
        # Nombres modernos de grado (7mo-11vo) o nombre del curso en CFP
        'grados_display':    [(g, _display_grados(area).get(g, g)) for g in grados],
        # <--- hecho por claude code: contexto del ámbito (Colegio / CFP)
        'ambito':            ambito,
        'ambito_label':      cfg['label'],
        'label_grado':       cfg['label_grado'],
        'label_grupo':       cfg['label_grupo'],
        'es_cfp':            ambito == 'cfp',
        # Coordinador
        'mc_form':           mc_form,
        'mc_lista':          mc_lista,
        'editar_mc_id':      request.GET.get('editar_mc', ''),
    }
    # <--- hecho por claude code (13-oct-2026): pestaña Historial (todas las salidas con filtros)
    ctx.update(_historial_datos(request, ambito, areas))
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
    if not hasattr(data, 'get'):   # <--- hecho por claude code (seguridad 05-nov-2026): un JSON que no es objeto daba 500
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)

    # <--- hecho por claude code (seguridad 05-nov-2026): todo llega como texto y acotado al largo de la columna (un número o un texto enorme daban 500)
    def _txt(clave, largo=None):
        v = data.get(clave)
        v = '' if v is None else str(v).strip()
        return v[:largo] if largo else v

    periodo_id   = _pk(data.get('periodo_id'))
    ingr_egr_id  = _pk(data.get('ingr_egr_id'))
    alumno       = _txt('alumno', 120)
    grado        = _txt('grado', 160)
    grupo        = _txt('grupo', 20)
    area         = _txt('area', 20)
    clase        = _txt('clase', 80)
    hora_salida  = _txt('hora_salida')
    hora_regreso = _txt('hora_regreso')
    comentario   = _txt('comentario')

    if not all([periodo_id, ingr_egr_id, alumno, area, clase, hora_salida]):
        return JsonResponse({'ok': False, 'error': 'Faltan campos requeridos.'}, status=400)
    if not 0 < ingr_egr_id < 2 ** 31:   # <--- hecho por claude code (seguridad 05-nov-2026): fuera del rango de la columna INT daba 500
        return JsonResponse({'ok': False, 'error': 'Alumno inválido.'}, status=400)

    # <--- hecho por claude code: el área viene del navegador, así que hay que
    # comprobar que el usuario pertenezca a ESE ámbito (antes no se validaba).
    # <--- hecho por claude code (seguridad 05-nov-2026): y que sea un área real (un área inventada caía en el ámbito Colegio y se guardaba igual).
    if area not in _AREAS_VALIDAS:
        return JsonResponse({'ok': False, 'error': 'Sin permiso para esta área.'}, status=403)
    ambito = _ambito_de_area(area)
    if not _puede_acceder(request.user, ambito):
        return JsonResponse({'ok': False, 'error': 'Sin permiso para esta área.'}, status=403)

    # <--- hecho por claude code (seguridad 05-nov-2026): en CFP el instructor registra solo en SUS cursos (la misma regla con la que index le arma la nómina).
    if area == 'cfp':
        _mis_cursos = _cursos_cfp_permitidos(request.user, _es_coordinador_sb(request.user, ambito))
        if _mis_cursos is not None and grado not in _mis_cursos:
            return JsonResponse({'ok': False, 'error': 'Este curso no está asignado a tu usuario.'}, status=403)

    periodo = get_object_or_404(PeriodoEscolarConducta, pk=periodo_id)
    # <--- hecho por claude code (seguridad 05-nov-2026; 06-nov-2026 período general): el período tiene que servirle a ESA área (Colegio/Bachillerato = 'colegio'/'ambas'; CFP = 'cfp').
    if periodo.area not in _areas_periodo(area) or not periodo.modulo_abierto('sal'):   # <--- + módulo cerrado (06-nov-2026)
        return JsonResponse({'ok': False, 'error': 'El período no corresponde a esta área.'}, status=403)

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
    if count_hoy >= 3 and not _es_coordinador_sb(request.user, ambito):
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
# API: alumnos que siguen AFUERA (para la alerta de regreso sin registrar)
# ══════════════════════════════════════════════════════════════════════════════

# <--- hecho por claude code: minutos que se toleran antes de avisar al maestro
MINUTOS_ALERTA_REGRESO = 5


@login_required
@require_GET
def salidas_pendientes(request):
    """Alumnos con una salida abierta (sin hora de regreso) del día de hoy.

    Se consulta al SERVIDOR y no al estado del navegador: así el aviso desaparece
    aunque el regreso lo haya registrado otro maestro desde otra pantalla.
    """
    area = request.GET.get('area', '')
    # <--- hecho por claude code (seguridad 05-nov-2026): el área tiene que ser real (antes un área vacía o inventada caía en el ámbito Colegio)
    if area not in _AREAS_VALIDAS:
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    ambito = _ambito_de_area(area)
    if not _puede_acceder(request.user, ambito):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)

    periodo = _get_periodo_activo(area)
    if not periodo:
        return JsonResponse({'ok': True, 'pendientes': [], 'minutos_alerta': MINUTOS_ALERTA_REGRESO})

    # <--- hecho por claude code: el proyecto va con USE_TZ=False, así que
    # timezone.localtime() revienta ("naive datetime"). Se usa la hora local directa.
    ahora = datetime.now()
    ahora_min = ahora.hour * 60 + ahora.minute
    items = []
    _qs = SalidaBano.objects.filter(periodo=periodo, area=area, fecha=date.today(),
                                    hora_regreso__isnull=True)
    # <--- hecho por claude code (seguridad 05-nov-2026): en CFP la instructora recibe el aviso solo de SUS cursos, como su nómina en index (antes le sonaba y le salía el nombre de alumnos de otros cursos). En Colegio el aviso sigue siendo de toda el área: cualquier maestro cierra el regreso de otro.
    if area == 'cfp':
        _mis_cursos = _cursos_cfp_permitidos(request.user, _es_coordinador_sb(request.user, ambito))
        if _mis_cursos is not None:
            _qs = _qs.filter(grado__in=_mis_cursos)
    for s in (_qs
              .select_related('maestro')
              .order_by('hora_salida')):
        if not s.hora_salida:
            continue
        transcurridos = ahora_min - (s.hora_salida.hour * 60 + s.hora_salida.minute)
        if transcurridos < 0:      # marca futura (reloj desfasado): se ignora
            continue
        items.append({
            'id':          s.id,
            'ingr_egr_id': s.ingr_egr_id,
            'alumno':      s.alumno,
            'grado':       s.grado,
            'grupo':       s.grupo,
            'clase':       s.clase,
            'hora_salida': s.hora_salida.strftime('%H:%M'),
            'minutos':     transcurridos,
            'maestro':     (s.maestro.get_full_name() or s.maestro.username) if s.maestro else '',
        })
    return JsonResponse({
        'ok': True,
        'pendientes': items,
        'minutos_alerta': MINUTOS_ALERTA_REGRESO,
        'ahora': ahora.strftime('%H:%M'),
    })


# ══════════════════════════════════════════════════════════════════════════════
# API: registrar regreso
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@require_POST
def marcar_regreso(request, pk):
    # <--- hecho por claude code (seguridad 05-nov-2026): quien no es de ningún ámbito recibe 403 ANTES de buscar el registro (antes 404/403 delataba qué ids existen).
    if not (_puede_acceder(request.user, 'colegio') or _puede_acceder(request.user, 'cfp')):
        return JsonResponse({'ok': False, 'error': 'Sin permiso para esta área.'}, status=403)
    salida = get_object_or_404(SalidaBano, pk=pk)
    # <--- hecho por claude code (seguridad 05-nov-2026): el ámbito sale del REGISTRO (salida.area) y se exige el grupo de ese ámbito; antes cualquier usuario con sesión marcaba el regreso de cualquier salida de Colegio o CFP. No se exige autoría: el historial muestra maestros del ámbito marcando regresos de salidas ajenas (la alerta de pendientes lo permite).
    if not _puede_acceder(request.user, _ambito_de_area(salida.area)):
        return JsonResponse({'ok': False, 'error': 'Sin permiso para esta área.'}, status=403)
    # <--- hecho por claude code (seguridad 05-nov-2026): en CFP, solo salidas de los cursos del instructor (la misma regla de su nómina y de su aviso de pendientes).
    if salida.area == 'cfp':
        _mis_cursos = _cursos_cfp_permitidos(request.user, _es_coordinador_sb(request.user, 'cfp'))
        if _mis_cursos is not None and salida.grado not in _mis_cursos:
            return JsonResponse({'ok': False, 'error': 'Este curso no está asignado a tu usuario.'}, status=403)
    # <--- hecho por claude code (seguridad 05-nov-2026): solo el regreso de salidas de HOY (la pantalla y el aviso solo muestran las de hoy); antes se podía reescribir la hora de cualquier salida vieja. El historial no tiene ningún regreso marcado otro día.
    if salida.fecha != date.today():
        return JsonResponse({'ok': False, 'error': 'Solo se registra el regreso de las salidas de hoy.'}, status=403)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    if not hasattr(data, 'get'):   # <--- hecho por claude code (seguridad 05-nov-2026): un JSON que no es objeto daba 500
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)
    hora_regreso = data.get('hora_regreso') or ''
    try:
        hr = datetime.strptime(str(hora_regreso).strip(), '%H:%M').time()
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
    # <--- hecho por claude code (seguridad 05-nov-2026): quien no coordina ningún ámbito recibe 403 ANTES de buscar el registro (antes 404/403 delataba qué ids existen).
    if not (_es_coordinador_sb(request.user, 'colegio') or _es_coordinador_sb(request.user, 'cfp')):
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    # <--- hecho por claude code: el coordinador de un ámbito no borra salidas del otro
    salida = get_object_or_404(SalidaBano, pk=pk)
    if not _es_coordinador_sb(request.user, _ambito_de_area(salida.area)):
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    if not _puede_eliminar_salidas(request.user):
        return JsonResponse({'ok': False, 'error': 'Permiso de eliminación no activo o expirado.'}, status=403)

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
    # <--- hecho por claude code (seguridad 05-nov-2026): el área es OBLIGATORIA y se exige el grupo de su ámbito. Antes cualquier usuario con sesión leía el historial de cualquier menor y, sin ?area=, mezclaba CFP (PersonaID) con Colegio (IngrEgrID). El JS siempre manda ?area=.
    if area not in _AREAS_VALIDAS:
        return JsonResponse({'ok': False, 'error': 'Sin permiso para esta área.', 'salidas': []}, status=403)
    ambito = _ambito_de_area(area)
    if not _puede_acceder(request.user, ambito):
        return JsonResponse({'ok': False, 'error': 'Sin permiso para esta área.', 'salidas': []}, status=403)
    periodo  = _get_periodo_activo(area)

    qs = SalidaBano.objects.filter(ingr_egr_id=ingr_egr_id)
    # <--- hecho por claude code: hay que filtrar por área — en CFP este ID es el
    # PersonaID y en el colegio el IngrEgrID: son espacios distintos y pueden chocar.
    qs = qs.filter(area=area)
    if periodo:
        qs = qs.filter(periodo=periodo)
    # <--- hecho por claude code (seguridad 05-nov-2026): el maestro ve lo que registró él (la regla de la pestaña Historial) + las salidas de HOY del alumno, que ya comparte la pantalla (semáforo del día, aviso de pendientes); la coordinación del ámbito ve todo. En CFP, además, solo los cursos del instructor.
    if not _es_coordinador_sb(request.user, ambito):
        qs = qs.filter(Q(maestro=request.user) | Q(fecha=date.today()))
        if area == 'cfp':
            _mis_cursos = _cursos_cfp_permitidos(request.user, False)
            if _mis_cursos is not None:
                qs = qs.filter(grado__in=_mis_cursos)
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

        # <--- hecho por claude code: CFP tiene su propia etiqueta y su propio destinatario
        area_label  = {'colegio': 'Colegio', 'bachillerato': 'Bachillerato',
                       'cfp': 'CFP'}.get(salida.area, salida.area)
        hora_str    = salida.hora_salida.strftime('%H:%M') if salida.hora_salida else '—'
        maestro_str = salida.maestro.get_full_name() or salida.maestro.username if salida.maestro else '—'
        comentario  = salida.comentario or '—'
        from accounts.models import DestinatarioEmail
        from core.utils_notifications import crear_notificacion as _crear_notif_global
        campo_mod = {'bachillerato': 'salidas_negro_bach',
                     'cfp':          'salidas_negro_cfp'}.get(salida.area, 'salidas_negro_col')
        dest_qs = DestinatarioEmail.objects.filter(**{campo_mod: True}).select_related('user')
        extras    = [d.user.email for d in dest_qs if d.user.email]
        to_email  = list(set(extras))
        from_email = settings.DEFAULT_FROM_EMAIL

        # <--- hecho por claude code: en CFP el eje es el curso y no hay grupo
        # <--- hecho por claude code (seguridad 05-nov-2026): en la parte HTML todo dato va escapado (alumno, grado, grupo, clase y comentario llegan del navegador; antes se podía inyectar HTML/enlaces en el correo a coordinación).
        if salida.area == 'cfp':
            etiqueta_ubic = 'Curso'
            ubicacion     = f'{area_label} · {salida.grado}'
            ubicacion_html = f'{escape(area_label)} · <strong>{escape(salida.grado)}</strong>'
        else:
            etiqueta_ubic = 'Grado / Grupo'
            ubicacion     = f'{area_label} {salida.grado} — Grupo {salida.grupo}'
            ubicacion_html = f'{escape(area_label)} <strong>{escape(salida.grado)}</strong> — Grupo {escape(salida.grupo)}'

        asunto = f'⚫ ALERTA NEGRA — {salida.alumno}  |  {ubicacion}'

        # ── Texto plano ───────────────────────────────────────────────────────
        texto = (
            f'ALERTA NEGRA — SISTEMA SALIDAS AL BAÑO\n'
            f'{"="*45}\n\n'
            f'El/la siguiente estudiante ha alcanzado su 4ª salida al baño el día de hoy.\n\n'
            f'  Alumno/a    : {salida.alumno}\n'
            f'  {etiqueta_ubic:<12}: {ubicacion}\n'
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
            row('👤', 'Alumno/a',       f'<strong style="font-size:15px;">{escape(salida.alumno)}</strong>', shade=True)
          + row('🏫', etiqueta_ubic,    ubicacion_html)
          + row('📖', 'Clase / Maestro', escape(salida.clase),  shade=True)
          + row('🕐', 'Hora de salida', escape(hora_str))
          + row('👩‍🏫', 'Registrado por', escape(maestro_str),    shade=True)
          + row('💬', 'Comentario',     escape(comentario))
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
# Vistas de coordinador
# ══════════════════════════════════════════════════════════════════════════════

# <--- hecho por claude code (seguridad 05-nov-2026): las pantallas sueltas Períodos y Maestros-Clases son del ámbito COLEGIO (no tienen ruta CFP; CFP usa las pestañas de su index). Solo ven, crean, editan y borran registros de Colegio/Bachillerato/Ambos; antes el coordinador de Colegio tocaba los de CFP.
_AMBITO_PANTALLAS_SUELTAS = 'colegio'
_AREAS_ADMIN_COLEGIO      = ['colegio', 'bachillerato', 'ambos']


def _area_choices_colegio():
    return [(a, l) for a, l in MaestroClase.AREA_CHOICES if a in _AREAS_ADMIN_COLEGIO]


@login_required
def maestros_clases_view(request):
    if not _es_coordinador_sb(request.user, _AMBITO_PANTALLAS_SUELTAS):
        return HttpResponseForbidden()
    area_choices = _area_choices_colegio()   # <--- hecho por claude code (seguridad 05-nov-2026): sin CFP en el desplegable de Área

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
    # <--- hecho por claude code (seguridad 05-nov-2026): solo asignaciones del ámbito (una de CFP da 404) y un id no numérico ya no da 500
    instancia = (get_object_or_404(MaestroClase, pk=_pk(edit_id), area__in=_AREAS_ADMIN_COLEGIO)
                 if edit_id else None)

    if request.method == 'POST':
        accion = request.POST.get('accion', '')

        if accion == 'eliminar':
            if not _puede_eliminar_salidas(request.user):
                messages.error(request, 'Permiso de eliminación no activo o expirado.')
                return redirect('salidas_bano:maestros_clases')
            mid = _pk(request.POST.get('mc_id'))
            MaestroClase.objects.filter(pk=mid, area__in=_AREAS_ADMIN_COLEGIO).delete()
            messages.success(request, 'Asignación eliminada.')
            return redirect('salidas_bano:maestros_clases')

        if not _puede_editar_salidas(request.user):
            messages.error(request, 'No tienes permiso de edición en Salidas Baño.')
            return redirect('salidas_bano:maestros_clases')
        form = MaestroClaseForm(request.POST, instance=instancia, grado_choices=grados_para_mc,
                                area_choices=area_choices)
        if form.is_valid():
            form.save()
            messages.success(request, 'Asignación guardada correctamente.')
            return redirect('salidas_bano:maestros_clases')
    else:
        form = MaestroClaseForm(instance=instancia, grado_choices=grados_para_mc, area_choices=area_choices)

    # Mapeo combinado para mostrar etiquetas en la tabla
    _display_all = {}
    for _ak in ('colegio', 'bachillerato'):
        _display_all.update(GRADO_DISPLAY.get(_ak, {}))

    asignaciones = list(
        MaestroClase.objects.filter(area__in=_AREAS_ADMIN_COLEGIO)   # <--- hecho por claude code (seguridad 05-nov-2026): sin las de CFP
        .select_related('maestro').order_by('area', 'grado', 'maestro__first_name')
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


# ══════════════════════════════════════════════════════════════════════════════
# Historial general (pestaña "Historial") — hecho por claude code (13-oct-2026)
# Coordinación y superusuario ven todas las salidas del ámbito; el maestro, las que registró él.
# Siempre filtrado por ÁREA del ámbito (en CFP el ID es PersonaID: espacios distintos).
# ══════════════════════════════════════════════════════════════════════════════
_HIST_LIMITE = 500
_SEMAFOROS = [('verde', 'Verde'), ('amarillo', 'Amarillo'), ('rojo', 'Rojo'), ('negro', 'Negro')]


def _historial_qs(request, ambito, areas):
    """(queryset filtrado, filtros elegidos). Filtros por GET con prefijo h_."""
    from django.db.models import Q
    claves = [a for a, _ in areas]
    G = request.GET
    f = {k: (G.get('h_' + k) or '').strip() for k in ('periodo', 'desde', 'hasta', 'area', 'grado', 'semaforo', 'q', 'maestro', 'pendiente')}
    qs = SalidaBano.objects.filter(area__in=claves).select_related('maestro', 'periodo')
    if not _es_coordinador_sb(request.user, ambito):
        qs = qs.filter(maestro=request.user)
        f['maestro'] = ''
    if f['periodo'].isdigit():
        qs = qs.filter(periodo_id=int(f['periodo']))
    for campo, k in (('fecha__gte', 'desde'), ('fecha__lte', 'hasta')):
        try:
            qs = qs.filter(**{campo: datetime.strptime(f[k], '%Y-%m-%d').date()})
        except ValueError:
            f[k] = ''
    if f['area'] in claves:
        qs = qs.filter(area=f['area'])
    else:
        f['area'] = ''
    if f['grado']:   # valor "area|grado": en Colegio y Bachillerato los grados se llaman igual
        _a, _, _g = f['grado'].partition('|')
        if _g and _a not in claves:   # <--- hecho por claude code (seguridad 05-nov-2026): el área del filtro tiene que ser del ámbito
            f['grado'] = ''
        else:
            qs = qs.filter(area=_a, grado=_g) if _g else qs.filter(grado=_a)
    if f['semaforo'] in dict(_SEMAFOROS):
        qs = qs.filter(semaforo=f['semaforo'])
    if f['q']:
        qs = qs.filter(Q(alumno__icontains=f['q']) | Q(clase__icontains=f['q']) | Q(comentario__icontains=f['q']))
    if f['maestro'].isdigit():
        qs = qs.filter(maestro_id=int(f['maestro']))
    if f['pendiente'] == '1':
        qs = qs.filter(hora_regreso__isnull=True)
    return qs.order_by('-fecha', '-hora_salida', '-id'), f


def _grado_label(area, grado):
    return _display_grados(area).get(grado, grado) if grado else ''


def _historial_datos(request, ambito, areas):
    from django.db.models import Count
    qs, f = _historial_qs(request, ambito, areas)
    claves = [a for a, _ in areas]
    total = qs.count()
    filas = list(qs[:_HIST_LIMITE])
    for s in filas:
        s.grado_label = _grado_label(s.area, s.grado)
    por_sem = dict(qs.values_list('semaforo').annotate(n=Count('id')).values_list('semaforo', 'n'))
    duraciones = [d for d in (s.duracion_minutos for s in filas) if d is not None]
    top = list(qs.values('ingr_egr_id', 'area', 'alumno', 'grado', 'grupo').annotate(n=Count('id')).order_by('-n', 'alumno')[:10])
    for t in top:
        t['grado_label'] = _grado_label(t['area'], t['grado'])
    base = SalidaBano.objects.filter(area__in=claves)
    if not _es_coordinador_sb(request.user, ambito):
        base = base.filter(maestro=request.user)
    grados = sorted({(a, g) for a, g in base.values_list('area', 'grado').distinct() if g})
    maestros = []
    if _es_coordinador_sb(request.user, ambito):
        ids = base.exclude(maestro__isnull=True).values_list('maestro_id', flat=True).distinct()
        maestros = [(u.id, u.get_full_name() or u.username) for u in get_user_model().objects.filter(id__in=ids).order_by('first_name', 'last_name')]
    filtros_activos = any(f.values())
    return {
        'h_f':          f,
        'h_filas':      filas,
        'h_total':      total,
        'h_limite':     _HIST_LIMITE,
        'h_recortado':  total > _HIST_LIMITE,
        'h_alumnos':    qs.values('area', 'ingr_egr_id').distinct().count(),
        'h_sin_regreso': qs.filter(hora_regreso__isnull=True).count(),
        'h_promedio':   round(sum(duraciones) / len(duraciones)) if duraciones else None,
        'h_semaforos':  [(k, l, por_sem.get(k, 0)) for k, l in _SEMAFOROS],
        'h_top':        top,
        'h_periodos':   PeriodoEscolarConducta.objects.filter(area__in=(['cfp'] if ambito == 'cfp' else ['colegio', 'ambas'])).order_by('-anio', '-parcial'),   # <--- período general (06-nov-2026)
        'h_grados':     [(f'{a}|{g}', _grado_label(a, g) + (f' · {dict(areas).get(a, a)}' if len(areas) > 1 else '')) for a, g in grados],
        'h_maestros':   maestros,
        'h_semaforo_choices': _SEMAFOROS,
        'h_filtrado':   filtros_activos,
        'h_query':      request.GET.urlencode(),
    }


@login_required
@require_GET
def historial_exportar(request, ambito='colegio'):
    """Excel del historial con los mismos filtros de la pestaña."""
    if not _puede_acceder(request.user, ambito):
        return HttpResponseForbidden()
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from django.http import HttpResponse
    cfg = AMBITOS.get(ambito, AMBITOS['colegio'])
    qs, f = _historial_qs(request, ambito, cfg['areas'])
    wb = Workbook(); ws = wb.active; ws.title = 'Historial'
    ws.append([f'Historial de salidas al baño · {cfg["label"]}'])
    ws['A1'].font = Font(bold=True, size=13)
    ws.append([f'Generado {datetime.now():%d/%m/%Y %H:%M} por {request.user.get_full_name() or request.user.username}'])
    ws.append([])
    enc = ['Fecha', 'Salida', 'Regreso', 'Minutos', 'Alumno', cfg['label_grado'], cfg['label_grupo'], 'Área', 'Clase', 'Semáforo', 'Registró', 'Comentario']
    ws.append(enc)
    for c in ws[4]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='0F766E'); c.alignment = Alignment(horizontal='center')
    for s in qs:
        ws.append([s.fecha, s.hora_salida.strftime('%H:%M') if s.hora_salida else '', s.hora_regreso.strftime('%H:%M') if s.hora_regreso else '',
                   s.duracion_minutos, s.alumno, _grado_label(s.area, s.grado), s.grupo, s.get_area_display(), s.clase,
                   s.get_semaforo_display(), (s.maestro.get_full_name() or s.maestro.username) if s.maestro else '', s.comentario])
        # <--- hecho por claude code (seguridad 05-nov-2026): openpyxl convierte en FÓRMULA todo texto que empieza con "=" (un comentario "=HYPERLINK(...)" se ejecutaba al abrir el Excel de coordinación); se fuerza a texto.
        for _c in ws[ws.max_row]:
            if _c.data_type == 'f':
                _c.data_type = 's'
        ws.cell(row=ws.max_row, column=1).number_format = 'DD/MM/YYYY'
    for col, ancho in zip('ABCDEFGHIJKL', (12, 8, 8, 9, 34, 12, 10, 13, 22, 11, 24, 40)):
        ws.column_dimensions[col].width = ancho
    ws.freeze_panes = 'A5'
    resp = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="salidas_bano_{ambito}_{date.today():%Y%m%d}.xlsx"'
    wb.save(resp)
    return resp
