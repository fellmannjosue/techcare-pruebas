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
from reportlab.lib.pagesizes import landscape, letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
    SabadoAsignacion,
    TiempoCompensatorio,
    PermisoEmpleado,
    ReporteNota,
    ReporteComentario,
    FeriadoAsignacion,
    CompensatorioCalculo,
    CompensatorioInstructor,
    CompensatorioInstructorTE,
    CompensatorioInstructorTomado,
    CompensatorioMensualDetalle,
    CompensatorioMensualEmpleado,
    CompensatorioMensualValor,
    CompensatorioTomadoManual,
    DiaNoLaborableANA,
    MaestroHoraEntrada,
    MaestroHoraDia,
    RazonPermiso,
    ReportePermisoMensual,
    PermisoReporte,
    TiempoExtraDia,
    VacacionConfig,
    RelojPermiso,
    RelojConfigGlobal,
)


def _reloj_can(user, modulo, accion):
    """Verifica si el usuario puede editar/eliminar en un módulo del reloj.
    Superusers siempre pueden. Staff consulta RelojPermiso."""
    if user.is_superuser:
        return True
    try:
        return bool(getattr(user.reloj_permiso, f'{modulo}_{accion}', False))
    except Exception:
        return False


def _reloj_can_ver(user, modulo):
    """Puede VISUALIZAR el módulo.
    - Superuser: siempre.
    - Toggle "Todos" (ver_todos) activo: ve TODOS los módulos.
    - Si no: ve solo los módulos con 'ver' (o editar/eliminar, que implican ver)."""
    if user.is_superuser:
        return True
    try:
        if user.reloj_permiso.ver_todos:
            return True
    except Exception:
        return False
    return (_reloj_can(user, modulo, 'ver')
            or _reloj_can(user, modulo, 'editar')
            or _reloj_can(user, modulo, 'eliminar'))


def _reloj_ver_required(modulo):
    """Decorador: bloquea el acceso por URL si el usuario no puede ver el módulo."""
    from functools import wraps as _wraps

    def deco(viewfunc):
        @_wraps(viewfunc)
        def wrapper(request, *args, **kwargs):
            if not _reloj_can_ver(request.user, modulo):
                messages.error(request, 'No tiene permiso para ver este módulo.')
                return redirect('reloj_dashboard')
            return viewfunc(request, *args, **kwargs)
        return wrapper
    return deco


def _es_pdf(request):
    """True si la petición pide el reporte en PDF (?fmt=pdf)."""
    return request.GET.get('fmt') == 'pdf'


def _ultimo_dia_laborable(year, month):
    """Último día hábil del mes (lun–vie, saltando feriados)."""
    import calendar as _cal
    from datetime import date as _d, timedelta as _td
    try:
        feriados = set()
        for f in Feriado.objects.filter(fecha_inicio__year=year, fecha_inicio__month=month):
            d = f.fecha_inicio
            while d <= (f.fecha_fin or f.fecha_inicio):
                if d.year == year and d.month == month:
                    feriados.add(d)
                d += _td(days=1)
    except Exception:
        feriados = set()
    d = _d(year, month, _cal.monthrange(year, month)[1])
    while d.weekday() >= 5 or d in feriados:
        d -= _td(days=1)
    return d


def _permiso_mes_cerrado(fecha, user=None):
    """True si ya pasó el cierre de permisos del mes de `fecha`:
    último día hábil del mes a las 16:35. El superuser nunca se bloquea."""
    if user is not None and getattr(user, 'is_superuser', False):
        return False
    from datetime import datetime as _dt, time as _time
    from django.utils import timezone as _tz
    uld = _ultimo_dia_laborable(fecha.year, fecha.month)
    deadline = _dt.combine(uld, _time(16, 35))
    now = _tz.localtime() if _tz.is_aware(_tz.now()) else _dt.now()
    if _tz.is_aware(now):
        deadline = _tz.make_aware(deadline, now.tzinfo)
    # Permiso PROVISIONAL: si el usuario tiene una ventana vigente para registrar
    # permisos fuera de fecha, no se le bloquea (hasta que esa fecha/hora expire).
    if user is not None:
        rp = getattr(user, 'reloj_permiso', None)
        hasta = getattr(rp, 'permisos_registrar_hasta', None) if rp else None
        if hasta:
            h = hasta
            if _tz.is_aware(now) and not _tz.is_aware(h):
                h = _tz.make_aware(h, now.tzinfo)
            elif not _tz.is_aware(now) and _tz.is_aware(h):
                h = _tz.make_naive(h, h.tzinfo)
            if now < h:
                return False
    return now >= deadline


def _reporte_pdf(request, template, context, filename):
    """Renderiza `template` (HTML de impresión) con `context` y devuelve un PDF
    vía WeasyPrint. Inline (?inline=1) para vista previa, o adjunto para descargar."""
    from weasyprint import HTML as _WHTML
    from django.template.loader import render_to_string as _rts
    html = _rts(template, context, request=request)
    pdf_bytes = _WHTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    disp = 'inline' if request.GET.get('inline') == '1' else 'attachment'
    resp = HttpResponse(pdf_bytes, content_type='application/pdf')
    resp['Content-Disposition'] = f'{disp}; filename="{filename}"'
    resp['X-Frame-Options'] = 'SAMEORIGIN'  # permitir vista previa en iframe del mismo sitio
    return resp


@login_required
@_reloj_ver_required('reportes_pdf')
def reportes_pdf(request):
    """Página con tabs: vista previa (PDF embebido) y descarga de cada reporte."""
    import calendar as _cal
    hoy = date.today()
    mes_str = request.GET.get('mes', hoy.strftime('%Y-%m'))
    anio = request.GET.get('anio', str(hoy.year))
    fi = hoy.replace(day=1).strftime('%Y-%m-%d')
    ff = hoy.strftime('%Y-%m-%d')
    return render(request, 'reloj/reportes_pdf.html', {
        'mes_str': mes_str, 'anio': anio, 'fi': fi, 'ff': ff,
    })

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
    _disp = 'inline' if request.GET.get('inline') == '1' else 'attachment'
    response['Content-Disposition'] = f'{_disp}; filename="reporte_asistencia.pdf"'
    response['X-Frame-Options'] = 'SAMEORIGIN'  # permitir vista previa en iframe

    from xml.sax.saxutils import escape as _xesc

    MARGIN = 22
    page_w, _ = landscape(A4)                       # A4 horizontal (más ancho para comentarios)
    avail_w = page_w - 2 * MARGIN
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                            leftMargin=MARGIN, rightMargin=MARGIN, topMargin=22, bottomMargin=22)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle('cell', parent=styles['Normal'], fontSize=8, leading=10)
    sub_style  = ParagraphStyle('sub', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#555555"))
    elements = []

    # Encabezado: título + rango + quién y cuándo lo generó
    usuario = (request.user.get_full_name() or request.user.get_username()) if request.user.is_authenticated else 'Anónimo'
    generado = hoy.strftime('%d/%m/%Y %H:%M')
    elements.append(Paragraph("Reporte de Asistencia", styles["Title"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"Desde: <b>{fecha_inicio}</b> &nbsp;&nbsp;&nbsp; Hasta: <b>{fecha_fin}</b>", styles["Normal"]))
    elements.append(Paragraph(f"Generado el {generado} por {_xesc(usuario)}", sub_style))
    elements.append(Spacer(1, 8))

    pdf_columnas = columnas + ["Comentarios"]
    # Columnas que envuelven texto (Paragraph); el resto queda centrado como texto plano
    WRAP = {'Empleado', 'Cargo', 'Marcas', 'Comentarios'}
    # Pesos de ancho por columna (se escalan al 100% del papel)
    PESOS = {'ID_Empleado': 55, 'Empleado': 130, 'Cargo': 95, 'Fecha': 60,
             'Marcas': 110, 'Cantidad_Marcas': 62, 'Estado': 66, 'Comentarios': 210}
    pesos = [PESOS.get(c, 80) for c in pdf_columnas]
    factor = avail_w / sum(pesos)
    col_widths = [p * factor for p in pesos]

    data = [[Paragraph(f'<b>{_xesc(c)}</b>', ParagraphStyle('h', parent=cell_style, textColor=colors.white))
             for c in pdf_columnas]]
    marcas_col_idx = columnas.index('Marcas') if 'Marcas' in columnas else None
    for row in datos:
        emp_code_r = str(row.get('ID_Empleado') or "").strip()
        fecha_r    = row.get('Fecha')
        comentarios_txt = " | ".join(pdf_comentarios_map.get((emp_code_r, fecha_r), []))
        fila = [str(row[c]) if row.get(c) is not None else "" for c in columnas]
        if marcas_col_idx is not None and fila[marcas_col_idx]:
            raw_marks = [m.strip() for m in fila[marcas_col_idx].split(',') if m.strip()]
            fila[marcas_col_idx] = ', '.join(_dedup_marcas_hora(raw_marks))
        valores = fila + [comentarios_txt]
        celdas = []
        for c, v in zip(pdf_columnas, valores):
            if c in WRAP:
                celdas.append(Paragraph(_xesc(v or ""), cell_style))
            else:
                celdas.append(v)
        data.append(celdas)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
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
    """Renderiza el panel principal del módulo Reloj.
    Los cards se muestran según el permiso de visualización por módulo."""
    mods = ['reporte', 'plantilla', 'asignacion', 'compensatorio',
            'feriado', 'sabado', 'calculo_comp', 'vacaciones', 'reportes_pdf',
            'vigilancia']
    puede = {m: _reloj_can_ver(request.user, m) for m in mods}
    return render(request, 'reloj/dashboard.html', {'puede': puede})


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
@_reloj_ver_required('reporte')
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
@_reloj_ver_required('reporte')
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

            # Mapa de sábados especiales: (emp_code, date) -> descripcion
            sabados_especiales_r = set()
            sabados_especiales_desc_r = {}
            try:
                for asig in SabadoAsignacion.objects.filter(
                    sabado__fecha__gte=fi_d,
                    sabado__fecha__lte=ff_d,
                ).select_related("sabado"):
                    key = (asig.emp_code.strip(), asig.sabado.fecha)
                    sabados_especiales_r.add(key)
                    sabados_especiales_desc_r[key] = asig.sabado.descripcion or "Sábado especial"
            except Exception as _ex:
                print(f"[WARN] sabados_especiales reporte: {_ex}")

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

                # Sábado especial asignado a este empleado
                es_sabado_especial = (emp_code, fecha_d) in sabados_especiales_r if fecha_d else False

                # Filtro por horario: omitir días que el empleado no trabaja
                # (excepto si marcó físicamente, es feriado asignado, o sábado especial)
                cantidad_marcas = int(row.get('Cantidad_Marcas') or 0)
                if cantidad_marcas == 0 and not es_feriado and not es_sabado_especial:
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
                row['Es_Sabado_Esp']    = es_sabado_especial
                row['Sabado_Esp_Desc']  = sabados_especiales_desc_r.get((emp_code, fecha_d), "") if es_sabado_especial else ""
                # Cierre de permisos: bloquea ingreso pasado el último día hábil 16:35
                row['Bloqueado']        = _permiso_mes_cerrado(fecha_d, request.user)
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
    can_edit_permisos   = _reloj_can(u, 'reporte', 'editar')
    can_delete_permisos = _reloj_can(u, 'reporte', 'eliminar')

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
        'razones': list(RazonPermiso.objects.filter(activo=True).values_list('texto', flat=True)),
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
@_reloj_ver_required('plantilla')
def plantilla_list(request):
    """Lista de plantillas de horario (con enlace para editar y agregar reglas)."""
    plantillas = ScheduleTemplate.objects.all().order_by("nombre")
    return render(request, "reloj/plantilla_list.html", {
        "plantillas":  plantillas,
        "can_edit":    _reloj_can(request.user, 'plantilla', 'editar'),
        "can_delete":  _reloj_can(request.user, 'plantilla', 'eliminar'),
    })


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
@_reloj_ver_required('asignacion')
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
        'form':         form,
        'can_edit':     _reloj_can(request.user, 'asignacion', 'editar'),
        'can_delete':   _reloj_can(request.user, 'asignacion', 'eliminar'),
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
@_reloj_ver_required('feriado')
def feriados_list(request):
    from django.db.models import Count
    feriados = Feriado.objects.annotate(total_asignados=Count("asignaciones")).order_by("-fecha_inicio")
    return render(request, "reloj/feriados_list.html", {
        "feriados":   feriados,
        "can_edit":   _reloj_can(request.user, 'feriado', 'editar'),
        "can_delete": _reloj_can(request.user, 'feriado', 'eliminar'),
    })


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
@_reloj_ver_required('sabado')
def sabados_list(request):
    from django.db.models import Count
    qs = SabadoEspecial.objects.annotate(total_asignados=Count('asignaciones')).order_by("-fecha")
    paginator = Paginator(qs, 20)
    page = request.GET.get("page")
    sabados = paginator.get_page(page)
    return render(request, "reloj/sabados_list.html", {
        "sabados":    sabados,
        "can_edit":   _reloj_can(request.user, 'sabado', 'editar'),
        "can_delete": _reloj_can(request.user, 'sabado', 'eliminar'),
    })


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
            return redirect("reloj_sabado_edit", pk=obj.pk)
    else:
        form = SabadoEspecialForm(instance=obj)
    asignados_codes = set(
        SabadoAsignacion.objects.filter(sabado=obj).values_list("emp_code", flat=True)
    )
    try:
        empleados_opts = get_empleado_options()
    except Exception:
        empleados_opts = []
    empleados_check = [
        {"code": code, "label": label, "checked": code in asignados_codes}
        for code, label in empleados_opts
    ]
    return render(request, "reloj/sabado_form.html", {
        "form": form, "modo": "Editar", "obj": obj,
        "empleados_check": empleados_check,
        "total_asignados": len(asignados_codes),
    })


@staff_required
def sabado_delete(request, pk):
    obj = get_object_or_404(SabadoEspecial, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Sábado especial eliminado.")
        return redirect("reloj_sabados_list")
    return render(request, "reloj/confirm_delete.html", {"obj": obj, "titulo": "Eliminar sábado especial"})


@staff_required
@require_POST
def sabado_asignacion_bulk(request, pk):
    """Guarda la selección completa de empleados para un sábado especial."""
    sabado = get_object_or_404(SabadoEspecial, pk=pk)
    selected = set(filter(None, (c.strip() for c in request.POST.getlist("emp_codes"))))
    existing = set(SabadoAsignacion.objects.filter(sabado=sabado).values_list("emp_code", flat=True))

    to_add    = selected - existing
    to_remove = existing - selected

    SabadoAsignacion.objects.filter(sabado=sabado, emp_code__in=to_remove).delete()

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
        SabadoAsignacion.objects.create(
            sabado=sabado,
            emp_code=emp_code,
            nombre_empleado=nombres.get(emp_code, ""),
            asignado_por=request.user,
        )

    total = SabadoAsignacion.objects.filter(sabado=sabado).count()
    return JsonResponse({
        "ok": True,
        "added": len(to_add),
        "removed": len(to_remove),
        "total": total,
    })


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
@_reloj_ver_required('compensatorio')
def compensatorio_list(request):
    hoy = date.today()
    _fi_def = hoy.replace(day=1).strftime("%Y-%m-%d")
    _ff_def = hoy.strftime("%Y-%m-%d")
    fecha_inicio_str = _safe_date(request.GET.get("fecha_inicio") or _fi_def, _fi_def)
    fecha_fin_str    = _safe_date(request.GET.get("fecha_fin")    or _ff_def, _ff_def)
    emp_code_f       = (request.GET.get("emp_code") or "").strip()

    # Empleados activos con "horario asistentes" o "horario instructores"
    asistentes_qs = (
        EmployeeScheduleAssignment.objects
        .filter(activo=True)
        .filter(models.Q(template__nombre__icontains="asistente") |
                models.Q(template__nombre__icontains="instructor"))
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

    # Suma el tiempo extra autorizado al total acumulado  <--- hecho por claude code
    total_extra_emp = sum(f['extra_min'] for f in filas)
    total_min_emp   = total_min_emp + total_extra_emp

    u = request.user
    can_edit_extra = _reloj_can(u, 'compensatorio', 'editar')

    ctx = {
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
        "total_extra_emp":  total_extra_emp,
        "can_edit_extra":   can_edit_extra,
        "can_edit":         _reloj_can(u, 'compensatorio', 'editar'),
        "can_delete":       _reloj_can(u, 'compensatorio', 'eliminar'),
        "razones": list(RazonPermiso.objects.filter(activo=True).values_list('texto', flat=True)),
    }
    if _es_pdf(request):
        return _reporte_pdf(request, 'reloj/pdf/compensatorio_pdf.html', ctx, 'tiempo_compensatorio.pdf')
    return render(request, "reloj/compensatorio_list.html", ctx)


@login_required
@require_POST
def compensatorio_list_set_extra(request):
    """AJAX: guarda tiempo extra autorizado por día para un empleado."""
    u = request.user
    if not _reloj_can(u, 'compensatorio', 'editar'):
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

    if razon:
        RazonPermiso.objects.get_or_create(texto=razon[:200], defaults={'activo': True})

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


def _dias_hab_necesarios(total_min, min_dia):
    """Días hábiles para compensar total_min. min/día == 0 → sin acumulación
    diaria (solo tiempo extra) → 0 días. None/negativo → usa el default (47)."""
    if min_dia == 0 or total_min is None or total_min <= 0:
        return 0
    if min_dia is None or min_dia < 0:
        min_dia = MINUTOS_POR_DIA_COMP
    return _math.ceil(total_min / min_dia)


def _calcular_fecha_fin(fecha_inicio, dias_adeudados, feriados=None, minutos_dia=None):
    from datetime import timedelta
    feriados = feriados or set()
    minutos = float(dias_adeudados) * JORNADA_MIN
    if minutos_dia == 0:
        # sin acumulación diaria (solo tiempo extra) → sin fecha fin
        return None, int(minutos), 0
    if minutos_dia is None or minutos_dia < 0:
        minutos_dia = MINUTOS_POR_DIA_COMP
    dias_hab = _math.ceil(minutos / minutos_dia)
    fecha = fecha_inicio
    contados = 0
    while contados < dias_hab:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5 and fecha not in feriados:
            contados += 1
    return fecha, int(minutos), dias_hab


def _fecha_fin_por_saldo(hoy, saldo_min, minutos_dia, feriados=None):
    """Fecha fin estimada según el Saldo deuda = Total − (Compensado + T. extra):
    minutos pendientes ÷ minutos/día → días hábiles contados desde hoy."""
    from datetime import timedelta as _td
    feriados = feriados or set()
    if saldo_min <= 0:
        return None  # ya completado
    if minutos_dia == 0:
        return None  # sin acumulación diaria (solo tiempo extra) → sin fecha fin
    md = minutos_dia if (minutos_dia and minutos_dia > 0) else MINUTOS_POR_DIA_COMP
    dias_hab = _math.ceil(saldo_min / md)
    fecha, contados = hoy, 0
    while contados < dias_hab:
        fecha += _td(days=1)
        if fecha.weekday() < 5 and fecha not in feriados:
            contados += 1
    return fecha


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


# Orden deseado por usuario (fragmento único del nombre en minúsculas)
_ESPECIALES_COMP = ['alvarado', 'caceres', 'banegas', 'zuniga', 'chavez',
                    'figueroa', 'liliana', 'zavala', 'espino', 'lorena',
                    'johannys', 'fellmann']
_ESPECIALES_ORDEN = _ESPECIALES_COMP

def _especial_rank(nombre):
    n = nombre.lower()
    for i, key in enumerate(_ESPECIALES_ORDEN):
        if key in n:
            return i
    return len(_ESPECIALES_ORDEN)

# ── Permiso compensatorio tomado (fuente: PermisoReporte tipo compensatorio) ──
# <--- hecho por claude code
_TIPOS_PERMISO_COMP = ('compensatorio_dias',)
_HORAS_POR_DIA_COMP = 8  # conversión días → horas cuando el permiso se registró en días


def _permiso_horas_val(horas, dias):
    """Horas efectivas de un permiso: usa `horas` si existe; si no, días × 8."""
    if horas:
        return float(horas)
    return round(float(dias or 0) * _HORAS_POR_DIA_COMP, 2)


def _permiso_comp_horas(emp_codes, anio=None):
    """Σ horas de permiso compensatorio por emp_code. Si anio, filtra ese año.
    Convierte días → horas (×8) cuando el permiso se registró en días."""
    qs = PermisoReporte.objects.filter(emp_code__in=emp_codes, tipo__in=_TIPOS_PERMISO_COMP)
    if anio:
        qs = qs.filter(fecha__year=anio)
    out = {}
    for row in qs.values('emp_code', 'horas', 'dias'):
        ec = str(row['emp_code'])
        out[ec] = out.get(ec, 0) + _permiso_horas_val(row['horas'], row['dias'])
    return {k: round(v, 2) for k, v in out.items()}


def _permiso_comp_horas_por_mes(emp_codes, anio):
    """{emp_code: {mes: horas}} de permiso compensatorio en un año (días→horas ×8)."""
    qs = PermisoReporte.objects.filter(
        emp_code__in=emp_codes, tipo__in=_TIPOS_PERMISO_COMP, fecha__year=anio,
    ).values('emp_code', 'fecha', 'horas', 'dias')
    out = {}
    for row in qs:
        ec = str(row['emp_code'])
        mes = row['fecha'].month
        out.setdefault(ec, {})
        out[ec][mes] = out[ec].get(mes, 0.0) + _permiso_horas_val(row['horas'], row['dias'])
    return out


_MESES_CORTO = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def _compensado_real_map(emp_codes, fi, ff, tope=47, inicio_map=None):
    """Σ minutos compensatorios reales (marcas ZKBio) por emp_code en un rango.
    inicio_map: {emp_code: date} para contar solo desde la fecha de inicio de cada uno."""
    out = {}
    if not emp_codes:
        return out
    codigos_sql = ', '.join(f"'{c}'" for c in emp_codes)
    try:
        with connections['zkbio_sqlserver'].cursor() as cur:
            cur.execute(f"""
                SELECT CAST(t.emp_code AS VARCHAR(20)),
                       CONVERT(DATE, t.punch_time),
                       MIN(CAST(t.punch_time AS TIME)),
                       MAX(CAST(t.punch_time AS TIME))
                FROM dbo.iclock_transaction t
                WHERE CONVERT(DATE, t.punch_time) BETWEEN '{fi}' AND '{ff}'
                  AND t.emp_code IN ({codigos_sql})
                GROUP BY t.emp_code, CONVERT(DATE, t.punch_time)
            """)
            for emp_code, _fecha, primera, ultima in cur.fetchall():
                ec = str(emp_code).strip()
                # Si hay fecha de inicio por empleado, ignorar marcas anteriores
                if inicio_map is not None:
                    ini = inicio_map.get(ec)
                    if ini and _fecha and _fecha < ini:
                        continue
                comp_min, _ = _comp_min_dia(ec, _t_to_seg(primera), _t_to_seg(ultima), tope)
                if comp_min > 0:
                    out[ec] = out.get(ec, 0) + comp_min
    except Exception as ex:
        print(f"[WARN] _compensado_real_map: {ex}")
    return out


def _mensual_rows(anio):
    """Filas de la matriz mensual (tabs Horas Trabajadas / Horas Tomadas) para un año."""
    empleados = list(CompensatorioMensualEmpleado.objects.all())
    ecs = [str(e.emp_code) for e in empleados]
    valores = {
        (v.empleado_id, v.mes): v
        for v in CompensatorioMensualValor.objects.filter(empleado__in=empleados, anio=anio)
    }
    permiso_mes = _permiso_comp_horas_por_mes(ecs, anio)  # {emp: {mes: horas}}
    # Totales del detalle de comentarios (horas) por empleado/tipo
    from django.db.models import Sum as _Sum
    det_tot = {}
    for d in (CompensatorioMensualDetalle.objects.filter(empleado__in=empleados, anio=anio)
              .values('empleado_id', 'tipo').annotate(t=_Sum('horas'))):
        det_tot[(d['empleado_id'], d['tipo'])] = round(float(d['t'] or 0), 2)
    rows = []
    for e in empleados:
        trabajadas, tomadas, tomadas_permiso = [], [], []
        tot_trab = tot_tom = 0.0
        perm = permiso_mes.get(str(e.emp_code), {})
        for mes in range(1, 13):
            v = valores.get((e.pk, mes))
            t = float(v.horas_trabajadas) if v else 0.0
            perm_mes = round(perm.get(mes, 0.0), 2)
            # tomadas: override si existe, si no el permiso compensatorio del mes
            if v and v.horas_tomadas is not None:
                tm = float(v.horas_tomadas)
            else:
                tm = perm_mes
            trabajadas.append(round(t, 2))
            tomadas.append(round(tm, 2))
            tomadas_permiso.append(perm_mes)
            tot_trab += t
            tot_tom += tm
        rows.append({
            'emp': e,
            'meses': list(zip(range(1, 13), [round(x, 2) for x in trabajadas],
                              [round(x, 2) for x in tomadas], tomadas_permiso)),
            'trabajadas': trabajadas,
            'tomadas': tomadas,
            'total_trab': round(tot_trab, 2),
            'total_tom': round(tot_tom, 2),
            # Saldo del tab Horas Tomadas = trabajadas − tomadas (siempre se muestra)
            'total_saldo': round(tot_trab - tot_tom, 2),
            'comentario_trab': e.comentario_trab,
            'comentario_tom':  e.comentario_tom,
            'det_trab_total':  det_tot.get((e.pk, 'trab'), 0),
            'det_tom_total':   det_tot.get((e.pk, 'tom'), 0),
        })
    return rows


def _instructores_rows(anio, hoy, feriados=None):
    """Filas del tab Instructores (todo calculado menos tiempo extra autorizado)."""
    instructores = list(CompensatorioInstructor.objects.all())
    ecs = [str(i.emp_code) for i in instructores]
    # Cada instructor cuenta el compensado desde su fecha de inicio (o inicio de año)
    inicio_map = {str(i.emp_code): (i.fecha_inicio or date(anio, 1, 1)) for i in instructores}
    fi = min(inicio_map.values()) if inicio_map else date(anio, 1, 1)
    ff = min(hoy, date(anio, 12, 31))
    comp_map    = _compensado_real_map(ecs, fi, ff, tope=47, inicio_map=inicio_map)
    permiso_map = _permiso_comp_horas(ecs, anio)
    # Horario programado (rango de horas de la plantilla activa: "07:00 – 15:48")
    horario_map = {}
    for a in (EmployeeScheduleAssignment.objects.filter(emp_code__in=ecs, activo=True)
              .select_related('template').prefetch_related('template__reglas')):
        ec = str(a.emp_code)
        if ec in horario_map:
            continue
        regla = next((r for r in a.template.reglas.all() if r.trabaja and r.entrada_manana), None)
        if regla:
            ini = regla.entrada_manana.strftime('%H:%M')
            fin = regla.salida_tarde or regla.salida_manana
            horario_map[ec] = f"{ini} – {fin.strftime('%H:%M')}" if fin else ini
        else:
            horario_map[ec] = a.template.nombre
    # Totales de TE (minutos) y tomado manual (horas) por instructor
    from django.db.models import Sum as _SumI
    te_tot = {r['instructor_id']: int(r['t'] or 0)
              for r in CompensatorioInstructorTE.objects.values('instructor_id').annotate(t=_SumI('minutos'))}
    tom_tot = {r['instructor_id']: round(float(r['t'] or 0), 2)
               for r in CompensatorioInstructorTomado.objects.values('instructor_id').annotate(t=_SumI('horas'))}
    rows = []
    for i in instructores:
        ec = str(i.emp_code)
        comp_min  = comp_map.get(ec, 0)
        comp_hrs  = round(comp_min / 60, 2)
        te_min    = te_tot.get(i.pk, 0)
        te_hrs    = round(te_min / 60, 2)
        total_hrs = round(comp_hrs + te_hrs, 2)
        tomado_permiso = round(permiso_map.get(ec, 0), 2)
        tomado_hrs = round(tomado_permiso + tom_tot.get(i.pk, 0), 2)
        saldo_hrs = round(max(0.0, total_hrs - tomado_hrs), 2)
        rows.append({
            'i': i,
            'horario': horario_map.get(ec, '—'),
            'comp_hrs': comp_hrs,
            'te_min': te_min,
            'te_hrs': te_hrs,
            'total_hrs': total_hrs,
            'tomado_hrs': tomado_hrs,
            'tomado_permiso': tomado_permiso,
            'saldo_hrs': saldo_hrs,
            'fecha_inicio': i.fecha_inicio,
            'fecha_fin': i.fecha_fin,   # manual
        })
    return rows


def _receso_compute(desde, hasta):
    """Tiempo de receso (almuerzo) de los empleados con horario 07:00–15:48,
    en el rango [desde, hasta]. Marcas de receso = primer PAR dentro de la
    ventana de almuerzo (11:00–14:30); los ajustes manuales la reemplazan.
    Devuelve {'rows': [...], 'error': str|None}."""
    from datetime import time as _gt
    error = None
    # Plantillas con horario 07:00 → 15:48
    _tpl_ids = set(ScheduleRule.objects.filter(entrada_manana=_gt(7, 0)).filter(
        models.Q(salida_tarde=_gt(15, 48)) | models.Q(salida_manana=_gt(15, 48))
    ).values_list('template_id', flat=True))
    codes = set(EmployeeScheduleAssignment.objects.filter(
        activo=True, template_id__in=_tpl_ids).exclude(emp_code='9').values_list('emp_code', flat=True))
    # Excluir instructores (Matute, Giron, Rodríguez, Lagos…): tienen su propio control
    codes -= {str(c) for c in CompensatorioInstructor.objects.values_list('emp_code', flat=True)}
    nombres, marcas = {}, {}
    if codes:
        _in = ",".join(f"'{c}'" for c in sorted(codes))
        try:
            with connections['zkbio_sqlserver'].cursor() as cur:
                cur.execute(f"""
                    SELECT CAST(t.emp_code AS VARCHAR(20)),
                           (e.first_name + ' ' + e.last_name),
                           CONVERT(DATE, t.punch_time),
                           CONVERT(VARCHAR(5), CAST(t.punch_time AS TIME), 108)
                    FROM dbo.iclock_transaction t
                    INNER JOIN dbo.personnel_employee e ON e.emp_code = t.emp_code
                    WHERE CAST(t.emp_code AS VARCHAR(20)) IN ({_in})
                      AND CONVERT(DATE, t.punch_time) BETWEEN '{desde.isoformat()}' AND '{hasta.isoformat()}'
                    ORDER BY t.emp_code, t.punch_time
                """)
                for ec, nom, f, h in cur.fetchall():
                    ec = str(ec).strip()
                    nombres[ec] = nom.strip()
                    marcas.setdefault(ec, {}).setdefault(f, []).append(h)
        except Exception as e:
            error = str(e)

    def _rmin(h):
        hh, mm = map(int, h.split(':'))
        return hh * 60 + mm

    _VENT_INI, _VENT_FIN = 11 * 60, 14 * 60 + 30
    from .models import RecesoAjuste
    ajustes = {(a.emp_code, a.fecha): a for a in RecesoAjuste.objects.filter(
        fecha__gte=desde, fecha__lte=hasta)}

    rows = []
    for ec, nom in sorted(nombres.items(), key=lambda kv: kv[1]):
        dias_r, tot = [], 0
        for f in sorted(marcas.get(ec, {})):
            hs = marcas[ec][f]
            aj = ajustes.get((ec, f))
            manual = False
            if aj and aj.m2 and aj.m3:
                m2, m3 = aj.m2, aj.m3
                mins = max(0, _rmin(m3) - _rmin(m2))
                manual = True
            else:
                ventana = [h for h in hs if _VENT_INI <= _rmin(h) <= _VENT_FIN]
                if len(ventana) >= 2:
                    m2, m3 = ventana[0], ventana[1]
                    mins = max(0, _rmin(m3) - _rmin(m2))
                else:
                    m2 = ventana[0] if ventana else None
                    m3, mins = None, 0
            tot += mins
            extra = max(0, mins - 30) if m3 else 0   # minutos de más sobre los 30 permitidos
            dias_r.append({'fecha': f, 'm2': m2, 'm3': m3, 'minutos': mins,
                           'extra': extra, 'manual': manual, 'marcas': hs})
        if dias_r:
            extra_tot = sum(d['extra'] for d in dias_r)
            rows.append({
                'emp_code': ec, 'nombre': nom, 'dias': dias_r, 'ndias': len(dias_r),
                'total_min': tot, 'total_str': f"{tot // 60}h {tot % 60:02d}m",
                'extra_total': extra_tot,
            })
    return {'rows': rows, 'error': error}


@login_required
def compensatorio_calculo_list(request):
    # Requiere permiso de visualización del Control Compensatorio
    if not _reloj_can_ver(request.user, 'calculo_comp'):
        messages.error(request, 'No tiene permiso para ver el Control Compensatorio.')
        return redirect('reloj_dashboard')
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
        topes_map         = {str(r.emp_code): r.minutos_autorizados_dia for r in todos_registros}
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

    # ── Días no laborables ANA por calculo ──────────────────────────────────
    ids_calculos = [r.pk for r in todos_registros]
    dias_no_lab_qs = DiaNoLaborableANA.objects.filter(calculo_id__in=ids_calculos)
    dias_no_lab_map = {}  # {calculo_pk: [dia, ...]}
    for d in dias_no_lab_qs:
        dias_no_lab_map.setdefault(d.calculo_id, []).append(d)

    # ── Tiempos extra por empleado (TiempoExtraDia) ──────────────────────────
    # <--- hecho por claude code: suma todos los TiempoExtraDia por emp_code
    emp_codes_list = [str(r.emp_code) for r in todos_registros]
    te_sum_map    = {}   # {emp_code: total_minutos}
    te_detail_map = {}   # {emp_code: [lista TiempoExtraDia]}
    if emp_codes_list:
        for te in TiempoExtraDia.objects.filter(
            emp_code__in=emp_codes_list
        ).order_by('fecha'):
            ec_s = str(te.emp_code)
            te_detail_map.setdefault(ec_s, []).append(te)
            te_sum_map[ec_s] = te_sum_map.get(ec_s, 0) + te.minutos

    # ── Permiso compensatorio tomado (todas las fechas) por empleado ──────────
    permiso_comp_map = _permiso_comp_horas(emp_codes_list)  # {emp: horas}
    # Tiempo tomado manual (suma de entradas) por cálculo
    from django.db.models import Sum as _SumTM
    manual_tomado_map = {
        row['calculo_id']: round(float(row['t'] or 0), 2)
        for row in CompensatorioTomadoManual.objects.values('calculo_id').annotate(t=_SumTM('horas'))
    }

    # ── Receso: minutos de más (sobre los 30) se descuentan como Tiempo Tomado ──
    # Desde la fecha_inicio más antigua hasta hoy (mismo período del compensatorio).
    receso_extra_map = {}  # {emp_code: horas de más en receso}
    if todos_registros:
        try:
            _rec = _receso_compute(min(r.fecha_inicio for r in todos_registros), hoy)
            receso_extra_map = {str(row['emp_code']): row['extra_total'] / 60.0
                                for row in _rec.get('rows', [])}
        except Exception as _ex:
            print('[compensatorio] receso extra:', _ex)

    # ── Construir registros_data ─────────────────────────────────────────────
    def _min_to_h(m): return round(m / 60, 1)

    registros_data = []
    for r in todos_registros:
        ec           = str(r.emp_code)
        dias_trans   = _contar_dias_habiles_rango(r.fecha_inicio, hoy, feriados)

        # Compensado real desde marcas ZKBio (o override manual si existe)
        real_min = real_comp_map.get(ec, 0)
        minutos_compensados = r.minutos_compensados_manual if r.minutos_compensados_manual is not None else real_min

        # ── Total = Horas adeudadas (directo) + Permisos extras ──
        dias_nl        = dias_no_lab_map.get(r.pk, [])
        hrs_no_lab     = round(sum(d.total_horas for d in dias_nl), 2)

        factor         = round(float(r.factor_horas_dia or 8.0), 1)  # solo fallback
        # Horas adeudadas: valor directo si existe; si no, días × 8 (compatibilidad)
        if r.horas_adeudadas_manual is not None:
            horas_adeudadas = round(float(r.horas_adeudadas_manual), 2)
        else:
            horas_adeudadas = round(float(r.dias_adeudados) * factor, 2)
        permisos_extras = round(float(r.permisos_extras_horas or 0), 2)
        total_hrs      = round(horas_adeudadas + permisos_extras, 2)
        total_min      = round(total_hrs * 60)

        # min/día == 0 → sin acumulación diaria (solo tiempo extra) → 0 días hábiles
        dias_hab_calc = _dias_hab_necesarios(total_min, r.minutos_autorizados_dia)

        # Tiempo extra autorizado (suma de TiempoExtraDia del empleado) — informativo
        tiempo_extra_min = te_sum_map.get(ec, 0)

        # Tiempo TOMADO = permiso compensatorio + entradas manuales
        # Tiempo tomado = permiso compensatorio + manual + receso extra (min de más ÷ 60)
        tomado_hrs = round(permiso_comp_map.get(ec, 0) + manual_tomado_map.get(r.pk, 0)
                           + receso_extra_map.get(ec, 0), 2)
        tomado_min = round(tomado_hrs * 60)

        # Neto = Compensado + Tiempo extra ; Saldo restante = Neto − Tiempo tomado
        comp_mas_te_min = minutos_compensados + tiempo_extra_min
        neto_min        = comp_mas_te_min
        saldo_min       = max(0, neto_min - tomado_min)
        es_especial = any(k in r.nombre_empleado.lower() for k in _ESPECIALES_COMP)

        # Conversión a días para mostrar en tabla
        dias_no_lab_display  = round(hrs_no_lab / 8, 2) if hrs_no_lab else 0
        permisos_extras_dias = round(permisos_extras / factor, 2) if factor else 0

        registros_data.append({
            'r':                r,
            'saldo':            saldo_min,
            'dias_transcurridos': dias_trans,
            'minutos_compensados': minutos_compensados,
            'es_especial':      es_especial,
            'compensado_es_manual': r.minutos_compensados_manual is not None,
            'es_manual':            r.minutos_autorizados_dia == 0,  # min/día 0 → empleado manual (solo tiempo extra)
            # días no lab ANA (referencia)
            'hrs_no_lab':            hrs_no_lab,
            'dias_no_lab_display':   dias_no_lab_display,
            # cálculo principal
            'factor':           factor,
            'horas_adeudadas':  horas_adeudadas,
            'permisos_extras':  permisos_extras,
            'permisos_extras_dias': permisos_extras_dias,
            'total_hrs':        total_hrs,
            'total_min':        total_min,
            'dias_hab_calc':    dias_hab_calc,
            # tiempo extra autorizado (múltiples entradas)
            'tiempo_extra_min':     tiempo_extra_min,
            'tiempo_extra_hrs':     _min_to_h(tiempo_extra_min),
            'tiempo_extra_detalle': te_detail_map.get(ec, []),
            # tiempo extra tomado (override o permiso compensatorio)
            'tomado_hrs':           tomado_hrs,
            'tomado_min':           tomado_min,
            'tomado_es_override':   manual_tomado_map.get(r.pk, 0) > 0,
            # Saldo deuda = Total a compensar − (Compensado + T. extra)
            'saldo_fecha_hrs':      round(total_hrs - _min_to_h(comp_mas_te_min), 2),
            # Fecha fin estimada según el Saldo deuda (días hábiles desde hoy)
            'fecha_fin_est':        _fecha_fin_por_saldo(hoy, total_min - comp_mas_te_min,
                                                         r.minutos_autorizados_dia, feriados),
            # columnas nuevas: Compensado+T.extra y Neto
            'comp_mas_te_hrs':  _min_to_h(comp_mas_te_min),
            'comp_mas_te_min':  comp_mas_te_min,
            'neto_hrs':         _min_to_h(neto_min),
            'neto_min':         neto_min,
            # formateados
            'horas_compensados': _min_to_h(minutos_compensados),
            'horas_saldo':      _min_to_h(saldo_min),
        })

    # Especiales primero (en el orden definido), luego el resto alfabético
    registros_data.sort(key=lambda x: (
        _especial_rank(x['r'].nombre_empleado),
        x['r'].nombre_empleado.lower()
    ))

    # Especiales primero (en el orden definido), luego el resto alfabético
    u = request.user
    can_edit              = _reloj_can(u, 'calculo_comp', 'editar')
    can_delete            = _reloj_can(u, 'calculo_comp', 'eliminar')
    can_edit_compensado   = _reloj_can(u, 'calculo_comp', 'editar')
    can_edit_tiempo_extra = _reloj_can(u, 'calculo_comp', 'editar')
    # Todos los tabs usan el mismo permiso (Control Compensatorio = calculo_comp)
    can_edit_extra        = _reloj_can(u, 'calculo_comp', 'editar')
    can_delete_extra      = _reloj_can(u, 'calculo_comp', 'eliminar')

    # ── Año seleccionado (tabs 3/4/5) ──
    try:
        anio_sel = int(request.GET.get('anio') or hoy.year)
    except (TypeError, ValueError):
        anio_sel = hoy.year
    anios_set = set(CompensatorioMensualValor.objects.values_list('anio', flat=True))
    anios_set.update({hoy.year, hoy.year - 1, hoy.year + 1, anio_sel})
    anios = sorted(anios_set, reverse=True)

    # ── Datos tabs 3/4 (matriz mensual) y tab 5 (instructores) ──
    mensual_rows     = _mensual_rows(anio_sel)
    instructor_rows  = _instructores_rows(anio_sel, hoy, feriados)

    # ── Tab Gilma Lorenzo (emp 9): marcas y tiempo trabajado por RANGO de fechas ──
    from datetime import date as _gd, timedelta as _gtd
    import calendar as _gcal
    _GDIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    # Por defecto: mes actual (el usuario puede elegir quincenal o mensual)
    _def_ini = hoy.replace(day=1)
    _def_fin = hoy.replace(day=_gcal.monthrange(hoy.year, hoy.month)[1])
    _gini = _safe_date(request.GET.get('gini', _def_ini.isoformat()), _def_ini.isoformat())
    _gfin = _safe_date(request.GET.get('gfin', _def_fin.isoformat()), _def_fin.isoformat())
    _gini_d = _gd.fromisoformat(_gini)
    _gfin_d = _gd.fromisoformat(_gfin)
    if _gfin_d < _gini_d:                     # si vienen al revés, se corrigen
        _gini_d, _gfin_d = _gfin_d, _gini_d
    if (_gfin_d - _gini_d).days > 62:         # tope de seguridad (máx ~2 meses)
        _gfin_d = _gini_d + _gtd(days=62)
    gilma_marcas, gilma_error = {}, None
    try:
        with connections['zkbio_sqlserver'].cursor() as _gcur:
            _gcur.execute(f"""
                SELECT CONVERT(DATE, t.punch_time),
                       CONVERT(VARCHAR(5), CAST(t.punch_time AS TIME), 108)
                FROM dbo.iclock_transaction t
                WHERE CAST(t.emp_code AS VARCHAR(20)) = '9'
                  AND CONVERT(DATE, t.punch_time) BETWEEN '{_gini_d.isoformat()}' AND '{_gfin_d.isoformat()}'
                ORDER BY t.punch_time
            """)
            for _f, _h in _gcur.fetchall():
                gilma_marcas.setdefault(_f, []).append(_h)
    except Exception as _e:
        gilma_error = str(_e)
    gilma_dias, gilma_total_min = [], 0
    _d = _gini_d
    while _d <= _gfin_d:
        _hs = gilma_marcas.get(_d, [])
        _ent = _hs[0] if _hs else None
        _sal = _hs[-1] if len(_hs) > 1 else None
        _tmin = 0
        if _ent and _sal:
            _eh, _em = map(int, _ent.split(':')); _sh, _sm = map(int, _sal.split(':'))
            _tmin = max(0, (_sh * 60 + _sm) - (_eh * 60 + _em))
        gilma_total_min += _tmin
        gilma_dias.append({
            'dia': _GDIAS[_d.weekday()], 'fecha': _d, 'marcas': _hs,
            'entrada': _ent, 'salida': _sal,
            'trab': f"{_tmin/60:.2f} h" if (_ent and _sal) else "—",  # horas decimales
        })
        _d += _gtd(days=1)
    gilma = {
        'nombre': 'Gilma Lorenzo', 'emp_code': '9', 'dias': gilma_dias,
        'total_str': f"{gilma_total_min/60:.2f} h",  # horas decimales
        'ini': _gini_d, 'fin': _gfin_d,
        'error': gilma_error,
    }

    cfg = RelojConfigGlobal.get()
    ctx = {
        "gilma": gilma,
        "registros_data": registros_data,
        "feriados_count": Feriado.objects.count(),
        "minutos_dia": MINUTOS_POR_DIA_COMP,
        "can_edit":              can_edit,
        "can_delete":            can_delete,
        "can_edit_compensado":   can_edit_compensado,
        "can_edit_tiempo_extra": can_edit_tiempo_extra,
        "url_set_compensado":    "reloj_compensatorio_calculo_set_compensado",
        "factor_visible":        cfg.factor_horas_visible,
        # tabs 3/4/5
        "anio_sel":        anio_sel,
        "anios":           anios,
        "meses_corto":     _MESES_CORTO[1:],
        "mensual_rows":    mensual_rows,
        "instructor_rows": instructor_rows,
        "can_edit_extra":   can_edit_extra,
        "can_delete_extra": can_delete_extra,
    }
    if _es_pdf(request):
        sec = request.GET.get('sec', 'adeudados')
        if sec not in ('adeudados', 'general', 'instructores', 'gilma'):
            sec = 'adeudados'
        ctx['sec'] = sec
        return _reporte_pdf(request, 'reloj/pdf/calculo_pdf.html', ctx,
                            f'{sec}_{anio_sel}.pdf')
    return render(request, "reloj/compensatorio_calculo_list.html", ctx)


@login_required
def compensatorio_calculo_new(request):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
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
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
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
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        valor = int(request.POST.get('minutos', 0))
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})
    if valor < 0:
        return JsonResponse({'ok': False, 'error': 'No puede ser negativo'})
    # valor == 0 → sin acumulación diaria (empleado manual, solo tiempo extra)

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
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    raw = request.POST.get('minutos', '')
    try:
        if raw == '':            # vacío → vuelve a automático (marcas ZKBio)
            obj.minutos_compensados_manual = None
            valor = None
        else:
            valor = int(raw)
            if valor < 0:
                raise ValueError
            obj.minutos_compensados_manual = valor
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})

    obj.save(update_fields=['minutos_compensados_manual'])
    data = _recalc_calculo(obj)
    data['ok'] = True
    data['es_manual'] = valor is not None
    data['horas_compensados'] = round((valor or 0) / 60, 1) if valor is not None else None
    return JsonResponse(data)


@login_required
def compensatorio_calculo_set_tiempo_extra(request, pk):
    """AJAX: guarda minutos de tiempo extra autorizado y recalcula días hábiles + fecha fin."""
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
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

    minutos_efectivos = max(0, obj.minutos_total - tiempo_extra)
    # min/día == 0 → sin acumulación diaria (solo tiempo extra) → 0 días hábiles
    dias_hab = _dias_hab_necesarios(minutos_efectivos, obj.minutos_autorizados_dia)

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
def compensatorio_calculo_get_tiempo_extra(request, pk):
    """
    AJAX GET: devuelve las entradas TiempoExtraDia del empleado en el calculo.
    <--- hecho por claude code
    """
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    qs = TiempoExtraDia.objects.filter(emp_code=obj.emp_code).order_by('fecha')
    total_te = sum(t.minutos for t in qs)
    entries = [
        {
            'pk':      t.pk,
            'fecha':   t.fecha.strftime('%d/%m/%Y'),
            'minutos': t.minutos,
            'razon':   t.razon or '—',
        }
        for t in qs
    ]
    return JsonResponse({
        'ok':        True,
        'total_min': total_te,
        'total_hrs': round(total_te / 60, 1),
        'entries':   entries,
    })


@login_required
@require_POST
def compensatorio_calculo_add_tiempo_extra_entrada(request, pk):
    """
    AJAX: agrega (o suma a) una entrada TiempoExtraDia para el empleado del calculo.
    Permite múltiples entradas usando fechas distintas.
    Si ya existe una entrada para esa fecha, suma los minutos.
    <--- hecho por claude code
    """
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        body    = json.loads(request.body or b'{}')
        fecha   = date.fromisoformat(body.get('fecha', '').strip())
        minutos = int(body.get('minutos', 0))
        razon   = body.get('razon', '').strip()[:300]
        if minutos <= 0:
            raise ValueError('minutos <= 0')
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Datos inválidos: {e}'})

    te, created = TiempoExtraDia.objects.get_or_create(
        emp_code=obj.emp_code,
        fecha=fecha,
        defaults={'minutos': minutos, 'razon': razon, 'registrado_por': request.user}
    )
    if not created:
        te.minutos        += minutos   # Suma al existente de esa fecha
        te.razon           = razon or te.razon
        te.registrado_por  = request.user
        te.save()

    # Total acumulado
    total_te = sum(
        t.minutos for t in TiempoExtraDia.objects.filter(emp_code=obj.emp_code)
    )
    entries = [
        {
            'pk':      t.pk,
            'fecha':   t.fecha.strftime('%d/%m/%Y'),
            'minutos': t.minutos,
            'razon':   t.razon or '—',
        }
        for t in TiempoExtraDia.objects.filter(emp_code=obj.emp_code).order_by('fecha')
    ]
    rc = _recalc_calculo(obj)
    return JsonResponse({
        'ok':        True,
        'total_min': total_te,
        'total_hrs': round(total_te / 60, 1),
        'entries':   entries,
        'comp_mas_te_hrs': rc['comp_mas_te_hrs'], 'neto_hrs': rc['neto_hrs'], 'saldo_min': rc['saldo_min'],
    })


@login_required
@require_POST
def compensatorio_calculo_del_tiempo_extra_entrada(request, te_pk):
    """
    AJAX: elimina una entrada TiempoExtraDia específica.
    <--- hecho por claude code
    """
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    te = get_object_or_404(TiempoExtraDia, pk=te_pk)
    emp_code = str(te.emp_code)
    te.delete()
    total_te = sum(
        t.minutos for t in TiempoExtraDia.objects.filter(emp_code=emp_code)
    )
    entries = [
        {
            'pk':      t.pk,
            'fecha':   t.fecha.strftime('%d/%m/%Y'),
            'minutos': t.minutos,
            'razon':   t.razon or '—',
        }
        for t in TiempoExtraDia.objects.filter(emp_code=emp_code).order_by('fecha')
    ]
    resp = {
        'ok':        True,
        'total_min': total_te,
        'total_hrs': round(total_te / 60, 1),
        'entries':   entries,
    }
    _cc = CompensatorioCalculo.objects.filter(emp_code=emp_code).first()
    if _cc:
        rc = _recalc_calculo(_cc)
        resp.update({'comp_mas_te_hrs': rc['comp_mas_te_hrs'], 'neto_hrs': rc['neto_hrs'], 'saldo_min': rc['saldo_min']})
    return JsonResponse(resp)


@login_required
@require_POST
def compensatorio_add_tiempo_extra_byemp(request, emp_code):
    """
    AJAX: agrega una entrada TiempoExtraDia directamente por emp_code.
    Usado desde compensatorio_list cuando se filtra un empleado.
    <--- hecho por claude code
    """
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    try:
        body    = json.loads(request.body or b'{}')
        fecha   = date.fromisoformat(body.get('fecha', '').strip())
        minutos = int(body.get('minutos', 0))
        razon   = body.get('razon', '').strip()[:300]
        if minutos <= 0:
            raise ValueError('minutos <= 0')
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Datos inválidos: {e}'})

    te, created = TiempoExtraDia.objects.get_or_create(
        emp_code=emp_code,
        fecha=fecha,
        defaults={'minutos': minutos, 'razon': razon, 'registrado_por': request.user}
    )
    if not created:
        te.minutos       += minutos
        te.razon          = razon or te.razon
        te.registrado_por = request.user
        te.save()

    return JsonResponse({'ok': True, 'fecha': str(fecha), 'minutos': te.minutos})


@login_required
@require_POST
def compensatorio_set_dias_adeudados(request, pk):
    """AJAX POST: actualiza dias_adeudados y recalcula totales."""
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        body = json.loads(request.body or b'{}')
        valor = round(float(body.get('dias', 0)), 2)
        if valor < 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})
    obj.dias_adeudados = valor
    obj.save(update_fields=['dias_adeudados'])
    # Días adeudados es informativo; las horas adeudadas se editan aparte.
    data = _recalc_calculo(obj)
    data.update({'ok': True, 'dias': valor})
    return JsonResponse(data)


@login_required
@require_POST
def compensatorio_set_factor(request, pk):
    """AJAX POST: actualiza factor_horas_dia y recalcula totales."""
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        body = json.loads(request.body or b'{}')
        valor = round(float(body.get('factor', 8.0)), 1)
        if valor <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})
    obj.factor_horas_dia = valor
    obj.save(update_fields=['factor_horas_dia'])

    horas_adeudadas = round(float(obj.dias_adeudados) * valor, 2)
    permisos_extras = round(float(obj.permisos_extras_horas or 0), 2)
    total_hrs       = round(horas_adeudadas + permisos_extras, 2)
    total_min       = round(total_hrs * 60)
    min_dia         = obj.minutos_autorizados_dia
    dias_hab        = _dias_hab_necesarios(total_min, min_dia)

    hoy = date.today()
    from datetime import timedelta as _td
    feriados = set()
    for f in Feriado.objects.all():
        d = f.fecha_inicio
        while d <= f.fecha_fin:
            feriados.add(d)
            d += _td(days=1)
    dias_trans = _contar_dias_habiles_rango(obj.fecha_inicio, hoy, feriados)
    auto_comp  = min(dias_trans * min_dia, total_min)
    comp       = obj.minutos_compensados_manual if obj.minutos_compensados_manual is not None else auto_comp
    saldo_min  = max(0, total_min - comp)

    permisos_horas_actual = round(float(obj.permisos_extras_horas or 0), 2)
    permisos_extras_dias  = round(permisos_horas_actual / valor, 2) if valor else 0
    return JsonResponse({
        'ok': True, 'factor': valor,
        'horas_adeudadas': horas_adeudadas,
        'permisos_extras_dias': permisos_extras_dias,
        'total_hrs': total_hrs, 'total_min': total_min,
        'saldo_min': saldo_min, 'dias_hab': dias_hab,
    })


@login_required
def compensatorio_dias_no_lab_get(request, pk):
    """AJAX GET: devuelve lista de días no laborables ANA de un CompensatorioCalculo."""
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    dias = [
        {'id': d.pk, 'descripcion': d.descripcion, 'horas': float(d.horas)}
        for d in obj.dias_no_laborables.all()
    ]
    total_hrs = round(sum(d['horas'] for d in dias), 2)
    return JsonResponse({'ok': True, 'dias': dias, 'total_hrs': total_hrs})


@login_required
@require_POST
def compensatorio_dias_no_lab_add(request, pk):
    """AJAX POST: agrega un día no laborable ANA."""
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        body = json.loads(request.body or b'{}')
    except Exception:
        body = {}
    descripcion = body.get('descripcion', '').strip()
    horas_str   = body.get('horas', '8.8')
    try:
        horas = round(float(horas_str), 2)
        if horas <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor de horas inválido'})
    dia = DiaNoLaborableANA.objects.create(calculo=obj, descripcion=descripcion, horas=horas)
    dias = list(obj.dias_no_laborables.all())
    total_hrs = round(sum(float(d.horas) for d in dias), 2)
    return JsonResponse({
        'ok':          True,
        'id':          dia.pk,
        'descripcion': dia.descripcion,
        'horas':       float(dia.horas),
        'total_hrs':   total_hrs,
        'count':       len(dias),
    })


@login_required
@require_POST
def compensatorio_dias_no_lab_delete(request, dia_pk):
    """AJAX POST: elimina un día no laborable ANA específico."""
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    dia = get_object_or_404(DiaNoLaborableANA, pk=dia_pk)
    calculo_pk = dia.calculo_id
    dia.delete()
    dias = list(DiaNoLaborableANA.objects.filter(calculo_id=calculo_pk))
    total_hrs = round(sum(d.total_horas for d in dias), 2)
    return JsonResponse({'ok': True, 'total_hrs': total_hrs, 'count': len(dias)})


@login_required
@require_POST
def compensatorio_set_permisos_extras(request, pk):
    """AJAX POST: guarda permisos_extras (en días) y recalcula saldo."""
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        body = json.loads(request.body or b'{}')
        horas_val = round(float(body.get('horas', 0)), 2)
        if horas_val < 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})

    factor = round(float(obj.factor_horas_dia or 8.0), 1)
    obj.permisos_extras_horas = horas_val if horas_val > 0 else None
    obj.save(update_fields=['permisos_extras_horas'])

    data = _recalc_calculo(obj)
    data['ok'] = True
    data['permisos_extras_dias'] = round(horas_val / factor, 2) if factor else 0
    return JsonResponse(data)


# ── Recálculo central de un CompensatorioCalculo (tabs 1-2) ──────────────────
# <--- hecho por claude code
def _recalc_calculo(obj, feriados=None):
    from datetime import timedelta as _td
    factor = float(obj.factor_horas_dia or 8.0)
    if obj.horas_adeudadas_manual is not None:
        horas_adeudadas = round(float(obj.horas_adeudadas_manual), 2)
    else:
        horas_adeudadas = round(float(obj.dias_adeudados) * factor, 2)
    permisos  = round(float(obj.permisos_extras_horas or 0), 2)
    total_hrs = round(horas_adeudadas + permisos, 2)
    total_min = round(total_hrs * 60)
    min_dia   = obj.minutos_autorizados_dia
    dias_hab  = _dias_hab_necesarios(total_min, min_dia)

    if feriados is None:
        feriados = set()
        for f in Feriado.objects.all():
            d = f.fecha_inicio
            while d <= f.fecha_fin:
                feriados.add(d)
                d += _td(days=1)
    dias_trans = _contar_dias_habiles_rango(obj.fecha_inicio, date.today(), feriados)
    auto_comp  = min(dias_trans * min_dia, total_min)
    comp       = obj.minutos_compensados_manual if obj.minutos_compensados_manual is not None else auto_comp

    # Tiempo extra autorizado (suma de TiempoExtraDia)
    te_min = sum(t.minutos for t in TiempoExtraDia.objects.filter(emp_code=str(obj.emp_code)))

    # Tiempo tomado = permiso compensatorio + entradas manuales
    from django.db.models import Sum as _SumTM2
    manual_h = obj.tomados_manual.aggregate(t=_SumTM2('horas'))['t'] or 0
    permiso_h = _permiso_comp_horas([str(obj.emp_code)]).get(str(obj.emp_code), 0)
    tomado_hrs = round(float(permiso_h) + float(manual_h), 2)
    tomado_min = round(tomado_hrs * 60)

    # Neto = Compensado + Tiempo extra ; Saldo = Neto − Tiempo tomado
    comp_mas_te_min = comp + te_min
    neto_min        = comp_mas_te_min
    saldo_min       = max(0, neto_min - tomado_min)
    _h = lambda m: round(m / 60, 1)
    return {
        'horas_adeudadas': horas_adeudadas,
        'total_hrs': total_hrs, 'total_min': total_min,
        'dias_hab': dias_hab, 'saldo_min': saldo_min,
        'tomado_hrs': tomado_hrs,
        'comp_mas_te_hrs': _h(comp_mas_te_min), 'neto_hrs': _h(neto_min),
    }


def _tomado_manual_payload(obj):
    manual = [
        {'pk': t.pk, 'fecha': t.fecha.strftime('%d/%m/%Y'),
         'horas': round(float(t.horas), 2), 'razon': t.razon or '—'}
        for t in obj.tomados_manual.all()
    ]
    total_manual = round(sum(m['horas'] for m in manual), 2)
    return manual, total_manual


@login_required
def compensatorio_calculo_get_tomado(request, pk):
    """AJAX GET: detalle del permiso compensatorio + tomado manual de un empleado."""
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    qs = PermisoReporte.objects.filter(
        emp_code=obj.emp_code, tipo__in=_TIPOS_PERMISO_COMP
    ).order_by('fecha')
    entries = [
        {'fecha': p.fecha.strftime('%d/%m/%Y'),
         'horas': _permiso_horas_val(p.horas, p.dias),
         'razon': p.razon or '—'}
        for p in qs
    ]
    total_permiso = round(sum(e['horas'] for e in entries), 2)
    manual, total_manual = _tomado_manual_payload(obj)
    # Receso: minutos de más (sobre los 30) por MES → se cuentan como tiempo tomado extra
    receso_por_mes = {}
    try:
        _rec = _receso_compute(obj.fecha_inicio, date.today())
        for row in _rec.get('rows', []):
            if str(row['emp_code']) == str(obj.emp_code):
                for d in row['dias']:
                    if d.get('extra', 0) > 0:
                        mk = d['fecha'].strftime('%Y-%m')
                        receso_por_mes[mk] = receso_por_mes.get(mk, 0) + d['extra']
                break
    except Exception as _ex:
        print('[tomado] receso extra:', _ex)
    _MESES_ES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
                 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    receso = [{'mes': f'{_MESES_ES[int(mk[5:7]) - 1]} {mk[:4]}', 'minutos': v}
              for mk, v in sorted(receso_por_mes.items())]
    receso_min = sum(receso_por_mes.values())
    receso_hrs = round(receso_min / 60, 2)
    return JsonResponse({
        'ok': True, 'entries': entries, 'total_permiso': total_permiso,
        'manual': manual, 'total_manual': total_manual,
        'receso': receso, 'receso_min': receso_min, 'receso_hrs': receso_hrs,
        'total_tomado': round(total_permiso + total_manual + receso_hrs, 2),
    })


@login_required
@require_POST
def compensatorio_tomado_manual_add(request, pk):
    """AJAX: agrega una entrada de tiempo tomado manual y recalcula."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    body = json.loads(request.body or b'{}')
    try:
        fecha = date.fromisoformat((body.get('fecha') or '').strip())
        horas = round(float(body.get('horas') or 0), 2)
        razon = (body.get('razon') or '').strip()[:300]
        if horas <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
    CompensatorioTomadoManual.objects.create(calculo=obj, fecha=fecha, horas=horas, razon=razon)
    manual, total_manual = _tomado_manual_payload(obj)
    rc = _recalc_calculo(obj)
    return JsonResponse({'ok': True, 'manual': manual, 'total_manual': total_manual,
                         'tomado_hrs': rc['tomado_hrs'], 'neto_hrs': rc['neto_hrs'], 'saldo_min': rc['saldo_min']})


@login_required
@require_POST
def compensatorio_tomado_manual_del(request, tm_pk):
    """AJAX: elimina una entrada de tiempo tomado manual y recalcula."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    tm = get_object_or_404(CompensatorioTomadoManual, pk=tm_pk)
    obj = tm.calculo
    tm.delete()
    manual, total_manual = _tomado_manual_payload(obj)
    rc = _recalc_calculo(obj)
    return JsonResponse({'ok': True, 'manual': manual, 'total_manual': total_manual,
                         'tomado_hrs': rc['tomado_hrs'], 'neto_hrs': rc['neto_hrs'], 'saldo_min': rc['saldo_min']})


@login_required
@require_POST
def compensatorio_set_horas_adeudadas(request, pk):
    """AJAX: guarda horas_adeudadas directo (reemplaza días × factor) y recalcula."""
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        body = json.loads(request.body or b'{}')
        valor = round(float(body.get('horas', 0)), 2)
        if valor < 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})
    obj.horas_adeudadas_manual = valor
    obj.save(update_fields=['horas_adeudadas_manual'])
    data = _recalc_calculo(obj)
    data['ok'] = True
    return JsonResponse(data)


@login_required
@require_POST
def compensatorio_set_tomado(request, pk):
    """AJAX: guarda override de tiempo extra tomado (h). Vacío → vuelve al permiso."""
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    obj = get_object_or_404(CompensatorioCalculo, pk=pk)
    try:
        body = json.loads(request.body or b'{}')
        raw = body.get('horas', None)
        if raw in (None, ''):
            obj.horas_tiempo_extra_tomado_manual = None
        else:
            v = round(float(raw), 2)
            if v < 0:
                raise ValueError
            obj.horas_tiempo_extra_tomado_manual = v
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})
    obj.save(update_fields=['horas_tiempo_extra_tomado_manual'])
    data = _recalc_calculo(obj)
    data['ok'] = True
    data['es_override'] = obj.horas_tiempo_extra_tomado_manual is not None
    return JsonResponse(data)


# ── Buscador de empleados ZKBio (para "Agregar empleado" tabs 3/4/5) ──────────
@login_required
def compensatorio_emp_buscar(request):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    q = (request.GET.get('q') or '').strip()
    empleados = []
    try:
        with connections['zkbio_sqlserver'].cursor() as cur:
            cur.execute("""
                SELECT TOP 50 CAST(e.emp_code AS VARCHAR(20)) AS emp_code,
                       e.first_name + ' ' + ISNULL(e.last_name,'') AS nombre
                FROM dbo.personnel_employee e
                WHERE (%s = '' OR e.first_name + ' ' + ISNULL(e.last_name,'') LIKE %s
                       OR CAST(e.emp_code AS VARCHAR(20)) LIKE %s)
                ORDER BY e.first_name, e.last_name
            """, [q, f'%{q}%', f'%{q}%'])
            for code, nombre in cur.fetchall():
                empleados.append({'emp_code': (code or '').strip(), 'nombre': (nombre or '').strip()})
    except Exception as ex:
        return JsonResponse({'ok': False, 'error': str(ex)})
    return JsonResponse({'ok': True, 'empleados': empleados})


# ── Tabs 3/4: matriz mensual ──────────────────────────────────────────────────
@login_required
@require_POST
def compensatorio_mensual_add(request):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    body = json.loads(request.body or b'{}')
    emp_code = (body.get('emp_code') or '').strip()
    nombre   = (body.get('nombre') or '').strip()
    if not emp_code:
        return JsonResponse({'ok': False, 'error': 'Falta empleado'}, status=400)
    obj, created = CompensatorioMensualEmpleado.objects.get_or_create(
        emp_code=emp_code, defaults={'nombre_empleado': nombre or emp_code})
    return JsonResponse({'ok': True, 'created': created})


@login_required
@require_POST
def compensatorio_mensual_cell(request):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    body = json.loads(request.body or b'{}')
    try:
        emp_id = int(body.get('empleado_id'))
        anio   = int(body.get('anio'))
        mes    = int(body.get('mes'))
        campo  = (body.get('campo') or '').strip()  # 'trabajadas' | 'tomadas'
        raw    = body.get('valor', '')
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
    if campo not in ('trabajadas', 'tomadas') or not (1 <= mes <= 12):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
    emp = get_object_or_404(CompensatorioMensualEmpleado, pk=emp_id)
    val, _ = CompensatorioMensualValor.objects.get_or_create(empleado=emp, anio=anio, mes=mes)
    if campo == 'trabajadas':
        val.horas_trabajadas = round(float(raw or 0), 2)
    else:  # tomadas (override; vacío → null = vuelve al permiso)
        val.horas_tomadas = None if raw in (None, '') else round(float(raw), 2)
    val.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def compensatorio_mensual_comentario(request):
    """AJAX: guarda el comentario por empleado (trab/tom) en la matriz mensual."""
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    body = json.loads(request.body or b'{}')
    try:
        emp_id = int(body.get('empleado_id'))
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
    campo = (body.get('campo') or '').strip()  # 'trab' | 'tom'
    texto = (body.get('texto') or '').strip()
    emp = get_object_or_404(CompensatorioMensualEmpleado, pk=emp_id)
    if campo == 'trab':
        emp.comentario_trab = texto
        emp.save(update_fields=['comentario_trab'])
    elif campo == 'tom':
        emp.comentario_tom = texto
        emp.save(update_fields=['comentario_tom'])
    else:
        return JsonResponse({'ok': False, 'error': 'Campo inválido'}, status=400)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def compensatorio_mensual_delete(request, pk):
    if not _reloj_can(request.user, 'calculo_comp', 'eliminar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    get_object_or_404(CompensatorioMensualEmpleado, pk=pk).delete()
    return JsonResponse({'ok': True})


# ── Detalle de comentarios con horas (modal estilo tiempo extra) ──────────────
def _detalle_payload(emp, anio, tipo):
    qs = CompensatorioMensualDetalle.objects.filter(empleado=emp, anio=anio, tipo=tipo).order_by('fecha', 'pk')
    entries = [
        {'pk': d.pk, 'fecha': d.fecha.strftime('%d/%m/%Y'),
         'horas': round(float(d.horas), 2), 'comentario': d.comentario or '—'}
        for d in qs
    ]
    total = round(sum(e['horas'] for e in entries), 2)
    return entries, total


@login_required
def compensatorio_mensual_detalle_get(request):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    try:
        emp = get_object_or_404(CompensatorioMensualEmpleado, pk=int(request.GET.get('empleado_id')))
        anio = int(request.GET.get('anio'))
        tipo = (request.GET.get('tipo') or '').strip()
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
    if tipo not in ('trab', 'tom'):
        return JsonResponse({'ok': False, 'error': 'Tipo inválido'}, status=400)
    entries, total = _detalle_payload(emp, anio, tipo)
    return JsonResponse({'ok': True, 'entries': entries, 'total': total})


@login_required
@require_POST
def compensatorio_mensual_detalle_add(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    body = json.loads(request.body or b'{}')
    try:
        emp = get_object_or_404(CompensatorioMensualEmpleado, pk=int(body.get('empleado_id')))
        anio  = int(body.get('anio'))
        tipo  = (body.get('tipo') or '').strip()
        fecha = date.fromisoformat((body.get('fecha') or '').strip())
        horas = round(float(body.get('horas') or 0), 2)
        comentario = (body.get('comentario') or '').strip()[:300]
        if tipo not in ('trab', 'tom') or horas <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
    CompensatorioMensualDetalle.objects.create(
        empleado=emp, anio=anio, tipo=tipo, fecha=fecha, horas=horas, comentario=comentario)
    entries, total = _detalle_payload(emp, anio, tipo)
    return JsonResponse({'ok': True, 'entries': entries, 'total': total})


@login_required
@require_POST
def compensatorio_mensual_detalle_delete(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    d = get_object_or_404(CompensatorioMensualDetalle, pk=pk)
    emp, anio, tipo = d.empleado, d.anio, d.tipo
    d.delete()
    entries, total = _detalle_payload(emp, anio, tipo)
    return JsonResponse({'ok': True, 'entries': entries, 'total': total})


# ── Tab 5: instructores ─────────────────────────────────────────────────────
@login_required
@require_POST
def compensatorio_instructor_add(request):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    body = json.loads(request.body or b'{}')
    emp_code = (body.get('emp_code') or '').strip()
    nombre   = (body.get('nombre') or '').strip()
    if not emp_code:
        return JsonResponse({'ok': False, 'error': 'Falta empleado'}, status=400)
    obj, created = CompensatorioInstructor.objects.get_or_create(
        emp_code=emp_code, defaults={'nombre_empleado': nombre or emp_code})
    return JsonResponse({'ok': True, 'created': created})


@login_required
@require_POST
def compensatorio_instructor_set(request, pk):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    obj = get_object_or_404(CompensatorioInstructor, pk=pk)
    body = json.loads(request.body or b'{}')
    campo = (body.get('campo') or '').strip()  # 'fecha_inicio' | 'fecha_fin'
    raw   = body.get('valor', '')
    try:
        if campo == 'fecha_inicio':
            obj.fecha_inicio = date.fromisoformat(raw) if raw else None
            obj.save(update_fields=['fecha_inicio'])
        elif campo == 'fecha_fin':
            obj.fecha_fin = date.fromisoformat(raw) if raw else None
            obj.save(update_fields=['fecha_fin'])
        else:
            return JsonResponse({'ok': False, 'error': 'Campo inválido'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'}, status=400)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def compensatorio_instructor_delete(request, pk):
    if not _reloj_can(request.user, 'calculo_comp', 'eliminar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    get_object_or_404(CompensatorioInstructor, pk=pk).delete()
    return JsonResponse({'ok': True})


# ── Instructor: Tiempo extra (entradas Fecha+Minutos+Comentario) ──────────────
def _inst_te_payload(inst):
    qs = inst.te_entradas.all().order_by('fecha', 'pk')
    entries = [{'pk': t.pk, 'fecha': t.fecha.strftime('%d/%m/%Y'),
                'minutos': t.minutos, 'comentario': t.comentario or '—'} for t in qs]
    total_min = sum(e['minutos'] for e in entries)
    return entries, total_min


@login_required
def compensatorio_instructor_te_get(request, pk):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    inst = get_object_or_404(CompensatorioInstructor, pk=pk)
    entries, total_min = _inst_te_payload(inst)
    return JsonResponse({'ok': True, 'entries': entries, 'total_min': total_min,
                         'total_hrs': round(total_min / 60, 2)})


@login_required
@require_POST
def compensatorio_instructor_te_add(request, pk):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    inst = get_object_or_404(CompensatorioInstructor, pk=pk)
    body = json.loads(request.body or b'{}')
    try:
        fecha = date.fromisoformat((body.get('fecha') or '').strip())
        minutos = int(round(float(body.get('minutos') or 0)))
        comentario = (body.get('comentario') or '').strip()[:300]
        if minutos <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
    CompensatorioInstructorTE.objects.create(instructor=inst, fecha=fecha, minutos=minutos, comentario=comentario)
    entries, total_min = _inst_te_payload(inst)
    return JsonResponse({'ok': True, 'entries': entries, 'total_min': total_min, 'total_hrs': round(total_min / 60, 2)})


@login_required
@require_POST
def compensatorio_instructor_te_del(request, te_pk):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    t = get_object_or_404(CompensatorioInstructorTE, pk=te_pk)
    inst = t.instructor
    t.delete()
    entries, total_min = _inst_te_payload(inst)
    return JsonResponse({'ok': True, 'entries': entries, 'total_min': total_min, 'total_hrs': round(total_min / 60, 2)})


# ── Instructor: Permiso tomado manual (solo superuser) ────────────────────────
def _inst_tomado_payload(inst, anio):
    permiso = round(_permiso_comp_horas([str(inst.emp_code)], anio).get(str(inst.emp_code), 0), 2)
    manual = [{'pk': t.pk, 'fecha': t.fecha.strftime('%d/%m/%Y'),
               'horas': round(float(t.horas), 2), 'razon': t.razon or '—'}
              for t in inst.tomados_manual.all().order_by('fecha', 'pk')]
    total_manual = round(sum(m['horas'] for m in manual), 2)
    return permiso, manual, total_manual


@login_required
def compensatorio_instructor_tomado_get(request, pk):
    if not _reloj_can(request.user, 'calculo_comp', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    inst = get_object_or_404(CompensatorioInstructor, pk=pk)
    try:
        anio = int(request.GET.get('anio') or date.today().year)
    except (ValueError, TypeError):
        anio = date.today().year
    permiso, manual, total_manual = _inst_tomado_payload(inst, anio)
    return JsonResponse({'ok': True, 'permiso': permiso, 'manual': manual,
                         'total_manual': total_manual, 'total_tomado': round(permiso + total_manual, 2)})


@login_required
@require_POST
def compensatorio_instructor_tomado_add(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    inst = get_object_or_404(CompensatorioInstructor, pk=pk)
    body = json.loads(request.body or b'{}')
    try:
        anio = int(body.get('anio') or date.today().year)
        fecha = date.fromisoformat((body.get('fecha') or '').strip())
        horas = round(float(body.get('horas') or 0), 2)
        razon = (body.get('razon') or '').strip()[:300]
        if horas <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
    CompensatorioInstructorTomado.objects.create(instructor=inst, fecha=fecha, horas=horas, razon=razon)
    permiso, manual, total_manual = _inst_tomado_payload(inst, anio)
    return JsonResponse({'ok': True, 'permiso': permiso, 'manual': manual,
                         'total_manual': total_manual, 'total_tomado': round(permiso + total_manual, 2)})


@login_required
@require_POST
def compensatorio_instructor_tomado_del(request, tm_pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    t = get_object_or_404(CompensatorioInstructorTomado, pk=tm_pk)
    inst = t.instructor
    anio = t.fecha.year
    t.delete()
    permiso, manual, total_manual = _inst_tomado_payload(inst, anio)
    return JsonResponse({'ok': True, 'permiso': permiso, 'manual': manual,
                         'total_manual': total_manual, 'total_tomado': round(permiso + total_manual, 2)})


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

# date.weekday() (0=Lunes .. 6=Domingo) → código usado en dias_laborables
_WEEKDAY_COD = {0: 'L', 1: 'M', 2: 'X', 3: 'J', 4: 'V', 5: 'S', 6: 'D'}
_DIAS_LABORABLES_DEFAULT = {'L', 'M', 'X', 'J', 'V'}


def _parse_dias_laborables(valor: str) -> set:
    """Convierte 'L,M,X,J,V' → {'L','M','X','J','V'}. Vacío → default L-V."""
    if not valor:
        return set(_DIAS_LABORABLES_DEFAULT)
    cods = {c.strip().upper() for c in valor.split(',') if c.strip()}
    return cods or set(_DIAS_LABORABLES_DEFAULT)


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


_TARDE_REGLAS_DEFAULT = [
    {'min': 11, 'max': 30, 'horas': 0.5},
    {'min': 31, 'max': 60, 'horas': 1.0},
]


def _rebaja_por_dia(minutos: int, reglas=None) -> float:
    """Horas rebajadas según los minutos de tardanza, usando reglas configurables.
    Toma el tramo más alto cuyo 'min' se alcanza; el último tramo aplica también
    por encima de su 'max'."""
    reglas = reglas or _TARDE_REGLAS_DEFAULT
    horas = 0.0
    for rg in sorted(reglas, key=lambda x: x.get('min', 0)):
        try:
            if minutos >= int(rg.get('min', 0)):
                horas = float(rg.get('horas', 0))
        except (TypeError, ValueError):
            continue
    return horas


@login_required
@_reloj_ver_required('reporte')
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

    # Maestros por hora (tabla de horas variable) — excluye a Gilma Lorenzo (9)
    from django.db.models import Sum as _SumMH
    from reloj.models import EmployeeScheduleAssignment as _ESA
    maestro_hora_codes = set(
        _ESA.objects
        .filter(activo=True, template__nombre__icontains='maestro por hora')
        .exclude(emp_code='9')
        .values_list('emp_code', flat=True)
    )
    mh_totales = {
        str(r['emp_code']): round(float(r['t'] or 0), 2)
        for r in MaestroHoraDia.objects.filter(
            emp_code__in=maestro_hora_codes
        ).values('emp_code').annotate(t=_SumMH('horas'))
    }
    # Total del MES: suma de las horas de cada día laborable que cae en el mes
    from datetime import timedelta as _td2
    _mh_dias = {}  # {emp: {weekday: horas}}
    for d in MaestroHoraDia.objects.filter(emp_code__in=maestro_hora_codes):
        _mh_dias.setdefault(str(d.emp_code), {})[d.weekday] = float(d.horas)
    mh_total_mes = {}
    for ec_m, wd_h in _mh_dias.items():
        tot, dd = 0.0, mes_inicio
        while dd <= mes_fin:
            tot += wd_h.get(dd.weekday(), 0)  # solo días con horas (laborables)
            dd += _td2(days=1)
        mh_total_mes[ec_m] = round(tot, 2)

    # Restar las horas de los permisos NO PAGADO del total mensual del maestro por hora
    if maestro_hora_codes:
        _np = (PermisoReporte.objects
               .filter(emp_code__in=maestro_hora_codes, tipo='ausencias_dias',
                       fecha__gte=mes_inicio, fecha__lte=mes_fin)
               .values('emp_code').annotate(h=_SumMH('horas')))
        for r in _np:
            ec_np = str(r['emp_code'])
            if ec_np in mh_total_mes:
                mh_total_mes[ec_np] = round(max(0.0, mh_total_mes[ec_np] - float(r['h'] or 0)), 2)

    # Reglas configurables de rebaja por tardanza
    _tarde_reglas = RelojConfigGlobal.get().tarde_reglas or _TARDE_REGLAS_DEFAULT

    empleados = []
    # {emp_code: [minutos_tarde_por_dia, ...]}
    tarde_por_dia_map: dict = {}
    error_sql = None

    # Días laborables configurados por empleado para este mes (controla qué
    # marcas tardías cuentan: una marca en un día no laborable se ignora).
    dias_lab_map = {
        r.emp_code: _parse_dias_laborables(r.dias_laborables)
        for r in ReportePermisoMensual.objects.filter(mes=mes_inicio)
    }

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
                # Solo contar la tardanza si el día es laborable para el empleado.
                dias_lab = dias_lab_map.get(ec, _DIAS_LABORABLES_DEFAULT)
                if _fecha is not None and _WEEKDAY_COD.get(_fecha.weekday()) not in dias_lab:
                    continue
                tarde_por_dia_map.setdefault(ec, []).append(int(mins or 0))

    except Exception as exc:
        error_sql = str(exc)

    # ── Marca de ENTRADA (primera marca) por empleado/día del mes (para el bono) ──
    entrada_por_dia_map = {}
    try:
        with connections['zkbio_sqlserver'].cursor() as cursor:
            cursor.execute(f"""
                SELECT CAST(e.emp_code AS VARCHAR(20)),
                       CONVERT(DATE, t.punch_time),
                       CONVERT(VARCHAR(5), MIN(CAST(t.punch_time AS TIME)), 108)
                FROM dbo.personnel_employee e
                INNER JOIN dbo.iclock_transaction t
                        ON t.emp_code = e.emp_code
                       AND CONVERT(DATE, t.punch_time) BETWEEN '{mes_inicio}' AND '{mes_fin}'
                GROUP BY e.emp_code, CONVERT(DATE, t.punch_time)
                ORDER BY e.emp_code, CONVERT(DATE, t.punch_time)
            """)
            for code, _f, hhmm in cursor.fetchall():
                ec = (code or '').strip()
                entrada_por_dia_map.setdefault(ec, []).append((_f, hhmm))
    except Exception:
        pass

    # ── Entrada NOCTURNA de vigilantes (primera marca >= 17:00) para el bono ──
    vigil_codes = {e['emp_code'] for e in empleados if 'vigilan' in (e['cargo'] or '').lower()}
    vigil_entrada_map = {}
    if vigil_codes:
        _vin = ",".join(f"'{c}'" for c in vigil_codes)
        try:
            with connections['zkbio_sqlserver'].cursor() as cursor:
                cursor.execute(f"""
                    SELECT CAST(t.emp_code AS VARCHAR(20)),
                           CONVERT(DATE, t.punch_time),
                           CONVERT(VARCHAR(5), MIN(CAST(t.punch_time AS TIME)), 108)
                    FROM dbo.iclock_transaction t
                    WHERE CAST(t.emp_code AS VARCHAR(20)) IN ({_vin})
                      AND CONVERT(DATE, t.punch_time) BETWEEN '{mes_inicio}' AND '{mes_fin}'
                      AND CAST(t.punch_time AS TIME) >= '17:00:00'
                    GROUP BY t.emp_code, CONVERT(DATE, t.punch_time)
                    ORDER BY t.emp_code, CONVERT(DATE, t.punch_time)
                """)
                for code, _f, hhmm in cursor.fetchall():
                    vigil_entrada_map.setdefault(str(code).strip(), []).append((_f, hhmm))
        except Exception:
            pass

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
        if str(ec) == '9':   # Gilma Lorenzo (Administración) — fuera de permisos
            continue
        cargo_l = emp['cargo'].lower()
        excluido = any(exc in cargo_l for exc in _CARGOS_EXCLUIDOS_TARDE) or ec in excluir_codes
        lista_mins = tarde_por_dia_map.get(ec, [])

        minutos_tarde = sum(lista_mins) if not excluido else None
        # La rebaja se calcula sobre el TOTAL del mes (no por día): 11–30 → 0.5h, 31–60 → 1h.
        horas_rebaja = _rebaja_por_dia(sum(lista_mins), _tarde_reglas) if not excluido else None

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
            'es_maestro_hora': ec in maestro_hora_codes,
            'mh_total':        mh_totales.get(ec, 0),
            'mh_total_mes':    mh_total_mes.get(ec, 0),
            'grupo': ('maestro' if ec in maestro_hora_codes
                      else 'vigilante' if 'vigilan' in cargo_l  # 'Vigilancia' → sección Vigilancia (abajo)
                      else 'general'),
        })

    _DIAS_SEMANA = [('L','Lun'),('M','Mar'),('X','Mié'),('J','Jue'),('V','Vie'),('S','Sáb'),('D','Dom')]
    rows_general   = [r for r in rows if r['grupo'] == 'general']
    rows_maestro   = [r for r in rows if r['grupo'] == 'maestro']
    rows_vigilante = [r for r in rows if r['grupo'] == 'vigilante']

    # Sub-tabs del tab general según las horas diarias laboradas (8.0 vs 8.8)
    def _hdl(row):
        reg = row.get('r')
        try:
            return float(reg.horas_diarias_laboradas) if reg else 8.0
        except Exception:
            return 8.0
    rows_general_88 = [r for r in rows_general if _hdl(r) == 8.8]
    rows_general_80 = [r for r in rows_general if _hdl(r) != 8.8]

    # ── Tab Tiempo receso (mensual): marcas de almuerzo de empleados 07:00–15:48 ──
    receso = _receso_compute(mes_inicio, mes_fin)
    receso['mes'] = mes_inicio

    # ── Tab Bono por Asistencia: cálculo automático según reglas ──
    from .models import BonoConfig, BonoReglaExtra, BonoHorarioEmpleado
    bcfg = BonoConfig.get()
    reglas_extra = list(BonoReglaExtra.objects.filter(activa=True))
    # Horarios especiales por empleado/día (maestros por hora): {(emp, weekday): min}
    _horario_esp = {}
    for he in BonoHorarioEmpleado.objects.filter(activa=True):
        _horario_esp[(str(he.emp_code), he.weekday)] = he.hora.hour * 60 + he.hora.minute
    CAMPOS_PERMISO_MAP = {c: l for c, l, _ in CAMPOS_PERMISO}
    # No Pagado (ausencias) y Compensatorio NUNCA hacen perder el bono.
    _BONO_NO_PIERDE = {'ausencias_dias', 'compensatorio_dias'}
    # Tipos de permiso elegibles para reglas extra (excluye los que nunca pierden)
    _CAMPOS_BONO = ['otro_pagado_dias', 'vacaciones_dias', 'enfermedad_dias',
                    'pct25_dias', 'pct50_dias', 'pct75_dias', 'pct100_dias']

    def _hm(hhmm):
        try:
            h, m = hhmm.split(':'); return int(h) * 60 + int(m)
        except Exception:
            return None
    _lim_min = bcfg.hora_limite.hour * 60 + bcfg.hora_limite.minute
    _extra_horas = [(r.hora.hour * 60 + r.hora.minute) for r in reglas_extra if r.tipo == 'hora' and r.hora]
    _extra_permisos = [r.permiso_tipo for r in reglas_extra if r.tipo == 'permiso' and r.permiso_tipo]
    _hora_activa = bcfg.regla_hora_activa or bool(_extra_horas)
    _base_cands = ([_lim_min] if bcfg.regla_hora_activa else []) + _extra_horas
    _base_lim = min(_base_cands) if _base_cands else None

    _lim_vig1 = bcfg.hora_vigilancia.hour * 60 + bcfg.hora_vigilancia.minute      # turno 19:00
    _lim_vig2 = bcfg.hora_vigilancia_2.hour * 60 + bcfg.hora_vigilancia_2.minute  # turno 00:00
    _SPLIT_VIG = 21 * 60  # entradas antes de 21:00 = turno tarde; después = turno noche
    _intentos_tarde = bcfg.intentos_tarde or 0  # entradas tarde toleradas; pierde al siguiente

    # Otro Pagado REAL (excluye Compensatorio): el compensatorio NO hace perder el bono,
    # pero el otro pagado normal sí. (Compensatorio se suma a otro_pagado_dias en el
    # mensual, así que lo recalculamos directo desde PermisoReporte por tipo.)
    _otro_real_map = {}
    for _p in (PermisoReporte.objects
               .filter(tipo='otro_pagado_dias', fecha__gte=mes_inicio, fecha__lte=mes_fin)
               .values('emp_code').annotate(d=_SumMH('dias'))):
        _otro_real_map[str(_p['emp_code'])] = float(_p['d'] or 0)

    bono_rows = []
    for row in rows:
        ec = row['emp_code']
        es_mh = ec in maestro_hora_codes
        es_vig = 'vigilan' in (row['cargo'] or '').lower()
        r = row['r']
        if es_vig:
            # Vigilantes: turno nocturno; se usa la entrada de la noche (>=17:00)
            marcas = vigil_entrada_map.get(ec, [])
            marcas_fmt = [{'fecha': f, 'hora': hh} for f, hh in marcas]
            dias_tarde = []
            if bcfg.regla_vigilancia:
                for f, hh in marcas:
                    m = _hm(hh)
                    if m is None:
                        continue
                    # turno según hora: antes de 21:00 = 19:00 (lím 18:45); si no = 00:00 (lím 23:45)
                    limit_v = _lim_vig1 if m < _SPLIT_VIG else _lim_vig2
                    if m > limit_v:
                        dias_tarde.append({'fecha': f, 'hora': hh})
        else:
            marcas = entrada_por_dia_map.get(ec, [])
            marcas_fmt = [{'fecha': f, 'hora': hh} for f, hh in marcas]
            # Días tardíos: entrada después de la hora límite del día.
            # Maestros por hora: solo se evalúan los días con horario especial definido.
            dias_tarde = []
            if _hora_activa:
                for f, hh in marcas:
                    m = _hm(hh)
                    if m is None:
                        continue
                    wd = f.weekday()
                    if (ec, wd) in _horario_esp:
                        limit_day = _horario_esp[(ec, wd)]
                    elif es_mh:
                        limit_day = None  # maestro por hora sin horario especial ese día
                    else:
                        limit_day = _base_lim
                    # La marca EXACTA a la hora límite (p. ej. 06:58) ya cuenta como
                    # intento tarde. Se toleran `intentos_tarde`; al siguiente, pierde.
                    if limit_day is not None and m >= limit_day:
                        dias_tarde.append({'fecha': f, 'hora': hh})
        # Tipos de permiso que afectan el bono
        tipos = []
        otro = _otro_real_map.get(str(ec), 0.0)  # otro pagado SIN compensatorio
        enf = float(r.enfermedad_dias) if r else 0
        if bcfg.regla_otro_pagado and otro > 0:
            tipos.append('Otro Pagado')
        if bcfg.regla_enfermedad and enf > 0:
            tipos.append('Enfermedad')
        # Reglas extra por tipo de permiso
        for pt in _extra_permisos:
            if pt in _BONO_NO_PIERDE or pt in ('otro_pagado_dias', 'enfermedad_dias'):
                continue  # No Pagado y Compensatorio nunca pierden; otros dos ya contados
            val = float(getattr(r, pt, 0) or 0) if r else 0
            if val > 0:
                tipos.append(CAMPOS_PERMISO_MAP.get(pt, pt))
        # dias_tarde solo se llena cuando la regla aplicable está activa.
        # Se toleran `intentos_tarde` entradas tardías; pierde a partir de la siguiente.
        pierde_auto = bool(tipos) or (len(dias_tarde) > _intentos_tarde)
        override = (r.bono_override if r else '') or ''
        if override == 'si':
            pierde = True
        elif override == 'no':
            pierde = False
        else:
            pierde = pierde_auto
        bono_rows.append({
            'emp_code': row['emp_code'], 'nombre': row['nombre'], 'nombre_sort': row['nombre_sort'],
            'cargo': row['cargo'], 'marcas': marcas_fmt, 'n_marcas': len(marcas_fmt),
            'dias_tarde': dias_tarde, 'n_tarde': len(dias_tarde), 'tipos': tipos,
            'pierde': pierde, 'pierde_auto': pierde_auto, 'override': override,
        })

    # Catálogo de tipos de permiso para el modal "agregar regla"
    bono_tipos_permiso = [(c, CAMPOS_PERMISO_MAP[c]) for c in _CAMPOS_BONO]
    reglas_extra_ctx = [{
        'id': r.pk, 'tipo': r.tipo,
        'detalle': (dict(CAMPOS_PERMISO_MAP).get(r.permiso_tipo, r.permiso_tipo) if r.tipo == 'permiso'
                    else (r.hora.strftime('%H:%M') if r.hora else '')),
        'activa': r.activa,
    } for r in BonoReglaExtra.objects.all()]

    cfg = RelojConfigGlobal.get()
    ctx = {
        'rows':            rows,
        'rows_general':    rows_general,
        'rows_general_80': rows_general_80,
        'rows_general_88': rows_general_88,
        'rows_maestro':    rows_maestro,
        'rows_vigilante':  rows_vigilante,
        'receso':          receso,
        'mes':             mes_inicio,
        'mes_str':         mes_str,
        'campos_permiso':  CAMPOS_PERMISO,
        'error_sql':       error_sql,
        'can_delete':      _reloj_can(request.user, 'reporte', 'eliminar'),
        'dias_semana':     _DIAS_SEMANA,
        'dias_full':       [(c, l, i) for i, (c, l) in enumerate(_DIAS_SEMANA)],
        'horas_diarias_visible': cfg.horas_diarias_visible,
        'tarde_reglas':    _tarde_reglas,
        'maestro_hora_codes':    maestro_hora_codes,
        'bono_rows':       bono_rows,
        'bono_cfg':        bcfg,
        'bono_reglas_extra': reglas_extra_ctx,
        'bono_tipos_permiso': bono_tipos_permiso,
        'bono_horarios_esp': list(BonoHorarioEmpleado.objects.filter(activa=True)),
    }
    if _es_pdf(request):
        _sec = request.GET.get('sec')
        # sec=receso → PDF del tiempo de receso mensual
        if _sec == 'receso':
            ctx['sec'] = 'receso'
            ctx['receso_mes'] = mes_inicio
            return _reporte_pdf(request, 'reloj/pdf/calculo_pdf.html', ctx,
                                f'receso_mensual_{mes_str}.pdf')
        # sec=bono → lista de empleados que conservan el bono (solo nombres)
        if _sec == 'bono':
            ctx['bono_conservan'] = [b for b in bono_rows if not b['pierde']]
            return _reporte_pdf(request, 'reloj/pdf/bono_pdf.html', ctx,
                                f'bono_asistencia_{mes_str}.pdf')
        # Reporte único agrupado: General (alfabético) → Maestros por hora → Vigilancia
        ctx['rows'] = rows_general + rows_maestro + rows_vigilante
        return _reporte_pdf(request, 'reloj/pdf/permiso_reporte_pdf.html', ctx,
                            f'permiso_mensual_{mes_str}.pdf')
    return render(request, 'reloj/permiso_reporte.html', ctx)


# ── Bono por Asistencia: reglas + override ──  <--- hecho por claude code
@login_required
@require_POST
def bono_reglas_save(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    from .models import BonoConfig
    body = json.loads(request.body or b'{}')
    cfg = BonoConfig.get()
    hora = (body.get('hora_limite') or '').strip()
    if hora:
        try:
            hh, mm = hora.split(':')
            cfg.hora_limite = time(int(hh), int(mm))
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'Hora inválida'}, status=400)
    cfg.regla_otro_pagado = bool(body.get('regla_otro_pagado'))
    cfg.regla_enfermedad = bool(body.get('regla_enfermedad'))
    cfg.regla_hora_activa = bool(body.get('regla_hora_activa'))
    cfg.regla_vigilancia = bool(body.get('regla_vigilancia'))
    for campo, attr in (('hora_vigilancia', 'hora_vigilancia'), ('hora_vigilancia_2', 'hora_vigilancia_2')):
        hv = (body.get(campo) or '').strip()
        if hv:
            try:
                hh, mm = hv.split(':')
                setattr(cfg, attr, time(int(hh), int(mm)))
            except ValueError:
                return JsonResponse({'ok': False, 'error': 'Hora vigilancia inválida'}, status=400)
    cfg.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def bono_regla_extra_add(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    from .models import BonoReglaExtra, ReportePermisoMensual  # noqa
    body = json.loads(request.body or b'{}')
    tipo = body.get('tipo')
    if tipo == 'permiso':
        pt = (body.get('permiso_tipo') or '').strip()
        if not pt:
            return JsonResponse({'ok': False, 'error': 'Falta el tipo de permiso'}, status=400)
        label = dict((c, l) for c, l, _ in CAMPOS_PERMISO).get(pt, pt)
        BonoReglaExtra.objects.create(tipo='permiso', permiso_tipo=pt,
                                      descripcion=f"Permiso: {label}")
    elif tipo == 'hora':
        hora = (body.get('hora') or '').strip()
        try:
            hh, mm = hora.split(':')
            t = time(int(hh), int(mm))
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'Hora inválida'}, status=400)
        BonoReglaExtra.objects.create(tipo='hora', hora=t,
                                      descripcion=f"Entrada máx {hora}")
    else:
        return JsonResponse({'ok': False, 'error': 'Tipo inválido'}, status=400)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def bono_regla_extra_delete(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    from .models import BonoReglaExtra
    BonoReglaExtra.objects.filter(pk=pk).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def bono_override_set(request):
    """Override manual del superusuario sobre el bono de un empleado/mes."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    from .models import ReportePermisoMensual
    body = json.loads(request.body or b'{}')
    emp = (body.get('emp_code') or '').strip()
    nombre = (body.get('nombre') or '').strip()
    mes_str = (body.get('mes') or '').strip()
    valor = (body.get('valor') or '').strip()
    if valor not in ('', 'si', 'no'):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'}, status=400)
    try:
        y, m = map(int, mes_str.split('-')[:2]); mes = date(y, m, 1)
    except (ValueError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'Mes inválido'}, status=400)
    obj, _ = ReportePermisoMensual.objects.get_or_create(
        emp_code=emp, mes=mes, defaults={'nombre_empleado': nombre})
    obj.bono_override = valor
    obj.save(update_fields=['bono_override'])
    return JsonResponse({'ok': True})


# ── Maestros por hora: tabla de horas (sin fecha) por mes ─────────────────────
def _mh_parse_mes(s):
    from datetime import date as _d
    y, m = map(int, (s or '').split('-'))
    return _d(y, m, 1)


def _mh_payload(emp_code, mes):
    qs = MaestroHoraEntrada.objects.filter(emp_code=emp_code, mes=mes).order_by('pk')
    entries = [{'pk': e.pk, 'horas': round(float(e.horas), 2), 'comentario': e.comentario or ''} for e in qs]
    total = round(sum(e['horas'] for e in entries), 2)
    return entries, total


@login_required
@require_POST
def receso_ajuste_set(request):
    """Ajuste manual del receso de un día (excepciones). Solo superuser."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo el superusuario puede ajustar el receso'}, status=403)
    from .models import RecesoAjuste
    body = json.loads(request.body or b'{}')
    emp_code = (body.get('emp_code') or '').strip()
    fecha_str = (body.get('fecha') or '').strip()
    m2 = (body.get('m2') or '').strip()[:5]
    m3 = (body.get('m3') or '').strip()[:5]
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)
    if not emp_code:
        return JsonResponse({'ok': False, 'error': 'Falta empleado'}, status=400)
    if not m2 or not m3:
        # Restaurar automático
        RecesoAjuste.objects.filter(emp_code=emp_code, fecha=fecha).delete()
        return JsonResponse({'ok': True, 'manual': False})
    import re as _re
    if not (_re.match(r'^\d{1,2}:\d{2}$', m2) and _re.match(r'^\d{1,2}:\d{2}$', m3)):
        return JsonResponse({'ok': False, 'error': 'Formato de hora inválido (HH:MM)'}, status=400)
    RecesoAjuste.objects.update_or_create(
        emp_code=emp_code, fecha=fecha, defaults={'m2': m2, 'm3': m3})
    return JsonResponse({'ok': True, 'manual': True})


# ── Horas por día de la semana (maestros por hora) ───────────────────────────
def _mh_dia_payload(emp_code):
    horas = {d.weekday: round(float(d.horas), 2)
             for d in MaestroHoraDia.objects.filter(emp_code=emp_code)}
    dias = {str(w): horas.get(w, 0) for w in range(7)}
    total = round(sum(horas.values()), 2)  # suma simple de las horas configuradas
    return dias, total


def _mh_total(emp_code):
    """Suma simple de las horas por día configuradas de un maestro por hora."""
    from django.db.models import Sum as _S
    return round(float(MaestroHoraDia.objects.filter(emp_code=emp_code)
                       .aggregate(t=_S('horas'))['t'] or 0), 2)


def _mh_horas_para_fecha(emp_code, fecha):
    """Horas que el maestro trabaja en el día de la semana de `fecha` (0 si no)."""
    d = MaestroHoraDia.objects.filter(emp_code=emp_code, weekday=fecha.weekday()).first()
    return round(float(d.horas), 2) if d else 0.0


def _es_maestro_hora(emp_code):
    """True si el emp_code es maestro por hora (plantilla, excluye Gilma/9)."""
    if str(emp_code) == '9':
        return False
    from reloj.models import EmployeeScheduleAssignment as _ESA
    return _ESA.objects.filter(
        emp_code=emp_code, activo=True,
        template__nombre__icontains='maestro por hora').exists()


@login_required
def maestro_dia_get(request):
    if not _reloj_can(request.user, 'reporte', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    emp_code = (request.GET.get('emp_code') or '').strip()
    dias, total = _mh_dia_payload(emp_code)
    return JsonResponse({'ok': True, 'dias': dias, 'total': total})


@login_required
@require_POST
def maestro_dia_set(request):
    if not _reloj_can(request.user, 'reporte', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    body = json.loads(request.body or b'{}')
    emp_code = (body.get('emp_code') or '').strip()
    horas_map = body.get('horas') or {}
    if not emp_code:
        return JsonResponse({'ok': False, 'error': 'Falta empleado'}, status=400)
    for w in range(7):
        raw = horas_map.get(str(w), horas_map.get(w))
        try:
            h = round(float(raw), 2) if raw not in (None, '') else 0
        except (ValueError, TypeError):
            h = 0
        if h > 0:
            MaestroHoraDia.objects.update_or_create(
                emp_code=emp_code, weekday=w, defaults={'horas': h})
        else:
            MaestroHoraDia.objects.filter(emp_code=emp_code, weekday=w).delete()
    dias, total = _mh_dia_payload(emp_code)
    # Total del mes (suma de días laborables que caen en el mes indicado)
    total_mes = None
    try:
        mes = _mh_parse_mes(body.get('mes'))
        import calendar as _cal
        from datetime import timedelta as _td
        ud = _cal.monthrange(mes.year, mes.month)[1]
        wd_h = {int(k): float(v) for k, v in dias.items()}
        tot, dd = 0.0, mes
        while dd.day <= ud and dd.month == mes.month:
            tot += wd_h.get(dd.weekday(), 0)
            dd += _td(days=1)
        total_mes = round(tot, 2)
    except Exception:
        pass
    return JsonResponse({'ok': True, 'dias': dias, 'total': total, 'total_mes': total_mes})


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
        # Cierre de mes: no se permiten permisos pasado el último día hábil 16:35
        if _permiso_mes_cerrado(fecha, request.user):
            return JsonResponse({'ok': False, 'error': 'Los permisos de este mes ya están cerrados (último día hábil a las 4:35 PM).'})
        horas = float(horas_str) if horas_str else None
        if dias_str:
            dias = float(dias_str)
        elif horas is not None:
            # Usar horas_diarias_laboradas del empleado para ese mes
            _mes_1 = fecha.replace(day=1)
            _cfg_emp = ReportePermisoMensual.objects.filter(
                emp_code=emp_code, mes=_mes_1
            ).values_list('horas_diarias_laboradas', flat=True).first()
            _divisor = float(_cfg_emp or 8.0)
            dias = round(horas / _divisor, 4)
        else:
            dias = 1.0
        # Maestros por hora:
        #  • Si el usuario escribió horas → permiso PARCIAL: respeta esas horas y
        #    calcula los días como fracción del día de ese maestro (horas/horas_del_día).
        #  • Si NO escribió horas → toma automáticamente el/los día(s) completo(s)
        #    según el horario configurado del rango fecha→fecha_fin.
        if _es_maestro_hora(emp_code):
            from datetime import timedelta as _td
            if horas is not None and horas > 0:
                hd_dia = _mh_horas_para_fecha(emp_code, fecha)
                dias = round(horas / hd_dia, 4) if hd_dia > 0 else 0.0
            else:
                total_h, ndias = 0.0, 0
                _d2 = fecha
                while _d2 <= fecha_fin:
                    hd = _mh_horas_para_fecha(emp_code, _d2)
                    if hd > 0:
                        total_h += hd
                        ndias += 1
                    _d2 += _td(days=1)
                if total_h > 0:
                    horas = round(total_h, 2)
                    dias = ndias
        if dias < 0:
            return JsonResponse({'ok': False, 'error': 'Días debe ser >= 0'})
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'})

    # Catálogo de razones: agrega la razón si es nueva
    if razon:
        RazonPermiso.objects.get_or_create(texto=razon[:200], defaults={'activo': True})

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
    if not _reloj_can(u, 'reporte', 'eliminar'):
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



# ─────────────────────────────────────────────────────────────
# VACACIONES
# ─────────────────────────────────────────────────────────────

def _years_of_service(fecha_inicio, hoy):
    years = hoy.year - fecha_inicio.year
    if (hoy.month, hoy.day) < (fecha_inicio.month, fecha_inicio.day):
        years -= 1
    return max(0, years)


def _dias_vacacion(es_docente, fecha_inicio, hoy, dias_fijos=None):
    # Caso especial: días fijos configurados manualmente (ignora todo lo demás)
    if dias_fijos is not None:
        return dias_fijos
    if not fecha_inicio:
        return 0
    years = _years_of_service(fecha_inicio, hoy)
    if years < 1:
        return 0
    if es_docente:
        return 60
    if years == 1:
        return 10
    if years == 2:
        return 12
    if years == 3:
        return 15
    return 20


def _dias_disponibles_calc(es_docente, dias_corresponden, dias_usados, hoy, es_caso_especial=False):
    """Días disponibles reales para docentes:
    - Los 5 días del año escolar (Feb-Nov) siempre se descuentan del total, aunque no se usen.
    - Feb-Nov: disponibles = max(0, 5 - usados)  [solo pueden tomar hasta 5 en este período]
    - Dic-Ene: disponibles = max(0, corresponden - max(5, usados))  [60 - al menos 5]
    - Caso especial (dias_fijos) y no docentes: corresponden - usados normalmente.
    """
    usados = float(dias_usados)
    corresponden = float(dias_corresponden)
    # Sin tope en 0: si se sobrepasa, se muestra el saldo en negativo.
    if es_docente and not es_caso_especial:
        if hoy.month not in (12, 1):
            return round(5.0 - usados, 2)
        else:
            return round(corresponden - max(5.0, usados), 2)
    return round(corresponden - usados, 2)


@login_required
@_reloj_ver_required('vacaciones')
def vacaciones_list(request):
    from django.db.models import Sum as _Sum
    hoy   = date.today()
    año   = hoy.year
    fi    = date(año, 2, 1)
    ff    = date(año, 11, 30)

    try:
        with connections['zkbio_sqlserver'].cursor() as cursor:
            cursor.execute("""
                SELECT CAST(emp_code AS VARCHAR(20)), first_name, last_name
                FROM dbo.personnel_employee
                ORDER BY last_name, first_name
            """)
            empleados_rows = cursor.fetchall()
    except Exception:
        empleados_rows = []

    configs = {str(c.emp_code): c for c in VacacionConfig.objects.all()}

    permisos_map = {
        str(p['emp_code']): float(p['dias_usados'] or 0)
        for p in PermisoReporte.objects.filter(
            tipo='vacaciones_dias',
            fecha__gte=fi,
            fecha__lte=ff,
        ).values('emp_code').annotate(dias_usados=_Sum('dias'))
    }

    filas = []
    for ec, fn, ln in empleados_rows:
        ec     = str(ec).strip()
        if ec == '9':   # Gilma Lorenzo (Administración) — fuera de vacaciones
            continue
        nombre = f"{fn} {ln}".strip()
        cfg    = configs.get(ec)
        años   = None
        dias_corresponden = 0
        if cfg and cfg.fecha_inicio_labores:
            años = _years_of_service(cfg.fecha_inicio_labores, hoy)
            dias_corresponden = _dias_vacacion(
                cfg.es_docente, cfg.fecha_inicio_labores, hoy,
                dias_fijos=cfg.dias_fijos,
            )
        # PermisoReporte sum + ajuste manual (aditivo para que permiso_reporte sincronice)
        dias_usados = permisos_map.get(ec, 0) + float(cfg.dias_usados_manual or 0 if cfg else 0)
        es_caso_especial = bool(cfg and cfg.dias_fijos is not None)
        dias_disponibles = _dias_disponibles_calc(
            bool(cfg and cfg.es_docente), dias_corresponden, dias_usados, hoy, es_caso_especial,
        )
        # Clasificación para tabs: caso_especial (días fijos) · docente (BL/Colegio) · no_docente
        if es_caso_especial:
            grupo = 'caso_especial'
        elif cfg and cfg.es_docente:
            grupo = 'docente_bl' if cfg.grupo_docente == 'bl' else 'docente_colegio'
        else:
            grupo = 'no_docente'   # incluye no docentes y sin configurar
        filas.append({
            'emp_code':         ec,
            'nombre':           nombre,
            'cfg':              cfg,
            'años':             años,
            'dias_corresponden':dias_corresponden,
            'dias_usados':      dias_usados,
            'dias_disponibles': dias_disponibles,
            'grupo':            grupo,
        })

    filas_no_docente     = [f for f in filas if f['grupo'] == 'no_docente']
    filas_caso_especial  = [f for f in filas if f['grupo'] == 'caso_especial']
    filas_docente_bl     = [f for f in filas if f['grupo'] == 'docente_bl']
    filas_docente_colegio= [f for f in filas if f['grupo'] == 'docente_colegio']

    ctx = {
        'filas':              filas,
        'filas_no_docente':   filas_no_docente,
        'filas_caso_especial':filas_caso_especial,
        'filas_docente_bl':   filas_docente_bl,
        'filas_docente_colegio': filas_docente_colegio,
        'periodo_inicio': fi,
        'periodo_fin':    ff,
        'hoy':            hoy,
        'can_edit':       _reloj_can(request.user, 'vacaciones', 'editar'),
    }
    if _es_pdf(request):
        return _reporte_pdf(request, 'reloj/pdf/vacaciones_pdf.html', ctx, 'vacaciones.pdf')
    return render(request, 'reloj/vacaciones_list.html', ctx)


@login_required
@require_POST
def vacacion_config_save(request):
    if not _reloj_can(request.user, 'vacaciones', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    try:
        body = json.loads(request.body or b'{}')
    except Exception:
        body = {}

    emp_code   = body.get('emp_code', '').strip()
    nombre     = body.get('nombre', '').strip()
    es_docente = bool(body.get('es_docente', False))
    fecha_str  = body.get('fecha_inicio', '').strip()
    dias_fijos_raw = body.get('dias_fijos', None)
    grupo_docente  = (body.get('grupo_docente') or '').strip()
    if grupo_docente not in ('bl', 'colegio'):
        grupo_docente = ''
    if not es_docente:
        grupo_docente = ''   # BL/Colegio solo aplica a docentes

    if not emp_code:
        return JsonResponse({'ok': False, 'error': 'emp_code requerido'})

    fecha_inicio = None
    if fecha_str:
        try:
            fecha_inicio = date.fromisoformat(fecha_str)
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'Fecha inválida'})

    dias_fijos = None
    if dias_fijos_raw not in (None, '', 0, '0'):
        try:
            dias_fijos = int(dias_fijos_raw)
            if dias_fijos <= 0:
                dias_fijos = None
        except (TypeError, ValueError):
            dias_fijos = None

    VacacionConfig.objects.update_or_create(
        emp_code=emp_code,
        defaults={
            'nombre_empleado':      nombre,
            'es_docente':           es_docente,
            'grupo_docente':        grupo_docente,
            'fecha_inicio_labores': fecha_inicio,
            'dias_fijos':           dias_fijos,
            'registrado_por':       request.user,
        }
    )

    hoy              = date.today()
    años             = _years_of_service(fecha_inicio, hoy) if fecha_inicio else None
    dias_corresponden= _dias_vacacion(es_docente, fecha_inicio, hoy, dias_fijos=dias_fijos)

    return JsonResponse({
        'ok':               True,
        'años':             años,
        'dias_corresponden': dias_corresponden,
        'dias_fijos':       dias_fijos,
        'es_docente':       es_docente,
        'grupo_docente':    grupo_docente,
        'fecha_inicio':     fecha_str,
    })


@login_required
def vacacion_balance(request):
    """AJAX GET: devuelve balance de vacaciones de un empleado para el período activo."""
    from django.db.models import Sum as _Sum
    emp_code = (request.GET.get('emp_code') or '').strip()
    if not emp_code:
        return JsonResponse({'ok': False, 'error': 'emp_code requerido'})

    hoy = date.today()
    año = hoy.year
    fi  = date(año, 2, 1)
    ff  = date(año, 11, 30)

    try:
        cfg = VacacionConfig.objects.get(emp_code=emp_code)
        tiene_config      = True
        dias_corresponden = _dias_vacacion(cfg.es_docente, cfg.fecha_inicio_labores, hoy)
    except VacacionConfig.DoesNotExist:
        tiene_config      = False
        dias_corresponden = 0

    usados_raw = PermisoReporte.objects.filter(
        tipo='vacaciones_dias', emp_code=emp_code,
        fecha__gte=fi, fecha__lte=ff,
    ).aggregate(t=_Sum('dias'))['t'] or 0
    # Aditivo: suma PermisoReporte + ajuste manual del lápiz
    ajuste_manual    = float(cfg.dias_usados_manual or 0) if tiene_config and cfg.dias_usados_manual else 0
    dias_usados      = float(usados_raw) + ajuste_manual
    es_docente_bal   = tiene_config and cfg.es_docente
    es_caso_esp_bal  = tiene_config and cfg.dias_fijos is not None
    dias_disponibles = _dias_disponibles_calc(es_docente_bal, dias_corresponden, dias_usados, hoy, es_caso_esp_bal)

    return JsonResponse({
        'ok':               True,
        'tiene_config':     tiene_config,
        'dias_corresponden': dias_corresponden,
        'dias_usados':      dias_usados,
        'dias_disponibles': dias_disponibles,
        'periodo':          f"{fi.strftime('%d/%m/%Y')} — {ff.strftime('%d/%m/%Y')}",
    })


# ─────────────────────────────────────────────────────────────
# Importar fechas de inicio (solo staff)
# ─────────────────────────────────────────────────────────────
_MESES_ES = {
    'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,
    'jul':7,'ago':8,'sep':9,'oct':10,'nov':11,'dic':12,
}

def _parse_fecha_es(s):
    """Convierte '01-feb-18' → date(2018, 2, 1)."""
    try:
        partes = s.strip().lower().split('-')
        dia  = int(partes[0])
        mes  = _MESES_ES[partes[1]]
        año  = int(partes[2])
        if año < 100:
            año += 2000
        return date(año, mes, dia)
    except Exception:
        return None

def _norm(s):
    """Normaliza texto: minúsculas, sin tildes."""
    import unicodedata
    s = s.lower().strip()
    s = unicodedata.normalize('NFD', s)
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


@login_required
@require_POST
def vacacion_editar_dias_usados(request):
    if not _reloj_can(request.user, 'vacaciones', 'editar'):
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    try:
        body = json.loads(request.body or b'{}')
    except Exception:
        body = {}
    emp_code  = body.get('emp_code', '').strip()
    dias_str  = body.get('dias_usados', '')
    nombre    = body.get('nombre', '').strip()
    if not emp_code:
        return JsonResponse({'ok': False, 'error': 'emp_code requerido'})
    try:
        dias = round(float(dias_str), 2)
        if dias < 0:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})
    cfg, _ = VacacionConfig.objects.get_or_create(
        emp_code=emp_code,
        defaults={'nombre_empleado': nombre, 'registrado_por': request.user},
    )
    cfg.dias_usados_manual = dias
    cfg.save(update_fields=['dias_usados_manual'])
    hoy = date.today()
    año = hoy.year
    fi  = date(año, 2, 1)
    ff  = date(año, 11, 30)
    from django.db.models import Sum as _Sum
    permisos_sum = float(
        PermisoReporte.objects.filter(
            tipo='vacaciones_dias', emp_code=emp_code,
            fecha__gte=fi, fecha__lte=ff,
        ).aggregate(t=_Sum('dias'))['t'] or 0
    )
    dias_corresponden = _dias_vacacion(cfg.es_docente, cfg.fecha_inicio_labores, hoy, dias_fijos=cfg.dias_fijos)
    total_usados     = round(permisos_sum + dias, 2)
    dias_disponibles = _dias_disponibles_calc(
        cfg.es_docente, dias_corresponden, total_usados, hoy, es_caso_especial=cfg.dias_fijos is not None,
    )
    return JsonResponse({
        'ok': True,
        'dias_usados':       total_usados,
        'dias_disponibles':  dias_disponibles,
        'dias_corresponden': dias_corresponden,
    })


@login_required
def vacaciones_importar(request):
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()

    resultados = None

    if request.method == 'POST':
        texto = request.POST.get('datos', '').strip()
        lineas = [l.strip() for l in texto.splitlines() if l.strip()]

        # Cargar todos los empleados de ZKBio
        try:
            with connections['zkbio_sqlserver'].cursor() as cursor:
                cursor.execute("""
                    SELECT CAST(emp_code AS VARCHAR(20)), first_name, last_name
                    FROM dbo.personnel_employee
                """)
                zkbio_rows = cursor.fetchall()
        except Exception as e:
            return render(request, 'reloj/vacaciones_importar.html', {
                'error_sql': str(e), 'resultados': None
            })

        # Mapa: (norm_last, norm_first_parcial) → (emp_code, nombre_completo)
        zkbio_map = {}
        for ec, fn, ln in zkbio_rows:
            ec = str(ec).strip()
            norm_ln = _norm(ln or '')
            norm_fn = _norm(fn or '')
            # índice por primer token del last_name + primer token del first_name
            clave1 = (norm_ln, norm_fn)                               # exacto
            clave2 = (norm_ln, norm_fn.split()[0] if norm_fn else '')  # solo primer nombre
            for k in (clave1, clave2):
                if k not in zkbio_map:
                    zkbio_map[k] = (ec, f"{fn} {ln}".strip())

        resultados = []
        importados = 0

        for linea in lineas:
            tokens = linea.split()
            if len(tokens) < 3:
                resultados.append({'linea': linea, 'estado': 'error', 'msg': 'Formato inválido'})
                continue

            # Último token = fecha
            fecha_str = tokens[-1]
            fecha = _parse_fecha_es(fecha_str)
            if not fecha:
                resultados.append({'linea': linea, 'estado': 'error', 'msg': f'Fecha inválida: {fecha_str}'})
                continue

            # tokens[0]=ap1, tokens[1]=ap2, tokens[2:-1]=nombres
            ap1    = _norm(tokens[0])
            ap2    = _norm(tokens[1]) if len(tokens) > 2 else ''
            nombres= tokens[2:-1]
            n1     = _norm(nombres[0]) if nombres else ''
            n2     = _norm(nombres[1]) if len(nombres) > 1 else ''

            apellidos_norm = f"{ap1} {ap2}".strip()
            nombres_norm   = f"{n1} {n2}".strip()

            match = (
                zkbio_map.get((apellidos_norm, nombres_norm)) or
                zkbio_map.get((apellidos_norm, n1)) or
                zkbio_map.get((ap1, nombres_norm)) or
                zkbio_map.get((ap1, n1))
            )

            if not match:
                resultados.append({'linea': linea, 'estado': 'no_match',
                                   'msg': 'No se encontró en ZKBio'})
                continue

            emp_code, nombre_completo = match
            VacacionConfig.objects.update_or_create(
                emp_code=emp_code,
                defaults={
                    'nombre_empleado':      nombre_completo,
                    'fecha_inicio_labores': fecha,
                    'registrado_por':       request.user,
                }
            )
            importados += 1
            resultados.append({
                'linea':  linea,
                'estado': 'ok',
                'msg':    f'{nombre_completo} → {fecha.strftime("%d/%m/%Y")}',
            })

        return render(request, 'reloj/vacaciones_importar.html', {
            'resultados': resultados,
            'importados': importados,
            'total':      len(lineas),
        })

    return render(request, 'reloj/vacaciones_importar.html', {'resultados': None})


# ──────────────────────────────────────────────────────────────────────────────
# VIGILANCIA  (modo construcción)
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def vigilancia_list(request):
    rp = getattr(request.user, 'reloj_permiso', None)
    if not (request.user.is_superuser or request.user.is_staff or (rp and rp.vigilancia_ver)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    from datetime import date as _date, timedelta as _td
    HORAS_DIA_MIN = 5 * 60 + 12  # 5h 12min fijos por día trabajado
    _DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

    # Rango de fechas (Desde / Hasta). Por defecto, la semana actual (lunes–domingo).
    hoy = _date.today()
    _lun_def = hoy - _td(days=hoy.weekday())
    _dom_def = _lun_def + _td(days=6)
    fi = _safe_date(request.GET.get('fecha_inicio', _lun_def.isoformat()), _lun_def.isoformat())
    ff = _safe_date(request.GET.get('fecha_fin', _dom_def.isoformat()), _dom_def.isoformat())
    fi_d = _date.fromisoformat(fi)
    ff_d = _date.fromisoformat(ff)
    if ff_d < fi_d:
        ff_d = fi_d
    # Tope de seguridad: máximo 92 días
    if (ff_d - fi_d).days > 92:
        ff_d = fi_d + _td(days=92)
    n_dias = (ff_d - fi_d).days + 1
    lunes, domingo = fi_d, ff_d  # nombres reutilizados abajo en el SQL

    def _ampm(hhmm):
        try:
            h, m = map(int, hhmm.split(':'))
        except Exception:
            return hhmm
        suf = 'AM' if h < 12 else 'PM'
        return f"{h % 12 or 12}:{m:02d} {suf}"

    # ── Grupos de vigilancia ──
    NOCTURNA_CODES = ['57', '58']      # Gustavo Romero, Pastor Ortiz → jornada fija 5h 12m/día
    DIURNA_CODES   = ['8']             # Santos Bentacourth → según marcas, dentro de sus ventanas
    # Ventanas de Santos (minutos desde medianoche): 6:30–7:00 y 12:00–1:00
    SANTOS_WINDOWS = [(6 * 60 + 30, 7 * 60), (12 * 60, 13 * 60)]
    TODOS_CODES    = NOCTURNA_CODES + DIURNA_CODES
    codes_sql      = ', '.join(f"'{c}'" for c in TODOS_CODES)

    def _fmt_hm(m):
        return f"{m // 60}h {m % 60:02d}m"

    def _fmt_h(m):
        # Horas decimales (todo se trabaja en horas): minutos ÷ 60
        return f"{m / 60:.2f} h"

    def _min_marcas(marcas_hhmm):
        vals = []
        for h in marcas_hhmm:
            try:
                hh, mm = map(int, h.split(':'))
                vals.append(hh * 60 + mm)
            except Exception:
                pass
        return vals

    def _horas_ventanas(marcas_hhmm, ventanas):
        """Minutos reales dentro de las ventanas = solape de [1ª marca, última] con cada ventana."""
        vals = _min_marcas(marcas_hhmm)
        if len(vals) < 2:
            return 0
        lo, hi = min(vals), max(vals)
        return sum(max(0, min(hi, we) - max(lo, ws)) for ws, we in ventanas)

    emp_nombre, marcas_map, error_sql = {}, {}, None
    try:
        with connections['zkbio_sqlserver'].cursor() as cur:
            cur.execute(f"""
                SELECT CAST(e.emp_code AS VARCHAR(20)), (e.first_name + ' ' + e.last_name)
                FROM dbo.personnel_employee e
                WHERE CAST(e.emp_code AS VARCHAR(20)) IN ({codes_sql})
            """)
            for ec, nom in cur.fetchall():
                emp_nombre[str(ec).strip()] = (nom or '').strip()
            cur.execute(f"""
                SELECT CAST(t.emp_code AS VARCHAR(20)) AS emp_code,
                       CONVERT(DATE, t.punch_time)     AS fecha,
                       CONVERT(VARCHAR(5), CAST(t.punch_time AS TIME), 108) AS hora
                FROM dbo.iclock_transaction t
                WHERE CAST(t.emp_code AS VARCHAR(20)) IN ({codes_sql})
                  AND CONVERT(DATE, t.punch_time) BETWEEN '{lunes.isoformat()}' AND '{domingo.isoformat()}'
                ORDER BY t.punch_time
            """)
            for ec, fecha, hora in cur.fetchall():
                marcas_map.setdefault(str(ec).strip(), {}).setdefault(fecha, []).append(hora)
    except Exception as e:
        error_sql = str(e)

    def _guardia(ec, modo):
        dias_marcas = marcas_map.get(ec, {})
        dias, total_min = [], 0
        for i in range(n_dias):
            d = fi_d + _td(days=i)
            horas = dias_marcas.get(d, [])
            if modo == 'nocturna':
                hm = HORAS_DIA_MIN if horas else 0
            else:  # diurna: según marcas dentro de ventanas
                hm = _horas_ventanas(horas, SANTOS_WINDOWS)
            total_min += hm
            dias.append({
                'dia': _DIAS[d.weekday()], 'fecha': d,
                'marcas': [_ampm(h) for h in horas],
                'trabajado': bool(horas),
                'horas_str': _fmt_h(hm) if hm else '—',
            })
        dias_trab = sum(1 for x in dias if x['trabajado'])
        return {
            'emp_code': ec, 'nombre': emp_nombre.get(ec, ec), 'dias': dias,
            'dias_trab': dias_trab, 'total_str': _fmt_h(total_min), 'total_min': total_min,
        }

    grupos = [
        {'key': 'diurna', 'label': 'Vigilancia Diurna',
         'jornada': 'Según marcas · ventanas 6:30–7:00 y 12:00–1:00 (máx 1h 30m/día)',
         'guardias': [_guardia(c, 'diurna') for c in DIURNA_CODES if c in emp_nombre]},
        {'key': 'nocturna', 'label': 'Vigilancia Nocturna',
         'jornada': f'Jornada fija: {_fmt_h(HORAS_DIA_MIN)} por día',
         'guardias': [_guardia(c, 'nocturna') for c in NOCTURNA_CODES if c in emp_nombre]},
    ]

    return render(request, 'reloj/vigilancia_list.html', {
        'grupos': grupos,
        'fecha_inicio': fi_d.isoformat(),
        'fecha_fin': ff_d.isoformat(),
        'error_sql': error_sql,
    })


# ──────────────────────────────────────────────────────────────────────────────
# INSTRUCTORES CFP  (modo construcción)
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def cfp_list(request):
    rp = getattr(request.user, 'reloj_permiso', None)
    if not (request.user.is_superuser or request.user.is_staff or (rp and rp.cfp_ver)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, 'reloj/cfp_list.html', {})


# ──────────────────────────────────────────────────────────────────────────────
# AJAX: guardar Horas Diarias Laboradas en ReportePermisoMensual
# ──────────────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def permiso_reporte_set_horas_diarias(request):
    from datetime import date as _date
    emp_code  = (request.POST.get('emp_code') or '').strip()
    mes_str   = (request.POST.get('mes') or '').strip()
    valor_str = (request.POST.get('valor') or '8.0').strip().replace(',', '.')

    try:
        valor = float(valor_str)
        if valor <= 0:
            return JsonResponse({'ok': False, 'error': 'Valor debe ser > 0'})
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Valor inválido'})

    try:
        year, month = map(int, mes_str.split('-'))
        mes = _date(year, month, 1)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Mes inválido'})

    dias_str   = (request.POST.get('dias') or 'L,M,X,J,V').strip()
    comentario = (request.POST.get('comentario') or '').strip()[:200]

    obj, _ = ReportePermisoMensual.objects.get_or_create(
        emp_code=emp_code, mes=mes,
        defaults={'nombre_empleado': emp_code},
    )
    from decimal import Decimal
    obj.horas_diarias_laboradas = Decimal(str(round(valor, 1)))
    obj.dias_laborables  = dias_str
    obj.horario_comentario = comentario
    obj.save(update_fields=['horas_diarias_laboradas', 'dias_laborables', 'horario_comentario', 'actualizado_en'])
    return JsonResponse({'ok': True, 'valor': float(obj.horas_diarias_laboradas), 'dias': dias_str})


# ──────────────────────────────────────────────────────────────────────────────
# AJAX: superuser toggle visibilidad columna Factor H/Día
# ──────────────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def toggle_factor_visible(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    cfg = RelojConfigGlobal.get()
    cfg.factor_horas_visible = not cfg.factor_horas_visible
    cfg.save()
    return JsonResponse({'ok': True, 'visible': cfg.factor_horas_visible})

# ──────────────────────────────────────────────────────────────────────────────
# AJAX: superuser toggle visibilidad columna Horas Diarias Lab.
# ──────────────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def toggle_horas_diarias_visible(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    cfg = RelojConfigGlobal.get()
    cfg.horas_diarias_visible = not cfg.horas_diarias_visible
    cfg.save()
    return JsonResponse({'ok': True, 'visible': cfg.horas_diarias_visible})


@login_required
@require_POST
def set_tarde_reglas(request):
    """Guarda las reglas configurables de rebaja por tardanza (solo superuser)."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Solo superusuario'}, status=403)
    import json as _json
    try:
        reglas = _json.loads(request.body).get('reglas', [])
    except Exception:
        reglas = []
    limpias = []
    for r in reglas:
        try:
            mn = int(r.get('min'))
            mx = int(r.get('max')) if r.get('max') not in (None, '') else None
            hh = float(r.get('horas'))
        except (TypeError, ValueError):
            continue
        limpias.append({'min': mn, 'max': mx, 'horas': hh})
    cfg = RelojConfigGlobal.get()
    cfg.tarde_reglas = limpias or _TARDE_REGLAS_DEFAULT
    cfg.save(update_fields=['tarde_reglas'])
    return JsonResponse({'ok': True, 'reglas': cfg.tarde_reglas})
