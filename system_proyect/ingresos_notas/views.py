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
import logging
import time
import uuid
from datetime import date
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.db import connections, transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST

from .models import EscrituraNota

# <--- hecho por claude code (seguridad 05-nov-2026): los errores de la base van al log del servidor, no al navegador
logger = logging.getLogger(__name__)

# <--- hecho por claude code (seguridad 05-nov-2026): largos reales de las columnas del legacy (INFORMATION_SCHEMA de Test2)
MAX_COMENTARIO = 100   # tblEdcRecordHabitos*.Comentario varchar(100)
MAX_OTROS = 50         # tblEdcAusencias*.Otros varchar(50) (antes se cortaba a 255 y el legacy lo rechazaba)
# <--- hecho por claude code (seguridad 05-nov-2026): EscrituraNota.valor_antes/valor_nuevo son de 30 (sin migración se recorta aquí)
MAX_BITACORA = 30
# <--- hecho por claude code (seguridad 05-nov-2026): tope de escrituras por usuario y minuto (una persona capturando no pasa de ~60)
LIMITE_ESCRITURAS_MIN = 240
MSG_AJENO = 'Ese alumno no pertenece a esta área o ya no está vigente este año.'

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
PUNTOS_MIN = 1      # <--- hecho por claude code (06-nov-2026): tareas y hábitos de 1 a 10, enteros
NOTA_MIN = 1        # <--- hecho por claude code (06-nov-2026): exámenes de 1 a 100, enteros

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


# <--- hecho por claude code (seguridad 05-nov-2026): mensaje genérico con referencia; el detalle (tablas, driver ODBC) solo al log
def _falla(contexto, escribiendo=False):
    """Registra la excepción en curso en el log del servidor y devuelve un mensaje
    genérico con una referencia corta para encontrarla. Llamar SIEMPRE dentro de un `except`."""
    ref = uuid.uuid4().hex[:8]
    logger.exception('ingresos_notas: %s (ref %s)', contexto, ref)
    if escribiendo:
        return (f'No se pudo guardar en el sistema académico (ref. {ref}). '
                'Intenta de nuevo; si sigue fallando, avisa a Sistemas.')
    return f'No se pudo leer el sistema académico (ref. {ref}). Intenta de nuevo en un momento.'


# <--- hecho por claude code (seguridad 05-nov-2026): recorte para la bitácora (si no, MySQL estricto revienta DESPUÉS de escribir)
def _corto(valor, n=MAX_BITACORA):
    s = '' if valor is None else str(valor)
    return s if len(s) <= n else s[:n - 1] + '…'


# <--- hecho por claude code (seguridad 05-nov-2026): límite de tasa en las 4 APIs que escriben en el legacy
def limite_escrituras(view):
    """Tope de escrituras por usuario y minuto, con el caché compartido (BD) como contador."""
    @wraps(view)
    def _w(request, *args, **kwargs):
        clave = f'ingresos_notas:esc:{request.user.pk}:{int(time.time() // 60)}'
        try:
            n = (cache.get(clave) or 0) + 1
            cache.set(clave, n, 120)
        except Exception:
            n = 0          # si el caché falla no se frena el trabajo de nadie
        if n > LIMITE_ESCRITURAS_MIN:
            return JsonResponse({'ok': False, 'error': 'Demasiados cambios seguidos. '
                                 'Espera un minuto y vuelve a intentar.'}, status=429)
        return view(request, *args, **kwargs)
    return _w


# <--- hecho por claude code (seguridad 05-nov-2026): bitácora única; se llama DENTRO de la transacción del legacy
def _bitacora(request, area, tabla, materia_id, eval_id, parcial, columna, antes, nuevo, accion, alumno):
    """Si este INSERT falla, la excepción deshace también la escritura en SQL Server:
    nunca queda un cambio en el legacy sin su rastro en TechCare."""
    EscrituraNota.objects.create(
        usuario=request.user, area=area, rama=AREAS[area]['rama'], tabla=tabla,
        materia_id=materia_id, eval_id=eval_id, parcial=parcial, columna=columna[:80],
        valor_antes=_corto(antes), valor_nuevo=_corto(nuevo),
        accion=accion, alumno=(alumno or '')[:200])


# ── Consultas al legacy ──────────────────────────────────────────────────────
def _anio_actual():
    return date.today().year


# <--- hecho por claude code (seguridad 05-nov-2026): IDOR — toda escritura valida la matrícula con la MISMA cadena y filtros de las lecturas
def _alumno_de_materia(area_key, materia_id):
    """Nombre del alumno si `materia_id` (su matrícula en UNA clase) es de esta área,
    del año en curso y no desertor; None si no lo es.

    Antes `materia_id` llegaba del navegador y entraba directo al UPDATE/INSERT/DELETE:
    se podía escribir en años anteriores, en desertores o en áreas que el módulo no
    maneja (PreescolarBL). El nombre que va a la bitácora sale de aquí, no del navegador.
    """
    cfg, rama = AREAS[area_key], RAMAS[AREAS[area_key]['rama']]
    sql = f"""
        SELECT TOP 1 LTRIM(RTRIM(ISNULL(d.Nombre1,'') + ' ' + ISNULL(d.Nombre2,'') + ' ' +
                                 ISNULL(d.Apellido1,'') + ' ' + ISNULL(d.Apellido2,'')))
        FROM dbo.{rama['materias']} m
          JOIN dbo.tblEdcEjecCrso ec        ON ec.EjecCrsoID = m.EjecCrsoID
          JOIN dbo.tblEdcArea a             ON a.AreaID = ec.AreaID
          JOIN dbo.tblEdcDescripAreaEdc da  ON da.DescrAreaEdcID = a.DescrAreaEdcID
          JOIN dbo.tblEdcCrso cr            ON cr.CrsoID = ec.CrsoID
          JOIN dbo.tblPrsTipo t             ON t.IngrEgrID = a.IngrEgrID
          JOIN dbo.tblPrsDtosGen d          ON d.PersonaID = t.PersonaID
        WHERE m.{rama['pk_materia']} = %s AND da.Descripcion = %s
          AND DATEPART(yy, cr.FechaInicio) = %s AND ec.Desertor = 0
    """
    with connections['padres_sqlserver'].cursor() as c:
        c.execute(sql, [materia_id, cfg['descr'], _anio_actual()])
        fila = c.fetchone()
    if not fila:
        return None
    return ' '.join((fila[0] or '').split())


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


def _habitos_del_dia(area_key, materia_ids, fecha):
    """{materia_id: {habito_id: {'rec_id':…, 'puntos':…, 'comentario':…}}}.

    <--- hecho por claude code: trae los 5 hábitos del Record de una vez, porque en
    la práctica se registran juntos el mismo día. Si un hábito tiene más de una fila
    esa fecha (pasa en un tercio de los casos) se toma la última, que es la que el
    legacy muestra.
    """
    if not materia_ids:
        return {}
    rama = RAMAS[AREAS[area_key]['rama']]
    marcas = ','.join(['%s'] * len(materia_ids))
    ids_h = ','.join(str(h) for h, _ in HABITOS_RECORD)
    sql = f"""
        SELECT {rama['pk_materia']}, EdcDescrHabitosID, {rama['pk_record']},
               Puntos, ISNULL(Comentario, '')
        FROM dbo.{rama['record']}
        WHERE CAST(Fecha AS date) = %s AND EdcDescrHabitosID IN ({ids_h})
          AND {rama['pk_materia']} IN ({marcas})
        ORDER BY {rama['pk_materia']}, EdcDescrHabitosID, {rama['pk_record']}
    """
    por_alumno = {}
    with connections['padres_sqlserver'].cursor() as c:
        c.execute(sql, [fecha] + list(materia_ids))
        for mat, hab, rec_id, puntos, coment in c.fetchall():
            por_alumno.setdefault(mat, {})[hab] = {
                'rec_id': rec_id, 'puntos': puntos, 'comentario': coment or ''}
    return por_alumno


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
# <--- hecho por claude code: los 4 formularios pasan a ser pantallas propias, con
# un panel de tarjetas al estilo del de Inventario. Antes eran tabs en una sola
# página: cómodo para capturar, pero cada formulario necesita crecer con sus
# reportes y filtros, y todo junto se volvía inmanejable.
FORMULARIOS = [
    ('notas',       'Notas',             'ti-list-numbers', '#4f46e5', 'Cuadros por clase y parcial'),
    ('tareas',      'Tareas',            'ti-notebook',     '#0ea5e9', 'Puntos de 0 a 10 por fecha'),
    ('asistencias', 'Asistencias',       'ti-calendar-x',   '#f97316', 'Faltas, tardanzas y permisos'),
    ('habitos',     'Record de hábitos', 'ti-star',         '#14b8a6', 'Los 5 hábitos por fecha'),
]


@notas_required
def panel(request):
    """Panel de entrada: una tarjeta por formulario."""
    permitidas = areas_permitidas(request.user)
    area_key = request.GET.get('area') or permitidas[0]
    if area_key not in permitidas:
        area_key = permitidas[0]
    return render(request, 'ingresos_notas/panel.html', {
        'formularios': FORMULARIOS,
        'area_sel': area_key,
        'area_label': AREAS[area_key]['label'],
        'areas': [(k, AREAS[k]['label']) for k in permitidas],
        'anio': _anio_actual(),   # <--- hecho por claude code (04-nov-2026): contexto para el panel de trabajo (Opción B)
    })


# <--- hecho por claude code (04-nov-2026): "Proyecto Notas Fase 1" — galería de 12 plantillas DEMO
# (editables) de los reportes, servidas como estáticos, para validar cuál es más rápida al ingresar.
_PLANTILLAS_DEMO = [
    {'rep': 'tareas',      'titulo': 'Tareas',             'i': 'ti-notebook',          'c': '#0ea5e9'},
    {'rep': 'examenes',    'titulo': 'Exámenes',           'i': 'ti-file-certificate',  'c': '#4f46e5'},
    {'rep': 'habitos',     'titulo': 'Record de hábitos',  'i': 'ti-star',              'c': '#14b8a6'},
    {'rep': 'asistencias', 'titulo': 'Asistencias',        'i': 'ti-calendar-x',        'c': '#f97316'},
]
_PLANTILLAS_VARS = {
    'tareas':      [('a', 'Planilla editable'), ('b', 'Por alumno'), ('c', 'Captura + resumen')],
    'examenes':    [('a', 'Planilla editable'), ('b', 'Por alumno'), ('c', 'Captura + resumen')],
    'habitos':     [('a', 'Planilla editable'), ('b', 'Por alumno'), ('c', 'Captura + resumen')],
    'asistencias': [('a', 'Pase de lista rápido'), ('b', 'Matriz por fecha'), ('c', 'Captura + resumen')],
}


@notas_required
def plantillas_index(request):
    """Galería de las 12 plantillas demo (Proyecto Notas Fase 1)."""
    from django.templatetags.static import static
    grupos = []
    for g in _PLANTILLAS_DEMO:
        opciones = [{'v': v, 'label': lbl,
                     'url': static(f"ingresos_notas/plantillas/{g['rep']}_{v}.html")}
                    for v, lbl in _PLANTILLAS_VARS[g['rep']]]
        grupos.append({**g, 'opciones': opciones})
    return render(request, 'ingresos_notas/plantillas_index.html', {'grupos': grupos})


@notas_required
def index(request, form='notas'):
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
        # <--- hecho por claude code: qué formulario se está mostrando
        'form': form if form in {f[0] for f in FORMULARIOS} else 'notas',
        'formularios': FORMULARIOS,
        'error': '',
    }
    try:
        ctx['grados'] = _grados(area_key, ctx['anio'])
    except Exception:
        ctx['grados'] = []
        ctx['error'] = _falla('index: grados')   # <--- hecho por claude code (seguridad 05-nov-2026): antes mostraba el error crudo de la base
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
    except Exception:
        # <--- hecho por claude code (seguridad 05-nov-2026): mensaje genérico + log, y 500 en vez de 200
        return JsonResponse({'ok': False, 'error': _falla('api_clases')}, status=500)


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
    except Exception:
        # <--- hecho por claude code (seguridad 05-nov-2026): mensaje genérico + log, y 500 en vez de 200
        return JsonResponse({'ok': False, 'error': _falla('api_alumnos')}, status=500)


@notas_required
@require_POST
@limite_escrituras
def api_guardar(request):
    """Escribe UNA celda. UPDATE si la fila del parcial existe; si no, la crea.

    Nunca hace DELETE y solo toca la columna pedida, que además tiene que estar
    en la lista blanca de `_columnas_validas`.
    """
    try:
        body = json.loads(request.body or b'{}')
        area       = str(body.get('area') or '')
        materia_id = int(body.get('materia_id'))
        parcial    = int(body.get('parcial'))
        columna    = (body.get('columna') or '').strip()
        crudo      = (body.get('valor') or '').strip()
    except (TypeError, ValueError, AttributeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)
    if parcial not in PARCIALES:
        return JsonResponse({'ok': False, 'error': 'Parcial inválido'}, status=400)
    if _parcial_cerrado(area, parcial):
        return JsonResponse({'ok': False, 'error': f'El Parcial {parcial} está cerrado por coordinación. '
                             'Para corregir una nota, coordinación debe reabrirlo en Notas Mitad de Parcial.'}, status=409)
    if columna not in _columnas_escribibles(area):
        return JsonResponse({'ok': False, 'error': 'Columna no permitida'}, status=400)

    # Celda vacía = borrar el valor (NULL), no poner un cero.
    if crudo == '':
        valor = None
    else:
        # <--- hecho por claude code (06-nov-2026): regla del usuario — exámenes solo ENTEROS de 1 a 100
        if not crudo.isdecimal():
            return JsonResponse({'ok': False, 'error': 'La nota debe ser un número entero (sin decimales)'}, status=400)
        valor = int(crudo)
        if not (NOTA_MIN <= valor <= 100):
            return JsonResponse({'ok': False, 'error': f'La nota va de {NOTA_MIN} a 100'}, status=400)

    rama = RAMAS[AREAS[area]['rama']]
    usuario = (request.user.get_username() or '')[:50]

    # <--- hecho por claude code (seguridad 05-nov-2026): la matrícula tiene que ser del área, del año y no desertor; el nombre lo pone el servidor
    try:
        alumno = _alumno_de_materia(area, materia_id)
    except Exception:
        return JsonResponse({'ok': False, 'error': _falla('api_guardar: validar matrícula', True)}, status=500)
    if alumno is None:
        return JsonResponse({'ok': False, 'error': MSG_AJENO}, status=403)

    # <--- hecho por claude code (seguridad 05-nov-2026): escritura + bitácora en UNA transacción del legacy (si la bitácora falla, se deshace)
    try:
        with transaction.atomic(using='padres_sqlserver'):
            with connections['padres_sqlserver'].cursor() as c:
                # <--- hecho por claude code (seguridad 05-nov-2026): orden fijo; si hay dos filas del mismo parcial no se adivina cuál tocar
                c.execute(f"""SELECT TOP 2 {rama['pk_eval']}, {columna} FROM dbo.{rama['eval']}
                              WHERE {rama['pk_materia']} = %s AND Parcial = %s
                              ORDER BY {rama['pk_eval']} DESC""",
                          [materia_id, parcial])
                filas = c.fetchall()
                if len(filas) > 1:
                    return JsonResponse({'ok': False, 'error': 'Este alumno tiene dos filas del mismo '
                                         'parcial en el sistema académico. Avisa a Sistemas.'}, status=409)

                if filas:
                    eval_id, antes = filas[0]
                    c.execute(f"""UPDATE dbo.{rama['eval']}
                                  SET {columna} = %s, Usuario = %s, FchaReg = GETDATE()
                                  WHERE {rama['pk_eval']} = %s""",
                              [valor, usuario, eval_id])
                    accion = 'update'
                else:
                    antes = None
                    c.execute(f"""INSERT INTO dbo.{rama['eval']}
                                  ({rama['pk_materia']}, Parcial, {columna}, Usuario, FchaReg, Fecha)
                                  VALUES (%s, %s, %s, %s, GETDATE(),
                                          DATEADD(minute, DATEDIFF(minute, 0, GETDATE()), 0))""",
                              # <--- hecho por claude code (06-nov-2026): Fecha es smalldatetime y redondea al minuto: con GETDATE() a los :30 s o más quedaba en el minuto SIGUIENTE y chocaba con el CHECK fecha<=getdate() (falla intermitente). Se trunca al minuto.
                              [materia_id, parcial, valor, usuario])
                    # <--- hecho por claude code (seguridad 05-nov-2026): READPAST = no esperar bloqueos ajenos mientras se tiene la fila nueva (la propia sí se ve)
                    c.execute(f"""SELECT TOP 1 {rama['pk_eval']} FROM dbo.{rama['eval']} WITH (READPAST)
                                  WHERE {rama['pk_materia']} = %s AND Parcial = %s
                                  ORDER BY {rama['pk_eval']} DESC""",
                              [materia_id, parcial])
                    r = c.fetchone()
                    eval_id = r[0] if r else None
                    accion = 'insert'

            # Bitácora del lado de TechCare (el trigger del legacy solo cubre UPDATE)
            _bitacora(request, area, rama['eval'], materia_id, eval_id, parcial, columna,
                      antes, valor, accion, alumno)
    except Exception:
        return JsonResponse({'ok': False, 'error': _falla('api_guardar', True)}, status=500)

    return JsonResponse({'ok': True, 'eval_id': eval_id, 'accion': accion,
                         'valor': '' if valor is None else valor})


# ── APIs del tab Tareas ──────────────────────────────────────────────────────
def _fecha_valida(texto):
    """'2026-07-30' -> date, o None si no sirve."""
    try:
        return date.fromisoformat((texto or '').strip())
    except (ValueError, TypeError, AttributeError):
        return None


# <--- hecho por claude code (seguridad 05-nov-2026): para ESCRIBIR la fecha va acotada al año escolar en curso y no futura
TIPO_TRAJO_EXCUSA = 5   # <--- hecho por claude code (05-nov-2026): tblEdcDescripAusencias «Trajo Excusa»
# <--- hecho por claude code (05-nov-2026, decisión del usuario): un parcial cerrado en Notas Mitad de Parcial queda cerrado aquí también. Notas llama 'bl' a Primaria BL.
_AREA_CIERRE_NOTAS = {'primaria_bl': 'bl'}


def _parcial_cerrado(area, parcial, anio=None):
    from notas_parcial.models import CierreNotas
    return CierreNotas.objects.filter(area=_AREA_CIERRE_NOTAS.get(area, area), parcial=parcial,
                                      anio=anio or date.today().year, parcial_cerrado=True,
                                      grado='', seccion='').exists()


def _fecha_escritura(texto, permitir_futura=False):
    """(fecha, None) si sirve para escribir; (None, motivo) si no.

    Antes se aceptaba cualquier fecha ISO (otro año, el futuro). En el legacy no hay
    registros con fecha de un año anterior al de su captura y los futuros son errores
    de digitación (0,1 %).
    """
    f = _fecha_valida(texto)
    if f is None:
        return None, 'Fecha inválida'
    hoy = date.today()
    if f.year != hoy.year:
        return None, f'Solo se pueden registrar fechas del año escolar {hoy.year}.'
    if f > hoy and not permitir_futura:   # <--- hecho por claude code (05-nov-2026): «Trajo Excusa» sí se registra por adelantado (decisión del usuario)
        return None, 'No se pueden registrar fechas futuras.'
    return f, None


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
    except Exception:
        # <--- hecho por claude code (seguridad 05-nov-2026): mensaje genérico + log, y 500 en vez de 200
        return JsonResponse({'ok': False, 'error': _falla('api_tareas')}, status=500)


@notas_required
@require_POST
@limite_escrituras
def api_tarea_guardar(request):
    """Guarda los puntos o el comentario de UNA tarea de UN alumno.

    Si la fila existe es UPDATE. Si no, se INSERTA — pero solo cuando al alumno
    le faltaba exactamente esa tarea (`previas == tarea - 1`); si le faltan
    tareas anteriores se rechaza, porque insertarla la correría de posición y
    quedaría pegada a la tarea equivocada.
    """
    try:
        body = json.loads(request.body or b'{}')
        area       = str(body.get('area') or '')
        materia_id = int(body.get('materia_id'))
        tarea      = int(body.get('tarea'))
        campo      = (body.get('campo') or '').strip()
        crudo      = (body.get('valor') or '').strip()
    except (TypeError, ValueError, AttributeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)
    fecha, motivo = _fecha_escritura(body.get('fecha'))
    if not fecha:
        return JsonResponse({'ok': False, 'error': motivo}, status=400)
    if tarea < 1:
        return JsonResponse({'ok': False, 'error': 'Tarea inválida'}, status=400)
    if campo not in ('puntos', 'comentario'):
        return JsonResponse({'ok': False, 'error': 'Campo no permitido'}, status=400)
    # <--- hecho por claude code (seguridad 05-nov-2026): el legacy guarda 100 caracteres; antes respondía con su error crudo
    if campo == 'comentario' and len(crudo) > MAX_COMENTARIO:
        return JsonResponse({'ok': False, 'error': f'El comentario admite hasta {MAX_COMENTARIO} '
                             'caracteres.'}, status=400)

    puntos = None
    if campo == 'puntos':
        if crudo == '':
            return JsonResponse({'ok': False,
                                 'error': 'Los puntos no pueden quedar vacíos'}, status=400)
        # <--- hecho por claude code (06-nov-2026): regla del usuario — tareas y hábitos solo ENTEROS de 1 a 10
        if not crudo.isdecimal():
            return JsonResponse({'ok': False, 'error': 'Los puntos deben ser un número entero (sin decimales)'}, status=400)
        puntos = int(crudo)
        if not (PUNTOS_MIN <= puntos <= PUNTOS_MAX):
            return JsonResponse({'ok': False,
                                 'error': f'Los puntos van de {PUNTOS_MIN} a {PUNTOS_MAX}'}, status=400)

    rama = RAMAS[AREAS[area]['rama']]
    usuario = (request.user.get_username() or '')[:50]

    # <--- hecho por claude code (seguridad 05-nov-2026): la matrícula tiene que ser del área, del año y no desertor; el nombre lo pone el servidor
    try:
        alumno = _alumno_de_materia(area, materia_id)
    except Exception:
        return JsonResponse({'ok': False, 'error': _falla('api_tarea_guardar: validar matrícula', True)}, status=500)
    if alumno is None:
        return JsonResponse({'ok': False, 'error': MSG_AJENO}, status=403)

    # <--- hecho por claude code (seguridad 05-nov-2026): escritura + bitácora en UNA transacción del legacy (si la bitácora falla, se deshace)
    try:
        with transaction.atomic(using='padres_sqlserver'):
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
                                                   f'tarea {len(filas) + 1}.'}, status=409)
                    if campo == 'comentario':
                        return JsonResponse(
                            {'ok': False,
                             'error': 'Pon primero los puntos y luego el comentario.'}, status=409)
                    antes, nuevo = None, puntos
                    c.execute(f"""INSERT INTO dbo.{rama['record']}
                                  ({rama['pk_materia']}, EdcDescrHabitosID, Fecha, Puntos,
                                   Usuario, FchaReg)
                                  VALUES (%s, %s, %s, %s, %s, GETDATE())""",
                              [materia_id, HABITO_TAREAS, fecha, puntos, usuario])
                    # <--- hecho por claude code (seguridad 05-nov-2026): SCOPE_IDENTITY() en otra llamada daba NULL (pyodbc parametriza en otro ámbito): 71 de 71 inserts sin ID en la bitácora
                    c.execute(f"""SELECT TOP 1 {rama['pk_record']} FROM dbo.{rama['record']} WITH (READPAST)
                                  WHERE {rama['pk_materia']} = %s AND EdcDescrHabitosID = %s
                                    AND CAST(Fecha AS date) = %s AND Usuario = %s
                                  ORDER BY {rama['pk_record']} DESC""",
                              [materia_id, HABITO_TAREAS, fecha, usuario])
                    r = c.fetchone()
                    rec_id = r[0] if r else None
                    accion = 'insert'

            _bitacora(request, area, rama['record'], materia_id, rec_id, 0,
                      f'Tarea{tarea}@{fecha:%Y-%m-%d}·{campo}', antes, nuevo, accion, alumno)
    except Exception:
        return JsonResponse({'ok': False, 'error': _falla('api_tarea_guardar', True)}, status=500)

    return JsonResponse({'ok': True, 'rec_id': rec_id, 'accion': accion})


# ── APIs del tab Record de Hábitos ───────────────────────────────────────────
@notas_required
@require_GET
def api_habitos(request):
    """Alumnos de la clase con sus 5 hábitos de esa fecha."""
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
        registros = _habitos_del_dia(area, [a['materia_id'] for a in alumnos], fecha)
        con_datos = 0
        for a in alumnos:
            r = registros.get(a['materia_id'], {})
            a['puntos'] = {str(h): ('' if h not in r else r[h]['puntos'])
                           for h, _ in HABITOS_RECORD}
            # el comentario es el mismo para los hábitos de ese día (así lo usan)
            a['comentario'] = next((v['comentario'] for v in r.values() if v['comentario']), '')
            if r:
                con_datos += 1
        return JsonResponse({'ok': True, 'alumnos': alumnos,
                             'habitos': [{'id': h, 'label': l} for h, l in HABITOS_RECORD],
                             'puntos_max': PUNTOS_MAX, 'con_datos': con_datos})
    except Exception:
        # <--- hecho por claude code (seguridad 05-nov-2026): mensaje genérico + log, y 500 en vez de 200
        return JsonResponse({'ok': False, 'error': _falla('api_habitos')}, status=500)


@notas_required
@require_POST
@limite_escrituras
def api_habito_guardar(request):
    """Guarda los puntos de UN hábito, o el comentario de todo el día del alumno."""
    try:
        body = json.loads(request.body or b'{}')
        area       = str(body.get('area') or '')
        materia_id = int(body.get('materia_id'))
        campo      = (body.get('campo') or 'puntos').strip()
        crudo      = (body.get('valor') or '').strip()
        habito     = int(body.get('habito')) if body.get('habito') else None
    except (TypeError, ValueError, AttributeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)
    fecha, motivo = _fecha_escritura(body.get('fecha'))
    if not fecha:
        return JsonResponse({'ok': False, 'error': motivo}, status=400)
    if campo not in ('puntos', 'comentario'):
        return JsonResponse({'ok': False, 'error': 'Campo no permitido'}, status=400)
    if campo == 'puntos' and habito not in {h for h, _ in HABITOS_RECORD}:
        return JsonResponse({'ok': False, 'error': 'Hábito fuera del catálogo'}, status=400)
    # <--- hecho por claude code (seguridad 05-nov-2026): el legacy guarda 100 caracteres; antes respondía con su error crudo
    if campo == 'comentario' and len(crudo) > MAX_COMENTARIO:
        return JsonResponse({'ok': False, 'error': f'El comentario admite hasta {MAX_COMENTARIO} '
                             'caracteres.'}, status=400)

    puntos = None
    if campo == 'puntos':
        if crudo == '':
            return JsonResponse({'ok': False,
                                 'error': 'Los puntos no pueden quedar vacíos'}, status=400)
        # <--- hecho por claude code (06-nov-2026): regla del usuario — tareas y hábitos solo ENTEROS de 1 a 10
        if not crudo.isdecimal():
            return JsonResponse({'ok': False, 'error': 'Los puntos deben ser un número entero (sin decimales)'}, status=400)
        puntos = int(crudo)
        if not (PUNTOS_MIN <= puntos <= PUNTOS_MAX):
            return JsonResponse({'ok': False,
                                 'error': f'Los puntos van de {PUNTOS_MIN} a {PUNTOS_MAX}'}, status=400)

    rama = RAMAS[AREAS[area]['rama']]
    usuario = (request.user.get_username() or '')[:50]

    # <--- hecho por claude code (seguridad 05-nov-2026): la matrícula tiene que ser del área, del año y no desertor; el nombre lo pone el servidor
    try:
        alumno = _alumno_de_materia(area, materia_id)
    except Exception:
        return JsonResponse({'ok': False, 'error': _falla('api_habito_guardar: validar matrícula', True)}, status=500)
    if alumno is None:
        return JsonResponse({'ok': False, 'error': MSG_AJENO}, status=403)

    # <--- hecho por claude code (seguridad 05-nov-2026): escritura + bitácora en UNA transacción del legacy (si la bitácora falla, se deshace)
    try:
        with transaction.atomic(using='padres_sqlserver'):
            actuales = _habitos_del_dia(area, [materia_id], fecha).get(materia_id, {})
            with connections['padres_sqlserver'].cursor() as c:
                if campo == 'comentario':
                    # <--- hecho por claude code: el comentario se aplica a los hábitos que
                    # el alumno ya tenga ese día (así lo usan: "III PARCIAL" en todos).
                    if not actuales:
                        return JsonResponse(
                            {'ok': False,
                             'error': 'Pon primero los puntos y luego el comentario.'}, status=409)
                    ids = [v['rec_id'] for v in actuales.values()]
                    marcas = ','.join(['%s'] * len(ids))
                    c.execute(f"""UPDATE dbo.{rama['record']}
                                  SET Comentario = %s, Usuario = %s, FchaReg = GETDATE()
                                  WHERE {rama['pk_record']} IN ({marcas})""",
                              [crudo or None, usuario] + ids)
                    antes = next((v['comentario'] for v in actuales.values() if v['comentario']), '')
                    rec_id, nuevo, accion = ids[0], crudo, 'update'
                elif habito in actuales:
                    rec_id = actuales[habito]['rec_id']
                    antes, nuevo = actuales[habito]['puntos'], puntos
                    c.execute(f"""UPDATE dbo.{rama['record']}
                                  SET Puntos = %s, Usuario = %s, FchaReg = GETDATE()
                                  WHERE {rama['pk_record']} = %s""", [puntos, usuario, rec_id])
                    accion = 'update'
                else:
                    coment = next((v['comentario'] for v in actuales.values() if v['comentario']), None)
                    c.execute(f"""INSERT INTO dbo.{rama['record']}
                                  ({rama['pk_materia']}, EdcDescrHabitosID, Fecha, Puntos,
                                   Comentario, Usuario, FchaReg)
                                  VALUES (%s, %s, %s, %s, %s, %s, GETDATE())""",
                              [materia_id, habito, fecha, puntos, coment, usuario])
                    # <--- hecho por claude code (seguridad 05-nov-2026): SCOPE_IDENTITY() en otra llamada daba NULL; se relee la fila recién creada
                    c.execute(f"""SELECT TOP 1 {rama['pk_record']} FROM dbo.{rama['record']} WITH (READPAST)
                                  WHERE {rama['pk_materia']} = %s AND EdcDescrHabitosID = %s
                                    AND CAST(Fecha AS date) = %s AND Usuario = %s
                                  ORDER BY {rama['pk_record']} DESC""",
                              [materia_id, habito, fecha, usuario])
                    r = c.fetchone()
                    antes, nuevo = None, puntos
                    rec_id, accion = (r[0] if r else None), 'insert'

            etiqueta = dict(HABITOS_RECORD).get(habito, campo)
            _bitacora(request, area, rama['record'], materia_id, rec_id, 0,
                      f'Habito:{etiqueta}@{fecha:%Y-%m-%d}', antes, nuevo, accion, alumno)
    except Exception:
        return JsonResponse({'ok': False, 'error': _falla('api_habito_guardar', True)}, status=500)

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
    except Exception:
        # <--- hecho por claude code (seguridad 05-nov-2026): mensaje genérico + log, y 500 en vez de 200
        return JsonResponse({'ok': False, 'error': _falla('api_ausencias')}, status=500)


@notas_required
@require_POST
@limite_escrituras
def api_ausencia_guardar(request):
    """Crea, actualiza o quita la ausencia de UN alumno en UNA fecha.

    Vaciar el tipo BORRA la fila: es la única forma de deshacer una ausencia
    puesta por error, y estas filas tienen efecto económico. Queda registrado
    en `EscrituraNota` con acción `delete`, que es el rastro que el legacy no
    guarda (sus triggers solo cubren UPDATE).
    """
    try:
        body = json.loads(request.body or b'{}')
        area       = str(body.get('area') or '')
        materia_id = int(body.get('materia_id'))
        tipo_txt   = (body.get('tipo') or '').strip()
        razon_txt  = (body.get('razon') or '').strip()
        otros      = (body.get('otros') or '').strip()
        # <--- hecho por claude code (seguridad 05-nov-2026): el borrado exige la confirmación explícita del usuario (antes bastaba tipo vacío o ausente)
        quitar     = body.get('quitar') is True
    except (TypeError, ValueError, AttributeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    if not _area_valida(request, area):
        return JsonResponse({'ok': False, 'error': 'Área no permitida'}, status=403)
    fecha, motivo = _fecha_escritura(body.get('fecha'), permitir_futura=(tipo_txt == str(TIPO_TRAJO_EXCUSA) or quitar))
    if not fecha:
        return JsonResponse({'ok': False, 'error': motivo}, status=400)
    # <--- hecho por claude code (seguridad 05-nov-2026): Otros es varchar(50) en el legacy (antes se cortaba a 255 y lo rechazaba)
    if len(otros) > MAX_OTROS:
        return JsonResponse({'ok': False, 'error': f'El detalle (Otros) admite hasta {MAX_OTROS} '
                             'caracteres.'}, status=400)

    # El tipo y la razón se validan contra el catálogo: van al SQL como enteros,
    # pero aun así no se acepta cualquiera.
    try:
        tipos_ok   = {t['id'] for t in _tipos_ausencia()}
        razones_ok = {r['id'] for r in _razones_ausencia()}
    except Exception:
        return JsonResponse({'ok': False, 'error': _falla('api_ausencia_guardar: catálogos', True)}, status=500)
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

    rama = RAMAS[AREAS[area]['rama']]
    usuario = (request.user.get_username() or '')[:50]

    # <--- hecho por claude code (seguridad 05-nov-2026): la matrícula tiene que ser del área, del año y no desertor; el nombre lo pone el servidor
    try:
        alumno = _alumno_de_materia(area, materia_id)
    except Exception:
        return JsonResponse({'ok': False, 'error': _falla('api_ausencia_guardar: validar matrícula', True)}, status=500)
    if alumno is None:
        return JsonResponse({'ok': False, 'error': MSG_AJENO}, status=403)

    # <--- hecho por claude code (seguridad 05-nov-2026): escritura + bitácora en UNA transacción del legacy (si la bitácora falla, se deshace)
    try:
        with transaction.atomic(using='padres_sqlserver'):
            actual = _ausencias_del_dia(area, [materia_id], fecha).get(materia_id)
            with connections['padres_sqlserver'].cursor() as c:
                if tipo is None:
                    if not actual:
                        return JsonResponse({'ok': True, 'accion': 'sin_cambio', 'aus_id': None})
                    # <--- hecho por claude code (seguridad 05-nov-2026): sin la confirmación del usuario no se borra (409 y la pantalla se recarga)
                    if not quitar:
                        return JsonResponse({'ok': False, 'error': 'Este alumno tiene una falta registrada '
                                             'ese día. Para quitarla hay que confirmarlo.'}, status=409)
                    c.execute(f"""DELETE FROM dbo.{rama['ausencias']}
                                  WHERE {rama['pk_ausencia']} = %s""", [actual['aus_id']])
                    # <--- hecho por claude code (seguridad 05-nov-2026): la bitácora guarda el ID borrado y lo esencial de la fila (antes eval_id=None)
                    antes  = f"tipo={actual['tipo']} razon={actual['razon']}" + \
                             (f" {actual['otros']}" if actual['otros'] else '')
                    nuevo  = ''
                    aus_id, accion = actual['aus_id'], 'delete'
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
                    # <--- hecho por claude code (seguridad 05-nov-2026): SCOPE_IDENTITY() en otra llamada daba NULL; se relee la fila recién creada
                    c.execute(f"""SELECT TOP 1 {rama['pk_ausencia']} FROM dbo.{rama['ausencias']} WITH (READPAST)
                                  WHERE {rama['pk_materia']} = %s AND CAST(Fecha AS date) = %s
                                    AND DescrAusenciasID = %s AND Usuario = %s
                                  ORDER BY {rama['pk_ausencia']} DESC""",
                              [materia_id, fecha, tipo, usuario])
                    r = c.fetchone()
                    antes  = ''
                    nuevo  = f"tipo={tipo} razon={razon}"
                    aus_id, accion = (r[0] if r else None), 'insert'

            _bitacora(request, area, rama['ausencias'], materia_id, aus_id, 0,
                      f'Ausencia@{fecha:%Y-%m-%d}', antes, nuevo, accion, alumno)
    except Exception:
        return JsonResponse({'ok': False, 'error': _falla('api_ausencia_guardar', True)}, status=500)

    return JsonResponse({'ok': True, 'aus_id': None if accion == 'delete' else aus_id,
                         'accion': accion})
