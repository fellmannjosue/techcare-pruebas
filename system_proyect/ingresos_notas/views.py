# <--- hecho por claude code: Ingreso de Notas — escribe en el sistema académico legacy (Test2)
"""Programa "Ingresos de Notas": tres formularios (notas, asistencias, hábitos)
separados por área educativa.

CADENA DE LLAVES DEL LEGACY (validada contra Test2: 118 FK reales, 0 huérfanos):

    tblPrsDtosGen  PersonaID
      └─ tblPrsTipo        IngrEgrID
           └─ tblEdcArea   AreaID          (+ tblEdcDescripAreaEdc = el ÁREA)
                └─ tblEdcEjecCrso EjecCrsoID   (+ tblEdcCrso = grado y grupo)
                     └─ tblEdcMaterias<rama>   (+ tblEdcDescripMateria = la CLASE)
                          └─ tblEdcEval<rama>  (una fila por PARCIAL)

Dos ramas vivas y simétricas: BL (PrimariaBL, ColegioBL) y Acad (Bachillerato,
Colegio). La rama `Col1` está muerta (0 registros del año en curso) y no se toca.

SOBRE ESCRIBIR: las filas de evaluación ya existen (se crean al matricular), así
que ingresar una nota es un UPDATE de una sola columna. El legacy audita con
`trg_Audit_tblEdcEval*`, pero SOLO en UPDATE; por eso además se guarda todo en
`EscrituraNota` (MySQL). Nunca se hace DELETE.
"""
import json
from datetime import date
from functools import wraps

from django.conf import settings
from django.db import connections
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST

from .models import EscrituraNota

# ── Ramas del legacy (mismas columnas en las dos) ────────────────────────────
RAMAS = {
    'bl': {
        'materias': 'tblEdcMateriasBL', 'pk_materia': 'EdcMateriaBLID',
        'eval': 'tblEdcEvalBL',         'pk_eval': 'EdcEvalBLID',
    },
    'acad': {
        'materias': 'tblEdcMateriasAcad', 'pk_materia': 'EdcMateriaAcadID',
        'eval': 'tblEdcEvalAcad',         'pk_eval': 'EdcEvalAcadID',
    },
}

# `descr` es el texto exacto de tblEdcDescripAreaEdc.Descripcion.
# <--- hecho por claude code: `grupo` = quién puede ingresar notas de esa área.
# Cada encargada ve SOLO la suya (Lidia bilingüe, Mayleen colegio).
AREAS = {
    'primaria_bl':  {'label': 'Primaria Bilingüe', 'descr': 'PrimariaBL',
                     'rama': 'bl',   'grupo': 'ingreso notas bilingue'},
    'colegio_bl':   {'label': 'Colegio Bilingüe',  'descr': 'ColegioBL',
                     'rama': 'bl',   'grupo': 'ingreso notas bilingue'},
    'colegio':      {'label': 'Colegio',           'descr': 'Colegio',
                     'rama': 'acad', 'grupo': 'ingreso notas colegio'},
    'bachillerato': {'label': 'Bachillerato',      'descr': 'Bachillerato',
                     'rama': 'acad', 'grupo': 'ingreso notas colegio'},
}

# <--- hecho por claude code: la base guarda "1ero/2do/3ero" pero en Colegio y
# Bachillerato esos años se llaman 7mo-11vo. Solo es la ETIQUETA: el valor que
# viaja a las consultas sigue siendo el de la base.
GRADO_DISPLAY = {
    'colegio':      {'1ero': '7mo',  '1': '7mo',
                     '2do':  '8vo',  '2': '8vo',
                     '3ero': '9no',  '3': '9no'},
    'bachillerato': {'1ero': '10mo', '1': '10mo',
                     '2do':  '11vo', '2': '11vo',
                     '3ero': '12vo', '3': '12vo'},
}


def _grado_label(area_key, grado):
    return GRADO_DISPLAY.get(area_key, {}).get(grado, grado)


# Los 20 Cuadro son evaluaciones normales y SE USAN: hay clases de este año que
# llegan hasta Cuadro19 (Ciencias Naturales, Inglés, Lectura, Matemática) y otras
# que solo usan 2. Por eso la cantidad de columnas se detecta POR CLASE.
CUADROS_MINIMOS = 6      # nunca se muestran menos, aunque la clase esté vacía
MAX_CUADROS = 20

# <--- hecho por claude code: las "Especial 1/2/3" son ExamenFinal2/3/4, NO los
# últimos cuadros. Confirmado con los datos: Cuadro19 tiene notas reales este año
# y ExamenFinal2/3/4 están vacíos en esas mismas clases.
EVAL_CONTINUA = [
    ('ExamenFinal2', 'Especial 1'),
    ('ExamenFinal3', 'Especial 2'),
    ('ExamenFinal4', 'Especial 3'),
]
# Las Especial solo aplican de 7mo en adelante.
AREAS_EVAL_CONTINUA = {'colegio_bl', 'colegio', 'bachillerato'}

# <--- hecho por claude code: `Nivelacion` se oculta a pedido del usuario (no se usa).
# La columna sigue en la base con sus datos históricos; solo deja de mostrarse y de
# poder escribirse desde aquí.
COLUMNAS_EXTRA = [
    ('Recup1',      'Recup 1'),
    ('Recup2',      'Recup 2'),
    ('Recup3',      'Recup 3'),
]
PARCIALES = [1, 2, 3, 4]


def _columnas(area_key, n_cuadros):
    """Columnas de la rejilla, en orden, como [(columna, etiqueta), ...].

    Orden pedido: cuadros → Especial 1-3 → examen final → recuperaciones.
    """
    n = max(1, min(n_cuadros, MAX_CUADROS))
    cols = [(f'Cuadro{i}', f'C{i}') for i in range(1, n + 1)]
    if area_key in AREAS_EVAL_CONTINUA:
        cols += EVAL_CONTINUA
    cols.append(('ExamenFinal', 'Ex. Final'))
    return cols + COLUMNAS_EXTRA


def _columnas_escribibles(area_key):
    """Lista blanca para escribir: todos los cuadros, no solo los visibles.

    El nombre de la columna se concatena al SQL, así que nada fuera de aquí se toca.
    """
    cols = [f'Cuadro{i}' for i in range(1, MAX_CUADROS + 1)] + ['ExamenFinal']
    if area_key in AREAS_EVAL_CONTINUA:
        cols += [c for c, _ in EVAL_CONTINUA]
    return cols + [c for c, _ in COLUMNAS_EXTRA]


# ── Acceso ───────────────────────────────────────────────────────────────────
# Grupo paraguas: da acceso a TODAS las áreas (para quien lleve más de una).
GRP_NOTAS = 'ingreso notas'


def areas_permitidas(user):
    """Áreas que este usuario puede ingresar. Superuser y el grupo paraguas ven todas."""
    if user.is_superuser:
        return list(AREAS)
    suyos = set(user.groups.values_list('name', flat=True))
    if GRP_NOTAS in suyos:
        return list(AREAS)
    return [k for k, v in AREAS.items() if v['grupo'] in suyos]


def _puede(user):
    return bool(areas_permitidas(user))


def notas_required(view):
    @wraps(view)
    def _w(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{settings.LOGIN_URL}?next={request.path}')
        if not _puede(request.user):
            return HttpResponseForbidden('No tienes permiso para el ingreso de notas.')
        return view(request, *args, **kwargs)
    return _w


def _area_valida(request, area):
    """El área tiene que existir Y estar permitida para este usuario.

    Sin esto, quien lleva Colegio podría leer o escribir notas de Bilingüe
    poniendo `?area=primaria_bl` a mano en la URL.
    """
    return area in AREAS and area in areas_permitidas(request.user)


# ── Consultas al legacy ──────────────────────────────────────────────────────
def _anio_actual():
    return date.today().year


def _grados(area_key, anio):
    """Grados y grupos con materias registradas en esa área y año."""
    cfg, rama = AREAS[area_key], RAMAS[AREAS[area_key]['rama']]
    sql = f"""
        SELECT DISTINCT cr.CrsoNumero, cr.GrupoNumero
        FROM dbo.{rama['materias']} m
          JOIN dbo.tblEdcEjecCrso ec        ON ec.EjecCrsoID = m.EjecCrsoID
          JOIN dbo.tblEdcArea a             ON a.AreaID = ec.AreaID
          JOIN dbo.tblEdcDescripAreaEdc da  ON da.DescrAreaEdcID = a.DescrAreaEdcID
          JOIN dbo.tblEdcCrso cr            ON cr.CrsoID = ec.CrsoID
        WHERE da.Descripcion = %s AND DATEPART(yy, cr.FechaInicio) = %s
          AND ec.Desertor = 0
        ORDER BY cr.CrsoNumero, cr.GrupoNumero
    """
    with connections['padres_sqlserver'].cursor() as c:
        c.execute(sql, [cfg['descr'], anio])
        return [{'grado': (g or '').strip(), 'grupo': (gr or '').strip(),
                 'label': _grado_label(area_key, (g or '').strip())}
                for g, gr in c.fetchall()]


def _clases(area_key, anio, grado, grupo):
    """Materias que se imparten a ese grado/grupo."""
    cfg, rama = AREAS[area_key], RAMAS[AREAS[area_key]['rama']]
    sql = f"""
        SELECT dm.EdcDescrMateriaID, dm.Descripcion, COUNT(*) AS alumnos
        FROM dbo.{rama['materias']} m
          JOIN dbo.tblEdcEjecCrso ec        ON ec.EjecCrsoID = m.EjecCrsoID
          JOIN dbo.tblEdcArea a             ON a.AreaID = ec.AreaID
          JOIN dbo.tblEdcDescripAreaEdc da  ON da.DescrAreaEdcID = a.DescrAreaEdcID
          JOIN dbo.tblEdcCrso cr            ON cr.CrsoID = ec.CrsoID
          JOIN dbo.tblEdcDescripMateria dm  ON dm.EdcDescrMateriaID = m.EdcDescrMateriaID
        WHERE da.Descripcion = %s AND DATEPART(yy, cr.FechaInicio) = %s
          AND cr.CrsoNumero = %s AND cr.GrupoNumero = %s AND ec.Desertor = 0
        GROUP BY dm.EdcDescrMateriaID, dm.Descripcion
        ORDER BY dm.Descripcion
    """
    with connections['padres_sqlserver'].cursor() as c:
        c.execute(sql, [cfg['descr'], anio, grado, grupo])
        return [{'id': (i or '').strip(), 'nombre': (d or '').strip(), 'alumnos': n}
                for i, d, n in c.fetchall()]


def _cuadros_de_la_clase(area_key, anio, grado, grupo, materia_id, parcial):
    """<--- hecho por claude code: cuántas columnas de cuadro mostrar para ESTA clase.

    Cada materia usa una cantidad distinta (de 2 a 19 según los datos del año), así
    que se busca el último cuadro con nota y se agrega uno en blanco para seguir
    capturando. Nunca menos de CUADROS_MINIMOS.
    """
    cfg, rama = AREAS[area_key], RAMAS[AREAS[area_key]['rama']]
    sel = ", ".join(f"MAX(CASE WHEN ev.Cuadro{i} IS NOT NULL THEN {i} ELSE 0 END)"
                    for i in range(1, MAX_CUADROS + 1))
    sql = f"""
        SELECT {sel}
        FROM dbo.{rama['eval']} ev
          JOIN dbo.{rama['materias']} m     ON m.{rama['pk_materia']} = ev.{rama['pk_materia']}
          JOIN dbo.tblEdcEjecCrso ec        ON ec.EjecCrsoID = m.EjecCrsoID
          JOIN dbo.tblEdcArea a             ON a.AreaID = ec.AreaID
          JOIN dbo.tblEdcDescripAreaEdc da  ON da.DescrAreaEdcID = a.DescrAreaEdcID
          JOIN dbo.tblEdcCrso cr            ON cr.CrsoID = ec.CrsoID
        WHERE da.Descripcion = %s AND DATEPART(yy, cr.FechaInicio) = %s
          AND cr.CrsoNumero = %s AND cr.GrupoNumero = %s
          AND m.EdcDescrMateriaID = %s AND ev.Parcial = %s AND ec.Desertor = 0
    """
    with connections['padres_sqlserver'].cursor() as c:
        c.execute(sql, [cfg['descr'], anio, grado, grupo, materia_id, parcial])
        fila = c.fetchone()
    usado = max([v or 0 for v in fila]) if fila else 0
    return max(CUADROS_MINIMOS, min(usado + 1, MAX_CUADROS))


def _alumnos_con_notas(area_key, anio, grado, grupo, materia_id, parcial, n_cuadros):
    """Filas de la rejilla: un alumno por fila con sus notas de ese parcial."""
    cfg, rama = AREAS[area_key], RAMAS[AREAS[area_key]['rama']]
    columnas = _columnas(area_key, n_cuadros)
    cols = [c for c, _ in columnas]
    sel_notas = ', '.join(f'ev.{c}' for c in cols)
    sql = f"""
        SELECT m.{rama['pk_materia']} AS materia_id,
               ev.{rama['pk_eval']}   AS eval_id,
               d.PersonaID,
               LTRIM(RTRIM(ISNULL(d.Nombre1,'') + ' ' + ISNULL(d.Nombre2,'') + ' ' +
                           ISNULL(d.Apellido1,'') + ' ' + ISNULL(d.Apellido2,''))) AS nombre,
               ISNULL(d.NumeroID,'') AS identidad,
               ev.NoParticipa,
               {sel_notas},
               ISNULL(d.Sexo,'') AS Sexo
        FROM dbo.{rama['materias']} m
          JOIN dbo.tblEdcEjecCrso ec        ON ec.EjecCrsoID = m.EjecCrsoID
          JOIN dbo.tblEdcArea a             ON a.AreaID = ec.AreaID
          JOIN dbo.tblEdcDescripAreaEdc da  ON da.DescrAreaEdcID = a.DescrAreaEdcID
          JOIN dbo.tblEdcCrso cr            ON cr.CrsoID = ec.CrsoID
          JOIN dbo.tblPrsTipo t             ON t.IngrEgrID = a.IngrEgrID
          JOIN dbo.tblPrsDtosGen d          ON d.PersonaID = t.PersonaID
          LEFT JOIN dbo.{rama['eval']} ev   ON ev.{rama['pk_materia']} = m.{rama['pk_materia']}
                                           AND ev.Parcial = %s
        WHERE da.Descripcion = %s AND DATEPART(yy, cr.FechaInicio) = %s
          AND cr.CrsoNumero = %s AND cr.GrupoNumero = %s
          AND m.EdcDescrMateriaID = %s AND ec.Desertor = 0
        -- <--- hecho por claude code: primero las niñas, luego los varones, y dentro
        -- de cada grupo alfabético por NOMBRE (no por apellido). Sexo viene como
        -- 'femenino'/'masculino' y puede ser NULL: esos van al final.
        ORDER BY CASE WHEN d.Sexo = 'femenino' THEN 0
                      WHEN d.Sexo = 'masculino' THEN 1
                      ELSE 2 END,
                 d.Nombre1, d.Nombre2, d.Apellido1
    """
    with connections['padres_sqlserver'].cursor() as c:
        c.execute(sql, [parcial, cfg['descr'], anio, grado, grupo, materia_id])
        filas = []
        for r in c.fetchall():
            notas = {col: r[6 + i] for i, col in enumerate(cols)}
            filas.append({
                'materia_id': r[0], 'eval_id': r[1], 'persona_id': r[2],
                'nombre': ' '.join((r[3] or '').split()),
                'identidad': (r[4] or '').strip(),
                'no_participa': bool(r[5]),
                'sexo': (r[6 + len(cols)] or '').strip(),
                'notas': {k: ('' if v is None else float(v)) for k, v in notas.items()},
            })
        return filas


# ── Pantallas ────────────────────────────────────────────────────────────────
@notas_required
def index(request):
    # <--- hecho por claude code: solo sus áreas; si pide otra, cae a la primera suya
    permitidas = areas_permitidas(request.user)
    area_key = request.GET.get('area') or permitidas[0]
    if area_key not in permitidas:
        area_key = permitidas[0]
    # Las columnas ya no se deciden aquí: dependen de la clase y las manda api_alumnos.
    ctx = {
        'areas': [(k, AREAS[k]['label']) for k in permitidas],
        'area_sel': area_key,
        'area_label': AREAS[area_key]['label'],
        'anio': _anio_actual(),
        'parciales': PARCIALES,
        'max_cuadros': MAX_CUADROS,
        'error': '',
    }
    try:
        ctx['grados'] = _grados(area_key, ctx['anio'])
    except Exception as e:
        ctx['grados'] = []
        ctx['error'] = f'No se pudo leer el sistema académico: {e}'
    return render(request, 'ingresos_notas/notas.html', ctx)


@notas_required
@require_GET
def api_clases(request):
    area = request.GET.get('area', '')
    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)
    try:
        clases = _clases(area, _anio_actual(),
                         request.GET.get('grado', ''), request.GET.get('grupo', ''))
        return JsonResponse({'ok': True, 'clases': clases})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=200)


@notas_required
@require_GET
def api_alumnos(request):
    area = request.GET.get('area', '')
    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)
    pedido = (request.GET.get('cuadros') or '').strip()
    try:
        parcial = int(request.GET.get('parcial') or 1)
        n_pedido = int(pedido) if pedido else None
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Parámetros inválidos'}, status=400)
    if parcial not in PARCIALES:
        return JsonResponse({'ok': False, 'error': 'Parcial inválido'}, status=400)

    anio  = _anio_actual()
    grado = request.GET.get('grado', '')
    grupo = request.GET.get('grupo', '')
    mat   = request.GET.get('materia', '')
    try:
        # <--- hecho por claude code: sin `cuadros` explícito, la clase decide cuántos
        auto = _cuadros_de_la_clase(area, anio, grado, grupo, mat, parcial)
        n_cuadros = auto if n_pedido is None else max(1, min(n_pedido, MAX_CUADROS))
        filas = _alumnos_con_notas(area, anio, grado, grupo, mat, parcial, n_cuadros)
        return JsonResponse({'ok': True, 'alumnos': filas,
                             'n_cuadros': n_cuadros, 'n_cuadros_auto': auto,
                             'columnas': [{'key': k, 'label': l}
                                          for k, l in _columnas(area, n_cuadros)]})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=200)


@notas_required
@require_POST
def api_guardar(request):
    """Escribe UNA celda. UPDATE si la fila del parcial existe; si no, la crea.

    Nunca hace DELETE y solo toca la columna pedida, que además tiene que estar
    en la lista blanca de `_columnas_validas`.
    """
    try:
        body = json.loads(request.body or b'{}')
        area       = body.get('area', '')
        materia_id = int(body.get('materia_id'))
        parcial    = int(body.get('parcial'))
        columna    = (body.get('columna') or '').strip()
        crudo      = (body.get('valor') or '').strip()
        alumno     = (body.get('alumno') or '')[:200]
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)
    if parcial not in PARCIALES:
        return JsonResponse({'ok': False, 'error': 'Parcial inválido'}, status=400)
    if columna not in _columnas_escribibles(area):
        return JsonResponse({'ok': False, 'error': f'Columna no permitida: {columna}'}, status=400)

    # Celda vacía = borrar el valor (NULL), no poner un cero.
    if crudo == '':
        valor = None
    else:
        try:
            valor = round(float(crudo.replace(',', '')), 2)
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'La nota debe ser un número'}, status=400)
        if not (0 <= valor <= 100):
            return JsonResponse({'ok': False, 'error': 'La nota debe estar entre 0 y 100'}, status=400)

    cfg, rama = AREAS[area], RAMAS[AREAS[area]['rama']]
    usuario = (request.user.get_username() or '')[:50]

    try:
        with connections['padres_sqlserver'].cursor() as c:
            c.execute(f"""SELECT {rama['pk_eval']}, {columna} FROM dbo.{rama['eval']}
                          WHERE {rama['pk_materia']} = %s AND Parcial = %s""",
                      [materia_id, parcial])
            fila = c.fetchone()

            if fila:
                eval_id, antes = fila
                c.execute(f"""UPDATE dbo.{rama['eval']}
                              SET {columna} = %s, Usuario = %s, FchaReg = GETDATE()
                              WHERE {rama['pk_eval']} = %s""",
                          [valor, usuario, eval_id])
                accion = 'update'
            else:
                antes = None
                c.execute(f"""INSERT INTO dbo.{rama['eval']}
                              ({rama['pk_materia']}, Parcial, {columna}, Usuario, FchaReg, Fecha)
                              VALUES (%s, %s, %s, %s, GETDATE(), GETDATE())""",
                          [materia_id, parcial, valor, usuario])
                c.execute(f"""SELECT {rama['pk_eval']} FROM dbo.{rama['eval']}
                              WHERE {rama['pk_materia']} = %s AND Parcial = %s""",
                          [materia_id, parcial])
                r = c.fetchone()
                eval_id = r[0] if r else None
                accion = 'insert'
    except Exception as e:
        return JsonResponse({'ok': False,
                             'error': f'El sistema académico rechazó el cambio: {e}'}, status=200)

    # Bitácora del lado de TechCare (el trigger del legacy solo cubre UPDATE)
    EscrituraNota.objects.create(
        usuario=request.user, area=area, rama=cfg['rama'], tabla=rama['eval'],
        materia_id=materia_id, eval_id=eval_id, parcial=parcial, columna=columna,
        valor_antes='' if antes is None else str(antes),
        valor_nuevo='' if valor is None else str(valor),
        accion=accion, alumno=alumno)

    return JsonResponse({'ok': True, 'eval_id': eval_id, 'accion': accion,
                         'valor': '' if valor is None else valor})
