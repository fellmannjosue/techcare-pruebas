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
        'record': 'tblEdcRecordHabitosBL', 'pk_record': 'EdcRecHabitosBLID',
        'ausencias': 'tblEdcAusenciasBL', 'pk_ausencia': 'EdcAusenciasBLID',
    },
    'acad': {
        'materias': 'tblEdcMateriasAcad', 'pk_materia': 'EdcMateriaAcadID',
        'eval': 'tblEdcEvalAcad',         'pk_eval': 'EdcEvalAcadID',
        'record': 'tblEdcRecordHabitosAcad', 'pk_record': 'EdcRecHabitosAcadID',
        'ausencias': 'tblEdcAusenciasAcad', 'pk_ausencia': 'EdcAusenciasAcadID',
    },
}

# <--- hecho por claude code: Asistencias. Una fila = UNA clase de UN alumno en UNA
# fecha (el grano es materia + fecha, no el día completo). OJO: estas filas tienen
# EFECTO ECONÓMICO, alimentan los recargos por no asistencia.
#   · `DescrAusenciasID`         → el tipo (tblEdcDescripAusencias, 4 opciones)
#   · `EdcDescrAusenciasRazonID` → la razón (tblEdcDescripAusenciasRazon, 162 activas)
# La razón va SIEMPRE por ID: está en el 100 % de las filas, mientras que el texto
# libre `Razon` solo en dos tercios. `RAZON_PENDIENTE` es la que ya usa la
# encargada cuando todavía no sabe el motivo.
RAZON_PENDIENTE = 4          # "aa-falta por ingresar"
AUSENCIA_TIPO_DEFECTO = 4    # "No se presentó"

# <--- hecho por claude code: Record de Hábitos. El catálogo (tblEdcDescripHabitos)
# marca con Academ/AcademBL los 6 que usan Colegio y Bilingüe; `Voc` es de CFP.
# "Tareas" va en su propio tab porque se registra a diario y en cantidad.
HABITO_TAREAS = 3
HABITOS_RECORD = [
    (18, 'Espíritu de Trabajo'),
    (19, 'Orden y Presentación'),
    (20, 'Moralidad'),
    (21, 'Sociabilidad'),
    (23, 'ExpresionesADH'),
]
# Una tarea NO tiene identificador propio en el legacy: solo Fecha, Puntos y
# Comentario. Varias tareas del mismo día se distinguen ÚNICAMENTE por el orden
# de inserción (la PK). Verificado: dentro de una clase y un día todos los
# alumnos tienen la misma cantidad, así que la posición N es la misma tarea
# para todos. Por eso se llena una tarea completa antes de crear la siguiente.
PUNTOS_MAX = 10

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

# <--- hecho por claude code: las "Especial 1/2/3" se guardan en Cuadro18/19/20.
# Verificado contra Access con la misma fila (Biología, Bachillerato 10mo A, P1):
# Cuadro1..4 = 39/80/80/95, Cuadro18 = 70 y Cuadro19 = 64, que Access rotula
# Especial1 y Especial2. ExamenFinal2/3/4 están vacíos y NO se usan.
EVAL_CONTINUA = [
    ('Cuadro18', 'Especial 1'),
    ('Cuadro19', 'Especial 2'),
    ('Cuadro20', 'Especial 3'),
]
# Las Especial solo aplican de 7mo en adelante.
AREAS_EVAL_CONTINUA = {'colegio_bl', 'colegio', 'bachillerato'}

# <--- hecho por claude code: donde hay Especial, los cuadros numerados llegan
# hasta 17: del 18 al 20 son las Especial y se pintan aparte, sin duplicarse.
MAX_CUADROS_CON_ESPECIAL = 17

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
    tope = MAX_CUADROS_CON_ESPECIAL if area_key in AREAS_EVAL_CONTINUA else MAX_CUADROS
    n = max(1, min(n_cuadros, tope))
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
    # <--- hecho por claude code: donde hay Especial no se cuentan 18-20 como cuadros,
    # o una clase con Especial contestada diría que usa 20 cuadros.
    tope = MAX_CUADROS_CON_ESPECIAL if area_key in AREAS_EVAL_CONTINUA else MAX_CUADROS
    sel = ", ".join(f"MAX(CASE WHEN ev.Cuadro{i} IS NOT NULL THEN {i} ELSE 0 END)"
                    for i in range(1, tope + 1))
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
    return max(CUADROS_MINIMOS, min(usado + 1, tope))


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


# ── Record de Hábitos: Tareas ────────────────────────────────────────────────
def _alumnos_de_la_clase(area_key, anio, grado, grupo, materia_id):
    """<--- hecho por claude code: alumnos de la clase SIN notas (para hábitos).

    Mismo recorrido de llaves que la rejilla de notas y el mismo orden (primero
    las niñas, luego los varones, alfabético por nombre).
    """
    cfg, rama = AREAS[area_key], RAMAS[AREAS[area_key]['rama']]
    sql = f"""
        SELECT m.{rama['pk_materia']},
               LTRIM(RTRIM(ISNULL(d.Nombre1,'') + ' ' + ISNULL(d.Nombre2,'') + ' ' +
                           ISNULL(d.Apellido1,'') + ' ' + ISNULL(d.Apellido2,''))) AS nombre,
               ISNULL(d.NumeroID,'') AS identidad
        FROM dbo.{rama['materias']} m
          JOIN dbo.tblEdcEjecCrso ec        ON ec.EjecCrsoID = m.EjecCrsoID
          JOIN dbo.tblEdcArea a             ON a.AreaID = ec.AreaID
          JOIN dbo.tblEdcDescripAreaEdc da  ON da.DescrAreaEdcID = a.DescrAreaEdcID
          JOIN dbo.tblEdcCrso cr            ON cr.CrsoID = ec.CrsoID
          JOIN dbo.tblPrsTipo t             ON t.IngrEgrID = a.IngrEgrID
          JOIN dbo.tblPrsDtosGen d          ON d.PersonaID = t.PersonaID
        WHERE da.Descripcion = %s AND DATEPART(yy, cr.FechaInicio) = %s
          AND cr.CrsoNumero = %s AND cr.GrupoNumero = %s
          AND m.EdcDescrMateriaID = %s AND ec.Desertor = 0
        ORDER BY CASE WHEN d.Sexo = 'femenino' THEN 0
                      WHEN d.Sexo = 'masculino' THEN 1
                      ELSE 2 END,
                 d.Nombre1, d.Nombre2, d.Apellido1
    """
    with connections['padres_sqlserver'].cursor() as c:
        c.execute(sql, [cfg['descr'], anio, grado, grupo, materia_id])
        return [{'materia_id': r[0], 'nombre': ' '.join((r[1] or '').split()),
                 'identidad': (r[2] or '').strip()} for r in c.fetchall()]


def _registros_del_dia(area_key, materia_ids, fecha, habito):
    """{materia_id: [(rec_id, puntos, comentario), ...]} en orden de inserción.

    El orden por PK ES la identidad de la tarea: la 2ª fila de un alumno es la
    misma tarea que la 2ª de otro (verificado: dentro de clase y día todos los
    alumnos tienen la misma cantidad de filas).
    """
    if not materia_ids:
        return {}
    rama = RAMAS[AREAS[area_key]['rama']]
    marcas = ','.join(['%s'] * len(materia_ids))
    sql = f"""
        SELECT {rama['pk_materia']}, {rama['pk_record']}, Puntos, Comentario
        FROM dbo.{rama['record']}
        WHERE EdcDescrHabitosID = %s AND CAST(Fecha AS date) = %s
          AND {rama['pk_materia']} IN ({marcas})
        ORDER BY {rama['pk_materia']}, {rama['pk_record']}
    """
    por_alumno = {}
    with connections['padres_sqlserver'].cursor() as c:
        c.execute(sql, [habito, fecha] + list(materia_ids))
        for mat, rec_id, puntos, coment in c.fetchall():
            por_alumno.setdefault(mat, []).append(
                {'rec_id': rec_id, 'puntos': puntos, 'comentario': coment or ''})
    return por_alumno


# ── Asistencias ──────────────────────────────────────────────────────────────
def _tipos_ausencia():
    """Los 4 tipos del catálogo, en el orden en que los guarda el legacy."""
    with connections['padres_sqlserver'].cursor() as c:
        c.execute("""SELECT DescrAusenciasID, Descripcion FROM dbo.tblEdcDescripAusencias
                     ORDER BY DescrAusenciasID""")
        return [{'id': r[0], 'label': r[1]} for r in c.fetchall()]


def _razones_ausencia():
    """Razones ACTIVAS. La pendiente va primero para que sea la opción por defecto."""
    with connections['padres_sqlserver'].cursor() as c:
        c.execute("""SELECT EdcDescrAusenciasRazonID, LTRIM(RTRIM(Descripcion))
                     FROM dbo.tblEdcDescripAusenciasRazon
                     WHERE Activo = 1
                     ORDER BY CASE WHEN EdcDescrAusenciasRazonID = %s THEN 0 ELSE 1 END,
                              Descripcion""", [RAZON_PENDIENTE])
        return [{'id': r[0], 'label': r[1]} for r in c.fetchall()]


def _ausencias_del_dia(area_key, materia_ids, fecha):
    """{materia_id: {...}} con la ausencia de esa clase y fecha, si existe.

    Puede haber más de una fila por alumno y día (tipos distintos); se toma la
    última registrada, que es la que el legacy muestra.
    """
    if not materia_ids:
        return {}
    rama = RAMAS[AREAS[area_key]['rama']]
    marcas = ','.join(['%s'] * len(materia_ids))
    sql = f"""
        SELECT {rama['pk_materia']}, {rama['pk_ausencia']}, DescrAusenciasID,
               EdcDescrAusenciasRazonID, ISNULL(Otros, '')
        FROM dbo.{rama['ausencias']}
        WHERE CAST(Fecha AS date) = %s AND {rama['pk_materia']} IN ({marcas})
        ORDER BY {rama['pk_materia']}, {rama['pk_ausencia']}
    """
    por_alumno = {}
    with connections['padres_sqlserver'].cursor() as c:
        c.execute(sql, [fecha] + list(materia_ids))
        for mat, aus_id, tipo, razon, otros in c.fetchall():
            por_alumno[mat] = {'aus_id': aus_id, 'tipo': tipo,
                               'razon': razon, 'otros': otros or ''}
    return por_alumno


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
        'hoy': date.today().isoformat(),   # valor inicial del tab Tareas
        # <--- hecho por claude code: cambiar de área recarga la página; `tab` la
        # devuelve al formulario donde estaba y no siempre a Notas.
        'tab_sel': request.GET.get('tab', ''),
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


# ── APIs del tab Tareas ──────────────────────────────────────────────────────
def _fecha_valida(texto):
    """'2026-07-30' -> date, o None si no sirve."""
    try:
        return date.fromisoformat((texto or '').strip())
    except ValueError:
        return None


@notas_required
@require_GET
def api_tareas(request):
    """Alumnos de la clase con la tarea N de esa fecha (puntos y comentario)."""
    area = request.GET.get('area', '')
    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)

    fecha = _fecha_valida(request.GET.get('fecha'))
    if not fecha:
        return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)
    try:
        pedida = int(request.GET.get('tarea') or 0)
    except ValueError:
        pedida = 0

    try:
        alumnos = _alumnos_de_la_clase(
            area, _anio_actual(), request.GET.get('grado', ''),
            request.GET.get('grupo', ''), request.GET.get('materia', ''))
        ids = [a['materia_id'] for a in alumnos]
        registros = _registros_del_dia(area, ids, fecha, HABITO_TAREAS)

        # Cuántas tareas hay ya ese día y si la clase está pareja
        cuentas = [len(registros.get(i, [])) for i in ids] or [0]
        n_tareas = max(cuentas)
        desiguales = bool(ids) and min(cuentas) != n_tareas

        # Sin tarea pedida se abre la última con datos; si no hay ninguna, la 1
        tarea = pedida if pedida > 0 else max(1, n_tareas)
        for a in alumnos:
            filas = registros.get(a['materia_id'], [])
            r = filas[tarea - 1] if len(filas) >= tarea else None
            a['rec_id']     = r['rec_id'] if r else None
            a['puntos']     = '' if r is None else r['puntos']
            a['comentario'] = '' if r is None else r['comentario']
            a['previas']    = len(filas)      # para no desalinear al insertar
        return JsonResponse({'ok': True, 'alumnos': alumnos, 'tarea': tarea,
                             'n_tareas': n_tareas, 'desiguales': desiguales,
                             'puntos_max': PUNTOS_MAX})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=200)


@notas_required
@require_POST
def api_tarea_guardar(request):
    """Guarda los puntos o el comentario de UNA tarea de UN alumno.

    Si la fila existe es UPDATE. Si no, se INSERTA — pero solo cuando al alumno
    le faltaba exactamente esa tarea (`previas == tarea - 1`); si le faltan
    tareas anteriores se rechaza, porque insertarla la correría de posición y
    quedaría pegada a la tarea equivocada.
    """
    try:
        body = json.loads(request.body or b'{}')
        area       = body.get('area', '')
        materia_id = int(body.get('materia_id'))
        tarea      = int(body.get('tarea'))
        campo      = (body.get('campo') or '').strip()
        crudo      = (body.get('valor') or '').strip()
        alumno     = (body.get('alumno') or '')[:200]
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    fecha = _fecha_valida(body.get('fecha'))
    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)
    if not fecha:
        return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)
    if tarea < 1:
        return JsonResponse({'ok': False, 'error': 'Tarea inválida'}, status=400)
    if campo not in ('puntos', 'comentario'):
        return JsonResponse({'ok': False, 'error': 'Campo no permitido'}, status=400)

    puntos = None
    if campo == 'puntos':
        if crudo == '':
            return JsonResponse({'ok': False,
                                 'error': 'Los puntos no pueden quedar vacíos'}, status=400)
        try:
            puntos = int(round(float(crudo)))
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'Los puntos deben ser un número'}, status=400)
        if not (0 <= puntos <= PUNTOS_MAX):
            return JsonResponse({'ok': False,
                                 'error': f'Los puntos van de 0 a {PUNTOS_MAX}'}, status=400)

    cfg, rama = AREAS[area], RAMAS[AREAS[area]['rama']]
    usuario = (request.user.get_username() or '')[:50]

    try:
        filas = _registros_del_dia(area, [materia_id], fecha, HABITO_TAREAS).get(materia_id, [])
        with connections['padres_sqlserver'].cursor() as c:
            if len(filas) >= tarea:
                actual = filas[tarea - 1]
                rec_id = actual['rec_id']
                if campo == 'puntos':
                    antes, nuevo = actual['puntos'], puntos
                    c.execute(f"""UPDATE dbo.{rama['record']}
                                  SET Puntos = %s, Usuario = %s, FchaReg = GETDATE()
                                  WHERE {rama['pk_record']} = %s""", [puntos, usuario, rec_id])
                else:
                    antes, nuevo = actual['comentario'], crudo
                    c.execute(f"""UPDATE dbo.{rama['record']}
                                  SET Comentario = %s, Usuario = %s, FchaReg = GETDATE()
                                  WHERE {rama['pk_record']} = %s""",
                              [crudo or None, usuario, rec_id])
                accion = 'update'
            else:
                if len(filas) != tarea - 1:
                    return JsonResponse(
                        {'ok': False, 'error': f'A este alumno le faltan tareas anteriores '
                                               f'(tiene {len(filas)}). Llena primero la '
                                               f'tarea {len(filas) + 1}.'}, status=200)
                if campo == 'comentario':
                    return JsonResponse(
                        {'ok': False,
                         'error': 'Pon primero los puntos y luego el comentario.'}, status=200)
                antes, nuevo = None, puntos
                c.execute(f"""INSERT INTO dbo.{rama['record']}
                              ({rama['pk_materia']}, EdcDescrHabitosID, Fecha, Puntos,
                               Usuario, FchaReg)
                              VALUES (%s, %s, %s, %s, %s, GETDATE())""",
                          [materia_id, HABITO_TAREAS, fecha, puntos, usuario])
                c.execute('SELECT CAST(SCOPE_IDENTITY() AS int)')
                r = c.fetchone()
                rec_id = r[0] if r else None
                accion = 'insert'
    except Exception as e:
        return JsonResponse({'ok': False,
                             'error': f'El sistema académico rechazó el cambio: {e}'}, status=200)

    EscrituraNota.objects.create(
        usuario=request.user, area=area, rama=cfg['rama'], tabla=rama['record'],
        materia_id=materia_id, eval_id=rec_id, parcial=0,
        columna=f'Tarea{tarea}@{fecha:%Y-%m-%d}·{campo}',
        valor_antes='' if antes is None else str(antes),
        valor_nuevo='' if nuevo is None else str(nuevo),
        accion=accion, alumno=alumno)

    return JsonResponse({'ok': True, 'rec_id': rec_id, 'accion': accion})


# ── APIs del tab Asistencias ─────────────────────────────────────────────────
@notas_required
@require_GET
def api_ausencias(request):
    """Alumnos de la clase con su ausencia de esa fecha (si la tienen)."""
    area = request.GET.get('area', '')
    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)

    fecha = _fecha_valida(request.GET.get('fecha'))
    if not fecha:
        return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

    try:
        alumnos = _alumnos_de_la_clase(
            area, _anio_actual(), request.GET.get('grado', ''),
            request.GET.get('grupo', ''), request.GET.get('materia', ''))
        registros = _ausencias_del_dia(area, [a['materia_id'] for a in alumnos], fecha)
        for a in alumnos:
            r = registros.get(a['materia_id'])
            a['aus_id'] = r['aus_id'] if r else None
            a['tipo']   = r['tipo']   if r else ''
            a['razon']  = r['razon']  if r else ''
            a['otros']  = r['otros']  if r else ''
        return JsonResponse({'ok': True, 'alumnos': alumnos,
                             'tipos': _tipos_ausencia(),
                             'razones': _razones_ausencia(),
                             'razon_pendiente': RAZON_PENDIENTE,
                             'tipo_defecto': AUSENCIA_TIPO_DEFECTO,
                             'ausentes': sum(1 for a in alumnos if a['tipo'])})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=200)


@notas_required
@require_POST
def api_ausencia_guardar(request):
    """Crea, actualiza o quita la ausencia de UN alumno en UNA fecha.

    Vaciar el tipo BORRA la fila: es la única forma de deshacer una ausencia
    puesta por error, y estas filas tienen efecto económico. Queda registrado
    en `EscrituraNota` con acción `delete`, que es el rastro que el legacy no
    guarda (sus triggers solo cubren UPDATE).
    """
    try:
        body = json.loads(request.body or b'{}')
        area       = body.get('area', '')
        materia_id = int(body.get('materia_id'))
        alumno     = (body.get('alumno') or '')[:200]
        tipo_txt   = (body.get('tipo') or '').strip()
        razon_txt  = (body.get('razon') or '').strip()
        otros      = (body.get('otros') or '').strip()[:255]
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    fecha = _fecha_valida(body.get('fecha'))
    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)
    if not fecha:
        return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

    # El tipo y la razón se validan contra el catálogo: van al SQL como enteros,
    # pero aun así no se acepta cualquiera.
    tipos_ok   = {t['id'] for t in _tipos_ausencia()}
    razones_ok = {r['id'] for r in _razones_ausencia()}
    tipo = None
    if tipo_txt:
        try:
            tipo = int(tipo_txt)
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'Tipo inválido'}, status=400)
        if tipo not in tipos_ok:
            return JsonResponse({'ok': False, 'error': 'Tipo fuera del catálogo'}, status=400)
    razon = RAZON_PENDIENTE
    if razon_txt:
        try:
            razon = int(razon_txt)
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'Razón inválida'}, status=400)
        if razon not in razones_ok:
            return JsonResponse({'ok': False, 'error': 'Razón fuera del catálogo'}, status=400)

    cfg, rama = AREAS[area], RAMAS[AREAS[area]['rama']]
    usuario = (request.user.get_username() or '')[:50]

    try:
        actual = _ausencias_del_dia(area, [materia_id], fecha).get(materia_id)
        with connections['padres_sqlserver'].cursor() as c:
            if tipo is None:
                if not actual:
                    return JsonResponse({'ok': True, 'accion': 'sin_cambio', 'aus_id': None})
                c.execute(f"""DELETE FROM dbo.{rama['ausencias']}
                              WHERE {rama['pk_ausencia']} = %s""", [actual['aus_id']])
                antes  = f"tipo={actual['tipo']} razon={actual['razon']}"
                nuevo  = ''
                aus_id, accion = None, 'delete'
            elif actual:
                c.execute(f"""UPDATE dbo.{rama['ausencias']}
                              SET DescrAusenciasID = %s, EdcDescrAusenciasRazonID = %s,
                                  Otros = %s, Usuario = %s, FchaReg = GETDATE()
                              WHERE {rama['pk_ausencia']} = %s""",
                          [tipo, razon, otros or None, usuario, actual['aus_id']])
                antes  = f"tipo={actual['tipo']} razon={actual['razon']}"
                nuevo  = f"tipo={tipo} razon={razon}"
                aus_id, accion = actual['aus_id'], 'update'
            else:
                c.execute(f"""INSERT INTO dbo.{rama['ausencias']}
                              ({rama['pk_materia']}, DescrAusenciasID,
                               EdcDescrAusenciasRazonID, Fecha, Otros, Usuario, FchaReg)
                              VALUES (%s, %s, %s, %s, %s, %s, GETDATE())""",
                          [materia_id, tipo, razon, fecha, otros or None, usuario])
                c.execute('SELECT CAST(SCOPE_IDENTITY() AS int)')
                r = c.fetchone()
                antes  = ''
                nuevo  = f"tipo={tipo} razon={razon}"
                aus_id, accion = (r[0] if r else None), 'insert'
    except Exception as e:
        return JsonResponse({'ok': False,
                             'error': f'El sistema académico rechazó el cambio: {e}'}, status=200)

    EscrituraNota.objects.create(
        usuario=request.user, area=area, rama=cfg['rama'], tabla=rama['ausencias'],
        materia_id=materia_id, eval_id=aus_id, parcial=0,
        columna=f'Ausencia@{fecha:%Y-%m-%d}',
        valor_antes=antes, valor_nuevo=nuevo, accion=accion, alumno=alumno)

    return JsonResponse({'ok': True, 'aus_id': aus_id, 'accion': accion})
