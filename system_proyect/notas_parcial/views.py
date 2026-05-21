import io
import json
import os
from collections import OrderedDict
from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.db import connections
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from django.contrib.auth import get_user_model

from django.core.mail import send_mail

from .models import NotaComentario, AsignacionMaestro, RevisionFinalizada

User = get_user_model()

_GRUPOS_COORD        = {'coordinador_bilingue', 'coordinador_colegio', 'coordinadores_colegio', 'coordinadores', 'coord_notas_parcial', 'coordinador_bl', 'coordinador_col', 'coord_progress_bl', 'notas_revision', 'coord_revision'}
_GRUPOS_COORD_FULL   = {'coord_notas_parcial'}
_GRUPOS_MAESTRO      = {'maestros_bilingue', 'maestros_colegio', 'maestros_notas_parcial'}
_GRUPOS_BL           = {'coordinador_bilingue', 'coordinador_bl', 'coord_progress_bl', 'coord_revision', 'coord_notas_parcial'}
_GRUPOS_COLEGIO      = {'coordinador_colegio', 'coordinadores_colegio', 'coordinador_col'}

AREAS_BL      = [('bl', 'Primaria Bilingüe'), ('colegio_bl', 'Colegio BL')]
AREAS_COLEGIO = [('colegio', 'Colegio'), ('bachillerato', 'Bachillerato')]


def _areas_para(user):
    """Retorna las áreas visibles según el grupo del usuario."""
    if user.is_superuser:
        return AREAS
    grupos = set(user.groups.values_list('name', flat=True))
    es_bl      = bool(grupos & _GRUPOS_BL)
    es_colegio = bool(grupos & _GRUPOS_COLEGIO)
    if es_bl and not es_colegio:
        return AREAS_BL
    if es_colegio and not es_bl:
        return AREAS_COLEGIO
    return AREAS


def _es_coordinador(user):
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=_GRUPOS_COORD).exists()


def _es_solo_revision(user):
    """True si el usuario solo puede ver el carrusel (coord_revision sin acceso completo)."""
    if user.is_superuser:
        return False
    grupos = set(user.groups.values_list('name', flat=True))
    return 'coord_revision' in grupos and not (grupos & _GRUPOS_COORD_FULL)


def _es_maestro(user):
    return user.groups.filter(name__in=_GRUPOS_MAESTRO).exists()


_coordinador = user_passes_test(_es_coordinador, login_url='login')
_solo_maestro = user_passes_test(
    lambda u: u.is_authenticated and (_es_coordinador(u) or _es_maestro(u)),
    login_url='login',
)

_superuser = user_passes_test(lambda u: u.is_superuser, login_url='login')

AREAS = [
    ('bl',           'Primaria Bilingüe'),
    ('colegio_bl',   'Colegio BL'),
    ('colegio',      'Colegio'),
    ('bachillerato', 'Bachillerato'),
]

# (sp_name, usa_curso)
SP_MAP = {
    'bl':           ('spEdcNotasInsertPrimariaBL',  False),
    'colegio_bl':   ('spEdcNotasInsertColegioBL',   False),
    'colegio':      ('spEdcNotasInsertColegio',      False),
    'bachillerato': ('spEdcNotasInsertBachillerato', True),
}

# Tablas de staging donde el SP persiste los datos
_TABLA_STAGING = {
    'bl':           'tblEdcNotasInsertPrimariaBL',
    'colegio_bl':   'tblEdcNotasInsertColegioBL',
    'colegio':      'tblEdcNotasInsertColegio',
    'bachillerato': 'tblEdcNotasInsertBachillerato',
}

DIAS_ES   = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']
MESES_ES  = ['enero','febrero','marzo','abril','mayo','junio',
             'julio','agosto','septiembre','octubre','noviembre','diciembre']


# Columnas exactas que usa _agrupar — evita traer columnas innecesarias
_COLS_STAGING = (
    'IngrEgrID, NombreCompl, AreaCurso, CrsoNumero, GrupoNumero, '
    'InicioParcial, FinalParcial, Materia, Tarea, '
    'Cuadro1, Cuadro2, Cuadro3, Cuadro4, Cuadro5, '
    'Cuadro6, Cuadro7, Cuadro8, Cuadro9, Cuadro10'
)
_CACHE_TTL = 28800  # 8 horas

# Correo destino según usuario — bilingüe → lchavez, colegio → malvarado
_DEST_POR_USUARIO = {
    'druiz':      'lchavez@ana-hn.org',
    'cvarela':    'lchavez@ana-hn.org',
    'ialcerro':   'lchavez@ana-hn.org',
    'jmartinez':  'lchavez@ana-hn.org',
    'coordi_bl':  'lchavez@ana-hn.org',
    'jvalladres': 'malvarado@ana-hn.org',
    'coordi_col': 'malvarado@ana-hn.org',
}
_CORREO_PRUEBAS   = 'admin2@ana-hn.org'
_CORREOS_VALIDOS  = {'lchavez@ana-hn.org', 'malvarado@ana-hn.org', 'admin2@ana-hn.org'}


def _destinatarios_para(user):
    """Retorna la lista de correos que puede ver este coordinador en el select."""
    if user.is_superuser:
        return ['lchavez@ana-hn.org', 'malvarado@ana-hn.org', _CORREO_PRUEBAS]
    grupos = set(user.groups.values_list('name', flat=True))
    if 'coordinador_bl' in grupos:
        return ['lchavez@ana-hn.org', _CORREO_PRUEBAS]
    if 'coordinador_col' in grupos:
        return ['malvarado@ana-hn.org', _CORREO_PRUEBAS]
    # Fallback para usuarios existentes asignados por username
    dest = _DEST_POR_USUARIO.get(user.username)
    if dest:
        return [dest, _CORREO_PRUEBAS]
    return [_CORREO_PRUEBAS]


def _cache_key(area, parcial, anio, curso):
    return f'notas_sp_{area}_{parcial}_{anio}_{curso or ""}'


def _leer_staging_directo(area, parcial, anio, curso=None):
    """Lee staging table con columnas específicas + NOLOCK para mayor velocidad."""
    tabla = _TABLA_STAGING.get(area)
    if not tabla:
        return [], []
    try:
        with connections['padres_sqlserver'].cursor() as cursor:
            bach = f" AND CrsoNumero LIKE '{int(curso)}%'" if (area == 'bachillerato' and curso) else ''
            sql = (
                f"SELECT {_COLS_STAGING} "
                f"FROM {tabla} WITH (NOLOCK) "
                f"WHERE Parcial={int(parcial)} AND Año={int(anio)}{bach}"
            )
            cursor.execute(sql)
            if cursor.description is None:
                return [], []
            cols = [c[0] for c in cursor.description]
            rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        return rows, cols
    except Exception as e:
        print(f">>> ERROR staging {tabla}:", e)
        return [], []


def _llamar_sp(area, parcial, anio, curso=None):
    key = _cache_key(area, parcial, anio, curso)

    # 1. Caché en BD Django (válida 15 min, compartida entre workers)
    cached = cache.get(key)
    if cached:
        return cached

    # 2. Staging table directo (sin llamar el SP)
    rows, cols = _leer_staging_directo(area, parcial, anio, curso)
    if rows:
        cache.set(key, (rows, cols), _CACHE_TTL)
        return rows, cols

    # 3. Llamar SP (lento — también puebla la staging table)
    entry = SP_MAP.get(area)
    if not entry:
        return [], []
    sp, usa_curso = entry
    try:
        with connections['padres_sqlserver'].cursor() as cursor:
            if usa_curso and curso:
                sql = f"EXEC {sp} @Curso='{curso}', @Parcial={int(parcial)}, @Año={int(anio)}"
            else:
                sql = f"EXEC {sp} @Parcial={int(parcial)}, @Año={int(anio)}"
            cursor.execute(sql)
            while cursor.description is None:
                if not cursor.nextset():
                    return [], []
            cols = [c[0] for c in cursor.description]
            rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
        if rows:
            cache.set(key, (rows, cols), _CACHE_TTL)
        return rows, cols
    except Exception as e:
        print(f">>> ERROR SP {sp}:", e)
        return [], []


def _get(row, *keys, default=''):
    for k in keys:
        v = row.get(k)
        if v is not None:
            return v
    return default


def _agrupar(rows):
    alumnos = OrderedDict()
    for r in rows:
        iid = r.get('IngrEgrID')
        if iid is None:
            continue
        iid = int(iid)
        if iid not in alumnos:
            alumnos[iid] = {
                'ingr_egr_id': iid,
                'nombre':      str(r.get('NombreCompl') or '').strip(),
                'area_curso':  str(r.get('AreaCurso') or '').strip(),
                'grado':       str(r.get('CrsoNumero') or '').strip(),
                'grupo':       str(r.get('GrupoNumero') or '').strip(),
                'fecha_desde': r.get('InicioParcial'),
                'fecha_hasta': r.get('FinalParcial'),
                'comentario':  '',
                'materias':    [],
            }

        mat_nombre = str(r.get('Materia') or '').strip()
        tarea   = r.get('Tarea')
        cuadros = [r.get(f'Cuadro{i}') for i in range(1, 11)]
        alumnos[iid]['materias'].append({
            'nombre':  mat_nombre,
            'tarea':   tarea,
            'cuadros': cuadros,
        })
    return list(alumnos.values())


def _fmt_fecha(d):
    if not d:
        return ''
    if hasattr(d, 'strftime'):
        return d.strftime('%d/%m/%Y')
    return str(d)


# ─── Views ───────────────────────────────────────────────────────────────────

@login_required
@_superuser
def notas_index(request):
    from django.shortcuts import redirect as _redirect
    return _redirect('notas_parcial_coordinador')
    # vista heredada — ya no se usa directamente
    parcial  = request.GET.get('parcial', '')
    anio     = request.GET.get('anio', date.today().year)
    area     = request.GET.get('area', '')
    curso    = request.GET.get('curso', '')
    grado    = request.GET.get('grado', '')
    seccion  = request.GET.get('seccion', '')
    alumnos  = []
    grados   = []
    secciones = []
    error    = ''

    secciones_grado = []

    if parcial and area:
        if area == 'bachillerato' and not curso:
            error = 'Selecciona 1er o 2do año de Bachillerato.'
        else:
            rows, _ = _llamar_sp(area, parcial, anio, curso or None)
            if rows:
                todos     = _agrupar(rows)
                grados    = sorted({a['grado'] for a in todos})
                if grado:
                    en_grado        = [a for a in todos if a['grado'] == grado]
                    secciones_grado = sorted({a['grupo'] for a in en_grado})
                    alumnos = [a for a in en_grado if (not seccion or a['grupo'] == seccion)]
                else:
                    alumnos = todos
                ids = [a['ingr_egr_id'] for a in alumnos]
                comentarios_db = {
                    c.ingr_egr_id: c.comentario
                    for c in NotaComentario.objects.filter(
                        ingr_egr_id__in=ids, parcial=int(parcial), anio=int(anio), area=area,
                    )
                }
                for a in alumnos:
                    db_com = comentarios_db.get(a['ingr_egr_id'], '')
                    if db_com:
                        a['comentario'] = db_com
            else:
                error = 'No se obtuvieron datos. Verifica los parámetros o la conexión.'

    return render(request, 'notas_parcial/index.html', {
        'areas':           AREAS,
        'parcial':         parcial,
        'anio':            anio,
        'area':            area,
        'curso':           curso,
        'grado':           grado,
        'grados':          grados,
        'seccion':         seccion,
        'secciones_grado': secciones_grado,
        'alumnos':         alumnos,
        'error':           error,
    })


@login_required
@_solo_maestro
def grados_secciones(request):
    """AJAX: returns {grados, secciones} via direct table query (fast) with SP fallback."""
    area    = request.GET.get('area', '')
    parcial = request.GET.get('parcial', '')
    anio    = request.GET.get('anio', '')
    curso   = request.GET.get('curso', '') or None

    if not (area and parcial and anio):
        return JsonResponse({'grados': [], 'secciones': []})

    tabla = _TABLA_STAGING.get(area)
    if not tabla:
        return JsonResponse({'grados': [], 'secciones': []})

    try:
        with connections['padres_sqlserver'].cursor() as cursor:
            bach_filtro = f" AND CrsoNumero LIKE '{int(curso)}%'" if (area == 'bachillerato' and curso) else ''

            # 1. Exacto: mismo parcial y año
            sql = f"SELECT DISTINCT CrsoNumero, GrupoNumero FROM {tabla} WHERE Parcial={int(parcial)} AND Año={int(anio)}{bach_filtro}"
            cursor.execute(sql)
            rows = cursor.fetchall()

            # 2. Sin datos exactos: mismo año, cualquier parcial
            if not rows:
                sql = f"SELECT DISTINCT CrsoNumero, GrupoNumero FROM {tabla} WHERE Año={int(anio)}{bach_filtro}"
                cursor.execute(sql)
                rows = cursor.fetchall()

            # 3. Sin datos del año: el año más reciente disponible
            if not rows:
                sql = f"SELECT TOP 1 Año FROM {tabla} ORDER BY Año DESC"
                cursor.execute(sql)
                ultimo = cursor.fetchone()
                if ultimo:
                    sql = f"SELECT DISTINCT CrsoNumero, GrupoNumero FROM {tabla} WHERE Año={ultimo[0]}{bach_filtro}"
                    cursor.execute(sql)
                    rows = cursor.fetchall()

        grados    = sorted({str(r[0]).strip() for r in rows if r[0]})
        secciones = sorted({str(r[1]).strip() for r in rows if r[1]})
        return JsonResponse({'grados': grados, 'secciones': secciones})
    except Exception as e:
        print(f">>> grados_secciones error: {e}")
        return JsonResponse({'grados': [], 'secciones': []})


@login_required
@_solo_maestro
@require_POST
def guardar_comentario(request):
    try:
        data      = json.loads(request.body)
        iid       = int(data['ingr_egr_id'])
        parcial_v = int(data['parcial'])
        anio_v    = int(data['anio'])
        area_v    = data['area']
        comentario = data.get('comentario', '')
        NotaComentario.objects.update_or_create(
            ingr_egr_id=iid,
            parcial=parcial_v,
            anio=anio_v,
            area=area_v,
            defaults={'comentario': comentario, 'actualizado_por': request.user},
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@_solo_maestro
def generar_pdf(request):
    parcial = request.GET.get('parcial', '')
    anio    = request.GET.get('anio', date.today().year)
    area    = request.GET.get('area', '')
    curso   = request.GET.get('curso', '') or None
    grado   = request.GET.get('grado', '')
    seccion = request.GET.get('seccion', '')

    if not parcial or not area:
        return HttpResponse('Parámetros incompletos.', status=400)

    rows, _  = _llamar_sp(area, parcial, anio, curso)
    alumnos  = _agrupar(rows)
    if grado:
        alumnos = [a for a in alumnos if a['grado'] == grado]
    if seccion:
        alumnos = [a for a in alumnos if a['grupo'] == seccion]
    if not alumnos:
        return HttpResponse('Sin datos para los parámetros indicados.', status=404)

    # Leer comentarios del maestro desde BD Django
    ids = [a['ingr_egr_id'] for a in alumnos]
    comentarios_db = {
        c.ingr_egr_id: c.comentario
        for c in NotaComentario.objects.filter(
            ingr_egr_id__in=ids,
            parcial=int(parcial),
            anio=int(anio),
            area=area,
        )
    }
    for a in alumnos:
        db_com = comentarios_db.get(a['ingr_egr_id'], '')
        if db_com:
            a['comentario'] = db_com

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=letter)
    pdf.setTitle(f"Reporte Notas Parcial {parcial} {anio}.pdf")

    total = len(alumnos)
    for idx, alumno in enumerate(alumnos, 1):
        _dibujar_pagina(pdf, alumno, int(parcial), int(anio), idx, total)
        if idx < total:
            pdf.showPage()

    pdf.save()
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="notas_parcial_{parcial}_{anio}.pdf"'
    return resp


# ─── PDF helpers ─────────────────────────────────────────────────────────────

LOGO_PATH = os.path.join(settings.STATIC_ROOT, 'conducta', 'img', 'ana-transformed.png')

# Table column widths (mm)
_COL_ASIG   = 50
_COL_TAREAS = 14
_COL_E      = 11   # each Ei column
_NUM_E      = 10
_ROW_H      = 6
_HDR_H      = 8
_X0         = 10   # left margin


def _dibujar_tabla(pdf, materias, y_top):
    """Draw the grades table. Returns the Y position after the last row."""
    col_ws  = [_COL_ASIG, _COL_TAREAS] + [_COL_E] * _NUM_E
    headers = ['Asignatura', 'Tareas'] + [f'E{i}' for i in range(1, _NUM_E + 1)]
    total_w = sum(col_ws)
    x0      = _X0 * mm
    y       = y_top

    # Header row
    pdf.setFont('Helvetica-Bold', 8)
    x = x0
    for header, cw in zip(headers, col_ws):
        cw_pt = cw * mm
        pdf.rect(x, y - _HDR_H * mm, cw_pt, _HDR_H * mm, fill=0, stroke=1)
        if header == 'Asignatura':
            pdf.drawString(x + 2 * mm, y - _HDR_H * mm + 2 * mm, header)
        else:
            pdf.drawCentredString(x + cw_pt / 2, y - _HDR_H * mm + 2 * mm, header)
        x += cw_pt
    y -= _HDR_H * mm

    # Data rows
    pdf.setFont('Helvetica', 8)
    for i, mat in enumerate(materias):
        cuadros = mat.get('cuadros', [])
        tareas  = mat.get('tarea')
        evals   = cuadros[:_NUM_E]

        fill = colors.Color(0.95, 0.95, 0.95) if i % 2 == 1 else colors.white
        pdf.setFillColor(fill)
        pdf.rect(x0, y - _ROW_H * mm, total_w * mm, _ROW_H * mm, fill=1, stroke=0)
        pdf.setFillColor(colors.black)

        x = x0
        # Borders + content
        pdf.rect(x, y - _ROW_H * mm, _COL_ASIG * mm, _ROW_H * mm, fill=0, stroke=1)
        nombre = (mat.get('nombre') or '')[:38]
        pdf.drawString(x + 2 * mm, y - _ROW_H * mm + 2 * mm, nombre)
        x += _COL_ASIG * mm

        pdf.rect(x, y - _ROW_H * mm, _COL_TAREAS * mm, _ROW_H * mm, fill=0, stroke=1)
        if tareas is not None:
            try:
                pdf.setFillColor(colors.red if float(tareas) < 70 else colors.black)
            except (TypeError, ValueError):
                pdf.setFillColor(colors.black)
            pdf.drawCentredString(x + _COL_TAREAS * mm / 2, y - _ROW_H * mm + 2 * mm, str(tareas))
            pdf.setFillColor(colors.black)
        x += _COL_TAREAS * mm

        for j in range(_NUM_E):
            val = evals[j] if j < len(evals) else None
            pdf.rect(x, y - _ROW_H * mm, _COL_E * mm, _ROW_H * mm, fill=0, stroke=1)
            if val is not None:
                try:
                    pdf.setFillColor(colors.red if float(val) < 70 else colors.black)
                except (TypeError, ValueError):
                    pdf.setFillColor(colors.black)
                pdf.drawCentredString(x + _COL_E * mm / 2, y - _ROW_H * mm + 2 * mm, str(val))
                pdf.setFillColor(colors.black)
            x += _COL_E * mm

        y -= _ROW_H * mm

    return y


def _dibujar_pagina(pdf, alumno, parcial, anio, num_pag, total_pag):
    w, h = letter

    # ── Logo ──────────────────────────────────────────────────────
    logo_sz = 22 * mm
    if os.path.exists(LOGO_PATH):
        pdf.drawImage(LOGO_PATH, 10 * mm, h - 30 * mm, width=logo_sz, height=logo_sz, mask='auto')

    # ── Títulos centrados ─────────────────────────────────────────
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawCentredString(w / 2, h - 14 * mm, 'Centro Educativo Nuevo Amanecer')
    pdf.setFont('Helvetica', 10)
    pdf.drawCentredString(w / 2, h - 20 * mm, 'La Venta D.C.')
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawCentredString(w / 2, h - 28 * mm, 'Reporte de Notas a mitad de Parcial')

    # Línea separadora
    pdf.setLineWidth(0.5)
    pdf.line(10 * mm, h - 32 * mm, w - 10 * mm, h - 32 * mm)

    # ── Info fila 1 ───────────────────────────────────────────────
    y = h - 38 * mm
    area_grado = f"{alumno['area_curso']}  {alumno['grado']}  {alumno['grupo']}"

    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(10 * mm, y, 'Area y Grado:')
    pdf.setFont('Helvetica', 9)
    pdf.drawString(36 * mm, y, area_grado)

    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(120 * mm, y, 'Desde:')
    pdf.setFont('Helvetica', 9)
    pdf.drawString(134 * mm, y, _fmt_fecha(alumno.get('fecha_desde')))

    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(163 * mm, y, 'Parcial')
    pdf.setFont('Helvetica', 9)
    pdf.drawString(180 * mm, y, str(parcial))

    # ── Info fila 2 ───────────────────────────────────────────────
    y -= 6 * mm
    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(10 * mm, y, 'Alumno:')
    pdf.setFont('Helvetica', 9)
    pdf.drawString(26 * mm, y, alumno['nombre'])

    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(120 * mm, y, 'Hasta:')
    pdf.setFont('Helvetica', 9)
    pdf.drawString(134 * mm, y, _fmt_fecha(alumno.get('fecha_hasta')))

    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(163 * mm, y, 'Año')
    pdf.setFont('Helvetica', 9)
    pdf.drawString(174 * mm, y, str(anio))

    # ── Tabla ─────────────────────────────────────────────────────
    y_tabla = y - 5 * mm
    y_after  = _dibujar_tabla(pdf, alumno['materias'], y_tabla)

    # Nota "Todas las notas a base 100"
    y_nota = y_after - 3 * mm
    pdf.setFont('Helvetica-Oblique', 7)
    pdf.drawRightString(w - 10 * mm, y_nota, 'Todas las notas a base 100')

    # ── Comentarios ───────────────────────────────────────────────
    y_com = y_nota - 7 * mm
    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(10 * mm, y_com, 'Comentarios y sugerencias del Maestro:')
    y_com -= 6 * mm

    comentario = (alumno.get('comentario') or '').strip()
    if comentario:
        lineas = simpleSplit(comentario, 'Helvetica', 9, w - 20 * mm)
    else:
        lineas = []

    for i in range(6):
        if i < len(lineas):
            pdf.setFont('Helvetica', 9)
            pdf.drawString(10 * mm, y_com, lineas[i])
        pdf.setLineWidth(0.3)
        pdf.line(10 * mm, y_com - 1 * mm, w - 10 * mm, y_com - 1 * mm)
        y_com -= 6 * mm

    # ── Texto legal ───────────────────────────────────────────────
    y_legal = y_com - 5 * mm
    legal = (
        'El presente documento es una herramienta para facilitar el mejoramiento del desempeño '
        'de su hijo(a), favor de firmar y enviar de regreso lo más tarde el día viernes. '
        'Gracias por su colaboración.'
    )
    pdf.setFont('Helvetica', 8)
    for line in simpleSplit(legal, 'Helvetica', 8, w - 20 * mm):
        pdf.drawString(10 * mm, y_legal, line)
        y_legal -= 5 * mm

    # ── Firmas ────────────────────────────────────────────────────
    y_firma = y_legal - 24 * mm
    pdf.setLineWidth(0.5)
    pdf.line(10 * mm, y_firma + 8 * mm, 75 * mm, y_firma + 8 * mm)
    pdf.setFont('Helvetica', 9)
    pdf.drawCentredString(42 * mm, y_firma, 'Firma del Encargado')

    pdf.line(w / 2 + 5 * mm, y_firma + 8 * mm, w - 10 * mm, y_firma + 8 * mm)
    pdf.drawCentredString(w / 2 + 40 * mm, y_firma, 'Firma del Maestro')

    # ── Footer ────────────────────────────────────────────────────
    hoy      = date.today()
    fecha_es = f"{DIAS_ES[hoy.weekday()]} {hoy.day} de {MESES_ES[hoy.month - 1]} de {hoy.year}"
    pdf.setFont('Helvetica', 7)
    pdf.drawString(10 * mm, 8 * mm, fecha_es)
    pdf.drawRightString(w - 10 * mm, 8 * mm, f'Page {num_pag} of {total_pag}')


# ─── Vista Coordinador ───────────────────────────────────────────────────────

@login_required
@_coordinador
def coordinador_notas(request):
    parcial   = request.GET.get('parcial', '')
    anio      = request.GET.get('anio', date.today().year)
    area      = request.GET.get('area', '')
    curso     = request.GET.get('curso', '')
    grado     = request.GET.get('grado', '')
    seccion   = request.GET.get('seccion', '')
    alumnos   = []
    grados    = []
    secciones = []
    error     = ''
    asignaciones_dict = {}

    # Maestros disponibles para asignar — filtrados por área
    _areas_bl_keys = {a for a, _ in AREAS_BL}
    if area in _areas_bl_keys:
        _grupos_maestro_area = {'maestros_bilingue'}
    elif area in {a for a, _ in AREAS_COLEGIO}:
        _grupos_maestro_area = {'maestros_colegio'}
    else:
        _grupos_maestro_area = _GRUPOS_MAESTRO
    maestros = User.objects.filter(
        groups__name__in=_grupos_maestro_area
    ).distinct().order_by('first_name', 'last_name', 'username')

    secciones_grado = []

    if parcial and area:
        if area == 'bachillerato' and not curso:
            pass  # Course tabs in template handle user guidance
        else:
            rows, _ = _llamar_sp(area, parcial, anio, curso or None)
            if rows:
                todos  = _agrupar(rows)
                grados = sorted({a['grado'] for a in todos})
                if grado:
                    en_grado        = [a for a in todos if a['grado'] == grado]
                    secciones_grado = sorted({a['grupo'] for a in en_grado})
                    alumnos = [a for a in en_grado if (not seccion or a['grupo'] == seccion)]
                else:
                    alumnos = todos

                ids = [a['ingr_egr_id'] for a in alumnos]
                comentarios = {
                    c.ingr_egr_id: c.comentario
                    for c in NotaComentario.objects.filter(
                        ingr_egr_id__in=ids, parcial=int(parcial), anio=int(anio), area=area,
                    )
                }
                for a in alumnos:
                    a['comentario'] = comentarios.get(a['ingr_egr_id'], '')

                qs = AsignacionMaestro.objects.filter(
                    area=area, parcial=int(parcial), anio=int(anio)
                ).select_related('maestro')
                for asig in qs:
                    asignaciones_dict[(asig.grado, asig.seccion)] = asig
            else:
                error = 'No se obtuvieron datos. Verifica los parámetros o la conexión.'

    notificaciones = (
        RevisionFinalizada.objects
        .filter(leida=False)
        .select_related('maestro')
        .order_by('-fecha')
    )

    return render(request, 'notas_parcial/coordinador.html', {
        'areas':             AREAS,
        'parcial':           parcial,
        'anio':              anio,
        'area':              area,
        'curso':             curso,
        'grado':             grado,
        'grados':            grados,
        'seccion':           seccion,
        'secciones_grado':   secciones_grado,
        'alumnos':           alumnos,
        'error':             error,
        'maestros':          maestros,
        'asignaciones_dict': asignaciones_dict,
        'notificaciones':    notificaciones,
        'destinatarios':          _destinatarios_para(request.user),
        'solo_carrusel':          _es_solo_revision(request.user) and area in {'bl', 'colegio_bl'},
        'ocultar_asignaciones':   _es_solo_revision(request.user),
        'areas':                  _areas_para(request.user),
    })


@login_required
@_coordinador
@require_POST
def asignar_maestro_view(request):
    try:
        data     = json.loads(request.body)
        maestro_id = data.get('maestro_id')
        area     = data['area']
        parcial  = int(data['parcial'])
        anio     = int(data['anio'])
        grado    = data['grado']
        seccion  = data.get('seccion', '')

        if maestro_id:
            maestro = User.objects.get(pk=int(maestro_id))
            obj, created = AsignacionMaestro.objects.update_or_create(
                area=area, parcial=parcial, anio=anio, grado=grado, seccion=seccion,
                defaults={'maestro': maestro, 'asignado_por': request.user},
            )
            nombre = maestro.get_full_name() or maestro.username
        else:
            AsignacionMaestro.objects.filter(
                area=area, parcial=parcial, anio=anio, grado=grado, seccion=seccion
            ).delete()
            nombre = ''
        return JsonResponse({'ok': True, 'nombre': nombre})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


# ─── Vista Maestro ───────────────────────────────────────────────────────────

@login_required
@_solo_maestro
def maestro_notas(request):
    user = request.user
    # Coordinadores/superusers ven todas las asignaciones; maestros solo las suyas
    if _es_coordinador(user):
        asignaciones = AsignacionMaestro.objects.select_related('maestro').order_by(
            '-anio', 'parcial', 'area', 'grado', 'seccion'
        )
    else:
        asignaciones = AsignacionMaestro.objects.filter(maestro=user).order_by(
            '-anio', 'parcial', 'area', 'grado', 'seccion'
        )

    area_sel    = request.GET.get('area', '')
    parcial_sel = request.GET.get('parcial', '')
    anio_sel    = request.GET.get('anio', '')
    grado_sel   = request.GET.get('grado', '')
    seccion_sel = request.GET.get('seccion', '')
    curso_sel   = request.GET.get('curso', '')
    alumnos     = []
    error       = ''
    asig_activa = None

    if area_sel and parcial_sel and anio_sel:
        # Verificar que el maestro tenga asignación (o sea coordinador)
        if _es_coordinador(user):
            asig_activa = AsignacionMaestro.objects.filter(
                area=area_sel, parcial=int(parcial_sel), anio=int(anio_sel),
                grado=grado_sel, seccion=seccion_sel,
            ).first()
        else:
            asig_activa = AsignacionMaestro.objects.filter(
                maestro=user,
                area=area_sel, parcial=int(parcial_sel), anio=int(anio_sel),
                grado=grado_sel, seccion=seccion_sel,
            ).first()
            if not asig_activa:
                error = 'No tienes asignación para esos parámetros.'

        if not error:
            rows, _ = _llamar_sp(area_sel, parcial_sel, anio_sel, curso_sel or None)
            if rows:
                alumnos = _agrupar(rows)
                if grado_sel:
                    alumnos = [a for a in alumnos if a['grado'] == grado_sel]
                if seccion_sel:
                    alumnos = [a for a in alumnos if a['grupo'] == seccion_sel]
                # Cargar comentarios desde BD Django
                ids = [a['ingr_egr_id'] for a in alumnos]
                comentarios = {
                    c.ingr_egr_id: c.comentario
                    for c in NotaComentario.objects.filter(
                        ingr_egr_id__in=ids,
                        parcial=int(parcial_sel),
                        anio=int(anio_sel),
                        area=area_sel,
                    )
                }
                for a in alumnos:
                    a['comentario'] = comentarios.get(a['ingr_egr_id'], '')
            else:
                error = 'No se obtuvieron datos del SP.'

    area_label = dict(AREAS).get(area_sel, area_sel)

    return render(request, 'notas_parcial/maestro.html', {
        'asignaciones': asignaciones,
        'areas':        AREAS,
        'area_sel':     area_sel,
        'area_label':   area_label,
        'parcial_sel':  parcial_sel,
        'anio_sel':     anio_sel,
        'grado_sel':    grado_sel,
        'seccion_sel':  seccion_sel,
        'curso_sel':    curso_sel,
        'alumnos':      alumnos,
        'error':        error,
        'asig_activa':  asig_activa,
        'es_coord':     _es_coordinador(user),
    })


@login_required
@_solo_maestro
@require_POST
def finalizar_revision(request):
    try:
        data    = json.loads(request.body)
        area    = data['area']
        parcial = int(data['parcial'])
        anio    = int(data['anio'])
        grado   = data.get('grado', '')
        seccion = data.get('seccion', '')

        RevisionFinalizada.objects.update_or_create(
            maestro=request.user,
            area=area, parcial=parcial, anio=anio,
            grado=grado, seccion=seccion,
            defaults={'leida': False},
        )

        maestro_nombre = request.user.get_full_name() or request.user.username
        area_label     = dict(AREAS).get(area, area)

        _areas_bl_keys = {a for a, _ in AREAS_BL}
        if area in _areas_bl_keys:
            _grupos_email = _GRUPOS_BL - {'coord_progress_bl'}
        else:
            _grupos_email = _GRUPOS_COLEGIO | {'coordinadores', 'coord_notas_parcial'}
        coordinadores_emails = list(
            User.objects.filter(groups__name__in=_grupos_email)
            .exclude(email='').values_list('email', flat=True).distinct()
        )
        if coordinadores_emails:
            from urllib.parse import urlencode
            params = {'parcial': parcial, 'anio': anio, 'area': area}
            if grado:   params['grado']   = grado
            if seccion: params['seccion'] = seccion
            coord_url = request.build_absolute_uri(
                f'/notas-parcial/coordinador/?{urlencode(params)}'
            )
            asunto = f'Revisión completada – {maestro_nombre}'
            cuerpo = (
                f'El/la maestro/a {maestro_nombre} ha finalizado de ingresar comentarios a los reportes de notas:\n\n'
                f'  Área:    {area_label}\n'
                f'  Parcial: {parcial} / {anio}\n'
                f'  Grado:   {grado}  Sección: {seccion or "—"}\n\n'
                f'Haz clic en el siguiente enlace para revisar y generar el PDF:\n'
                f'{coord_url}'
            )
            send_mail(asunto, cuerpo, None, coordinadores_emails, fail_silently=True)

        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@_coordinador
@require_POST
def leer_notificacion(request):
    try:
        data = json.loads(request.body)
        pk   = int(data['pk'])
        RevisionFinalizada.objects.filter(pk=pk).update(leida=True)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@_coordinador
@require_POST
def enviar_pdf_email(request):
    """Genera el PDF y lo envía por correo a lchavez@ana-hn.org."""
    try:
        data         = json.loads(request.body)
        parcial      = data.get('parcial', '')
        anio         = data.get('anio', '')
        area         = data.get('area', '')
        curso        = data.get('curso') or None
        grado        = data.get('grado', '')
        seccion      = data.get('seccion', '')
        destinatario = data.get('destinatario', '')
    except Exception:
        parcial      = request.POST.get('parcial', '')
        anio         = request.POST.get('anio', '')
        area         = request.POST.get('area', '')
        curso        = request.POST.get('curso') or None
        grado        = request.POST.get('grado', '')
        seccion      = request.POST.get('seccion', '')
        destinatario = request.POST.get('destinatario', '')

    # Validar que el correo sea uno de los permitidos
    if destinatario not in _CORREOS_VALIDOS:
        destinos = _destinatarios_para(request.user)
        destinatario = destinos[0] if destinos else 'lchavez@ana-hn.org'

    if not parcial or not area:
        return JsonResponse({'ok': False, 'error': 'Parámetros incompletos.'})

    rows, _ = _llamar_sp(area, int(parcial), int(anio), curso)
    alumnos = _agrupar(rows)
    if grado:
        alumnos = [a for a in alumnos if a['grado'] == grado]
    if seccion:
        alumnos = [a for a in alumnos if a['grupo'] == seccion]
    if not alumnos:
        return JsonResponse({'ok': False, 'error': 'Sin datos para los parámetros indicados.'})

    ids = [a['ingr_egr_id'] for a in alumnos]
    comentarios_db = {
        c.ingr_egr_id: c.comentario
        for c in NotaComentario.objects.filter(
            ingr_egr_id__in=ids, parcial=int(parcial), anio=int(anio), area=area,
        )
    }
    for a in alumnos:
        a['comentario'] = comentarios_db.get(a['ingr_egr_id'], '')

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=letter)
    pdf.setTitle(f"Reporte Notas Parcial {parcial} {anio}.pdf")
    total = len(alumnos)
    for idx, alumno in enumerate(alumnos, 1):
        _dibujar_pagina(pdf, alumno, int(parcial), int(anio), idx, total)
        if idx < total:
            pdf.showPage()
    pdf.save()
    buf.seek(0)

    from django.core.mail import EmailMessage as DjangoEmailMessage
    area_label  = dict(AREAS).get(area, area)
    remitente   = request.user.get_full_name() or request.user.username
    asunto      = f'Reporte de Notas – Parcial {parcial}/{anio} – {area_label}'
    if grado:
        asunto += f' – Grado {grado}'
    if seccion:
        asunto += f' – Sección {seccion}'
    cuerpo = (
        f'Se adjunta el reporte de notas a mitad de parcial para imprimir.\n\n'
        f'Área:     {area_label}\n'
        f'Parcial:  {parcial} / {anio}\n'
        f'Grado:    {grado or "Todos"}\n'
        f'Sección:  {seccion or "Todas"}\n\n'
        f'Generado por: {remitente}'
    )
    mail = DjangoEmailMessage(subject=asunto, body=cuerpo, to=[destinatario])
    mail.attach(f'notas_parcial_{parcial}_{anio}.pdf', buf.getvalue(), 'application/pdf')
    try:
        mail.send()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
def notificaciones_json(request):
    if not _es_coordinador(request.user):
        return JsonResponse({'notificaciones': []})
    notifs = (
        RevisionFinalizada.objects
        .filter(leida=False)
        .select_related('maestro')
        .order_by('-fecha')
    )
    area_map = dict(AREAS)
    data = []
    for n in notifs:
        data.append({
            'pk':         n.pk,
            'maestro':    n.maestro.get_full_name() or n.maestro.username,
            'area':       n.area,
            'area_label': area_map.get(n.area, n.area),
            'parcial':    n.parcial,
            'anio':       n.anio,
            'grado':      n.grado,
            'seccion':    n.seccion,
            'fecha':      n.fecha.strftime('%d/%m/%Y %H:%M'),
        })
    return JsonResponse({'notificaciones': data})


# ─── Vista: Asignaciones del Coordinador ──────────────────────────────────────

@login_required
@_coordinador
def asignaciones_vista(request):
    """Lista de asignaciones con fecha límite y estado de cache por grupo."""
    areas_visibles = [a for a, _ in _areas_para(request.user)]
    qs = AsignacionMaestro.objects.filter(
        area__in=areas_visibles
    ).select_related(
        'maestro', 'asignado_por'
    ).order_by('-anio', 'parcial', 'area', 'grado', 'seccion')

    area_map = dict(AREAS)
    grupos = {}
    for a in qs:
        key = (a.area, a.parcial, a.anio)
        if key not in grupos:
            ck = _cache_key(a.area, a.parcial, a.anio, None)
            grupos[key] = {
                'area':       a.area,
                'area_label': area_map.get(a.area, a.area),
                'parcial':    a.parcial,
                'anio':       a.anio,
                'cached':     cache.get(ck) is not None,
                'items':      [],
            }
        grupos[key]['items'].append(a)

    return render(request, 'notas_parcial/asignaciones.html', {
        'grupos':   list(grupos.values()),
        'areas':    AREAS,
        'maestros': User.objects.filter(
            groups__name__in=_GRUPOS_MAESTRO
        ).distinct().order_by('first_name', 'last_name'),
    })


@login_required
@_coordinador
@require_POST
def actualizar_fecha_limite(request):
    """Actualiza o borra la fecha límite de una asignación."""
    try:
        data      = json.loads(request.body)
        asig      = AsignacionMaestro.objects.get(pk=int(data['id']))
        fecha_str = data.get('fecha_limite', '').strip()
        if fecha_str:
            from django.utils.dateparse import parse_datetime
            asig.fecha_limite = parse_datetime(fecha_str)
        else:
            asig.fecha_limite = None
        asig.save(update_fields=['fecha_limite'])
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@_coordinador
@require_POST
def eliminar_asignacion(request):
    """Elimina una AsignacionMaestro por pk."""
    try:
        data = json.loads(request.body)
        AsignacionMaestro.objects.filter(pk=int(data['id'])).delete()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@_coordinador
def precargar_cache(request):
    """Pre-carga el cache para un area/parcial/anio determinado."""
    area    = request.GET.get('area', '')
    parcial = request.GET.get('parcial', '')
    anio    = request.GET.get('anio', '')
    if not (area and parcial and anio):
        return JsonResponse({'ok': False, 'error': 'Faltan parámetros'})
    _llamar_sp(area, parcial, anio)
    return JsonResponse({'ok': True})


# ─── Vista: Revisión de Comentarios ───────────────────────────────────────────

@login_required
@_coordinador
def revision_comentarios_view(request):
    """Lista de comentarios con nombre de alumno, grados y edición/eliminación."""
    parcial   = request.GET.get('parcial', '')
    anio      = request.GET.get('anio', str(date.today().year))
    area      = request.GET.get('area', '')
    grado_sel = request.GET.get('grado', '')

    comentarios  = []
    alumnos_dict = {}
    grados       = []

    if parcial and area:
        todos_comentarios = list(
            NotaComentario.objects
            .filter(parcial=int(parcial), anio=int(anio), area=area)
            .select_related('actualizado_por')
            .order_by('-actualizado_en')
        )

        if todos_comentarios:
            rows, _ = _llamar_sp(area, parcial, anio)
            if rows:
                alumnos_dict = {a['ingr_egr_id']: a for a in _agrupar(rows)}
                ids_con_com  = {c.ingr_egr_id for c in todos_comentarios}
                grados = sorted({
                    alumnos_dict[iid]['grado']
                    for iid in ids_con_com if iid in alumnos_dict
                })

        base = todos_comentarios
        if grado_sel and alumnos_dict:
            ids_en_grado = {iid for iid, a in alumnos_dict.items() if a['grado'] == grado_sel}
            base = [c for c in todos_comentarios if c.ingr_egr_id in ids_en_grado]

        # Enriquecer cada comentario con datos del alumno
        comentarios = []
        for c in base:
            alumno = alumnos_dict.get(c.ingr_egr_id, {})
            comentarios.append({
                'obj':    c,
                'nombre': alumno.get('nombre', '—'),
                'grado':  alumno.get('grado', ''),
                'grupo':  alumno.get('grupo', ''),
            })

    return render(request, 'notas_parcial/revision_comentarios.html', {
        'areas':       AREAS,
        'parcial':     parcial,
        'anio':        anio,
        'area':        area,
        'grado_sel':   grado_sel,
        'grados':      grados,
        'comentarios': comentarios,
    })


@login_required
@_coordinador
@require_POST
def eliminar_comentario(request):
    """Elimina un NotaComentario por id."""
    try:
        data = json.loads(request.body)
        NotaComentario.objects.filter(pk=int(data['id'])).delete()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})
