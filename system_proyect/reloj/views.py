# ─────────────────────────────────────────────────────────────
# VIEWS · RELOJ (Asistencia con Plantillas de Horario)
# ─────────────────────────────────────────────────────────────
from django.shortcuts import render, get_object_or_404, redirect
import json
from django.db import connections, transaction, models
from django.urls import reverse
from django import forms
from datetime import datetime, time, date
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.dateparse import parse_date
from django.conf import settings
from django.views.decorators.http import require_GET
from django.http import HttpResponse
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from django.utils.dateparse import parse_date

# Modelos (plantillas + reglas + asignaciones + extras)
from .models import (
    ScheduleTemplate,
    ScheduleRule,
    EmployeeScheduleAssignment,
    OvertimeRequest,
    Feriado,
    SabadoEspecial,
    TiempoCompensatorio,
    PermisoEmpleado,
    ReporteNota,
    ReporteComentario,
    FeriadoAsignacion,
    CompensatorioCalculo,
    ReportePermisoMensual,
    PermisoReporte,
    TiempoExtraDia,
)

# Formularios
from .forms import (
    ScheduleTemplateForm,
    ScheduleRuleForm,
    RuleBulkForm,
    EmployeeScheduleAssignmentForm,
    FeriadoForm,
    SabadoEspecialForm,
    TiempoCompensatorioForm,
    PermisoEmpleadoForm,
    CompensatorioCalculoForm,
)


def _safe_date(value: str, default: str) -> str:
    """Valida que value sea una fecha ISO válida; devuelve default si no lo es.
    Previene SQL injection en queries que usan fechas de parámetros GET."""
    try:
        from datetime import date as _d
        return _d.fromisoformat(str(value)).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────
# Exportar PDF (placeholder)
# ─────────────────────────────────────────────────────────────

@login_required
def exportar_pdf(request):
    # Lee filtros GET igual que tu view de reporte
    hoy = datetime.today()
    _fi_def = hoy.replace(day=1).strftime('%Y-%m-%d')
    _ff_def = hoy.strftime('%Y-%m-%d')
    fecha_inicio = _safe_date(request.GET.get('fecha_inicio', _fi_def), _fi_def)
    fecha_fin    = _safe_date(request.GET.get('fecha_fin', _ff_def), _ff_def)
    emp_code_f = (request.GET.get('emp_code') or "").strip()

    datos = []
    columnas = []

    # Ejecuta el mismo query que tu reporte
    query = f"""
    DECLARE @fechaInicio DATE = '{fecha_inicio}';
    DECLARE @fechaFin    DATE = '{fecha_fin}';

    ;WITH fechas AS (
        SELECT @fechaInicio AS Fecha
        UNION ALL
        SELECT DATEADD(DAY, 1, Fecha)
        FROM fechas
        WHERE Fecha < @fechaFin
    ),
    marcas AS (
        SELECT
            CAST(t.emp_code AS VARCHAR(20)) AS emp_code,
            CONVERT(DATE, t.punch_time)     AS fecha,
            CONVERT(VARCHAR(5), CAST(t.punch_time AS TIME), 108) AS hora,
            t.punch_time
        FROM dbo.iclock_transaction t
        WHERE t.punch_time IS NOT NULL
    )
    SELECT 
        e.emp_code                               AS ID_Empleado,
        e.first_name + ' ' + e.last_name         AS Empleado,
        ISNULL(p.position_name, '-')             AS Cargo,
        f.Fecha,
        ISNULL((
            SELECT STRING_AGG(m2.hora, ', ') WITHIN GROUP (ORDER BY m2.punch_time)
            FROM marcas m2
            WHERE m2.emp_code = CAST(e.emp_code AS VARCHAR(20))
              AND m2.fecha    = f.Fecha
        ), '')                                   AS Marcas,
        COUNT(m.hora)                             AS Cantidad_Marcas,
        CASE WHEN COUNT(m.hora) = 0 THEN 'AUSENTE' ELSE 'PRESENTE' END AS Estado
    FROM fechas f
    CROSS JOIN dbo.personnel_employee e
    LEFT JOIN dbo.personnel_position p ON p.id = TRY_CONVERT(INT, e.position_id)
    LEFT JOIN marcas m
           ON m.emp_code = CAST(e.emp_code AS VARCHAR(20))
          AND m.fecha    = f.Fecha
    GROUP BY e.emp_code, e.first_name, e.last_name, p.position_name, f.Fecha
    ORDER BY e.last_name, e.first_name, f.Fecha
    OPTION (MAXRECURSION 0);
    """

    try:
        with connections['zkbio_sqlserver'].cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            columnas = [col[0] for col in cursor.description]
            for r in rows:
                row = dict(zip(columnas, r))
                if emp_code_f and str(row.get('ID_Empleado') or "").strip() != emp_code_f:
                    continue
                datos.append(row)
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}")

    # Cargar comentarios del rango para incluir en PDF
    from datetime import date as date_type
    try:
        fi_d = date_type.fromisoformat(fecha_inicio)
        ff_d = date_type.fromisoformat(fecha_fin)
    except ValueError:
        fi_d = ff_d = date_type.today()

    pdf_comentarios_map = {}
    for c in ReporteComentario.objects.filter(fecha__range=(fi_d, ff_d)):
        key = (str(c.emp_code).strip(), c.fecha)
        pdf_comentarios_map.setdefault(key, []).append(c.texto)

    # ----- PDF GENERATION -----
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'attachment; filename="reporte_asistencia.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    small_style = styles["Normal"].clone('small_style')
    small_style.fontSize = 8
    elements = []

    elements.append(Paragraph("Reporte de Asistencia", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Desde: {fecha_inicio} &nbsp;&nbsp;&nbsp; Hasta: {fecha_fin}", styles["Normal"]))
    elements.append(Spacer(1, 8))

    pdf_columnas = columnas + ["Comentarios"]
    data = [pdf_columnas]
    marcas_col_idx = columnas.index('Marcas') if 'Marcas' in columnas else None
    for row in datos:
        emp_code_r = str(row.get('ID_Empleado') or "").strip()
        fecha_r    = row.get('Fecha')
        comentarios_txt = " | ".join(pdf_comentarios_map.get((emp_code_r, fecha_r), []))
        fila = [str(row[c]) if row.get(c) is not None else "" for c in columnas]
        if marcas_col_idx is not None and fila[marcas_col_idx]:
            raw_marks = [m.strip() for m in fila[marcas_col_idx].split(',') if m.strip()]
            fila[marcas_col_idx] = ', '.join(_dedup_marcas_hora(raw_marks))
        data.append(fila + [comentarios_txt])

    col_count = len(pdf_columnas)
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (col_count-1,1), (col_count-1,-1), 'LEFT'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#34495E")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey]),
    ]))
    elements.append(table)
    doc.build(elements)
    return response
# ─────────────────────────────────────────────────────────────
# Utilidades generales
# ─────────────────────────────────────────────────────────────

def _is_ajax(request):
    """Devuelve True si la petición es AJAX (para respuestas JSON en modales)."""
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def staff_required(view_func):
    return login_required(user_passes_test(lambda u: u.is_staff or u.is_superuser)(view_func))


FMT_HHMM = "%H:%M"  # formato estándar HH:MM

def _to_hhmm(val):
    """
    Normaliza varios tipos (None/time/datetime/str) a cadena 'HH:MM'.
    - datetime aware -> se convierte a tz local y se formatea.
    - datetime naive -> se formatea directo.
    - str -> intenta parsear a HH:MM; si no, se retorna como viene.
    """
    if val is None:
        return None

    if isinstance(val, time):
        return val.strftime(FMT_HHMM)

    if isinstance(val, datetime):
        dt = val
        try:
            if timezone.is_aware(dt):
                dt = timezone.localtime(dt)
            return dt.strftime(FMT_HHMM)
        except Exception:
            return dt.replace(tzinfo=None).strftime(FMT_HHMM)

    if isinstance(val, str):
        s = val.strip()
        if len(s) >= 5 and len(s.split(":")[0]) in (1, 2) and s[2] == ':':
            # ya parece 'HH:MM...' (y soporta 'H:MM')
            # normaliza a 5 caracteres si viene 'H:MM'
            parts = s.split(":")
            hh = parts[0].zfill(2)
            mm = parts[1][:2]
            return f"{hh}:{mm}"
        for pat in ("%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(s, pat).strftime(FMT_HHMM)
            except Exception:
                continue
        return s

    try:
        return str(val)
    except Exception:
        return None


def _parse_hhmm_to_dt(hhmm):
    """Convierte 'HH:MM' en datetime (con fecha dummy de hoy) para poder restas/comparaciones."""
    if not hhmm:
        return None
    try:
        # Asegura dos dígitos en horas
        h, m = hhmm.split(":")
        hhmm = f"{int(h):02d}:{int(m):02d}"
        return datetime.strptime(hhmm, FMT_HHMM)
    except Exception:
        return None


def _mins_between(a_dt, b_dt):
    """Retorna los minutos (int) entre dos datetime."""
    return int((b_dt - a_dt).total_seconds() // 60)


def _dedup_marcas_hora(marcas: list, ventana_minutos: int = 5) -> list:
    """Elimina marcas duplicadas que llegaron dentro de `ventana_minutos` entre sí
    (doble toque accidental del reloj ZKBio). Marcas más separadas siempre se conservan."""
    if not marcas:
        return marcas
    deduped = [marcas[0]]
    for mk in marcas[1:]:
        try:
            t_prev = datetime.strptime(deduped[-1], '%H:%M')
            t_cur  = datetime.strptime(mk, '%H:%M')
            if abs((t_cur - t_prev).total_seconds()) > ventana_minutos * 60:
                deduped.append(mk)
        except Exception:
            deduped.append(mk)
    return deduped


def _sum_sched_minutes(segments):
    """
    Suma minutos programados de una lista de segmentos [(in_hhmm, out_hhmm), ...].
    Soporta turno partido (p. ej. mañana y tarde).
    """
    total = 0
    for hh_in, hh_out in segments:
        t_in = _parse_hhmm_to_dt(hh_in)
        t_out = _parse_hhmm_to_dt(hh_out)
        if t_in and t_out and t_out > t_in:
            total += _mins_between(t_in, t_out)
    return total


def _first_in_last_out(segments):
    """
    A partir de segmentos programados, devuelve:
    - primer_inicio ('HH:MM') para comparar llegadas
    - ultimo_fin    ('HH:MM') para comparar salidas
    Si no hay datos suficientes, retorna (None, None).
    """
    starts = [_parse_hhmm_to_dt(s[0]) for s in segments if s and s[0]]
    ends   = [_parse_hhmm_to_dt(s[1]) for s in segments if s and s[1]]
    starts = [s for s in starts if s]
    ends   = [e for e in ends if e]
    if not starts or not ends:
        return (None, None)
    return (min(starts).strftime(FMT_HHMM), max(ends).strftime(FMT_HHMM))


# ─────────────────────────────────────────────────────────────
# Helpers de PLANTILLAS/ASIGNACIONES para resolver horario del día
# ─────────────────────────────────────────────────────────────

def _plantilla_para_fecha(emp_code: str, fecha: date) -> int | None:
    """
    Devuelve el ID de la plantilla vigente para un empleado en 'fecha'.
    Reglas:
      - activo=True
      - fecha_inicio <= fecha <= fecha_fin (o fecha_fin es NULL)
    Si hay varias, prioriza la de fecha_inicio más reciente.
    """
    qs = (EmployeeScheduleAssignment.objects
          .filter(emp_code=emp_code, activo=True, fecha_inicio__lte=fecha)
          .order_by("-fecha_inicio"))
    for a in qs:
        if a.fecha_fin is None or a.fecha_fin >= fecha:
            return a.template_id
    return None


def _reglas_del_dia(template_id: int, weekday: int) -> ScheduleRule | None:
    """Devuelve la regla de la plantilla para un 'weekday' (0=Lunes ... 6=Domingo)."""
    try:
        return ScheduleRule.objects.get(template_id=template_id, weekday=weekday)
    except ScheduleRule.DoesNotExist:
        return None


def _segmentos_programados(emp_code: str, fecha: date):
    """
    Resuelve los segmentos programados para 'emp_code' en la 'fecha' dada.
    Retorna lista de tuplas [(entrada_hhmm, salida_hhmm), ...].
    Si el día no se trabaja o no hay plantilla, devuelve [].
    """
    tpl_id = _plantilla_para_fecha(emp_code, fecha)
    if not tpl_id:
        return []

    rule = _reglas_del_dia(tpl_id, fecha.weekday())
    if not rule or not rule.trabaja:
        return []

    segs = []
    if rule.entrada_manana and rule.salida_manana:
        segs.append((_to_hhmm(rule.entrada_manana), _to_hhmm(rule.salida_manana)))
    if rule.entrada_tarde and rule.salida_tarde:
        segs.append((_to_hhmm(rule.entrada_tarde), _to_hhmm(rule.salida_tarde)))
    return segs


# ─────────────────────────────────────────────────────────────
# Utilidad: obtener lista de empleados desde ZKBioTime (para combos)
# ─────────────────────────────────────────────────────────────

def get_empleados_zkbiotime():
    """
    Devuelve lista [(emp_code, 'Nombre Apellido')] para llenar dropdowns.
    Fuente: ZKBioTime (SQL Server).
    """
    with connections['zkbio_sqlserver'].cursor() as cursor:
        cursor.execute("""
            SELECT emp_code, first_name + ' ' + last_name AS nombre
            FROM dbo.personnel_employee
            ORDER BY first_name, last_name
        """)
        return cursor.fetchall()


# ─────────────────────────────────────────────────────────────
# Dashboard principal
# ─────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Renderiza el panel principal del módulo Reloj."""
    return render(request, 'reloj/dashboard.html')


# ─────────────────────────────────────────────────────────────
# Gráfica: detalle (modal) y totales (pastel)
# ─────────────────────────────────────────────────────────────

@login_required
def grafica_detalle(request):
    """
    (Modal) Devuelve JSON con filas por 'estado' entre fechas:
    - estado: 'PRESENTE' o 'AUSENTE'
    - fecha_inicio, fecha_fin: 'YYYY-MM-DD'
    Respuesta: {"success": bool, "error": str|None, "rows": [{emp_code, empleado, fecha, marcas}, ...]}
    """
    estado = (request.GET.get('estado') or 'PRESENTE').upper()
    hoy = datetime.today()
    fi_def = hoy.replace(day=1).strftime('%Y-%m-%d')
    ff_def = hoy.strftime('%Y-%m-%d')
    fecha_inicio = _safe_date(request.GET.get('fecha_inicio', fi_def), fi_def)
    fecha_fin    = _safe_date(request.GET.get('fecha_fin', ff_def), ff_def)

    rows_out, error = [], None

    if estado == 'PRESENTE':
        # Un registro por empleado/día, agregando TODAS las marcas ordenadas
        query = f"""
        DECLARE @fechaInicio DATE = '{fecha_inicio}';
        DECLARE @fechaFin    DATE = '{fecha_fin}';

        SELECT
            e.emp_code                                   AS emp_code,
            (e.first_name + ' ' + e.last_name)           AS empleado,
            CONVERT(DATE, t.punch_time)                  AS fecha,
            STRING_AGG(CONVERT(VARCHAR(5), CAST(t.punch_time AS TIME), 108), ', ')
                WITHIN GROUP (ORDER BY t.punch_time)     AS marcas
        FROM dbo.iclock_transaction t
        INNER JOIN dbo.personnel_employee e ON e.emp_code = t.emp_code
        WHERE t.punch_time >= @fechaInicio
          AND t.punch_time <  DATEADD(DAY, 1, @fechaFin)
        GROUP BY e.emp_code, e.first_name, e.last_name, CONVERT(DATE, t.punch_time)
        ORDER BY fecha, e.emp_code;
        """
        try:
            with connections['zkbio_sqlserver'].cursor() as cursor:
                cursor.execute(query)
                for emp_code, empleado, fecha, marcas in cursor.fetchall():
                    rows_out.append({
                        "emp_code": str(emp_code),
                        "empleado": empleado,
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "marcas": marcas or ""
                    })
        except Exception as e:
            error = str(e)

    else:  # AUSENTE
        # Universo de empleados × fechas MENOS los que marcaron
        query = f"""
        DECLARE @fechaInicio DATE = '{fecha_inicio}';
        DECLARE @fechaFin    DATE = '{fecha_fin}';

        ;WITH fechas AS (
            SELECT @fechaInicio AS f
            UNION ALL
            SELECT DATEADD(DAY, 1, f) FROM fechas WHERE f < @fechaFin
        ),
        presentes AS (
            SELECT DISTINCT t.emp_code, CONVERT(DATE, t.punch_time) AS fecha
            FROM dbo.iclock_transaction t
            WHERE t.punch_time >= @fechaInicio
              AND t.punch_time <  DATEADD(DAY, 1, @fechaFin)
        )
        SELECT
            e.emp_code                         AS emp_code,
            (e.first_name + ' ' + e.last_name) AS empleado,
            f.f                                AS fecha
        FROM dbo.personnel_employee e
        CROSS JOIN fechas f
        LEFT JOIN presentes p
               ON p.emp_code = e.emp_code AND p.fecha = f.f
        WHERE p.emp_code IS NULL
        ORDER BY f.f, e.emp_code
        OPTION (MAXRECURSION 0);
        """
        try:
            with connections['zkbio_sqlserver'].cursor() as cursor:
                cursor.execute(query)
                for emp_code, empleado, fecha in cursor.fetchall():
                    rows_out.append({
                        "emp_code": str(emp_code),
                        "empleado": empleado,
                        "fecha": fecha.strftime("%Y-%m-%d"),
                        "marcas": ""  # ausentes no tienen marcas
                    })
        except Exception as e:
            error = str(e)

    return JsonResponse({"success": error is None, "error": error, "rows": rows_out})


@login_required
def grafica(request):
    """
    (Vista) Renderiza la página de gráfico pastel:
    - Cuenta PRESENTE si hay al menos una marca por empleado/día en el rango,
      de lo contrario AUSENTE. Muestra totales en el pastel.
    """
    hoy = datetime.today()
    fecha_inicio_default = hoy.replace(day=1).strftime('%Y-%m-%d')
    fecha_fin_default    = hoy.strftime('%Y-%m-%d')

    fecha_inicio = _safe_date(request.GET.get('fecha_inicio', fecha_inicio_default), fecha_inicio_default)
    fecha_fin    = _safe_date(request.GET.get('fecha_fin', fecha_fin_default), fecha_fin_default)

    presentes = 0
    ausentes  = 0
    error     = None

    query = f"""
    DECLARE @fechaInicio DATE = '{fecha_inicio}';
    DECLARE @fechaFin    DATE = '{fecha_fin}';

    ;WITH fechas AS (
        SELECT @fechaInicio AS Fecha
        UNION ALL
        SELECT DATEADD(DAY, 1, Fecha)
        FROM fechas
        WHERE Fecha < @fechaFin
    ),
    estado_dia AS (
        SELECT
            e.emp_code,
            f.Fecha,
            CASE 
                WHEN EXISTS (
                    SELECT 1
                    FROM dbo.iclock_transaction t
                    WHERE t.emp_code = e.emp_code
                      AND CONVERT(DATE, t.punch_time) = f.Fecha
                )
                THEN 'PRESENTE' ELSE 'AUSENTE'
            END AS Estado
        FROM fechas f
        CROSS JOIN dbo.personnel_employee e
    )
    SELECT Estado, COUNT(*) AS Total
    FROM estado_dia
    GROUP BY Estado
    OPTION (MAXRECURSION 0);
    """

    try:
        with connections['zkbio_sqlserver'].cursor() as cursor:
            cursor.execute(query)
            for estado, total in cursor.fetchall():
                est = (estado or '').upper()
                if est == 'PRESENTE':
                    presentes = int(total or 0)
                elif est == 'AUSENTE':
                    ausentes = int(total or 0)
    except Exception as e:
        error = f"Error al consultar la base de datos: {str(e)}"

    contexto = {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'presentes': presentes,
        'ausentes': ausentes,
        'error': error,
    }
    return render(request, 'reloj/grafica.html', contexto)



# ─────────────────────────────────────────────────────────────
# Reporte de marcas diarias por empleado (STRING_AGG)
# ─────────────────────────────────────────────────────────────

def get_empleado_options():
    """Genera opciones para el <select> de empleado [(emp_code, "emp_code - Nombre"), ...]."""
    opciones = []
    with connections['zkbio_sqlserver'].cursor() as cursor:
        cursor.execute("""
            SELECT CAST(emp_code AS VARCHAR(20)) AS code,
                   (first_name + ' ' + last_name) AS nombre
            FROM dbo.personnel_employee
            ORDER BY first_name, last_name
        """)
        for code, nombre in cursor.fetchall():
            code = (code or "").strip()
            nombre = (nombre or "").strip()
            opciones.append((code, f"{code} - {nombre}"))
    return opciones


@login_required
def reporte(request):
    """
    Reporte principal de marcas con horario programado, chips coloreados y comentarios.
    Columnas: ID Empleado | Empleado | Horario Programado | Fecha |
              Marcas del Día | Cantidad Marcas | Comentario | Estado
    """
    hoy = datetime.today()
    fecha_inicio_default = hoy.replace(day=1).strftime('%Y-%m-%d')
    fecha_fin_default    = hoy.strftime('%Y-%m-%d')

    fecha_inicio = _safe_date(request.GET.get('fecha_inicio', fecha_inicio_default), fecha_inicio_default)
    fecha_fin    = _safe_date(request.GET.get('fecha_fin', fecha_fin_default), fecha_fin_default)
    emp_code_f   = (request.GET.get('emp_code') or "").strip()

    datos = []
    error = None

    if request.GET.get('fecha_inicio') and request.GET.get('fecha_fin'):
        # SQL simplificado: sin Cargo, solo datos base por empleado/día
        query = f"""
DECLARE @fechaInicio DATE = '{fecha_inicio}';
DECLARE @fechaFin    DATE = '{fecha_fin}';

;WITH fechas AS (
    SELECT @fechaInicio AS Fecha
    UNION ALL
    SELECT DATEADD(DAY, 1, Fecha)
    FROM fechas
    WHERE Fecha < @fechaFin
)
SELECT
    e.emp_code                        AS ID_Empleado,
    e.first_name + ' ' + e.last_name  AS Empleado,
    f.Fecha,
    MIN(t.punch_time)                  AS Hora_Entrada,
    MAX(t.punch_time)                  AS Hora_Salida,
    COUNT(t.punch_time)                AS Cantidad_Marcas,
    CASE WHEN COUNT(t.punch_time) = 0 THEN 'AUSENTE' ELSE 'PRESENTE' END AS Estado
FROM fechas f
CROSS JOIN dbo.personnel_employee e
LEFT JOIN dbo.iclock_transaction t
       ON t.emp_code = e.emp_code
      AND CONVERT(DATE, t.punch_time) = f.Fecha
GROUP BY e.emp_code, e.first_name, e.last_name, f.Fecha
ORDER BY e.last_name, e.first_name, f.Fecha
OPTION (MAXRECURSION 0);
"""
        try:
            with connections['zkbio_sqlserver'].cursor() as cursor:
                cursor.execute(query)
                rows      = cursor.fetchall()
                columnas  = [col[0] for col in cursor.description]

            # Marcas individuales por empleado/día (para chips coloreados)
            marcas_map = {}
            try:
                with connections['zkbio_sqlserver'].cursor() as cur2:
                    cur2.execute(f"""
                        SELECT
                            CAST(t.emp_code AS VARCHAR(20)) AS emp_code,
                            CONVERT(DATE, t.punch_time)     AS fecha,
                            CONVERT(VARCHAR(5), CAST(t.punch_time AS TIME), 108) AS hhmm
                        FROM dbo.iclock_transaction t
                        WHERE CONVERT(DATE, t.punch_time) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                        ORDER BY t.emp_code, t.punch_time
                    """)
                    for emp_m, fecha_m, hhmm in cur2.fetchall():
                        marcas_map.setdefault((str(emp_m).strip(), fecha_m), []).append(hhmm)
            except Exception as ex:
                print(f"[WARN] marcas_map reporte: {ex}")

            # Notas/comentarios en bulk para el rango
            from datetime import date as date_type
            try:
                fi_d = date_type.fromisoformat(fecha_inicio)
                ff_d = date_type.fromisoformat(fecha_fin)
            except ValueError:
                fi_d = ff_d = hoy.date()

            comentarios_map = {}
            for c in ReporteComentario.objects.filter(fecha__range=(fi_d, ff_d)):
                comentarios_map.setdefault((c.emp_code, c.fecha), []).append(
                    {'pk': c.pk, 'texto': c.texto}
                )

            # Mapa de feriados: (emp_code, date) -> descripcion
            from datetime import timedelta as _td2
            feriados_map_r = {}
            try:
                for asig in FeriadoAsignacion.objects.filter(
                    feriado__fecha_inicio__lte=ff_d,
                    feriado__fecha_fin__gte=fi_d,
                ).select_related("feriado"):
                    d = asig.feriado.fecha_inicio
                    while d <= asig.feriado.fecha_fin:
                        if fi_d <= d <= ff_d:
                            feriados_map_r[(asig.emp_code.strip(), d)] = asig.feriado.descripcion
                        d += _td2(days=1)
            except Exception as _ex:
                print(f"[WARN] feriados_map reporte: {_ex}")

            DEF_IN, DEF_OUT = "07:00", "16:48"

            # Diagnóstico: tipo de fecha_d (temporal)
            if rows:
                _muestra = dict(zip(columnas, rows[0]))
                _fd_muestra = _muestra.get('Fecha')
                print(f"[DIAG reporte] tipo fecha_d={type(_fd_muestra)} valor={_fd_muestra} "
                      f"total_rows={len(rows)} feriados_map_size={len(feriados_map_r)}")

            for r in rows:
                row      = dict(zip(columnas, r))
                emp_code = str(row.get('ID_Empleado') or "").strip()
                fecha_d  = row.get('Fecha')

                # Normalizar a datetime.date para comparaciones seguras
                from datetime import datetime as _dt_cls, date as _date_cls
                if isinstance(fecha_d, _dt_cls):
                    fecha_d = fecha_d.date()

                # Filtro por empleado
                if emp_code_f and emp_code != emp_code_f:
                    continue

                # Feriado asignado
                es_feriado = feriados_map_r.get((emp_code, fecha_d)) if fecha_d else None

                # Filtro por horario: omitir días que el empleado no trabaja
                # (excepto si marcó físicamente ese día o es feriado asignado)
                cantidad_marcas = int(row.get('Cantidad_Marcas') or 0)
                if cantidad_marcas == 0 and not es_feriado:
                    tpl_id = _plantilla_para_fecha(emp_code, fecha_d)
                    if tpl_id:
                        rule = _reglas_del_dia(tpl_id, fecha_d.weekday())
                        if not rule or not rule.trabaja:
                            continue
                    else:
                        # Sin plantilla → solo omitir fines de semana
                        if fecha_d.weekday() >= 5:
                            continue

                # Horario programado
                segs = _segmentos_programados(emp_code, fecha_d)
                if segs:
                    prog_first_in, prog_last_out = _first_in_last_out(segs)
                    no_programado = False
                else:
                    prog_first_in, prog_last_out = DEF_IN, DEF_OUT
                    no_programado = True

                # Colores de entrada / salida
                h_in_real  = _to_hhmm(row.get('Hora_Entrada'))
                h_out_real = _to_hhmm(row.get('Hora_Salida'))

                color_in_class  = ""
                color_out_class = ""
                try:
                    if h_in_real and prog_first_in:
                        tin_real = _parse_hhmm_to_dt(h_in_real)
                        tin_prog = _parse_hhmm_to_dt(prog_first_in)
                        color_in_class = "hora-verde" if tin_real <= tin_prog else "hora-rojo"
                    if h_out_real and prog_last_out:
                        tout_real = _parse_hhmm_to_dt(h_out_real)
                        tout_prog = _parse_hhmm_to_dt(prog_last_out)
                        if tout_real > tout_prog:
                            color_out_class = "hora-azul"
                        elif tout_real == tout_prog:
                            color_out_class = "hora-verde"
                        else:
                            color_out_class = "hora-rojo"
                except Exception:
                    pass

                # Chips coloreados — deduplicar marcas en la misma hora del reloj (mismo HH)
                key = (emp_code, fecha_d)
                marcas_list = _dedup_marcas_hora(marcas_map.get(key, []))
                marcas_coloreadas = []
                for idx, t_mark in enumerate(marcas_list):
                    cls = ""
                    if idx == 0:
                        cls = color_in_class
                    elif idx == len(marcas_list) - 1:
                        cls = color_out_class
                    marcas_coloreadas.append({'t': t_mark, 'cls': cls})

                row['No_Programado']    = no_programado
                row['Horario_Prog']     = f"{prog_first_in} → {prog_last_out}" if not no_programado else ""
                row['Marcas_Dia']       = marcas_coloreadas
                row['Cantidad_Marcas']  = len(marcas_coloreadas)
                row['Comentarios']      = comentarios_map.get((emp_code, fecha_d), [])
                row['Es_Feriado']       = bool(es_feriado)
                row['Feriado_Desc']     = es_feriado or ""
                # Sort key por apellido para DataTables
                nombre_e = str(row.get('Empleado') or '')
                partes_e = nombre_e.rsplit(' ', 1)
                row['Empleado_Sort'] = (partes_e[-1] + ' ' + partes_e[0]).lower() if len(partes_e) > 1 else nombre_e.lower()
                datos.append(row)

        except Exception as e:
            error = f"Error al consultar la base de datos: {str(e)}"

    # Mapa de permisos registrados → {"emp_code|YYYY-MM-DD": [PermisoReporte, ...]}
    permisos_map = {}
    if datos:
        from datetime import date as _d
        try:
            fi_p = _d.fromisoformat(fecha_inicio)
            ff_p = _d.fromisoformat(fecha_fin)
        except ValueError:
            fi_p = ff_p = date.today()
        from datetime import timedelta as _td
        for p in PermisoReporte.objects.filter(fecha__range=(fi_p, ff_p)):
            ec = (p.emp_code or '').strip()
            if emp_code_f and ec != emp_code_f:
                continue
            # Expandir el permiso a cada día del rango fecha..fecha_fin
            fin = p.fecha_fin if p.fecha_fin else p.fecha
            cur = p.fecha
            while cur <= fin:
                key = f"{ec}|{cur.isoformat()}"
                permisos_map.setdefault(key, []).append(p)
                cur += _td(days=1)

    # Serializar para JS: {emp_code|fecha: [{pk, tipo, dias, razon, comentario}, ...]}
    import json as _json
    permisos_json = {}
    for key, lista in permisos_map.items():
        permisos_json[key] = [
            {'pk': p.pk, 'tipo': p.tipo, 'dias': str(p.dias),
             'razon': p.razon, 'comentario': p.comentario,
             'fecha': p.fecha.isoformat(),
             'fecha_fin': p.fecha_fin.isoformat() if p.fecha_fin else None,
             'horas': str(p.horas) if p.horas is not None else None}
            for p in lista
        ]

    u = request.user
    can_edit_permisos   = u.is_staff or u.is_superuser
    can_delete_permisos = u.is_superuser or getattr(u, 'email', '') == 'glorenzo@ana-hn.org'

    contexto = {
        'datos': datos,
        'error': error,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'empleados_opts': get_empleado_options(),
        'emp_code_f': emp_code_f,
        'campos_permiso': CAMPOS_PERMISO,
        'permisos_json': _json.dumps(permisos_json),
        'can_edit_permisos':   can_edit_permisos,
        'can_delete_permisos': can_delete_permisos,
    }
    return render(request, 'reloj/reporte.html', contexto)


# ──────────────────────────────────────────────────────────────
# AJAX → Comentarios múltiples en Generar Reporte (máx. 5)
# ──────────────────────────────────────────────────────────────
@require_POST
@login_required
def comentario_add_ajax(request):
    from datetime import date as date_type
    emp_code  = request.POST.get('emp_code', '').strip()
    fecha_str = request.POST.get('fecha', '').strip()
    texto     = request.POST.get('texto', '').strip()

    if not emp_code or not fecha_str or not texto:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'}, status=400)

    try:
        fecha = date_type.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

    if ReporteComentario.objects.filter(emp_code=emp_code, fecha=fecha).count() >= 5:
        return JsonResponse({'ok': False, 'error': 'Máximo 5 comentarios por registro'}, status=400)

    obj = ReporteComentario.objects.create(
        emp_code=emp_code, fecha=fecha, texto=texto, creado_por=request.user
    )
    return JsonResponse({'ok': True, 'pk': obj.pk, 'texto': obj.texto})


@require_POST
@login_required
def comentario_delete_ajax(request, pk):
    obj = get_object_or_404(ReporteComentario, pk=pk)
    obj.delete()
    return JsonResponse({'ok': True})


@require_POST
@login_required
def reporte_nota_ajax(request):
    """Endpoint legacy — conservado para compatibilidad."""
    return JsonResponse({'ok': False, 'error': 'Usar comentario_add_ajax'}, status=410)


# ─────────────────────────────────────────────────────────────
# CRUD · Plantillas y Reglas (con creación en lote)
# ─────────────────────────────────────────────────────────────

@login_required
def plantilla_list(request):
    """Lista de plantillas de horario (con enlace para editar y agregar reglas)."""
    plantillas = ScheduleTemplate.objects.all().order_by("nombre")
    return render(request, "reloj/plantilla_list.html", {"plantillas": plantillas})


@login_required
def plantilla_edit(request, pk=None):
    """
    Crear/editar una plantilla. Si existe, muestra sus reglas.
    """
    plantilla = get_object_or_404(ScheduleTemplate, pk=pk) if pk else None
    if request.method == "POST":
        form = ScheduleTemplateForm(request.POST, instance=plantilla)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Plantilla guardada.")
            return redirect("reloj_plantilla_edit", pk=obj.pk)
    else:
        form = ScheduleTemplateForm(instance=plantilla)

    reglas = ScheduleRule.objects.filter(template=plantilla).order_by("weekday") if plantilla else []
    return render(request, "reloj/plantilla_form.html", {"form": form, "plantilla": plantilla, "reglas": reglas})


@login_required
def regla_add(request, template_pk):
    """
    Crea/actualiza reglas **en lote** para varios días a la vez con checkboxes.
    - Si ya existe la regla (template, weekday), se actualiza.
    - Si no existe, se crea.
    """
    plantilla = get_object_or_404(ScheduleTemplate, pk=template_pk)

    if request.method == "POST":
        form = RuleBulkForm(request.POST)
        if form.is_valid():
            weekdays = form.cleaned_data["weekdays"]      # lista de ints
            trabaja  = form.cleaned_data["trabaja"]
            em = form.cleaned_data["entrada_manana"]
            sm = form.cleaned_data["salida_manana"]
            et = form.cleaned_data["entrada_tarde"]
            st = form.cleaned_data["salida_tarde"]

            creadas, actualizadas = 0, 0
            with transaction.atomic():
                for wd in weekdays:
                    obj, created = ScheduleRule.objects.update_or_create(
                        template=plantilla,
                        weekday=wd,
                        defaults={
                            "trabaja": trabaja,
                            "entrada_manana": em if trabaja else None,
                            "salida_manana": sm if trabaja else None,
                            "entrada_tarde": et if trabaja else None,
                            "salida_tarde": st if trabaja else None,
                        }
                    )
                    if created:
                        creadas += 1
                    else:
                        actualizadas += 1

            messages.success(
                request,
                f"Reglas guardadas: Creadas {creadas}, Actualizadas {actualizadas}."
            )
            return redirect("reloj_plantilla_edit", plantilla.pk)
    else:
        # Por defecto marca L-V
        form = RuleBulkForm(initial={"weekdays": [0,1,2,3,4], "trabaja": True})

    return render(request, "reloj/regla_form.html", {
        "form": form,
        "plantilla": plantilla,
        "bulk": True,   # bandera para que el template muestre checkboxes
    })


@login_required
def regla_edit(request, pk):
    """
    Edición individual de una regla existente (un solo día).
    """
    regla = get_object_or_404(ScheduleRule, pk=pk)
    if request.method == "POST":
        form = ScheduleRuleForm(request.POST, instance=regla)
        if form.is_valid():
            form.save()
            messages.success(request, "Regla actualizada.")
            return redirect("reloj_plantilla_edit", pk=regla.template.pk)
    else:
        form = ScheduleRuleForm(instance=regla)
    return render(request, "reloj/regla_form.html", {"form": form, "plantilla": regla.template, "bulk": False})


# ─────────────────────────────────────────────────────────────
# CRUD · Asignaciones (esto reemplaza “horarios por empleado”)
# Mantengo nombres horarios_list/add/edit para no romper tus URLs
# ─────────────────────────────────────────────────────────────

@login_required
def horarios_list(request):
    """
    Lista de asignaciones de plantilla por empleado.
    (Sustituye a la antigua lista de 'EmployeeSchedule'). 
    """
    asignaciones = sorted(
        EmployeeScheduleAssignment.objects.select_related("template").order_by("-activo", "-fecha_inicio"),
        key=lambda a: (not a.activo, (a.nombre_empleado or '').rsplit(' ', 1)[-1].lower())
    )

    # Dropdown de empleados (ZKBioTime)
    empleados = get_empleados_zkbiotime()
    EMPLEADOS_CHOICES = [('', '--- Selecciona ---')] + [
        (str(e[0]), f"{e[0]} - {e[1]}") for e in empleados
    ]

    # Form para modal "crear"
    class _AsignacionCustomForm(EmployeeScheduleAssignmentForm):
        # 'nombre_empleado' lo llenamos desde la etiqueta del select
        emp_code = forms.ChoiceField(
            choices=EMPLEADOS_CHOICES,
            label="Empleado",
            widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_emp_dropdown'})
        )

    form = _AsignacionCustomForm()

    return render(request, 'reloj/horarios_list.html', {
        'asignaciones': asignaciones,
        'form': form,
    })


@login_required
def horarios_add(request):
    """
    Alta de asignación de plantilla a empleado (modal o página completa).
    """
    empleados = get_empleados_zkbiotime()
    EMPLEADOS_CHOICES = [('', '--- Selecciona ---')] + [
        (str(e[0]), f"{e[0]} - {e[1]}") for e in empleados
    ]

    class _AsignacionCustomForm(EmployeeScheduleAssignmentForm):
        emp_code = forms.ChoiceField(
            choices=EMPLEADOS_CHOICES,
            label="Empleado",
            widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_emp_dropdown'})
        )

    if request.method == 'POST':
        form = _AsignacionCustomForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)

            # Copia “nombre_empleado” desde la etiqueta del select
            emp_code_val = form.cleaned_data['emp_code']
            label = dict(form.fields['emp_code'].choices).get(emp_code_val, emp_code_val)
            instance.nombre_empleado = label.split(' - ', 1)[1].strip() if ' - ' in label else label

            instance.save()
            if _is_ajax(request):
                return JsonResponse({'success': True})
            messages.success(request, "Asignación creada.")
            return redirect('horarios_list')
        else:
            if _is_ajax(request):
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = _AsignacionCustomForm()

    return render(request, 'reloj/asignacion_form.html', {'form': form, 'modo': 'Agregar'})


@login_required
def horarios_edit(request, pk):
    """
    Edición de una asignación existente (modal o página completa).
    """
    asignacion = get_object_or_404(EmployeeScheduleAssignment, pk=pk)

    empleados = get_empleados_zkbiotime()
    EMPLEADOS_CHOICES = [('', '--- Selecciona ---')] + [
        (str(e[0]), f"{e[0]} - {e[1]}") for e in empleados
    ]

    class _AsignacionCustomForm(EmployeeScheduleAssignmentForm):
        emp_code = forms.ChoiceField(
            choices=EMPLEADOS_CHOICES,
            label="Empleado",
            widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_emp_dropdown'})
        )

    if request.method == 'POST':
        form = _AsignacionCustomForm(request.POST, instance=asignacion)
        if form.is_valid():
            instance = form.save(commit=False)

            emp_code_val = form.cleaned_data['emp_code']
            label = dict(form.fields['emp_code'].choices).get(emp_code_val, emp_code_val)
            instance.nombre_empleado = label.split(' - ', 1)[1].strip() if ' - ' in label else label

            instance.save()
            if _is_ajax(request):
                return JsonResponse({'success': True})
            messages.success(request, "Asignación actualizada.")
            return redirect('horarios_list')
        else:
            if _is_ajax(request):
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = _AsignacionCustomForm(instance=asignacion)
        # Preselección del empleado actual
        form.fields['emp_code'].initial = str(asignacion.emp_code)

    # AJAX GET → retorna solo el contenido del modal (parcial)
    if _is_ajax(request):
        return render(request, 'reloj/_asignacion_edit_modal.html', {
            'form': form,
            'asignacion': asignacion,
        })

    return render(request, 'reloj/asignacion_form.html', {
        'form': form,
        'modo': 'Editar',
        'asignacion': asignacion,
    })


# ─────────────────────────────────────────────────────────────
# Test de conexión a SQL Server (útil para validar ODBC)
# ─────────────────────────────────────────────────────────────

@login_required
def test_sqlserver_connection(request):
    """
    Ejecuta una consulta mínima en ZKBioTime para validar la conexión.
    Muestra un mensaje en pantalla sobre el estado (OK / ERROR).
    """
    try:
        with connections['zkbio_sqlserver'].cursor() as cursor:
            cursor.execute("SELECT TOP 1 emp_code, first_name FROM dbo.personnel_employee")
            row = cursor.fetchone()
            msg = f"Conexión OK: {row}"
    except Exception as e:
        msg = f"ERROR de conexión: {e}"
    return render(request, 'reloj/test_sql.html', {'mensaje': msg})


# ─────────────────────────────────────────────────────────────
# Tiempo por hora (comparación real vs programado por PLANTILLA)
# ─────────────────────────────────────────────────────────────

def _fmt_mins(m: int) -> str:
    """Devuelve 'Xh Ym' o 'M min' para mostrar minutos bonitos."""
    m = int(m or 0)
    if m <= 0:
        return "0 min"
    h, mm = divmod(m, 60)
    return f"{h}h {mm}m" if h else f"{mm} min"




# ─────────────────────────────────────────────────────────────
# AUTORIZAR TIEMPO EXTRA (JSON)
# ─────────────────────────────────────────────────────────────

@staff_required
@require_POST
def overtime_authorize(request):
    """
    Autoriza/Rechaza minutos de tiempo extra.
    Espera JSON:
      { "emp_code":"0001", "fecha":"YYYY-MM-DD", "minutos": 30, "status":"APPR"|"REJC", "comentario": "opc" }
    Devuelve JSON: { success, msg }
    """
    try:
        data = request.POST or {}
        # Soporta JSON en body
        if request.content_type.startswith("application/json"):
            import json
            data = json.loads(request.body.decode("utf-8"))
        emp_code = (data.get("emp_code") or "").strip()
        fecha = parse_date(data.get("fecha") or "")
        minutos = int(data.get("minutos") or 0)
        status = (data.get("status") or "APPR").upper()
        comentario = (data.get("comentario") or "").strip()

        if status not in ("APPR", "REJC"):
            return JsonResponse({"success": False, "msg": "Estado inválido."}, status=400)
        if not (emp_code and fecha is not None):
            return JsonResponse({"success": False, "msg": "Datos incompletos."}, status=400)
        if minutos < 0:
            minutos = 0

        ot, _ = OvertimeRequest.objects.get_or_create(emp_code=emp_code, fecha=fecha)
        ot.minutos_autorizados = minutos if status == "APPR" else 0
        ot.status = status
        ot.comentario = comentario
        ot.approved_by = request.user
        ot.approved_at = timezone.now()
        ot.save()
        return JsonResponse({"success": True, "msg": "Actualizado."})
    except Exception as e:
        return JsonResponse({"success": False, "msg": str(e)}, status=500)


# ─────────────────────────────────────────────────────────────
# GOOGLE FORMS HOOK · Tiempo compensatorio
# ─────────────────────────────────────────────────────────────

def _parse_date_flexible(s: str):
    """Acepta 'YYYY-MM-DD', 'DD/MM/YYYY' o 'MM/DD/YYYY' y retorna date (o None)."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

@require_GET
def compensatorio_employees_list(request):
    # Auth por el mismo token compartido
    token = request.headers.get("X-Forms-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != getattr(settings, "GOOGLE_FORMS_SHARED_TOKEN", ""):
        return JsonResponse({"ok": False, "error": "Forbidden"}, status=403)

    rows = []
    try:
        with connections['zkbio_sqlserver'].cursor() as c:
            c.execute("""
                SELECT CAST(emp_code AS VARCHAR(20)) AS code,
                       (first_name + ' ' + last_name) AS nombre
                FROM dbo.personnel_employee
                ORDER BY first_name, last_name
            """)
            rows = c.fetchall()
    except Exception as ex:
        return JsonResponse({"ok": False, "error": f"SQL error: {ex}"}, status=500)

    choices = [{"code": (code or "").strip(),
                "label": f"{(code or '').strip()} — {(nombre or '').strip()}"} for code, nombre in rows]

    return JsonResponse({"ok": True, "choices": choices})

@csrf_exempt
@require_POST
def compensatorio_google_hook(request):
    """
    Endpoint para Google Forms (Apps Script).
    - Auth: Authorization: Bearer <TOKEN>  (y fallbacks X-Forms-Token, ?token=)
    - JSON: {emp_code, fecha, minutos_registrados, motivo, ...}
    - Resuelve nombre_empleado oficial desde ZKBioTime.
    """
    # --- Auth robusto por token compartido ---
    expected = getattr(settings, "GOOGLE_FORMS_SHARED_TOKEN", "")
    raw = (
        request.headers.get("Authorization")
        or request.META.get("HTTP_AUTHORIZATION")
        or request.headers.get("X-Forms-Token")
        or request.GET.get("token")
    )
    token = ""
    if raw:
        token = raw.split(" ", 1)[1].strip() if str(raw).startswith("Bearer ") else str(raw).strip()

    if not token:
        return JsonResponse({"success": False, "error": "Falta token"}, status=401)
    if token != expected:
        return JsonResponse({"success": False, "error": "Token inválido"}, status=403)

    # --- Parse body ---
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except Exception as ex:
        return JsonResponse({"success": False, "error": f"JSON inválido: {ex}"}, status=400)

    emp_code = (data.get("emp_code") or "").strip()
    if not emp_code:
        return JsonResponse({"success": False, "error": "emp_code requerido"}, status=400)

    fecha = _parse_date_flexible((data.get("fecha") or "").strip())
    if not fecha:
        return JsonResponse({"success": False, "error": "fecha inválida"}, status=400)

    try:
        minutos = int(data.get("minutos_registrados") or 0)
        if minutos < 0:
            minutos = 0
    except Exception:
        return JsonResponse({"success": False, "error": "minutos_registrados inválido"}, status=400)

    motivo = (data.get("motivo") or "").strip()

    # --- Resolver nombre oficial desde ZKBioTime ---
    try:
        with connections["zkbio_sqlserver"].cursor() as c:
            c.execute(
                """
                SELECT (first_name + ' ' + last_name) AS nombre
                FROM dbo.personnel_employee
                WHERE CAST(emp_code AS VARCHAR(20)) = %s
                """,
                [emp_code],
            )
            row = c.fetchone()
    except Exception as ex:
        return JsonResponse({"success": False, "error": f"Error SQLServer: {ex}"}, status=500)

    if not row:
        return JsonResponse({"success": False, "error": "emp_code no existe en ZKBioTime"}, status=400)

    nombre_oficial = (row[0] or "").strip()

    # --- Crear/actualizar registro (clave emp_code+fecha) ---
    obj = TiempoCompensatorio.objects.create(
        emp_code=emp_code,
        nombre_empleado=nombre_oficial,
        fecha=fecha,
     minutos_registrados=minutos,
        motivo=motivo,
    )
    created = True


    return JsonResponse({
        "success": True,
        "created": created,
        "id": obj.id,
        "emp_code": emp_code,
        "nombre": nombre_oficial,
        "fecha": fecha.isoformat(),
        "minutos": minutos,
    })

# ─────────────────────────────────────────────────────────────
# CRUD · Feriados
# ─────────────────────────────────────────────────────────────

@staff_required
def feriados_list(request):
    from django.db.models import Count
    feriados = Feriado.objects.annotate(total_asignados=Count("asignaciones")).order_by("-fecha_inicio")
    return render(request, "reloj/feriados_list.html", {"feriados": feriados})


@staff_required
def feriado_new(request):
    if request.method == "POST":
        form = FeriadoForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.creado_por = request.user
            obj.save()
            messages.success(request, "Feriado creado.")
            return redirect("reloj_feriado_edit", pk=obj.pk)
    else:
        form = FeriadoForm()
    return render(request, "reloj/feriado_form.html", {"form": form, "modo": "Agregar"})


@staff_required
def feriado_edit(request, pk):
    obj = get_object_or_404(Feriado, pk=pk)
    if request.method == "POST":
        form = FeriadoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Feriado actualizado.")
            return redirect("reloj_feriado_edit", pk=obj.pk)
    else:
        form = FeriadoForm(instance=obj)
    asignados_codes = set(
        FeriadoAsignacion.objects.filter(feriado=obj).values_list("emp_code", flat=True)
    )
    try:
        empleados_opts = get_empleado_options()
    except Exception:
        empleados_opts = []
    # Marcar cuáles ya están asignados para los checkboxes
    empleados_check = [
        {"code": code, "label": label, "checked": code in asignados_codes}
        for code, label in empleados_opts
    ]
    return render(request, "reloj/feriado_form.html", {
        "form": form, "modo": "Editar", "obj": obj,
        "empleados_check": empleados_check,
        "total_asignados": len(asignados_codes),
    })


@staff_required
def feriado_delete(request, pk):
    obj = get_object_or_404(Feriado, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Feriado eliminado.")
        return redirect("reloj_feriados_list")
    return render(request, "reloj/confirm_delete.html", {"obj": obj, "titulo": "Eliminar feriado"})


@staff_required
@require_POST
def feriado_asignacion_bulk(request, pk):
    """Guarda la selección completa de checkboxes: agrega los nuevos, quita los desmarcados."""
    feriado = get_object_or_404(Feriado, pk=pk)
    selected = set(filter(None, (c.strip() for c in request.POST.getlist("emp_codes"))))
    existing = set(FeriadoAsignacion.objects.filter(feriado=feriado).values_list("emp_code", flat=True))

    to_add    = selected - existing
    to_remove = existing - selected

    # Quitar desmarcados
    FeriadoAsignacion.objects.filter(feriado=feriado, emp_code__in=to_remove).delete()

    # Obtener nombres de nuevos en una sola consulta
    nombres = {}
    if to_add:
        try:
            placeholders = ",".join(["%s"] * len(to_add))
            with connections["zkbio_sqlserver"].cursor() as c:
                c.execute(
                    f"SELECT CAST(emp_code AS VARCHAR(20)), first_name + ' ' + last_name "
                    f"FROM dbo.personnel_employee WHERE CAST(emp_code AS VARCHAR(20)) IN ({placeholders})",
                    list(to_add)
                )
                for code, nombre in c.fetchall():
                    nombres[(code or "").strip()] = (nombre or "").strip()
        except Exception:
            pass

    for emp_code in to_add:
        FeriadoAsignacion.objects.create(
            feriado=feriado,
            emp_code=emp_code,
            nombre_empleado=nombres.get(emp_code, ""),
            asignado_por=request.user,
        )

    return JsonResponse({
        "ok": True,
        "added": len(to_add),
        "removed": len(to_remove),
        "total": len(selected),
    })


# ─────────────────────────────────────────────────────────────
# CRUD · Sábados especiales
# ─────────────────────────────────────────────────────────────

@staff_required
def sabados_list(request):
    qs = SabadoEspecial.objects.all().order_by("-fecha")
    paginator = Paginator(qs, 20)
    page = request.GET.get("page")
    sabados = paginator.get_page(page)
    return render(request, "reloj/sabados_list.html", {"sabados": sabados})


@staff_required
def sabado_new(request):
    if request.method == "POST":
        form = SabadoEspecialForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.creado_por = request.user
            obj.save()
            messages.success(request, "Sábado especial creado.")
            return redirect("reloj_sabados_list")
    else:
        form = SabadoEspecialForm()
    return render(request, "reloj/sabado_form.html", {"form": form, "modo": "Agregar"})


@staff_required
def sabado_edit(request, pk):
    obj = get_object_or_404(SabadoEspecial, pk=pk)
    if request.method == "POST":
        form = SabadoEspecialForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Sábado especial actualizado.")
            return redirect("reloj_sabados_list")
    else:
        form = SabadoEspecialForm(instance=obj)
    return render(request, "reloj/sabado_form.html", {"form": form, "modo": "Editar", "obj": obj})


@staff_required
def sabado_delete(request, pk):
    obj = get_object_or_404(SabadoEspecial, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Sábado especial eliminado.")
        return redirect("reloj_sabados_list")
    return render(request, "reloj/confirm_delete.html", {"obj": obj, "titulo": "Eliminar sábado especial"})


# ─────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────
# Tiempo compensatorio · calculado desde ZKTeco (solo asistentes)
# ─────────────────────────────────────────────────────────────

_HORA_CORTE = time(15, 48)  # a partir de aquí se cuenta como compensatorio

# Empleados con cálculo especial: mañana (antes de inicio) + tarde (después de corte)
_EMP_HORARIO_ESPECIAL = {
    '75': {  # Nancy Alvarado
        'manana_inicio_seg': 6 * 3600 + 40 * 60,  # 06:40 — inicio fijo mañana (llegar antes cuenta igual)
        'manana_corte_seg':  7 * 3600,             # 07:00 — fin del bloque mañana
        'manana_max_min':    20,                   # máx. 20 min mañana
        'tarde_corte_seg':   15 * 3600 + 48 * 60, # 15:48 — inicio del bloque tarde
        'tarde_max_min':     27,                   # máx. 27 min tarde
    }
}

def _t_to_seg(t_val) -> int:
    """Convierte un valor time/timedelta a segundos desde medianoche."""
    if t_val is None:
        return 0
    if hasattr(t_val, 'seconds'):
        return t_val.seconds
    return t_val.hour * 3600 + t_val.minute * 60 + getattr(t_val, 'second', 0)

def _comp_min_dia(ec: str, primera_seg: int, ultima_seg: int, tope: int):
    """Retorna (total_comp_min, completo) para un empleado en un día."""
    regla = _EMP_HORARIO_ESPECIAL.get(str(ec))
    if regla:
        # Truncar a minutos y aplicar inicio fijo: si llegó antes de 06:40 cuenta igual que 06:40
        primera_min = (primera_seg // 60) * 60
        manana_inicio = regla.get('manana_inicio_seg', 0)
        manana_start = max(primera_min, manana_inicio)
        manana = max(0, min(regla['manana_corte_seg'] - manana_start, regla['manana_max_min'] * 60)) // 60
        tarde  = max(0, min(ultima_seg - regla['tarde_corte_seg'],    regla['tarde_max_min']  * 60)) // 60
        total  = manana + tarde
        completo = manana >= regla['manana_max_min'] and tarde >= regla['tarde_max_min']
        return total, completo
    else:
        diff = ultima_seg - (_HORA_CORTE.hour * 3600 + _HORA_CORTE.minute * 60)
        if diff <= 0:
            return 0, False
        total = min(diff // 60, tope)
        return total, total >= tope

@login_required
def compensatorio_list(request):
    hoy = date.today()
    _fi_def = hoy.replace(day=1).strftime("%Y-%m-%d")
    _ff_def = hoy.strftime("%Y-%m-%d")
    fecha_inicio_str = _safe_date(request.GET.get("fecha_inicio") or _fi_def, _fi_def)
    fecha_fin_str    = _safe_date(request.GET.get("fecha_fin")    or _ff_def, _ff_def)
    emp_code_f       = (request.GET.get("emp_code") or "").strip()

    # Empleados activos con "horario asistentes"
    asistentes_qs = (
        EmployeeScheduleAssignment.objects
        .filter(template__nombre__icontains="asistente", activo=True)
        .values_list("emp_code", "nombre_empleado")
    )
    emp_map = {code: nombre for code, nombre in asistentes_qs}  # {code: nombre}
    codigos = list(emp_map.keys())

    if emp_code_f:
        codigos = [c for c in codigos if c == emp_code_f]

    # Tope de minutos por empleado (desde CompensatorioCalculo)
    topes_emp = {
        obj.emp_code: obj.minutos_autorizados_dia
        for obj in CompensatorioCalculo.objects.filter(emp_code__in=codigos)
    }

    filas = []
    error = None

    if codigos:
        codigos_sql = ", ".join(f"'{c}'" for c in codigos)
        query = f"""
        DECLARE @fi DATE = '{fecha_inicio_str}';
        DECLARE @ff DATE = '{fecha_fin_str}';

        SELECT
            t.emp_code,
            CONVERT(DATE, t.punch_time)   AS fecha,
            STRING_AGG(
                CONVERT(VARCHAR(5), CAST(t.punch_time AS TIME), 108), ', ')
                WITHIN GROUP (ORDER BY t.punch_time) AS marcas,
            MIN(CAST(t.punch_time AS TIME)) AS primera_marca,
            MAX(CAST(t.punch_time AS TIME)) AS ultima_marca
        FROM dbo.iclock_transaction t
        WHERE t.punch_time >= @fi
          AND t.punch_time <  DATEADD(DAY, 1, @ff)
          AND t.emp_code IN ({codigos_sql})
        GROUP BY t.emp_code, CONVERT(DATE, t.punch_time)
        ORDER BY fecha DESC, t.emp_code;
        """
        try:
            with connections["zkbio_sqlserver"].cursor() as cursor:
                cursor.execute(query)
                for emp_code, fecha, marcas, primera, ultima in cursor.fetchall():
                    ec           = str(emp_code).strip()
                    primera_seg  = _t_to_seg(primera)
                    ultima_seg   = _t_to_seg(ultima)
                    tope_emp     = topes_emp.get(ec, 47)
                    total_comp_min, completo = _comp_min_dia(ec, primera_seg, ultima_seg, tope_emp)
                    tiene_comp   = total_comp_min > 0
                    horas_comp   = total_comp_min // 60
                    minutos_comp = total_comp_min % 60
                    ult_str = str(ultima)[:5] if hasattr(ultima, 'seconds') else ultima.strftime("%H:%M")
                    # Desglose mañana/tarde para empleados con horario especial
                    regla_esp = _EMP_HORARIO_ESPECIAL.get(ec)
                    if regla_esp:
                        primera_min    = (primera_seg // 60) * 60
                        man_inicio     = regla_esp.get('manana_inicio_seg', 0)
                        man_start      = max(primera_min, man_inicio)
                        manana_min = max(0, min(regla_esp['manana_corte_seg'] - man_start, regla_esp['manana_max_min'] * 60)) // 60
                        tarde_min  = max(0, min(ultima_seg - regla_esp['tarde_corte_seg'],  regla_esp['tarde_max_min']  * 60)) // 60
                        manana_max = regla_esp['manana_max_min']
                        tarde_max  = regla_esp['tarde_max_min']
                    else:
                        manana_min = None
                        tarde_min  = None
                        manana_max = None
                        tarde_max  = None
                    filas.append({
                        "emp_code":     emp_code,
                        "nombre":       emp_map.get(ec, ec),
                        "fecha":        fecha,
                        "marcas":       marcas or "",
                        "ultima_marca": ult_str,
                        "horas":        horas_comp,
                        "minutos":      minutos_comp,
                        "tiene_comp":   tiene_comp,
                        "completo":     completo,
                        "tope":         tope_emp,
                        "manana_min":   manana_min,
                        "tarde_min":    tarde_min,
                        "manana_max":   manana_max,
                        "tarde_max":    tarde_max,
                    })
        except Exception as exc:
            error = str(exc)

    # Totales para empleado individual
    total_min_emp = sum(
        f['horas'] * 60 + f['minutos']
        for f in filas if f['tiene_comp']
    )
    total_dias_emp = sum(1 for f in filas if f['tiene_comp'])

    # Extras por día registrados manualmente
    fi_date = date.fromisoformat(fecha_inicio_str)
    ff_date = date.fromisoformat(fecha_fin_str)
    extras_qs = TiempoExtraDia.objects.filter(
        fecha__gte=fi_date, fecha__lte=ff_date,
    )
    if emp_code_f:
        extras_qs = extras_qs.filter(emp_code=emp_code_f)
    extra_map = {(str(e.emp_code), str(e.fecha)): e for e in extras_qs}

    for f in filas:
        ec_str = str(f['emp_code'])
        fe_str = str(f['fecha'])
        ex = extra_map.get((ec_str, fe_str))
        f['extra_pk']           = ex.pk if ex else None
        f['extra_min']          = ex.minutos if ex else 0
        f['extra_razon']        = ex.razon if ex else ''
        f['extra_comentario']   = ex.comentario if ex else ''
        f['extra_autorizado_por'] = ex.autorizado_por if ex else ''

    u = request.user
    can_edit_extra = u.is_superuser or getattr(u, 'email', '') == 'glorenzo@ana-hn.org'

    return render(request, "reloj/compensatorio_list.html", {
        "filas":            filas,
        "emp_map":          emp_map,
        "fecha_inicio":     fecha_inicio_str,
        "fecha_fin":        fecha_fin_str,
        "emp_code_f":       emp_code_f,
        "error":            error,
        "hora_corte":       "15:48",
        "total_min_emp":    total_min_emp,
        "total_horas_emp":  total_min_emp // 60,
        "total_mins_emp":   total_min_emp % 60,
        "total_dias_emp":   total_dias_emp,
        "can_edit_extra":   can_edit_extra,
    })


@login_required
@require_POST
def compensatorio_list_set_extra(request):
    """AJAX: guarda tiempo extra autorizado por día para un empleado."""
    u = request.user
    if not (u.is_superuser or getattr(u, 'email', '') == 'glorenzo@ana-hn.org'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    try:
        body = json.loads(request.body or b'{}')
    except Exception:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    emp_code       = (body.get('emp_code') or '').strip()
    fecha_str      = (body.get('fecha') or '').strip()
    minutos        = int(body.get('minutos') or 0)
    razon          = (body.get('razon') or '').strip()[:300]
    comentario     = (body.get('comentario') or '').strip()
    autorizado_por = (body.get('autorizado_por') or '').strip()[:200]

    if not emp_code or not fecha_str:
        return JsonResponse({'ok': False, 'error': 'Faltan datos'}, status=400)
    if minutos < 0:
        minutos = 0

    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

    obj, _ = TiempoExtraDia.objects.get_or_create(
        emp_code=emp_code, fecha=fecha,
        defaults={'registrado_por': u}
    )
    obj.minutos        = minutos
    obj.razon          = razon
    obj.comentario     = comentario
    obj.autorizado_por = autorizado_por
    obj.registrado_por = u
    obj.save()

    return JsonResponse({
        'ok':            True,
        'pk':            obj.pk,
        'minutos':       minutos,
        'razon':         razon,
        'comentario':    comentario,
        'autorizado_por': autorizado_por,
    })


@staff_required
def compensatorio_authorize(request, pk):
    obj = get_object_or_404(TiempoCompensatorio, pk=pk)
    if request.method == "POST":
        estado = request.POST.get("estado")
        minutos = int(request.POST.get("minutos_autorizados") or 0)
        comentario = (request.POST.get("comentario") or "").strip()
        obj.estado = estado
        obj.minutos_autorizados = minutos
        obj.comentario_autorizacion = comentario
        obj.autorizado_por = request.user
        obj.autorizado_en = timezone.now()
        obj.save()
        messages.success(request, "Tiempo compensatorio autorizado correctamente.")
        return redirect("reloj_compensatorio_list")
    return render(request, "reloj/compensatorio_authorize.html", {"obj": obj})



@login_required
def compensatorio_new(request):
    if request.method == "POST":
        form = TiempoCompensatorioForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.registrado_por = request.user
            obj.estado = "PEND"
            obj.save()
            messages.success(request, "Tiempo compensatorio registrado (pendiente).")
            return redirect("reloj_compensatorio_list")
    else:
        form = TiempoCompensatorioForm()
    return render(request, "reloj/compensatorio_form.html", {"form": form, "modo": "Agregar"})


@staff_required
def compensatorio_edit(request, pk):
    obj = get_object_or_404(TiempoCompensatorio, pk=pk)
    if request.method == "POST":
        form = TiempoCompensatorioForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro actualizado.")
            return redirect("reloj_compensatorio_list")
    else:
        form = TiempoCompensatorioForm(instance=obj)
    return render(request, "reloj/compensatorio_form.html", {"form": form, "modo": "Editar", "obj": obj})


@staff_required
def compensatorio_delete(request, pk):
    obj = get_object_or_404(TiempoCompensatorio, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Registro eliminado.")
        return redirect("reloj_compensatorio_list")
    return render(request, "reloj/confirm_delete.html", {"obj": obj, "titulo": "Eliminar registro de tiempo compensatorio"})


# ─────────────────────────────────────────────────────────────
# CRUD · Permisos
# ─────────────────────────────────────────────────────────────

@login_required
def permisos_list(request):
    qs = PermisoEmpleado.objects.all().order_by("-fecha_inicio", "emp_code")
    emp_code_f = (request.GET.get("emp_code") or "").strip()
    if emp_code_f:
        qs = qs.filter(emp_code__iexact=emp_code_f)
    paginator = Paginator(qs, 25)
    page = request.GET.get("page")
    items = paginator.get_page(page)
    return render(request, "reloj/permisos_list.html", {"items": items, "emp_code_f": emp_code_f})


@login_required
def permiso_new(request):
    if request.method == "POST":
        form = PermisoEmpleadoForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.registrado_por = request.user
            obj.save()
            messages.success(request, "Permiso registrado (pendiente de aprobación).")
            return redirect("reloj_permisos_list")
    else:
        form = PermisoEmpleadoForm()
    return render(request, "reloj/permiso_form.html", {"form": form, "modo": "Agregar"})


@staff_required
def permiso_edit(request, pk):
    obj = get_object_or_404(PermisoEmpleado, pk=pk)
    if request.method == "POST":
        form = PermisoEmpleadoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Permiso actualizado.")
            return redirect("reloj_permisos_list")
    else:
        form = PermisoEmpleadoForm(instance=obj)
    return render(request, "reloj/permiso_form.html", {"form": form, "modo": "Editar", "obj": obj})


@staff_required
@require_POST
def permiso_approve(request, pk):
    """Aprobar/rechazar permiso rápido (AJAX o POST normal)."""
    obj = get_object_or_404(PermisoEmpleado, pk=pk)
    action = (request.POST.get("action") or "").lower()
    comentario = (request.POST.get("comentario") or "").strip()
    if action not in ("aprobar", "rechazar"):
        return HttpResponseBadRequest("Acción inválida")
    obj.aprobado = (action == "aprobar")
    obj.autorizado_por = request.user
    if comentario:
        obj.comentario_autorizacion = comentario
    obj.save()
    if _is_ajax(request):
        return JsonResponse({"success": True, "aprobado": obj.aprobado})
    messages.success(request, "Permiso actualizado.")
    return redirect("reloj_permisos_list")


@staff_required
def permiso_delete(request, pk):
    obj = get_object_or_404(PermisoEmpleado, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Permiso eliminado.")
        return redirect("reloj_permisos_list")
    return render(request, "reloj/confirm_delete.html", {"obj": obj, "titulo": "Eliminar permiso"})


# ─────────────────────────────────────────────────────────────
# Cálculo de tiempo compensatorio (fecha fin por empleado)
# ─────────────────────────────────────────────────────────────
import math as _math

MINUTOS_POR_DIA_COMP = 47
JORNADA_MIN = 528  # 8.8 horas


def _calcular_fecha_fin(fecha_inicio, dias_adeudados, feriados=None, minutos_dia=None):
    from datetime import timedelta
    feriados = feriados or set()
    if minutos_dia is None or minutos_dia <= 0:
        minutos_dia = MINUTOS_POR_DIA_COMP
    minutos = float(dias_adeudados) * JORNADA_MIN
    dias_hab = _math.ceil(minutos / minutos_dia)
    fecha = fecha_inicio
    contados = 0
    while contados < dias_hab:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5 and fecha not in feriados:
            contados += 1
    return fecha, int(minutos), dias_hab


def _contar_dias_habiles_rango(desde, hasta, feriados=None):
    """Días hábiles lun–vie desde 'desde' (inclusive) hasta 'hasta' (exclusive)."""
    from datetime import timedelta
    feriados = feriados or set()
    count, d = 0, desde
    while d < hasta:
        if d.weekday() < 5 and d not in feriados:
            count += 1
        d += timedelta(days=1)
    return count


_ESPECIALES_COMP = ['zuniga', 'caceres', 'banegas', 'alvarado']
_ESPECIALES_ORDEN = ['zuniga', 'caceres', 'banegas', 'alvarado']

def _especial_rank(nombre):
    n = nombre.lower()
    for i, key in enumerate(_ESPECIALES_ORDEN):
        if key in n:
            return i
    return len(_ESPECIALES_ORDEN)

@login_required
def compensatorio_calculo_list(request):
    from datetime import timedelta as _td
    hoy = date.today()
    _CORTE_SEG = _HORA_CORTE.hour * 3600 + _HORA_CORTE.minute * 60

    # Construir set de feriados
    feriados = set()
    for f in Feriado.objects.all():
        d = f.fecha_inicio
        while d <= f.fecha_fin:
            feriados.add(d)
            d += _td(days=1)

    todos_registros = list(CompensatorioCalculo.objects.all())

    # ── Consultar marcas reales del ZKBio para todos los empleados ──────────
    # Obtiene la última marca de cada empleado/día desde la fecha_inicio más
    # antigua hasta hoy, y suma los minutos reales de compensatorio.
    real_comp_map = {}  # {emp_code: total_min_real}
    if todos_registros:
        fechas_inicio_map = {str(r.emp_code): r.fecha_inicio for r in todos_registros}
        topes_map         = {str(r.emp_code): (r.minutos_autorizados_dia or 47) for r in todos_registros}
        min_fecha         = min(fechas_inicio_map.values())
        codigos_sql       = ', '.join(f"'{c}'" for c in fechas_inicio_map.keys())
        try:
            with connections['zkbio_sqlserver'].cursor() as cur:
                cur.execute(f"""
                    SELECT
                        CAST(t.emp_code AS VARCHAR(20)) AS emp_code,
                        CONVERT(DATE, t.punch_time)     AS fecha,
                        MIN(CAST(t.punch_time AS TIME)) AS primera,
                        MAX(CAST(t.punch_time AS TIME)) AS ultima
                    FROM dbo.iclock_transaction t
                    WHERE CONVERT(DATE, t.punch_time) BETWEEN '{min_fecha}' AND '{hoy}'
                      AND t.emp_code IN ({codigos_sql})
                    GROUP BY t.emp_code, CONVERT(DATE, t.punch_time)
                """)
                for emp_code, fecha, primera, ultima in cur.fetchall():
                    ec = str(emp_code).strip()
                    fi = fechas_inicio_map.get(ec)
                    if fi and fecha < fi:
                        continue
                    comp_min, _ = _comp_min_dia(ec, _t_to_seg(primera), _t_to_seg(ultima), topes_map.get(ec, 47))
                    if comp_min > 0:
                        real_comp_map[ec] = real_comp_map.get(ec, 0) + comp_min
        except Exception as _ex:
            print(f"[WARN] compensatorio_calculo real_comp_map: {_ex}")

    # ── Construir registros_data ─────────────────────────────────────────────
    def _min_to_h(m): return round(m / 60, 1)

    registros_data = []
    for r in todos_registros:
        ec           = str(r.emp_code)
        tiempo_extra = r.minutos_tiempo_extra or 0
        dias_trans   = _contar_dias_habiles_rango(r.fecha_inicio, hoy, feriados)

        # Compensado real desde marcas ZKBio (o override manual si existe)
        real_min = real_comp_map.get(ec, 0)
        minutos_compensados = r.minutos_compensados_manual if r.minutos_compensados_manual is not None else real_min

        saldo = max(0, r.minutos_total - minutos_compensados - tiempo_extra)
        es_especial = any(k in r.nombre_empleado.lower() for k in _ESPECIALES_COMP)
        registros_data.append({
            'r': r, 'saldo': saldo,
            'dias_transcurridos':  dias_trans,
            'minutos_compensados': minutos_compensados,
            'es_especial':         es_especial,
            'horas_total':         _min_to_h(r.minutos_total),
            'horas_compensados':   _min_to_h(minutos_compensados),
            'horas_saldo':         _min_to_h(saldo),
            'horas_tiempo_extra':  _min_to_h(r.minutos_tiempo_extra) if r.minutos_tiempo_extra else None,
        })

    # Especiales primero (en el orden definido), luego el resto alfabético
    registros_data.sort(key=lambda x: (
        _especial_rank(x['r'].nombre_empleado),
        x['r'].nombre_empleado.lower()
    ))

    u = request.user
    can_edit              = u.is_superuser or u.username == 'glorenzo@ana-hn.org'
    can_delete            = u.is_superuser
    can_edit_compensado   = u.is_superuser or u.username == 'glorenzo@ana-hn.org'
    can_edit_tiempo_extra = u.is_superuser or u.username == 'glorenzo@ana-hn.org'

    return render(request, "reloj/compensatorio_calculo_list.html", {
        "registros_data": registros_data,
        "feriados_count": Feriado.objects.count(),
        "minutos_dia": MINUTOS_POR_DIA_COMP,
        "can_edit":              can_edit,
        "can_delete":            can_delete,
        "can_edit_compensado":   can_edit_compensado,
        "can_edit_tiempo_extra": can_edit_tiempo_extra,
        "url_set_compensado":    "reloj_compensatorio_calculo_set_compensado",
    })


@login_required
def compensatorio_calculo_new(request):
    if not (request.user.is_superuser or request.user.username == 'glorenzo@ana-hn.org'):
        from django.contrib import messages as _msg
        _msg.error(request, "No tiene permiso para crear registros.")
        return redirect("reloj_compensatorio_calculo_list")
    from datetime import timedelta as _td
    feriados = set()
    for f in Feriado.objects.all():
        d = f.fecha_inicio
        while d <= f.fecha_fin:
            feriados.add(d)
            d += _td(days=1)

    if request.method == "POST":
        form = CompensatorioCalculoForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # Autocompletar nombre si viene vacío
            if not obj.nombre_empleado:
                from .models import EmployeeScheduleAssignment
                asig = EmployeeScheduleAssignment.objects.filter(
                    emp_code=obj.emp_code, activo=True
                ).first()
                obj.nombre_empleado = asig.nombre_empleado if asig else obj.emp_code
            fecha_fin, minutos, dias_hab = _calcular_fecha_fin(
                obj.fecha_inicio, obj.dias_adeudados, feriados,
                minutos_dia=obj.minutos_autorizados_dia
            )
            obj.minutos_total = minutos
            obj.dias_habiles_necesarios = dias_hab
            obj.fecha_fin = fecha_fin
            obj.save()
            messages.success(request, f"Cálculo guardado. Fecha fin: {fecha_fin.strftime('%d/%m/%Y')}")
            return redirect("reloj_compensatorio_calculo_list")
    else:
        form = CompensatorioCalculoForm()
    return render(request, "reloj/compensatorio_calculo_form.html", {
        "form": form, "modo": "Nuevo",
        "minutos_dia": MINUTOS_POR_DIA_COMP,
    })


@login_required
def compensatorio_calculo_edit(request, pk):
    if not (request.user.is_superuser or request.user.username == 'glorenzo@ana-hn.org'):
        from django.contrib import messages as _msg
        _msg.error(request, "No tiene permiso para editar registros.")
        return redirect("reloj_compensatorio_calculo_list")
    from datetime import timedelta as _td
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    feriados = set()
    for f in Feriado.objects.all():
        d = f.fecha_inicio
        while d <= f.fecha_fin:
            feriados.add(d)
            d += _td(days=1)

    if request.method == "POST":
        form = CompensatorioCalculoForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            if not obj.nombre_empleado:
                from .models import EmployeeScheduleAssignment
                asig = EmployeeScheduleAssignment.objects.filter(
                    emp_code=obj.emp_code, activo=True
                ).first()
                obj.nombre_empleado = asig.nombre_empleado if asig else obj.emp_code
            fecha_fin, minutos, dias_hab = _calcular_fecha_fin(
                obj.fecha_inicio, obj.dias_adeudados, feriados,
                minutos_dia=obj.minutos_autorizados_dia
            )
            obj.minutos_total = minutos
            obj.dias_habiles_necesarios = dias_hab
            obj.fecha_fin = fecha_fin
            obj.save()
            messages.success(request, "Cálculo actualizado.")
            return redirect("reloj_compensatorio_calculo_list")
    else:
        form = CompensatorioCalculoForm(instance=obj)
    return render(request, "reloj/compensatorio_calculo_form.html", {
        "form": form, "modo": "Editar", "obj": obj,
        "minutos_dia": MINUTOS_POR_DIA_COMP,
    })


@login_required
def compensatorio_calculo_set_min_dia(request, pk):
    """AJAX: actualiza minutos_autorizados_dia y recalcula días hábiles + fecha fin."""
    if not (request.user.is_superuser or request.user.username == 'glorenzo@ana-hn.org'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        valor = int(request.POST.get('minutos', 0))
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})
    if valor <= 0:
        return JsonResponse({'ok': False, 'error': 'Debe ser mayor a 0'})

    from datetime import timedelta as _td
    feriados = set()
    for f in Feriado.objects.all():
        d = f.fecha_inicio
        while d <= f.fecha_fin:
            feriados.add(d)
            d += _td(days=1)

    obj.minutos_autorizados_dia = valor
    fecha_fin, minutos, dias_hab = _calcular_fecha_fin(
        obj.fecha_inicio, obj.dias_adeudados, feriados, minutos_dia=valor
    )
    obj.dias_habiles_necesarios = dias_hab
    obj.fecha_fin = fecha_fin
    obj.save()

    # Recalcular saldo al día de hoy
    hoy = date.today()
    dias_trans = _contar_dias_habiles_rango(obj.fecha_inicio, hoy, feriados)
    saldo = max(0, minutos - dias_trans * valor)
    minutos_compensados = min(dias_trans * valor, minutos)

    return JsonResponse({
        'ok': True,
        'minutos_dia': valor,
        'dias_habiles': dias_hab,
        'fecha_fin': fecha_fin.strftime('%d/%m/%Y') if fecha_fin else '—',
        'saldo': saldo,
        'minutos_compensados': minutos_compensados,
    })


@login_required
def compensatorio_calculo_set_compensado(request, pk):
    """AJAX: guarda override manual de minutos compensados para empleados especiales."""
    if not (request.user.is_superuser or request.user.username == 'glorenzo@ana-hn.org'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        valor = int(request.POST.get('minutos', 0))
        if valor < 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})

    obj.minutos_compensados_manual = valor
    obj.save(update_fields=['minutos_compensados_manual'])
    saldo = max(0, obj.minutos_total - valor)
    return JsonResponse({'ok': True, 'minutos_compensados': valor, 'saldo': saldo})


@login_required
def compensatorio_calculo_set_tiempo_extra(request, pk):
    """AJAX: guarda minutos de tiempo extra autorizado y recalcula días hábiles + fecha fin."""
    if not (request.user.is_superuser or request.user.username == 'glorenzo@ana-hn.org'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        valor = int(request.POST.get('minutos', 0))
        if valor < 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})

    obj.minutos_tiempo_extra = valor if valor > 0 else None
    obj.save(update_fields=['minutos_tiempo_extra'])

    tiempo_extra = obj.minutos_tiempo_extra or 0

    # Recalcular días hábiles y fecha fin descontando el tiempo extra
    from datetime import timedelta as _td
    import math as _math
    feriados = set()
    for f in Feriado.objects.all():
        d = f.fecha_inicio
        while d <= f.fecha_fin:
            feriados.add(d)
            d += _td(days=1)

    min_dia = obj.minutos_autorizados_dia if obj.minutos_autorizados_dia > 0 else MINUTOS_POR_DIA_COMP
    minutos_efectivos = max(0, obj.minutos_total - tiempo_extra)
    dias_hab = _math.ceil(minutos_efectivos / min_dia) if minutos_efectivos > 0 else 0

    # Contar dias_hab días hábiles desde fecha_inicio
    fecha_fin = None
    if dias_hab > 0:
        contados, d = 0, obj.fecha_inicio
        while contados < dias_hab:
            if d.weekday() < 5 and d not in feriados:
                contados += 1
            if contados < dias_hab:
                d += _td(days=1)
        fecha_fin = d

    obj.dias_habiles_necesarios = dias_hab
    obj.fecha_fin = fecha_fin
    obj.save(update_fields=['dias_habiles_necesarios', 'fecha_fin'])

    # Saldo al día de hoy
    hoy = date.today()
    dias_trans = _contar_dias_habiles_rango(obj.fecha_inicio, hoy, feriados)
    auto_comp = min(dias_trans * min_dia, obj.minutos_total)
    minutos_compensados = obj.minutos_compensados_manual if obj.minutos_compensados_manual is not None else auto_comp
    saldo = max(0, obj.minutos_total - minutos_compensados - tiempo_extra)

    return JsonResponse({
        'ok': True,
        'minutos': tiempo_extra,
        'dias_habiles': dias_hab,
        'fecha_fin': fecha_fin.strftime('%d/%m/%Y') if fecha_fin else '—',
        'saldo': saldo,
    })


@login_required
def compensatorio_calculo_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "No tiene permiso para eliminar registros.")
        return redirect("reloj_compensatorio_calculo_list")
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Registro eliminado.")
        return redirect("reloj_compensatorio_calculo_list")
    return render(request, "reloj/confirm_delete.html", {
        "obj": obj, "titulo": "Eliminar cálculo compensatorio"
    })


# ─────────────────────────────────────────────────────────────
# Reporte de Permisos Mensual
# ─────────────────────────────────────────────────────────────

_CARGOS_EXCLUIDOS_TARDE = ('hora', 'vigilante')

CAMPOS_PERMISO = [
    ('compensatorio_dias', 'Compensatorio', '#D0CECE'),
    ('ausencias_dias',     'No Pagado',     '#00FFFF'),
    ('otro_pagado_dias',   'Otro Pagado',   '#D0CECE'),
    ('vacaciones_dias',    'Vacaciones',    '#92D050'),
    ('enfermedad_dias',         'Enfermedad',                        '#FF33CC'),
    ('enfermedad_incapacidad',  'Enfermedad/Incapacidad',            '#FF33CC'),
    ('enfermedad_maternidad',   'Enfermedad/Incapacidad Maternidad', '#FF66CC'),
    ('enfermedad_citamedica',   'Enfermedad/Cita médica',            '#FF99DD'),
    ('enfermedad_consulta',     'Enfermedad/Consulta médica',        '#FFBBEE'),
    ('pct25_dias',         '25%',           '#FFFFB7'),
    ('pct50_dias',         '50%',           '#FFFF65'),
    ('pct75_dias',         '75%',           '#FFFF05'),
    ('pct100_dias',        '100%',          '#EFDC25'),
]


def _rebaja_por_dia(minutos: int) -> float:
    if minutos >= 31:
        return 1.0
    if minutos >= 11:
        return 0.5
    return 0.0


@login_required
def permiso_reporte_list(request):
    import calendar as _cal
    from datetime import date as _date

    hoy = _date.today()
    mes_str = request.GET.get('mes', hoy.strftime('%Y-%m'))
    try:
        year, month = map(int, mes_str.split('-'))
        mes_inicio = _date(year, month, 1)
    except Exception:
        mes_inicio = hoy.replace(day=1)
        mes_str = mes_inicio.strftime('%Y-%m')

    ultimo_dia = _cal.monthrange(mes_inicio.year, mes_inicio.month)[1]
    mes_fin = _date(mes_inicio.year, mes_inicio.month, ultimo_dia)

    empleados = []
    # {emp_code: [minutos_tarde_por_dia, ...]}
    tarde_por_dia_map: dict = {}
    error_sql = None

    try:
        with connections['zkbio_sqlserver'].cursor() as cursor:
            cursor.execute("""
                SELECT
                    CAST(e.emp_code AS VARCHAR(20))         AS emp_code,
                    e.first_name + ' ' + ISNULL(e.last_name,'') AS nombre,
                    ISNULL(p.position_name, '')              AS cargo
                FROM dbo.personnel_employee e
                LEFT JOIN dbo.personnel_position p
                       ON p.id = TRY_CONVERT(INT, e.position_id)
                ORDER BY e.last_name, e.first_name
            """)
            for code, nombre, cargo in cursor.fetchall():
                empleados.append({
                    'emp_code': (code or '').strip(),
                    'nombre':   (nombre or '').strip(),
                    'cargo':    (cargo or '').strip(),
                })

        # Empleados con plantillas excluidas (asistentes especiales y maestros por hora)
        from reloj.models import EmployeeScheduleAssignment
        excluir_codes = set(
            EmployeeScheduleAssignment.objects.filter(activo=True).filter(
                models.Q(template__nombre__icontains='horario especial asistentes') |
                models.Q(template__nombre__icontains='maestro')
            ).values_list('emp_code', flat=True)
        )

        with connections['zkbio_sqlserver'].cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    CAST(e.emp_code AS VARCHAR(20))             AS emp_code,
                    ISNULL(p.position_name, '')                  AS cargo,
                    CONVERT(DATE, t.punch_time)                  AS fecha,
                    DATEDIFF(MINUTE,'07:00:00',
                        MIN(CAST(t.punch_time AS TIME)))          AS minutos_tarde
                FROM dbo.personnel_employee e
                LEFT JOIN dbo.personnel_position p
                       ON p.id = TRY_CONVERT(INT, e.position_id)
                INNER JOIN dbo.iclock_transaction t
                        ON t.emp_code = e.emp_code
                       AND CONVERT(DATE, t.punch_time) BETWEEN '{mes_inicio}' AND '{mes_fin}'
                GROUP BY e.emp_code, p.position_name, CONVERT(DATE, t.punch_time)
                HAVING MIN(CAST(t.punch_time AS TIME)) >= '07:01:00'
                   AND MIN(CAST(t.punch_time AS TIME)) <= '08:00:00'
                ORDER BY e.emp_code, CONVERT(DATE, t.punch_time)
            """)
            for code, cargo, _fecha, mins in cursor.fetchall():
                ec = (code or '').strip()
                cargo_l = (cargo or '').lower()
                if any(exc in cargo_l for exc in _CARGOS_EXCLUIDOS_TARDE):
                    continue
                if ec in excluir_codes:
                    continue
                tarde_por_dia_map.setdefault(ec, []).append(int(mins or 0))

    except Exception as exc:
        error_sql = str(exc)

    registros_db = {
        r.emp_code: r
        for r in ReportePermisoMensual.objects.filter(mes=mes_inicio)
    }

    # Sumar horas por emp_code+tipo para mostrar en la tabla principal
    from django.db.models import Sum as _Sum
    from decimal import Decimal as _Dec
    _SUBTIPO_PARENT = {'enfermedad_incapacidad': 'enfermedad_dias',
                       'enfermedad_maternidad':  'enfermedad_dias',
                       'enfermedad_citamedica':  'enfermedad_dias',
                       'enfermedad_consulta':    'enfermedad_dias'}
    horas_agg: dict = {}
    for item in (PermisoReporte.objects
                 .filter(fecha__range=(mes_inicio, mes_fin), horas__isnull=False)
                 .values('emp_code', 'tipo')
                 .annotate(total_h=_Sum('horas'))):
        ec = (item['emp_code'] or '').strip()
        tipo = _SUBTIPO_PARENT.get(item['tipo'], item['tipo'])
        horas_agg.setdefault(ec, {})
        horas_agg[ec][tipo] = horas_agg[ec].get(tipo, _Dec('0')) + item['total_h']

    rows = []
    for emp in empleados:
        ec = emp['emp_code']
        cargo_l = emp['cargo'].lower()
        excluido = any(exc in cargo_l for exc in _CARGOS_EXCLUIDOS_TARDE) or ec in excluir_codes
        lista_mins = tarde_por_dia_map.get(ec, [])

        minutos_tarde = sum(lista_mins) if not excluido else None
        horas_rebaja = sum(_rebaja_por_dia(m) for m in lista_mins) if not excluido else None

        nombre = emp['nombre']
        partes = nombre.rsplit(' ', 1)
        nombre_sort = (partes[-1] + ' ' + partes[0]).lower() if len(partes) > 1 else nombre.lower()

        rows.append({
            'emp_code':     ec,
            'nombre':       nombre,
            'nombre_sort':  nombre_sort,
            'cargo':        emp['cargo'],
            'r':            registros_db.get(ec),
            'horas_map':    horas_agg.get(ec, {}),
            'minutos_tarde':  minutos_tarde,
            'horas_rebaja':   horas_rebaja,
            'excluido_tarde': excluido,
        })

    return render(request, 'reloj/permiso_reporte.html', {
        'rows':          rows,
        'mes':           mes_inicio,
        'mes_str':       mes_str,
        'campos_permiso': CAMPOS_PERMISO,
        'error_sql':     error_sql,
        'can_delete':    request.user.is_superuser,
    })


@require_POST
@login_required
def permiso_rebaja_toggle(request):
    """AJAX: activa/desactiva horas_rebaja para un empleado en un mes."""
    from datetime import date as _d
    emp_code = request.POST.get('emp_code', '').strip()
    mes_str  = request.POST.get('mes', '').strip()
    activa   = request.POST.get('activa') == '1'
    if not emp_code or not mes_str:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos'})
    try:
        year, month = map(int, mes_str.split('-'))
        mes = _d(year, month, 1)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Mes inválido'})
    obj, _ = ReportePermisoMensual.objects.get_or_create(
        emp_code=emp_code, mes=mes,
        defaults={'nombre_empleado': emp_code}
    )
    obj.rebaja_activa = activa
    obj.save(update_fields=['rebaja_activa'])
    return JsonResponse({'ok': True, 'activa': activa})


@login_required
def permiso_reporte_set_campo(request):
    """AJAX: guarda el valor de un campo de permiso para un empleado/mes."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    from datetime import date as _date

    emp_code  = (request.POST.get('emp_code') or '').strip()
    mes_str   = (request.POST.get('mes') or '').strip()
    campo     = (request.POST.get('campo') or '').strip()
    valor_str = (request.POST.get('valor') or '0').strip().replace(',', '.')

    campos_validos = {c[0] for c in CAMPOS_PERMISO} | {'pierde_bono'}
    if campo not in campos_validos:
        return JsonResponse({'ok': False, 'error': 'Campo inválido'})

    try:
        year, month = map(int, mes_str.split('-'))
        mes = _date(year, month, 1)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Mes inválido'})

    try:
        if campo == 'pierde_bono':
            valor = valor_str.lower() in ('1', 'true', 'on', 'yes')
        else:
            valor = float(valor_str)
            if valor < 0:
                return JsonResponse({'ok': False, 'error': 'Valor debe ser >= 0'})
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})

    # Nombre desde SQL o registro existente
    nombre = ''
    try:
        with connections['zkbio_sqlserver'].cursor() as cursor:
            cursor.execute("""
                SELECT e.first_name + ' ' + ISNULL(e.last_name,'')
                FROM dbo.personnel_employee e
                WHERE CAST(e.emp_code AS VARCHAR(20)) = %s
            """, [emp_code])
            row = cursor.fetchone()
            if row:
                nombre = (row[0] or '').strip()
    except Exception:
        pass

    obj, _ = ReportePermisoMensual.objects.get_or_create(
        emp_code=emp_code, mes=mes,
        defaults={'nombre_empleado': nombre or emp_code}
    )
    if nombre and not obj.nombre_empleado:
        obj.nombre_empleado = nombre

    setattr(obj, campo, valor)
    obj.save()

    return JsonResponse({'ok': True, 'campo': campo, 'valor': str(valor)})


_ENFERMEDAD_SUBTYPES = {'enfermedad_incapacidad', 'enfermedad_maternidad',
                        'enfermedad_citamedica',  'enfermedad_consulta'}
_OTRO_PAGADO_SUBTYPES = {'compensatorio_dias'}

def _sync_permiso_mensual(emp_code, fecha, tipo, nombre=''):
    """Recalcula el total mensual para emp_code/mes/tipo desde PermisoReporte y guarda."""
    from datetime import date as _d
    from django.db.models import Sum
    mes = _d(fecha.year, fecha.month, 1)

    # Los subtipos de enfermedad suman al campo enfermedad_dias del mensual
    # Los subtipos de otro_pagado suman al campo otro_pagado_dias del mensual
    if tipo in _ENFERMEDAD_SUBTYPES:
        campo_mensual = 'enfermedad_dias'
    elif tipo in _OTRO_PAGADO_SUBTYPES:
        campo_mensual = 'otro_pagado_dias'
    else:
        campo_mensual = tipo

    if tipo in _ENFERMEDAD_SUBTYPES:
        total = PermisoReporte.objects.filter(
            emp_code=emp_code, fecha__year=fecha.year,
            fecha__month=fecha.month, tipo__in=_ENFERMEDAD_SUBTYPES | {'enfermedad_dias'},
        ).aggregate(t=Sum('dias'))['t'] or 0
    elif tipo in _OTRO_PAGADO_SUBTYPES:
        total = PermisoReporte.objects.filter(
            emp_code=emp_code, fecha__year=fecha.year,
            fecha__month=fecha.month, tipo__in=_OTRO_PAGADO_SUBTYPES | {'otro_pagado_dias'},
        ).aggregate(t=Sum('dias'))['t'] or 0
    else:
        total = PermisoReporte.objects.filter(
            emp_code=emp_code, fecha__year=fecha.year,
            fecha__month=fecha.month, tipo=tipo,
        ).aggregate(t=Sum('dias'))['t'] or 0

    obj, _ = ReportePermisoMensual.objects.get_or_create(
        emp_code=emp_code, mes=mes,
        defaults={'nombre_empleado': nombre or emp_code}
    )
    setattr(obj, campo_mensual, total)
    obj.save()


@require_POST
@login_required
def permiso_reporte_save(request):
    """AJAX: crea o actualiza un PermisoReporte y sincroniza el resumen mensual."""
    from datetime import date as _d

    pk_str       = request.POST.get('pk', '').strip()
    emp_code     = request.POST.get('emp_code', '').strip()
    nombre       = request.POST.get('nombre', '').strip()
    fecha_str    = request.POST.get('fecha', '').strip()
    fecha_fin_str= request.POST.get('fecha_fin', '').strip()
    tipo         = request.POST.get('tipo', '').strip()
    dias_str     = request.POST.get('dias', '1').strip().replace(',', '.')
    horas_str    = request.POST.get('horas', '').strip().replace(',', '.')
    razon        = request.POST.get('razon', '').strip()
    comentario   = request.POST.get('comentario', '').strip()

    if not emp_code or not fecha_str or not tipo:
        return JsonResponse({'ok': False, 'error': 'Campos requeridos faltantes'})

    if tipo not in {c[0] for c in CAMPOS_PERMISO}:
        return JsonResponse({'ok': False, 'error': 'Tipo de permiso inválido'})

    try:
        fecha     = _d.fromisoformat(fecha_str)
        fecha_fin = _d.fromisoformat(fecha_fin_str) if fecha_fin_str else fecha
        if fecha_fin < fecha:
            fecha_fin = fecha
        horas = float(horas_str) if horas_str else None
        if dias_str:
            dias = float(dias_str)
        elif horas is not None:
            dias = round(horas / 8, 4)
        else:
            dias = 1.0
        if dias < 0:
            return JsonResponse({'ok': False, 'error': 'Días debe ser >= 0'})
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'})

    if pk_str:
        try:
            obj = PermisoReporte.objects.get(pk=int(pk_str))
            old_tipo  = obj.tipo
            old_fecha = obj.fecha
            obj.fecha = fecha; obj.fecha_fin = fecha_fin
            obj.tipo = tipo; obj.dias = dias; obj.horas = horas
            obj.razon = razon; obj.comentario = comentario
            obj.save()
            if old_tipo != tipo or old_fecha != fecha:
                _sync_permiso_mensual(emp_code, old_fecha, old_tipo, nombre)
        except PermisoReporte.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Permiso no encontrado'})
    else:
        obj, _ = PermisoReporte.objects.update_or_create(
            emp_code=emp_code, fecha=fecha, tipo=tipo,
            defaults={'nombre_empleado': nombre, 'dias': dias, 'horas': horas,
                      'fecha_fin': fecha_fin,
                      'razon': razon, 'comentario': comentario,
                      'registrado_por': request.user},
        )

    _sync_permiso_mensual(emp_code, fecha, tipo, nombre)
    return JsonResponse({'ok': True, 'pk': obj.pk, 'dias': str(obj.dias),
                         'horas': str(obj.horas) if obj.horas is not None else None,
                         'tipo': tipo, 'razon': razon,
                         'fecha': obj.fecha.isoformat(),
                         'fecha_fin': obj.fecha_fin.isoformat() if obj.fecha_fin else None})


@require_POST
@login_required
def permiso_reporte_delete(request, pk):
    """AJAX: elimina un PermisoReporte y recalcula el resumen mensual."""
    u = request.user
    if not (u.is_superuser or getattr(u, 'email', '') == 'glorenzo@ana-hn.org'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    try:
        obj = PermisoReporte.objects.get(pk=pk)
        emp_code = obj.emp_code
        fecha    = obj.fecha
        tipo     = obj.tipo
        nombre   = obj.nombre_empleado
        obj.delete()
        _sync_permiso_mensual(emp_code, fecha, tipo, nombre)
        return JsonResponse({'ok': True})
    except PermisoReporte.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Permiso no encontrado'})


@login_required
def permiso_list_mes(request):
    """AJAX GET: devuelve todos los PermisoReporte de un empleado en un mes."""
    from datetime import date as _date
    import calendar as _cal

    emp_code = (request.GET.get('emp_code') or '').strip()
    mes_str  = (request.GET.get('mes') or '').strip()
    tipo_f   = (request.GET.get('tipo') or '').strip()

    try:
        year, month = map(int, mes_str.split('-'))
        mes_inicio  = _date(year, month, 1)
        ultimo_dia  = _cal.monthrange(year, month)[1]
        mes_fin     = _date(year, month, ultimo_dia)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Mes inválido'})

    tipo_labels = {c[0]: c[1] for c in CAMPOS_PERMISO}

    qs = PermisoReporte.objects.filter(emp_code=emp_code, fecha__range=(mes_inicio, mes_fin))
    if tipo_f and tipo_f in tipo_labels:
        # enfermedad_dias agrupa también los subtipos incapacidad/cita médica
        if tipo_f == 'enfermedad_dias':
            qs = qs.filter(tipo__in=['enfermedad_dias', 'enfermedad_incapacidad',
                                     'enfermedad_maternidad', 'enfermedad_citamedica',
                                     'enfermedad_consulta'])
        elif tipo_f == 'otro_pagado_dias':
            qs = qs.filter(tipo__in=['otro_pagado_dias', 'compensatorio_dias'])
        else:
            qs = qs.filter(tipo=tipo_f)
    qs = qs.order_by('fecha', 'tipo')

    permisos = [
        {
            'pk':       p.pk,
            'fecha':    p.fecha.strftime('%d/%m/%Y'),
            'fecha_fin': p.fecha_fin.strftime('%d/%m/%Y') if p.fecha_fin else None,
            'fecha_iso': p.fecha.isoformat(),
            'tipo':     p.tipo,
            'label':    tipo_labels.get(p.tipo, p.tipo),
            'dias':     str(p.dias),
            'horas':    str(p.horas) if p.horas is not None else None,
            'razon':    p.razon or '',
        }
        for p in qs
    ]
    return JsonResponse({'ok': True, 'permisos': permisos})

