import io, os, json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from core.utils_notifications import crear_notificacion
from django.template.loader import render_to_string
from django.contrib import messages
from django.db import connections
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
import datetime as _dt_module

_COORD_BL_EMAIL_FALLBACK = {
    'C1': 'cvarela@ana-hn.org',
    'C2': 'druiz@ana-hn.org',
    'C3': 'ialcerro@ana-hn.org',
    'C4': 'jmartinez@ana-hn.org',
}
_COLEGIO_EMAILS_FALLBACK = [
    'flicona@ana-hn.org',
    'kgarcia@ana-hn.org',
    'fvalladares@ana-hn.org',
]

def _coord_bl_email(codigo):
    """Return email for a bilingüe coordinator by code, falling back to hardcoded dict."""
    cfg = ConfiguracionCoordinador.objects.filter(area='bilingue', codigo=codigo, activo=True).select_related('usuario').first()
    if cfg and cfg.usuario and cfg.usuario.email:
        return cfg.usuario.email
    return _COORD_BL_EMAIL_FALLBACK.get(codigo, '')

def _colegio_emails(md_colegio_obj=None):
    """Return list of colegio coordinator emails. Filters by md_colegio_obj.coordinadores if given."""
    qs = ConfiguracionCoordinador.objects.filter(area='colegio', activo=True).select_related('usuario')
    if md_colegio_obj is not None:
        assigned = md_colegio_obj.coordinadores.filter(activo=True)
        if assigned.exists():
            qs = assigned.select_related('usuario')
    emails = [c.usuario.email for c in qs if c.usuario and c.usuario.email]
    return emails if emails else _COLEGIO_EMAILS_FALLBACK
SITE_URL = 'https://servicios.ana-hn.org:437'

_EMAIL_COORDI_BL = 'coordinacion_bl@ana-hn.org'

_C1_GRADOS   = ['1ero', '2do', '3ero']
_C2_GRADOS   = ['4to', '5to', '6to', '7mo', '8vo', '9no']
_C3_MATERIAS = [
    'español', 'estudios sociales', 'eess', 'cívica', 'civica',
    'computacion', 'computación', 'penmanship', 'arte',
    'educacion fisica', 'educación física', 'biblia',
    'inteligencia emocional',
]

def _q_grados(grados):
    q = Q()
    for g in grados:
        q |= Q(grado__icontains=g)
    return q

def _q_materias(materias):
    q = Q()
    for m in materias:
        q |= Q(materia__icontains=m)
    return q

def _q_docentes(docentes):
    q = Q()
    for d in docentes:
        q |= Q(docente__icontains=d)
    return q

def _q_for_coord(codigo):
    """Q filter for a coordinator's dashboard: explicit override takes priority over docente match."""
    q_docente = _q_docentes_for_coord(codigo)
    no_override = Q(coord_asignado='') | Q(coord_asignado__isnull=True)
    return Q(coord_asignado=codigo) | (no_override & q_docente)

def _q_docentes_for_coord(codigo):
    """
    Builds Q() for reports belonging to coordinator `codigo`.
    For teachers shared across coordinators, restricts by the materias
    assigned to this coordinator in MateriaDocenteBilingue so that
    reports from shared teachers only appear in the right dashboard.
    """
    all_records = list(MateriaDocenteBilingue.objects.filter(activo=True))
    docente_all_coords = {}
    for md in all_records:
        for c in [x.strip() for x in md.coordinador.split(',')]:
            docente_all_coords.setdefault(md.docente, set()).add(c)
    q = Q()
    for md in all_records:
        if codigo not in [x.strip() for x in md.coordinador.split(',')]:
            continue
        other_coords = docente_all_coords[md.docente] - {codigo}
        if other_coords:
            q_mat = Q()
            for m in [x.strip() for x in md.materia.split(',') if x.strip()]:
                q_mat |= Q(materia__icontains=m)
            q |= Q(docente__icontains=md.docente) & q_mat
        else:
            q |= Q(docente__icontains=md.docente)
    return q

_TIPO_COLOR = {
    'Reporte Informativo': '#1971c2',
    'Reporte Conductual':  '#f59f00',
    'Progress Report':     '#0ca678',
}
_TIPO_ICON = {
    'Reporte Informativo': '&#8505;',
    'Reporte Conductual':  '&#9888;',
    'Progress Report':     '&#128200;',
}


def _notificar_coordinadores(tipo, maestro, alumno, grado, materia, area, coordinador_bl=None, md_colegio=None, subtipo=None):
    nombre = maestro.get_full_name() or maestro.username
    asunto = f"[TechCare] Nuevo {tipo} registrado – {alumno}"
    color = _TIPO_COLOR.get(tipo, '#1971c2')
    icon  = _TIPO_ICON.get(tipo, '&#128203;')
    anio  = _dt_module.datetime.now().year
    filas_html = ""
    for etiqueta, valor in [("Tipo", tipo), ("Maestro", nombre), ("Alumno", alumno),
                             ("Grado", grado), ("Materia", materia), ("Área", area)]:
        if valor:
            filas_html += (
                f'<tr><td style="padding:8px 0;font-size:12px;color:#6c757d;'
                f'text-transform:uppercase;letter-spacing:.4px;width:90px;">{etiqueta}</td>'
                f'<td style="padding:8px 0;font-size:14px;color:#1a1a2e;font-weight:600;">{valor}</td></tr>'
            )
    html_cuerpo = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.10);">
      <tr>
        <td style="background:linear-gradient(135deg,#1864ab,{color});padding:28px 40px;text-align:center;">
          <p style="margin:0;font-size:24px;font-weight:700;color:#fff;letter-spacing:-.5px;">TechCare</p>
          <p style="margin:4px 0 0;font-size:12px;color:rgba(255,255,255,.75);">Asociación Nuevo Amanecer</p>
        </td>
      </tr>
      <tr>
        <td style="padding:32px 40px 20px;">
          <p style="margin:0 0 4px;font-size:18px;font-weight:700;color:#1a1a2e;">
            {icon} Nuevo reporte registrado
          </p>
          <p style="margin:0 0 24px;font-size:14px;color:#6c757d;">Se ha registrado un nuevo reporte en el sistema.</p>
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="background:#f8f9fa;border-radius:8px;padding:16px 20px;margin-bottom:24px;border-left:4px solid {color};">
            {filas_html}
          </table>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center">
              <a href="{SITE_URL}"
                 style="display:inline-block;background:{color};color:#fff;text-decoration:none;
                        padding:12px 32px;border-radius:8px;font-size:14px;font-weight:600;">
                Ver en el sistema
              </a>
            </td></tr>
          </table>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:14px 40px;border-top:1px solid #e9ecef;text-align:center;">
          <p style="margin:0;font-size:11px;color:#adb5bd;">
            © {anio} Soporte Técnico – Asociación Nuevo Amanecer
          </p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body></html>"""
    texto_plano = (
        f"Nuevo {tipo} registrado.\n\n"
        f"Maestro : {nombre}\nAlumno  : {alumno}\nGrado   : {grado}\n"
        f"Materia : {materia}\nÁrea    : {area}\n\nRevisa: {SITE_URL}"
    )
    # 1. Regla explícita configurada en el admin
    _SUBTIPO_CAMPO = {
        'conductual':             'recibe_conductual',
        'informativo_academico':  'recibe_informativo_academico',
        'informativo_conductual': 'recibe_informativo_conductual',
        'progress':               'recibe_progress',
    }
    destinatarios = None
    if subtipo and subtipo in _SUBTIPO_CAMPO:
        campo = _SUBTIPO_CAMPO[subtipo]
        reglas = ConfiguracionNotificacion.objects.filter(
            area=area, activo=True, **{campo: True}
        ).select_related('coordinador__usuario')
        emails = [
            r.coordinador.usuario.email
            for r in reglas
            if r.coordinador.usuario and r.coordinador.usuario.email
        ]
        if emails:
            destinatarios = emails

    # 2. Fallback: lógica automática por materia/docente
    if destinatarios is None:
        if area == 'colegio':
            destinatarios = _colegio_emails(md_colegio)
        elif tipo == 'Reporte Conductual':
            destinatarios = [e for e in [_coord_bl_email('C3')] if e]
        elif coordinador_bl:
            codigos = [c.strip() for c in coordinador_bl.split(',') if c.strip()]
            destinatarios = list(dict.fromkeys(e for c in codigos for e in [_coord_bl_email(c)] if e))
        else:
            destinatarios = [e for c in _COORD_BL_EMAIL_FALLBACK for e in [_coord_bl_email(c)] if e]
    try:
        msg = EmailMultiAlternatives(
            asunto, texto_plano, settings.DEFAULT_FROM_EMAIL, destinatarios
        )
        msg.attach_alternative(html_cuerpo, "text/html")
        msg.send(fail_silently=True)
    except Exception as _e:
        print(f"[WARN] email coordinadores: {_e}")

    # Notificación en campanita para cada coordinador
    mensaje_noti = f"Nuevo {tipo} — {alumno} ({grado})"
    if materia:
        mensaje_noti += f" · {materia}"
    tipo_noti = 'alerta' if tipo == 'Reporte Conductual' else 'info'
    for email in destinatarios:
        try:
            coord_user = User.objects.get(email=email)
            crear_notificacion(
                coord_user,
                mensaje_noti,
                modulo='conducta',
                tipo=tipo_noti,
                enviar_correo=False,
            )
        except User.DoesNotExist:
            pass

# PDF y PowerPoint
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Pt

from .forms import (
    ReporteInformativoForm,
    ReporteConductualForm,
    ProgressReportForm
)
from .models import (
    IncisoConductual,
    ReporteInformativo,
    ReporteConductual,
    ProgressReport,
    MateriaDocenteBilingue,
    MateriaDocenteColegio,
    EvidenciaReporte,  # <--- hecho por claude code: importar modelo de evidencias para la view subir_evidencia
    ConfiguracionNotificacion,
    ConfiguracionCoordinador,
)
from tickets.models import Ticket


# ---------------------------
# FUNCIONES AUXILIARES
# ---------------------------
def obtener_alumnos_bilingue():
    query = """
    SELECT d.PersonaID, 
           ISNULL(d.Nombre1,'') + 
           CASE WHEN d.Nombre2 IS NOT NULL AND d.Nombre2 <> '' THEN ' ' + d.Nombre2 ELSE '' END + ' ' +
           ISNULL(d.Apellido1,'') + 
           CASE WHEN d.Apellido2 IS NOT NULL AND d.Apellido2 <> '' THEN ' ' + d.Apellido2 ELSE '' END AS NombreCompl,
           da.Descripcion AS AreaDesc, c.CrsoNumero, c.GrupoNumero
      FROM dbo.tblPrsDtosGen AS d
      JOIN dbo.tblPrsTipo           AS t  ON d.PersonaID = t.PersonaID
      JOIN dbo.tblEdcArea           AS a  ON t.IngrEgrID  = a.IngrEgrID
      JOIN dbo.tblEdcEjecCrso       AS ec ON a.AreaID     = ec.AreaID
      JOIN dbo.tblEdcCrso           AS c  ON ec.CrsoID    = c.CrsoID
      JOIN dbo.tblEdcDescripAreaEdc AS da ON a.DescrAreaEdcID = da.DescrAreaEdcID
     WHERE d.Alum = 1 
     AND DATEPART(yy, c.FechaInicio) = DATEPART(yyyy, GETDATE())
       AND da.Descripcion IN (N'PrimariaBL', N'ColegioBL', N'PreescolarBL')
       AND ec.Desertor = 0 AND ec.TrasladoPer = 0
     ORDER BY da.Descripcion, c.CrsoNumero, c.GrupoNumero, NombreCompl
    """
    alumnos = []
    try:
        with connections['padres_sqlserver'].cursor() as cursor:
            cursor.execute(query)
            for pid, nombre, area, crso, grupo in cursor.fetchall():
                label = nombre.strip()
                grado = f"{area} {crso}-{grupo}"
                alumnos.append({'id': str(pid), 'label': label, 'grado': grado})
    except Exception as e:
        print(">>> ERROR SQL BILINGUE:", e)
    return alumnos

def obtener_alumnos_colegio():
    query = """
    SELECT TOP (100) PERCENT d.PersonaID,
           ISNULL(d.Nombre1, '') + 
           CASE WHEN d.Nombre2 IS NOT NULL AND d.Nombre2 <> '' THEN ' ' + d.Nombre2 ELSE '' END + ' ' +
           ISNULL(d.Apellido1, '') + 
           CASE WHEN d.Apellido2 IS NOT NULL AND d.Apellido2 <> '' THEN ' ' + d.Apellido2 ELSE '' END AS NombreCompl,
           da.Descripcion AS AreaDesc, c.CrsoNumero, c.GrupoNumero
      FROM dbo.tblPrsDtosGen AS d
     INNER JOIN dbo.tblPrsTipo           AS t  ON d.PersonaID = t.PersonaID
     INNER JOIN dbo.tblEdcArea           AS a  ON t.IngrEgrID  = a.IngrEgrID
     INNER JOIN dbo.tblEdcEjecCrso       AS ec ON a.AreaID     = ec.AreaID
     INNER JOIN dbo.tblEdcCrso           AS c  ON ec.CrsoID    = c.CrsoID
     INNER JOIN dbo.tblEdcDescripAreaEdc AS da ON a.DescrAreaEdcID = da.DescrAreaEdcID
     WHERE (d.Alum = 1) 
       AND (DATEPART(yy, c.FechaInicio) = DATEPART(yyyy, GETDATE()))
       AND (da.Descripcion IN (N'Colegio', N'Bachillerato')) 
       AND (ec.Desertor = 0) AND (ec.TrasladoPer = 0)
     ORDER BY AreaDesc, c.CrsoNumero, c.GrupoNumero, NombreCompl
    """
    alumnos = []
    try:
        with connections['padres_sqlserver'].cursor() as cursor:
            cursor.execute(query)
            for pid, nombre, area, crso, grupo in cursor.fetchall():
                label = nombre.strip()
                grado = f"{area} {crso}-{grupo}"
                alumnos.append({'id': str(pid), 'label': label, 'grado': grado})
    except Exception as e:
        print(">>> ERROR SQL COLEGIO:", e)
    return alumnos


def get_materia_docente_choices(area):
    if area == 'bilingue':
        return [
            (str(md.pk), f"{md.materia} — {md.docente}")
            for md in MateriaDocenteBilingue.objects.filter(activo=True)
        ]
    else:
        return [
            (str(md.pk), f"{md.materia} — {md.docente}")
            for md in MateriaDocenteColegio.objects.filter(activo=True)
        ]

# ---------------------------
# DASHBOARDS Y FORMULARIOS
# ---------------------------
_USUARIOS_MULTI_AREA = {'druiz@ana-hn.org', 'admin2@ana-hn.org'}

@login_required
def dashboard_maestro(request):
    user = request.user
    area = request.GET.get('area')
    if user.username in _USUARIOS_MULTI_AREA:
        if area:
            request.session['maestro_area'] = area
        else:
            area = request.session.get('maestro_area')
    if not area:
        if user.groups.filter(name='maestros_bilingue').exists():
            area = 'bilingue'
        elif user.groups.filter(name='maestros_colegio').exists():
            area = 'colegio'
    return render(request, 'conducta/dashboard_maestros.html', {'area': area})

# ------------ REPORTE INFORMATIVO  ------------
@login_required
def reporte_informativo_bilingue(request):
    area = 'bilingue'
    students = obtener_alumnos_bilingue()  
    materia_docente_choices = get_materia_docente_choices(area)
    fecha = timezone.now().strftime("%Y-%m-%dT%H:%M")

    if request.method == 'POST':
        alumno_id = request.POST.get('alumno')
        grado = request.POST.get('grado')
        materia_docente_id = request.POST.get('materia_docente')
        comentario = request.POST.get('comentario', "")
        tipo_reporte = request.POST.get('tipo_reporte', 'academico')
        alumno_obj = next((a for a in students if a['id'] == alumno_id), None)
        alumno_label = alumno_obj['label'] if alumno_obj else ""
        materia = docente = coord_bl = ""
        if materia_docente_id:
            md_obj = MateriaDocenteBilingue.objects.filter(pk=materia_docente_id).first()
            if md_obj:
                materia = md_obj.materia
                docente = md_obj.docente
                coord_bl = md_obj.coordinador
        ReporteInformativo.objects.create(
            usuario=request.user,
            area=area,
            alumno_id=alumno_id,
            alumno_nombre=alumno_label,
            grado=grado,
            materia=materia,
            docente=docente,
            tipo_reporte=tipo_reporte,
            comentario=comentario
        )
        _notificar_coordinadores("Reporte Informativo", request.user, alumno_label, grado, materia, area,
                                 coordinador_bl=coord_bl, subtipo=f"informativo_{tipo_reporte}")
        messages.success(request, "¡Reporte registrado correctamente!")
        return redirect('reporte_informativo_bilingue')

    return render(request, 'conducta/form_informativo.html', {
        'students': students,    
        'materia_docente_choices': materia_docente_choices,
        'fecha': fecha,
        'area': area,
    })

@login_required
def reporte_informativo_colegio(request):
    area = 'colegio'
    students = obtener_alumnos_colegio()
    materia_docente_choices = get_materia_docente_choices(area)
    fecha = timezone.now().strftime("%Y-%m-%dT%H:%M")

    if request.method == 'POST':
        alumno_id = request.POST.get('alumno')
        grado = request.POST.get('grado')
        materia_docente_id = request.POST.get('materia_docente')
        comentario = request.POST.get('comentario', "")
        tipo_reporte = request.POST.get('tipo_reporte', 'academico')
        alumno_obj = next((a for a in students if a['id'] == alumno_id), None)
        alumno_label = alumno_obj['label'] if alumno_obj else ""
        materia = docente = ""
        md_obj = None
        if materia_docente_id:
            md_obj = MateriaDocenteColegio.objects.filter(pk=materia_docente_id).first()
            if md_obj:
                materia = md_obj.materia
                docente = md_obj.docente
        ReporteInformativo.objects.create(
            usuario=request.user,
            area=area,
            alumno_id=alumno_id,
            alumno_nombre=alumno_label,
            grado=grado,
            materia=materia,
            docente=docente,
            tipo_reporte=tipo_reporte,
            comentario=comentario
        )
        _notificar_coordinadores("Reporte Informativo", request.user, alumno_label, grado, materia, area,
                                 md_colegio=md_obj, subtipo=f"informativo_{tipo_reporte}")
        messages.success(request, "¡Reporte registrado correctamente!")
        return redirect('reporte_informativo_colegio')

    return render(request, 'conducta/form_informativo.html', {
        'students': students,
        'materia_docente_choices': materia_docente_choices,
        'fecha': fecha,
        'area': area,
    })

# ------------ REPORTE CONDUCTUAL  ------------
@login_required
def reporte_conductual_bilingue(request):
    area = 'bilingue'
    students = obtener_alumnos_bilingue()
    materia_docente_choices = get_materia_docente_choices(area)
    fecha = timezone.now().strftime("%Y-%m-%d")
    # Obtiene incisos por severidad
    incisos_leve = IncisoConductual.objects.filter(activo=True, tipo='leve').order_by('descripcion')
    incisos_grave = IncisoConductual.objects.filter(activo=True, tipo='grave').order_by('descripcion')
    incisos_muygrave = IncisoConductual.objects.filter(activo=True, tipo='muy_grave').order_by('descripcion')

    if request.method == 'POST':
        alumno_id = request.POST.get('alumno')
        grado = request.POST.get('grado')
        materia_docente_id = request.POST.get('materia_docente')
        fecha_val = request.POST.get('fecha')
        comentario = request.POST.get('comentario', "")

        # Obtén las listas seleccionadas si el checkbox está activo
        ids_leve = request.POST.getlist('inciso_leve[]') if request.POST.get('chk_leve') else []
        ids_grave = request.POST.getlist('inciso_grave[]') if request.POST.get('chk_grave') else []
        ids_muygrave = request.POST.getlist('inciso_muygrave[]') if request.POST.get('chk_muygrave') else []

        alumno_obj = next((a for a in students if a['id'] == alumno_id), None)
        alumno_label = alumno_obj['label'] if alumno_obj else ""
        materia = docente = coord_bl = ""
        if materia_docente_id:
            md_obj = MateriaDocenteBilingue.objects.filter(pk=materia_docente_id).first()
            if md_obj:
                materia = md_obj.materia
                docente = md_obj.docente
                coord_bl = md_obj.coordinador

        # Crea el reporte sin los ManyToMany
        reporte = ReporteConductual.objects.create(
            usuario=request.user,
            area=area,
            alumno_id=alumno_id,
            alumno_nombre=alumno_label,
            grado=grado,
            materia=materia,
            docente=docente,
            fecha=fecha_val,
            comentario=comentario,
        )
        if ids_leve:
            reporte.incisos_leve.set(ids_leve)
        if ids_grave:
            reporte.incisos_grave.set(ids_grave)
        if ids_muygrave:
            reporte.incisos_muygrave.set(ids_muygrave)

        _notificar_coordinadores("Reporte Conductual", request.user, alumno_label, grado, materia, area,
                                 coordinador_bl=coord_bl, subtipo='conductual')
        messages.success(request, "¡Reporte conductual registrado correctamente!")
        return redirect('reporte_conductual_bilingue')

    return render(request, 'conducta/form_conductual.html', {
        'students': students,
        'materia_docente_choices': materia_docente_choices,
        'fecha': fecha,
        'area': area,
        'incisos_leve': incisos_leve,
        'incisos_grave': incisos_grave,
        'incisos_muygrave': incisos_muygrave,
    })

@login_required
def reporte_conductual_colegio(request):
    area = 'colegio'
    students = obtener_alumnos_colegio()
    materia_docente_choices = get_materia_docente_choices(area)
    fecha = timezone.now().strftime("%Y-%m-%d")
    incisos_leve = IncisoConductual.objects.filter(activo=True, tipo='leve').order_by('descripcion')
    incisos_grave = IncisoConductual.objects.filter(activo=True, tipo='grave').order_by('descripcion')
    incisos_muygrave = IncisoConductual.objects.filter(activo=True, tipo='muy_grave').order_by('descripcion')

    if request.method == 'POST':
        alumno_id = request.POST.get('alumno')
        grado = request.POST.get('grado')
        materia_docente_id = request.POST.get('materia_docente')
        fecha_val = request.POST.get('fecha')
        comentario = request.POST.get('comentario', "")

        ids_leve = request.POST.getlist('inciso_leve[]') if request.POST.get('chk_leve') else []
        ids_grave = request.POST.getlist('inciso_grave[]') if request.POST.get('chk_grave') else []
        ids_muygrave = request.POST.getlist('inciso_muygrave[]') if request.POST.get('chk_muygrave') else []

        alumno_obj = next((a for a in students if a['id'] == alumno_id), None)
        alumno_label = alumno_obj['label'] if alumno_obj else ""
        materia = docente = ""
        md_obj = None
        if materia_docente_id:
            md_obj = MateriaDocenteColegio.objects.filter(pk=materia_docente_id).first()
            if md_obj:
                materia = md_obj.materia
                docente = md_obj.docente

        reporte = ReporteConductual.objects.create(
            usuario=request.user,
            area=area,
            alumno_id=alumno_id,
            alumno_nombre=alumno_label,
            grado=grado,
            materia=materia,
            docente=docente,
            fecha=fecha_val,
            comentario=comentario,
        )
        if ids_leve:
            reporte.incisos_leve.set(ids_leve)
        if ids_grave:
            reporte.incisos_grave.set(ids_grave)
        if ids_muygrave:
            reporte.incisos_muygrave.set(ids_muygrave)

        _notificar_coordinadores("Reporte Conductual", request.user, alumno_label, grado, materia, area,
                                 md_colegio=md_obj, subtipo='conductual')
        messages.success(request, "¡Reporte conductual registrado correctamente!")
        return redirect('reporte_conductual_colegio')

    return render(request, 'conducta/form_conductual.html', {
        'students': students,
        'materia_docente_choices': materia_docente_choices,
        'fecha': fecha,
        'area': area,
        'incisos_leve': incisos_leve,
        'incisos_grave': incisos_grave,
        'incisos_muygrave': incisos_muygrave,
    })

#-------------- PROGRESS REPORT -----------------
@login_required
def progress_report_bilingue(request):
    MATERIAS_PRIMARIA = [
        "Math", "Phonics", "Reading", "Language",
        "Science", "Español", "CCSS", "Asociadas"
    ]
    MATERIAS_COLEGIO = [
        "Math", "Spelling", "Reading", "Language", "Science",
        "Español", "CCSS", "Cívica", "Asociadas"
    ]

    students = obtener_alumnos_bilingue()
    alumnos_choices = [(s['id'], s['label']) for s in students]

    materias = MATERIAS_PRIMARIA
    grado = ""
    alumno_id = ""
    if request.method == 'POST':
        form = ProgressReportForm(alumnos_choices=alumnos_choices, data=request.POST)
        alumno_id = request.POST.get('alumno')
        grado = request.POST.get('grado', '')
        if alumno_id:
            alumno_obj = next((s for s in students if s['id'] == alumno_id), None)
            if alumno_obj:
                grado = alumno_obj['grado']
        if grado and ("Primaria" in grado or "Preescolar" in grado):
            materias = MATERIAS_PRIMARIA
        else:
            materias = MATERIAS_COLEGIO

        if form.is_valid():
            # --- PROCESAR MATERIAS ---
            usuario_actual = request.user.get_full_name() or request.user.username
            materias_list = []
            for materia in materias:
                if materia == "Asociadas":
                    asignaciones = request.POST.getlist('asignacion_Asociadas[]')
                    comentarios = request.POST.getlist('comentario_Asociadas[]')
                    # Máximo 5 asociadas
                    for idx, asignacion in enumerate(asignaciones[:5]):
                        comentario = comentarios[idx] if idx < len(comentarios) else ""
                        materias_list.append({
                            'materia': 'Asociadas',
                            'asignacion': asignacion,
                            'comentario': comentario,
                            'docente': usuario_actual if (asignacion.strip() or comentario.strip()) else '',
                        })
                else:
                    asignacion = request.POST.get(f"asignacion_{materia}", "")
                    comentario = request.POST.get(f"comentario_{materia}", "")
                    materias_list.append({
                        'materia': materia,
                        'asignacion': asignacion,
                        'comentario': comentario,
                        'docente': usuario_actual if (asignacion.strip() or comentario.strip()) else '',
                    })
            # --- DATOS GENERALES ---
            semana_inicio = form.cleaned_data.get('semana_inicio')
            semana_fin = form.cleaned_data.get('semana_fin')
            comentario_general = form.cleaned_data.get('comentario_general', "")
            alumno_id = form.cleaned_data.get('alumno')
            alumno_obj = next((s for s in students if s['id'] == alumno_id), None)
            alumno_label = alumno_obj['label'] if alumno_obj else ""
            grado = form.cleaned_data.get('grado')

            # --- CREAR REPORTE ---
            ProgressReport.objects.create(
                usuario=request.user,
                alumno_id=alumno_id,
                alumno_nombre=alumno_label,
                grado=grado,
                semana_inicio=semana_inicio,
                semana_fin=semana_fin,
                comentario_general=comentario_general,
                materias_json=materias_list
            )
            _notificar_coordinadores("Progress Report", request.user, alumno_label, grado, "", "bilingue",
                                     subtipo='progress')
            messages.success(request, "¡Progress report registrado correctamente!")
            return redirect('progress_report_bilingue')
    else:
        form = ProgressReportForm(alumnos_choices=alumnos_choices)
        materias = MATERIAS_PRIMARIA

    return render(request, 'conducta/form_progress.html', {
        'form': form,
        'materias': materias,
        'students': students,
        'grado': grado,
    })


#-------------- HISTORIAL MAESTROS -----------------
@login_required
def historial_maestro_bilingue(request):
    usuario = request.user
    usuario_actual = usuario.get_full_name()
    request.session['maestro_area'] = 'bilingue'
    reportes_informativo = ReporteInformativo.objects.filter(usuario=usuario, area='bilingue').order_by('-fecha')
    reportes_conductual = ReporteConductual.objects.filter(usuario=usuario, area='bilingue').order_by('-fecha')

    reportes_progress = ProgressReport.objects.all().order_by('-fecha')

    tickets_usuario = Ticket.objects.filter(email=usuario.email).order_by('-created_at')

    es_admin = request.user.groups.filter(name='administracion').exists()
    back_url = 'tickets/submit_ticket/' if es_admin else '/conducta/dashboard/maestro/'

    return render(request, 'conducta/historial_maestro.html', {
        'reportes_informativo': reportes_informativo,
        'reportes_conductual': reportes_conductual,
        'reportes_progress': reportes_progress,
        'tickets_usuario': tickets_usuario,
        'area': 'bilingue',
        'back_url': back_url,
        'today': timezone.now().strftime('%Y-%m-%d'),
    })


@login_required
def historial_maestro_colegio(request):
    usuario = request.user
    request.session['maestro_area'] = 'colegio'
    reportes_informativo = ReporteInformativo.objects.filter(usuario=usuario, area='colegio').order_by('-fecha')
    reportes_conductual = ReporteConductual.objects.filter(usuario=usuario, area='colegio').order_by('-fecha')

    tickets_usuario = Ticket.objects.filter(email=usuario.email).order_by('-created_at')

    es_admin = request.user.groups.filter(name='administracion').exists()
    back_url = 'tickets/submit_ticket/' if es_admin else '/conducta/dashboard/maestro/'

    return render(request, 'conducta/historial_maestro.html', {
        'reportes_informativo': reportes_informativo,
        'reportes_conductual': reportes_conductual,
        'reportes_progress': [],
        'tickets_usuario': tickets_usuario,
        'area': 'colegio',
        'back_url': back_url,
        'today': timezone.now().strftime('%Y-%m-%d'),
    })

# ────────────────────────────────────────────────────────────
# REENVIAR NOTIFICACIONES A COORDINADORES (solo superuser)
# ────────────────────────────────────────────────────────────
@login_required
def reenviar_reportes_coordinadores(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    fecha_str = request.POST.get('fecha', '').strip()
    if not fecha_str:
        return JsonResponse({'ok': False, 'error': 'Fecha requerida'}, status=400)

    from datetime import date as _date_type
    try:
        fecha = _date_type.fromisoformat(fecha_str)
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Fecha inválida'}, status=400)

    enviados = 0
    for r in ReporteInformativo.objects.filter(fecha__date=fecha):
        _notificar_coordinadores("Reporte Informativo", r.usuario, r.alumno_nombre, r.grado, r.materia, r.area,
                                 subtipo=f"informativo_{r.tipo_reporte}")
        enviados += 1
    for r in ReporteConductual.objects.filter(fecha=fecha):
        _notificar_coordinadores("Reporte Conductual", r.usuario, r.alumno_nombre, r.grado, r.materia, r.area,
                                 subtipo='conductual')
        enviados += 1
    for r in ProgressReport.objects.filter(semana_inicio__lte=fecha, semana_fin__gte=fecha):
        _notificar_coordinadores("Progress Report", r.usuario, r.alumno_nombre, r.grado, "", "bilingue",
                                 subtipo='progress')
        enviados += 1

    return JsonResponse({'ok': True, 'enviados': enviados})


# ────────────────
# EDITAR CONDUCTUAL
# ────────────────

@login_required
def editar_reporte_conductual(request, pk):
    reporte = get_object_or_404(ReporteConductual, pk=pk)

    # Elige coordinadores según área
    if reporte.area == "bilingue":
        coordinadores = COORDINADORES_BL
    else:
        coordinadores = COORDINADORES_COLEGIO

    # <--- hecho por claude code: se cargan todos los incisos activos para que el
    # coordinador pueda agregar/quitar incisos al editar el reporte conductual.
    incisos_leve     = IncisoConductual.objects.filter(activo=True, tipo='leve').order_by('descripcion')
    incisos_grave    = IncisoConductual.objects.filter(activo=True, tipo='grave').order_by('descripcion')
    incisos_muygrave = IncisoConductual.objects.filter(activo=True, tipo='muy_grave').order_by('descripcion')

    if request.method == "POST":
        reporte.comentario            = request.POST.get("comentario", "")
        reporte.comentario_coordinador = request.POST.get("comentario_coordinador", "")
        reporte.estado                = request.POST.get("estado", "enviado")
        reporte.coordinador_firma     = request.POST.get("coordinador_firma", "")
        reporte.save()
        # <--- hecho por claude code: actualizar incisos desde los checkboxes del coordinador
        ids_leve     = request.POST.getlist("incisos_leve")
        ids_grave    = request.POST.getlist("incisos_grave")
        ids_muygrave = request.POST.getlist("incisos_muygrave")
        reporte.incisos_leve.set(ids_leve)
        reporte.incisos_grave.set(ids_grave)
        reporte.incisos_muygrave.set(ids_muygrave)
        messages.success(request, "Reporte conductual actualizado correctamente.")
        return redirect('dashboard_coordinador', area=reporte.area)
    return render(request, "conducta/editor_conductual.html", {
        "reporte": reporte,
        "coordinadores": coordinadores,
        "incisos_leve": incisos_leve,
        "incisos_grave": incisos_grave,
        "incisos_muygrave": incisos_muygrave,
    })

# ────────────────
# EDITAR INFORMATIVO
# ────────────────

@login_required
def editar_reporte_informativo(request, pk):
    reporte = get_object_or_404(ReporteInformativo, pk=pk)

    # Elige coordinadores según área
    if reporte.area == "bilingue":
        coordinadores = COORDINADORES_BL
    else:
        coordinadores = COORDINADORES_COLEGIO

    if request.method == "POST":
        reporte.comentario            = request.POST.get("comentario", "")
        reporte.comentario_coordinador = request.POST.get("comentario_coordinador", "")
        reporte.estado                = request.POST.get("estado", "enviado")
        reporte.coordinador_firma     = request.POST.get("coordinador_firma", "")
        reporte.tipo_reporte          = request.POST.get("tipo_reporte", "academico")
        reporte.save()
        messages.success(request, "Reporte informativo actualizado correctamente.")
        return redirect('dashboard_coordinador', area=reporte.area)
    return render(request, "conducta/editor_informativo.html", {
        "reporte": reporte,
        "coordinadores": coordinadores,
    })

# ────────────────────────────────────────────────────────────────
# ELIMINAR REPORTES (AJAX) — solo coordinadores/staff
# Notifica a todos los superusuarios al eliminar.
# ────────────────────────────────────────────────────────────────

@login_required
def eliminar_reporte_conductual(request, pk):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    if not (request.user.is_staff or request.user.groups.filter(name__icontains='coordinador').exists()):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)

    reporte = get_object_or_404(ReporteConductual, pk=pk)
    info = {
        'pk': reporte.pk,
        'alumno': reporte.alumno_nombre,
        'materia': reporte.materia,
        'docente': reporte.docente,
        'fecha': reporte.fecha.strftime('%d/%m/%Y %H:%M') if reporte.fecha else '—',
        'eliminado_por': request.user.get_full_name() or request.user.username,
    }
    reporte.delete()

    msg = (f"⚠️ Reporte Conductual #{info['pk']} eliminado por {info['eliminado_por']}. "
           f"Alumno: {info['alumno']} | Materia: {info['materia']} – {info['docente']} | "
           f"Fecha: {info['fecha']}")
    for su in User.objects.filter(is_superuser=True):
        crear_notificacion(su, msg, 'conducta', tipo='warning')

    return JsonResponse({'ok': True})


@login_required
def eliminar_reporte_informativo(request, pk):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    if not (request.user.is_staff or request.user.groups.filter(name__icontains='coordinador').exists()):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)

    reporte = get_object_or_404(ReporteInformativo, pk=pk)
    info = {
        'pk': reporte.pk,
        'alumno': reporte.alumno_nombre,
        'materia': reporte.materia,
        'docente': reporte.docente,
        'tipo': reporte.get_tipo_reporte_display(),
        'fecha': reporte.fecha.strftime('%d/%m/%Y %H:%M') if reporte.fecha else '—',
        'eliminado_por': request.user.get_full_name() or request.user.username,
    }
    reporte.delete()

    msg = (f"⚠️ Reporte Informativo #{info['pk']} ({info['tipo']}) eliminado por {info['eliminado_por']}. "
           f"Alumno: {info['alumno']} | Materia: {info['materia']} – {info['docente']} | "
           f"Fecha: {info['fecha']}")
    for su in User.objects.filter(is_superuser=True):
        crear_notificacion(su, msg, 'conducta', tipo='warning')

    return JsonResponse({'ok': True})


@login_required
def set_coord_reporte(request):
    """AJAX: superuser cambia el coordinador asignado de un reporte."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    pk    = request.POST.get('pk')
    tipo  = request.POST.get('tipo')
    coord = request.POST.get('coord', '').strip().upper()

    if coord not in {'C1', 'C2', 'C3', 'C4', ''}:
        return JsonResponse({'ok': False, 'error': 'Coordinador inválido'}, status=400)

    if tipo == 'conductual':
        obj = get_object_or_404(ReporteConductual, pk=pk)
    elif tipo == 'informativo':
        obj = get_object_or_404(ReporteInformativo, pk=pk)
    else:
        return JsonResponse({'ok': False, 'error': 'Tipo inválido'}, status=400)

    obj.coord_asignado = coord
    obj.save(update_fields=['coord_asignado'])
    return JsonResponse({'ok': True, 'coord': coord or obj.coord_codigo})


# ────────────────
# EDITAR PROGRESS
# ────────────────

@login_required
def editar_progress_report(request, pk):
    # <--- hecho por claude code: view reescrita para corregir 3 bugs críticos:
    # Bug 1: Maestro A reclamaba TODAS las materias al guardar (incluso vacías),
    #         bloqueando a Maestro B. Fix: docente solo se asigna si hay contenido.
    # Bug 2: Indentación rota en el loop de Asociadas → NameError cuando el
    #         coordinador guardaba. Fix: loop correctamente indentado.
    # Bug 3: Solo se guardaba UNA fila de Asociadas (la última). Fix: loop correcto.
    # Extra: json.dumps() en un JSONField causaba doble serialización. Fix: lista directa.

    COORDINADORES_BL = ["Mr. Martinez", "Miss Alcerro", "Mr. Ruiz" , "Mrs. Varela"]

    reporte = get_object_or_404(ProgressReport, pk=pk)
    es_coord = es_coordinador(request.user)
    usuario_actual = request.user.get_full_name() or request.user.username

    # Decodificar materias — JSONField puede devolver str si fue guardado con json.dumps()
    materias = reporte.materias_json
    if isinstance(materias, str):
        try:
            materias = json.loads(materias)
        except Exception:
            materias = []
    if not materias:
        materias = []

    # Marcar editabilidad:
    # - Coordinador: siempre editable
    # - Materia vacía (sin contenido y sin docente): cualquier maestro puede llenarla
    # - Materia del propio maestro: editable
    # - Materia de otro maestro, o con contenido sin docente (legacy): readonly
    for mat in materias:
        docente_guardado  = mat.get("docente", "").strip()
        tiene_contenido   = bool(mat.get("asignacion", "").strip() or mat.get("comentario", "").strip())
        if es_coord:
            mat["editable"] = True
        elif docente_guardado == usuario_actual:
            mat["editable"] = True
        elif not docente_guardado and not tiene_contenido:
            mat["editable"] = True   # materia vacía, disponible para cualquiera
        else:
            mat["editable"] = False  # tiene contenido de otro maestro → protegida

    if request.method == 'POST':
        nuevas_materias = []

        # Separar Asociadas existentes para preservar sus docentes
        asociadas_existentes = [m for m in materias if m.get('materia') == 'Asociadas']

        # ── 1. Procesar materias normales (no Asociadas) ──────────────────────
        for mat in materias:
            if mat.get('materia') == 'Asociadas':
                continue  # se procesan en el bloque siguiente

            nombre = mat.get('materia', '')

            if mat["editable"]:
                asignacion_nueva   = request.POST.get(f'asignacion_{nombre}', '').strip()
                comentario_nuevo   = request.POST.get(f'comentario_{nombre}', '').strip()
                asignacion_previa  = mat.get('asignacion', '').strip()
                comentario_previo  = mat.get('comentario', '').strip()

                mat['asignacion'] = asignacion_nueva
                mat['comentario'] = comentario_nuevo

                if not es_coord:
                    # <--- hecho por claude code: fix crítico
                    # Solo reclamar docencia si el maestro REALMENTE cambió el valor.
                    # Sin esto, abrir el form y guardar sin tocar una materia de otro
                    # maestro la reclama como propia (readonly envía el valor igual).
                    cambio_real = (asignacion_nueva != asignacion_previa) or \
                                  (comentario_nuevo != comentario_previo)

                    if cambio_real:
                        if asignacion_nueva or comentario_nuevo:
                            mat['docente'] = usuario_actual  # el usuario editó → es suya
                        else:
                            mat['docente'] = ''  # borró todo → libera la materia
                    # Si no hubo cambio real, preservar el docente original tal como está

            # Guardar sin la clave 'editable' (es solo para el template, no va a la BD)
            nuevas_materias.append({k: v for k, v in mat.items() if k != 'editable'})

        # ── 2. Procesar TODAS las filas de Asociadas (máximo 5) ──────────────
        asignaciones_asociadas = request.POST.getlist('asignacion_Asociadas[]')
        comentarios_asociadas  = request.POST.getlist('comentario_Asociadas[]')

        for i, asignacion in enumerate(asignaciones_asociadas[:5]):
            comentario = comentarios_asociadas[i] if i < len(comentarios_asociadas) else ''

            # Determinar docente: preservar el original si la fila ya existía y no es editable
            if i < len(asociadas_existentes):
                docente_original  = asociadas_existentes[i].get('docente', '')
                era_editable      = asociadas_existentes[i].get('editable', True)
                if era_editable and not es_coord:
                    docente_valor = usuario_actual if (asignacion.strip() or comentario.strip()) else docente_original
                elif es_coord:
                    docente_valor = docente_original  # coordinador no cambia docente
                else:
                    docente_valor = docente_original  # fila ajena → preservar
            else:
                # Fila nueva agregada con el botón "+"
                docente_valor = usuario_actual if (asignacion.strip() or comentario.strip()) else ''

            nuevas_materias.append({
                'materia':    'Asociadas',
                'asignacion': asignacion,
                'comentario': comentario,
                'docente':    docente_valor,
            })

        # ── 3. Guardar ────────────────────────────────────────────────────────
        # JSONField acepta la lista directamente; json.dumps() causaba doble serialización
        reporte.materias_json     = nuevas_materias
        reporte.comentario_general = request.POST.get('comentario_general', reporte.comentario_general)

        if es_coord:
            reporte.coordinador_firma      = request.POST.get('coordinador_firma', reporte.coordinador_firma)
            reporte.estado                 = request.POST.get('estado', reporte.estado)
            reporte.comentario_coordinador = request.POST.get('comentario_coordinador', reporte.comentario_coordinador)

        reporte.save()
        messages.success(request, "¡Reporte actualizado correctamente!")

        if es_coord:
            return redirect('dashboard_coordinador', area='bilingue')
        return redirect('historial_maestro_bilingue')

    return render(request, 'conducta/editor_progress.html', {
        'reporte':       reporte,
        'materias':      materias,
        'es_coordinador': es_coord,
        'usuario_actual': usuario_actual,
        'coordinadores':  COORDINADORES_BL,
    })

# -----------  DESCARGA EN PDF  -----------
def draw_paragraph(pdf, text, x, y, max_width, font="Helvetica", font_size=10, bold=False, italic=False, leading=13):
    """
    Dibuja un párrafo con saltos de línea y justificación manual en ReportLab.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth
    fontname = font
    if bold and italic:
        fontname = "Helvetica-BoldOblique"
    elif bold:
        fontname = "Helvetica-Bold"
    elif italic:
        fontname = "Helvetica-Oblique"
    pdf.setFont(fontname, font_size)
    lines = []
    for raw_line in text.split('\n'):
        line = ""
        for word in raw_line.split():
            test_line = f"{line} {word}".strip()
            if stringWidth(test_line, fontname, font_size) < max_width:
                line = test_line
            else:
                lines.append(line)
                line = word
        lines.append(line)
    for l in lines:
        pdf.drawString(x, y, l)
        y -= leading
    return y


@login_required
def descargar_pdf_informativo(request, pk):
    from .models import ReporteInformativo
    reporte = get_object_or_404(ReporteInformativo, pk=pk)
    buf = io.BytesIO()
    w, h = letter
    pdf = canvas.Canvas(buf, pagesize=letter)
    pdf.setTitle("reporte_informativo.pdf")

    # Logo centrado
    width_logo = 35 * mm
    height_logo = 35 * mm
    x_logo = (w - width_logo) / 2
    logo_path = os.path.join(settings.STATIC_ROOT, "conducta/img/ana-transformed.png")
    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            x=x_logo,
            y=h-40*mm,
            width=width_logo,
            height=height_logo,
            mask='auto'
        )
    # 🔥 Más margen superior
    y_actual = h - 52*mm

    # Título y datos
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(w/2, y_actual, "Nuevo Amanecer School" if reporte.area == "bilingue" else "C.E.M.N.G Nuevo Amanecer")
    y_actual -= 14*mm
    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(w/2, y_actual, "Reporte informativo")
    y_actual -= 14*mm

    # <--- hecho por claude code: offsets calculados con stringWidth para que el valor
    # quede pegado a la etiqueta sin espacio extra visible.
    def label_val(pdf, x, y, label, valor, lbl_font="Helvetica-Bold", lbl_size=11, val_font="Helvetica", val_size=10, gap=2):
        pdf.setFont(lbl_font, lbl_size)
        pdf.drawString(x, y, label)
        ancho = pdf.stringWidth(label, lbl_font, lbl_size)
        pdf.setFont(val_font, val_size)
        pdf.drawString(x + ancho + gap, y, valor)

    label_val(pdf, 32*mm, y_actual, "Nombre:", reporte.alumno_nombre)
    label_val(pdf, 118*mm, y_actual, "Grado:", reporte.grado)
    y_actual -= 8*mm
    label_val(pdf, 32*mm, y_actual, "Docente:", reporte.docente or '')
    label_val(pdf, 100*mm, y_actual, "Fecha:", reporte.fecha.strftime('%d/%m/%Y') if reporte.fecha else '')
    y_actual -= 12*mm

    # Comentario del docente
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(32*mm, y_actual, "Comentario del Docente:")
    y_actual -= 8*mm
    pdf.setFont("Helvetica-Oblique", 10)
    y_actual = draw_paragraph(
        pdf, reporte.comentario or "-", x=38*mm, y=y_actual, max_width=w-65*mm,
        font="Helvetica", font_size=10, italic=True, leading=12
    )
    y_actual -= 10*mm

    # Comentario del coordinador si existe
    if hasattr(reporte, 'comentario_coordinador') and reporte.comentario_coordinador:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(32*mm, y_actual, "Comentario del Coordinador:")
        y_actual -= 8*mm
        pdf.setFont("Helvetica-Oblique", 10)
        y_actual = draw_paragraph(
            pdf, reporte.comentario_coordinador, x=38*mm, y=y_actual, max_width=w-65*mm,
            font="Helvetica", font_size=10, italic=True, leading=12
        )
        y_actual -= 8*mm

    # <--- hecho por claude code: firmas fijas hacia abajo de la página (28mm del borde),
    # líneas más largas, y "Firma Pariente:" en lugar de "Firma Padre/Madre:".
    y_firma = min(y_actual - 15*mm, 28*mm)
    largo_firma = 58 * mm
    x_col1 = 15 * mm
    x_col2 = 78 * mm
    x_col3 = 141 * mm

    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(0.7)

    for x_col, label, nombre in [
        (x_col1, "Firma:", reporte.docente or ""),
        (x_col2, "Firma:", getattr(reporte, 'coordinador_firma', '') or ""),
        (x_col3, "Firma Pariente:", ""),
    ]:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x_col, y_firma + 5*mm, label)
        ancho_lbl = pdf.stringWidth(label, "Helvetica-Bold", 10)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x_col + ancho_lbl + 2, y_firma + 5*mm, nombre)
        pdf.line(x_col, y_firma, x_col + largo_firma, y_firma)

    pdf.save()
    buf.seek(0)
    grado_slug = reporte.grado.replace(' ', '_').replace('/', '-')
    nombre_archivo = f"informativo_{reporte.alumno_nombre.replace(' ', '_')}_{grado_slug}.pdf"
    response = HttpResponse(buf, content_type="application/pdf")
    response['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'
    return response


@login_required
def descargar_pdf_conductual(request, pk):
    from .models import ReporteConductual
    reporte = get_object_or_404(ReporteConductual, pk=pk)
    buf = io.BytesIO()
    w, h = letter
    pdf = canvas.Canvas(buf, pagesize=letter)
    pdf.setTitle("reporte_conductual.pdf")

    # <--- hecho por claude code: logo reducido a 22mm y reposicionado para comprimir espacio superior
    width_logo = 22 * mm
    height_logo = 22 * mm
    x_logo = (w - width_logo) / 2
    logo_path = os.path.join(settings.STATIC_ROOT, "conducta/img/ana-transformed.png")
    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            x=x_logo,
            y=h - 28*mm,
            width=width_logo,
            height=height_logo,
            mask='auto'
        )
    y_actual = h - 33*mm

    # Título
    pdf.setFont("Helvetica-Bold", 16)
    titulo = "Nuevo Amanecer School" if getattr(reporte, "area", None) == "bilingue" else "C.E.M.N.G Nuevo Amanecer"
    pdf.drawCentredString(w/2, y_actual, titulo)
    y_actual -= 9*mm
    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(w/2, y_actual, "Reporte conductual")
    y_actual -= 10*mm

    # <--- hecho por claude code: misma función label_val para eliminar espacios extra
    def label_val(pdf, x, y, label, valor, lbl_font="Helvetica-Bold", lbl_size=11, val_font="Helvetica", val_size=11, gap=2):
        pdf.setFont(lbl_font, lbl_size)
        pdf.drawString(x, y, label)
        ancho = pdf.stringWidth(label, lbl_font, lbl_size)
        pdf.setFont(val_font, val_size)
        pdf.drawString(x + ancho + gap, y, valor)

    label_val(pdf, 32*mm, y_actual, "Nombre:", reporte.alumno_nombre)

    y_actual -= 7*mm
    label_val(pdf, 32*mm, y_actual, "Grado:", reporte.grado)
    label_val(pdf, 118*mm, y_actual, "Fecha:", reporte.fecha.strftime('%d/%m/%Y') if reporte.fecha else '')

    y_actual -= 7*mm
    label_val(pdf, 32*mm, y_actual, "Docente:", reporte.docente or "")
    y_actual -= 9*mm

    # ----------- INCISOS -----------
    maxw = w - 65*mm
    for tipo, label in [("incisos_leve", "Leve"), ("incisos_grave", "Grave"), ("incisos_muygrave", "Muy Grave")]:
        incisos = getattr(reporte, tipo).all()
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(32*mm, y_actual, f"Incisos {label}:")
        y_actual -= 6*mm
        if incisos:
            for i in incisos:
                y_actual = draw_paragraph(
                    pdf, i.descripcion, x=38*mm, y=y_actual, max_width=maxw,
                    font="Helvetica", font_size=10, bold=True, italic=True, leading=12
                )
        else:
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(38*mm, y_actual, "-")
            y_actual -= 6*mm
        y_actual -= 4*mm

    # ----------- COMENTARIOS -----------
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(32*mm, y_actual, "Comentario del Docente:")
    y_actual -= 6*mm
    y_actual = draw_paragraph(
        pdf, reporte.comentario or "-", x=38*mm, y=y_actual, max_width=maxw,
        font="Helvetica", font_size=10, italic=True, leading=12
    )
    y_actual -= 7*mm

    if hasattr(reporte, 'comentario_coordinador') and reporte.comentario_coordinador:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(32*mm, y_actual, "Comentario del Coordinador:")
        y_actual -= 6*mm
        y_actual = draw_paragraph(
            pdf, reporte.comentario_coordinador, x=38*mm, y=y_actual, max_width=maxw,
            font="Helvetica", font_size=10, italic=True, leading=12
        )
        y_actual -= 6*mm

    # <--- hecho por claude code: firma dinámica a 5mm (~15px) del último contenido,
    # <--- hecho por claude code: firmas fijas hacia abajo (28mm del borde),
    # líneas más largas y "Firma Pariente:" en lugar de "Firma Padre/Madre:".
    y_firma = min(y_actual - 15*mm, 28*mm)
    largo_firma = 58 * mm
    x_col1 = 15 * mm
    x_col2 = 78 * mm
    x_col3 = 141 * mm

    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(0.7)

    for x_col, label, nombre in [
        (x_col1, "Firma:", reporte.docente or ""),
        (x_col2, "Firma:", getattr(reporte, 'coordinador_firma', '') or ""),
        (x_col3, "Firma Pariente:", ""),
    ]:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x_col, y_firma + 5*mm, label)
        ancho_lbl = pdf.stringWidth(label, "Helvetica-Bold", 10)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x_col + ancho_lbl + 2, y_firma + 5*mm, nombre)
        pdf.line(x_col, y_firma, x_col + largo_firma, y_firma)

    pdf.save()
    buf.seek(0)
    grado_slug = reporte.grado.replace(' ', '_').replace('/', '-')
    nombre_archivo = f"conductual_{reporte.alumno_nombre.replace(' ', '_')}_{grado_slug}.pdf"
    response = HttpResponse(buf, content_type="application/pdf")
    response['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'
    return response


@login_required
def descargar_pdf_progress(request, pk):
    from pptx.oxml.ns import qn
    from lxml import etree
    from pptx.util import Emu

    # ── helpers ──────────────────────────────────────────────────────────────
    def _add_shadow(run):
        rPr = run._r.get_or_add_rPr()
        for ex in rPr.findall(qn('a:effectLst')):
            rPr.remove(ex)
        effectLst = etree.SubElement(rPr, qn('a:effectLst'))
        outer = etree.SubElement(effectLst, qn('a:outerShdw'),
                                 attrib={'blurRad': '40000', 'dist': '23000',
                                         'dir': '5400000', 'rotWithShape': '0'})
        clr = etree.SubElement(outer, qn('a:srgbClr'), val='000000')
        etree.SubElement(clr, qn('a:alpha'), val='40000')

    def _run_titulo(para, texto):
        run = para.add_run()
        run.text = texto
        run.font.name = 'Book Antiqua'
        run.font.size = Pt(40)
        run.font.bold = True
        run.font.italic = True
        run.font.underline = True
        _add_shadow(run)
        return run

    def _run_label(para, texto, size=28):
        run = para.add_run()
        run.text = texto
        run.font.name = 'Book Antiqua'
        run.font.size = Pt(size)
        run.font.bold = True
        run.font.italic = True
        run.font.underline = True
        _add_shadow(run)
        return run

    def _run_value(para, texto, size=28):
        run = para.add_run()
        run.text = texto
        run.font.name = 'Book Antiqua'
        run.font.size = Pt(size)
        run.font.italic = True
        _add_shadow(run)
        return run

    def _clear_table_style(tbl_obj):
        # Elimina el estilo de tabla predeterminado (causa el fondo gris y quita los bordes)
        tblPr = tbl_obj._tbl.find(qn('a:tblPr'))
        if tblPr is None:
            tblPr = etree.SubElement(tbl_obj._tbl, qn('a:tblPr'))
        for attr in ('bandRow', 'bandCol', 'firstRow', 'firstCol', 'lastRow', 'lastCol'):
            tblPr.set(attr, '0')
        for el in tblPr.findall(qn('a:tableStyleId')):
            tblPr.remove(el)
        # GUID "No Style, No Grid" — tabla limpia sin tema
        etree.SubElement(tblPr, qn('a:tableStyleId')).text = '{2D5ABB26-0587-4C30-8999-92F81FD0307C}'

    def _set_borders(cell, w=19050):
        # Los bordes deben ir ANTES del fill en tcPr (orden OOXML)
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        for tag in ('lnL', 'lnR', 'lnT', 'lnB'):
            for ex in tcPr.findall(qn(f'a:{tag}')):
                tcPr.remove(ex)
        for i, tag in enumerate(('lnL', 'lnR', 'lnT', 'lnB')):
            ln = etree.Element(qn(f'a:{tag}'), attrib={'w': str(w), 'cap': 'flat', 'cmpd': 'sng'})
            sf = etree.SubElement(ln, qn('a:solidFill'))
            etree.SubElement(sf, qn('a:srgbClr'), val='000000')
            tcPr.insert(i, ln)   # insertar antes del fill

    def _ordinal(d):
        if 11 <= d <= 13:
            return f"{d}th"
        return f"{d}{['th','st','nd','rd','th'][min(d % 10, 4)]}"

    def _clean_grado(grado):
        import re
        _map = {'1':'1st','2':'2nd','3':'3rd','4':'4th',
                '5':'5th','6':'6th','7':'7th','8':'8th','9':'9th'}
        m = re.search(r'(\d+)', grado or '')
        if m:
            return _map.get(m.group(1), grado)
        if 'kinder' in (grado or '').lower():
            return 'Kinder'
        return grado

    # ── datos ─────────────────────────────────────────────────────────────────
    reporte  = get_object_or_404(ProgressReport, pk=pk)
    materias = reporte.materias_json or []
    fondo_path = '/home/admin2/techcare_project/system_proyect/conducta/static/conducta/img/plantilla.jpg'

    # ── slide widescreen 13.33" × 7.5" ───────────────────────────────────────
    prs = Presentation()
    prs.slide_width  = Emu(12192000)
    prs.slide_height = Emu(6858000)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_picture(fondo_path, 0, 0, width=prs.slide_width, height=prs.slide_height)

    # Constantes de layout
    LEFT_X = Inches(0.2)
    TAB_X  = Inches(4.7)
    LEFT_W = TAB_X - LEFT_X          # nombre envuelve exactamente al borde de la tabla
    TAB_W  = Inches(8.5)             # tabla más ancha; total 4.7+8.5=13.2" ≈ slide

    # ── TÍTULO (encima de la tabla, derecha) ──────────────────────────────────
    tb = slide.shapes.add_textbox(TAB_X, Inches(0.05), TAB_W, Inches(0.9))
    tf = tb.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    _run_titulo(p, 'Progress Report.')

    # ── WEEKS ─────────────────────────────────────────────────────────────────
    semana_str = (f"{_ordinal(reporte.semana_inicio.day)} to "
                  f"{_ordinal(reporte.semana_fin.day)} {reporte.semana_fin.strftime('%B')}")
    tb = slide.shapes.add_textbox(LEFT_X, Inches(0.1), LEFT_W, Inches(1.5))
    tf = tb.text_frame
    tf.clear()
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    _run_label(p, 'Weeks:')
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.LEFT
    _run_value(p2, semana_str)

    # ── GRADE ─────────────────────────────────────────────────────────────────
    tb = slide.shapes.add_textbox(LEFT_X, Inches(1.75), LEFT_W, Inches(0.75))
    tf = tb.text_frame
    tf.clear()
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    _run_value(p, f'Grade: {_clean_grado(reporte.grado)}')

    # ── NAME label + nombre alumno ────────────────────────────────────────────
    tb = slide.shapes.add_textbox(LEFT_X, Inches(2.6), LEFT_W, Inches(1.4))
    tf = tb.text_frame
    tf.clear()
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    _run_label(p, 'Name:')
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.LEFT
    rn = p2.add_run()
    rn.text = reporte.alumno_nombre
    rn.font.name = 'Book Antiqua'
    rn.font.size = Pt(20)
    rn.font.italic = True

    # ── TABLA ─────────────────────────────────────────────────────────────────
    num_rows = len(materias) + 1
    tbl_top  = Inches(0.95)
    tbl_h    = Inches(6.55)   # ocupa casi toda la altura

    tbl = slide.shapes.add_table(num_rows, 3, TAB_X, tbl_top, TAB_W, tbl_h).table
    _clear_table_style(tbl)

    # anchos de columna: ~24% / ~19% / ~57%
    tbl.columns[0].width = Inches(2.0)
    tbl.columns[1].width = Inches(1.7)
    tbl.columns[2].width = Inches(4.8)

    def _cell_style(cell, texto, bold=False, align=PP_ALIGN.CENTER):
        cell.text = texto
        _set_borders(cell)         # bordes ANTES del fill (orden correcto en OOXML)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(255, 255, 255)
        para = cell.text_frame.paragraphs[0]
        para.font.name  = 'Arial'
        para.font.size  = Pt(18)
        para.font.bold  = bold
        para.font.color.rgb = RGBColor(0, 0, 0)
        para.alignment  = align

    # cabecera
    for idx, hdr in enumerate(['Materia', 'Asignación', 'Comentario/Observación']):
        _cell_style(tbl.cell(0, idx), hdr, bold=True, align=PP_ALIGN.CENTER)

    # filas de materias
    for row, mat in enumerate(materias, start=1):
        _cell_style(tbl.cell(row, 0), mat.get('materia', ''),    bold=True,  align=PP_ALIGN.CENTER)
        _cell_style(tbl.cell(row, 1), mat.get('asignacion', ''), bold=False, align=PP_ALIGN.LEFT)
        _cell_style(tbl.cell(row, 2), mat.get('comentario', ''), bold=False, align=PP_ALIGN.LEFT)

    # ── descarga ──────────────────────────────────────────────────────────────
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation')
    filename = f'progress_{reporte.alumno_nombre.replace(" ", "_")}.pptx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    prs.save(response)
    return response


@login_required
def descargar_zip_reportes(request):
    """Genera un ZIP con todos los reportes (PDF + PPTX) para coordinadores y admin."""
    import zipfile
    from reportlab.lib.pagesizes import letter as rl_letter
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.units import mm as rl_mm
    from reportlab.lib import colors as rl_colors
    from pptx import Presentation as PPTXPres
    from pptx.util import Inches as PPTXInches, Pt as PPTXPt, Emu as PPTXEmu
    from pptx.enum.text import PP_ALIGN as PPTXAlign
    from pptx.dml.color import RGBColor as PPTXColor
    from pptx.oxml.ns import qn as pptx_qn
    from lxml import etree as pptx_etree

    # Solo coordinadores y superusuario
    es_coord = request.user.groups.filter(
        name__in=['coordinador_bilingue', 'coordinadores_colegio', 'coordinadores']
    ).exists()
    if not (request.user.is_superuser or es_coord):
        return HttpResponseForbidden()

    logo_path = os.path.join(settings.STATIC_ROOT, 'conducta/img/ana-transformed.png')
    fondo_path = '/home/admin2/techcare_project/system_proyect/conducta/static/conducta/img/plantilla.jpg'

    # ── generador PDF informativo ─────────────────────────────────────────────
    def _pdf_informativo(r):
        buf = io.BytesIO()
        w, h = rl_letter
        pdf = rl_canvas.Canvas(buf, pagesize=rl_letter)
        if os.path.exists(logo_path):
            pdf.drawImage(logo_path, x=(w-35*rl_mm)/2, y=h-40*rl_mm,
                          width=35*rl_mm, height=35*rl_mm, mask='auto')
        y = h - 52*rl_mm
        pdf.setFont('Helvetica-Bold', 16)
        pdf.drawCentredString(w/2, y, 'Nuevo Amanecer School' if r.area == 'bilingue' else 'C.E.M.N.G Nuevo Amanecer')
        y -= 14*rl_mm
        pdf.setFont('Helvetica', 13)
        pdf.drawCentredString(w/2, y, 'Reporte informativo')
        y -= 14*rl_mm

        def lv(x, yy, lbl, val, ls=11, vs=10):
            pdf.setFont('Helvetica-Bold', ls); pdf.drawString(x, yy, lbl)
            aw = pdf.stringWidth(lbl, 'Helvetica-Bold', ls)
            pdf.setFont('Helvetica', vs); pdf.drawString(x+aw+2, yy, val)

        lv(32*rl_mm, y, 'Nombre:', r.alumno_nombre)
        lv(118*rl_mm, y, 'Grado:', r.grado); y -= 8*rl_mm
        lv(32*rl_mm, y, 'Docente:', r.docente or '')
        lv(100*rl_mm, y, 'Fecha:', r.fecha.strftime('%d/%m/%Y') if r.fecha else ''); y -= 12*rl_mm
        pdf.setFont('Helvetica-Bold', 11); pdf.drawString(32*rl_mm, y, 'Comentario del Docente:'); y -= 8*rl_mm
        y = draw_paragraph(pdf, r.comentario or '-', x=38*rl_mm, y=y,
                            max_width=w-65*rl_mm, font='Helvetica', font_size=10, italic=True, leading=12)
        y -= 10*rl_mm
        if getattr(r, 'comentario_coordinador', None):
            pdf.setFont('Helvetica-Bold', 11); pdf.drawString(32*rl_mm, y, 'Comentario del Coordinador:'); y -= 8*rl_mm
            y = draw_paragraph(pdf, r.comentario_coordinador, x=38*rl_mm, y=y,
                                max_width=w-65*rl_mm, font='Helvetica', font_size=10, italic=True, leading=12)
            y -= 8*rl_mm
        y_f = min(y-15*rl_mm, 28*rl_mm); lf = 58*rl_mm
        pdf.setStrokeColor(rl_colors.black); pdf.setLineWidth(0.7)
        for xc, lbl, nom in [(15*rl_mm,'Firma:',r.docente or ''),
                              (78*rl_mm,'Firma:',getattr(r,'coordinador_firma','')),
                              (141*rl_mm,'Firma Pariente:','')]:
            pdf.setFont('Helvetica-Bold',10); pdf.drawString(xc, y_f+5*rl_mm, lbl)
            aw = pdf.stringWidth(lbl,'Helvetica-Bold',10)
            pdf.setFont('Helvetica',10); pdf.drawString(xc+aw+2, y_f+5*rl_mm, nom or '')
            pdf.line(xc, y_f, xc+lf, y_f)
        pdf.save(); buf.seek(0); return buf

    # ── generador PDF conductual ──────────────────────────────────────────────
    def _pdf_conductual(r):
        buf = io.BytesIO()
        w, h = rl_letter
        pdf = rl_canvas.Canvas(buf, pagesize=rl_letter)
        if os.path.exists(logo_path):
            pdf.drawImage(logo_path, x=(w-22*rl_mm)/2, y=h-28*rl_mm,
                          width=22*rl_mm, height=22*rl_mm, mask='auto')
        y = h - 33*rl_mm
        pdf.setFont('Helvetica-Bold', 16)
        pdf.drawCentredString(w/2, y, 'Nuevo Amanecer School' if getattr(r,'area',None)=='bilingue' else 'C.E.M.N.G Nuevo Amanecer')
        y -= 9*rl_mm; pdf.setFont('Helvetica',13)
        pdf.drawCentredString(w/2, y, 'Reporte conductual'); y -= 10*rl_mm

        def lv(x, yy, lbl, val, s=11):
            pdf.setFont('Helvetica-Bold',s); pdf.drawString(x,yy,lbl)
            aw=pdf.stringWidth(lbl,'Helvetica-Bold',s)
            pdf.setFont('Helvetica',s); pdf.drawString(x+aw+2,yy,val)

        lv(32*rl_mm,y,'Nombre:',r.alumno_nombre); y-=7*rl_mm
        lv(32*rl_mm,y,'Grado:',r.grado)
        lv(118*rl_mm,y,'Fecha:',r.fecha.strftime('%d/%m/%Y') if r.fecha else ''); y-=7*rl_mm
        lv(32*rl_mm,y,'Docente:',r.docente or ''); y-=9*rl_mm
        mw = w-65*rl_mm
        for tipo, lbl in [('incisos_leve','Leve'),('incisos_grave','Grave'),('incisos_muygrave','Muy Grave')]:
            incs = getattr(r,tipo).all()
            pdf.setFont('Helvetica-Bold',11); pdf.drawString(32*rl_mm,y,f'Incisos {lbl}:'); y-=6*rl_mm
            if incs:
                for i in incs:
                    y=draw_paragraph(pdf,i.descripcion,x=38*rl_mm,y=y,max_width=mw,
                                     font='Helvetica',font_size=10,bold=True,italic=True,leading=12)
            else:
                pdf.setFont('Helvetica-Oblique',10); pdf.drawString(38*rl_mm,y,'-'); y-=6*rl_mm
            y-=4*rl_mm
        pdf.setFont('Helvetica-Bold',11); pdf.drawString(32*rl_mm,y,'Comentario del Docente:'); y-=6*rl_mm
        y=draw_paragraph(pdf,r.comentario or '-',x=38*rl_mm,y=y,max_width=mw,
                          font='Helvetica',font_size=10,italic=True,leading=12); y-=7*rl_mm
        if getattr(r,'comentario_coordinador',None):
            pdf.setFont('Helvetica-Bold',11); pdf.drawString(32*rl_mm,y,'Comentario del Coordinador:'); y-=6*rl_mm
            y=draw_paragraph(pdf,r.comentario_coordinador,x=38*rl_mm,y=y,max_width=mw,
                              font='Helvetica',font_size=10,italic=True,leading=12); y-=6*rl_mm
        y_f=min(y-15*rl_mm,28*rl_mm); lf=58*rl_mm
        pdf.setStrokeColor(rl_colors.black); pdf.setLineWidth(0.7)
        for xc,lbl,nom in [(15*rl_mm,'Firma:',r.docente or ''),
                            (78*rl_mm,'Firma:',getattr(r,'coordinador_firma','') or ''),
                            (141*rl_mm,'Firma Pariente:','')]:
            pdf.setFont('Helvetica-Bold',10); pdf.drawString(xc,y_f+5*rl_mm,lbl)
            aw=pdf.stringWidth(lbl,'Helvetica-Bold',10)
            pdf.setFont('Helvetica',10); pdf.drawString(xc+aw+2,y_f+5*rl_mm,nom)
            pdf.line(xc,y_f,xc+lf,y_f)
        pdf.save(); buf.seek(0); return buf

    # ── generador PPTX progress ───────────────────────────────────────────────
    def _pptx_progress(r):
        def _shadow(run):
            rPr=run._r.get_or_add_rPr()
            for ex in rPr.findall(pptx_qn('a:effectLst')): rPr.remove(ex)
            ef=pptx_etree.SubElement(rPr,pptx_qn('a:effectLst'))
            os_=pptx_etree.SubElement(ef,pptx_qn('a:outerShdw'),attrib={'blurRad':'40000','dist':'23000','dir':'5400000','rotWithShape':'0'})
            cl=pptx_etree.SubElement(os_,pptx_qn('a:srgbClr'),val='000000')
            pptx_etree.SubElement(cl,pptx_qn('a:alpha'),val='40000')
        def _run(para,txt,size,bold=False,italic=False,underline=False,shadow=False):
            run=para.add_run(); run.text=txt
            run.font.name='Book Antiqua'; run.font.size=PPTXPt(size)
            run.font.bold=bold; run.font.italic=italic; run.font.underline=underline
            if shadow: _shadow(run)
            return run
        def _borders(cell,w=19050):
            tc=cell._tc; tcPr=tc.get_or_add_tcPr()
            for tag in ('lnL','lnR','lnT','lnB'):
                for ex in tcPr.findall(pptx_qn(f'a:{tag}')): tcPr.remove(ex)
            for i,tag in enumerate(('lnL','lnR','lnT','lnB')):
                ln=pptx_etree.Element(pptx_qn(f'a:{tag}'),attrib={'w':str(w),'cap':'flat','cmpd':'sng'})
                sf=pptx_etree.SubElement(ln,pptx_qn('a:solidFill'))
                pptx_etree.SubElement(sf,pptx_qn('a:srgbClr'),val='000000')
                tcPr.insert(i,ln)
        def _ordinal(d):
            if 11<=d<=13: return f'{d}th'
            return f'{d}{["th","st","nd","rd","th"][min(d%10,4)]}'
        def _clean_g(g):
            import re; m=re.search(r'(\d+)',g or '')
            mp={'1':'1st','2':'2nd','3':'3rd','4':'4th','5':'5th','6':'6th','7':'7th','8':'8th','9':'9th'}
            if m: return mp.get(m.group(1),g)
            return 'Kinder' if 'kinder' in (g or '').lower() else g

        prs=PPTXPres(); prs.slide_width=PPTXEmu(12192000); prs.slide_height=PPTXEmu(6858000)
        slide=prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_picture(fondo_path,0,0,width=prs.slide_width,height=prs.slide_height)
        LX=PPTXInches(0.2); TX=PPTXInches(4.7); LW=TX-LX; TW=PPTXInches(8.5)
        # título
        tb=slide.shapes.add_textbox(TX,PPTXInches(0.05),TW,PPTXInches(0.9))
        tf=tb.text_frame; tf.clear(); p=tf.paragraphs[0]; p.alignment=PPTXAlign.CENTER
        _run(p,'Progress Report.',40,bold=True,italic=True,underline=True,shadow=True)
        # weeks
        sem=f"{_ordinal(r.semana_inicio.day)} to {_ordinal(r.semana_fin.day)} {r.semana_fin.strftime('%B')}"
        tb=slide.shapes.add_textbox(LX,PPTXInches(0.1),LW,PPTXInches(1.5))
        tf=tb.text_frame; tf.clear(); tf.word_wrap=True
        p=tf.paragraphs[0]; p.alignment=PPTXAlign.LEFT
        _run(p,'Weeks:',28,bold=True,italic=True,underline=True,shadow=True)
        p2=tf.add_paragraph(); p2.alignment=PPTXAlign.LEFT
        _run(p2,sem,28,italic=True,shadow=True)
        # grade
        tb=slide.shapes.add_textbox(LX,PPTXInches(1.75),LW,PPTXInches(0.75))
        tf=tb.text_frame; tf.clear(); tf.word_wrap=True
        p=tf.paragraphs[0]; p.alignment=PPTXAlign.LEFT
        _run(p,f'Grade: {_clean_g(r.grado)}',28,italic=True,shadow=True)
        # name
        tb=slide.shapes.add_textbox(LX,PPTXInches(2.6),LW,PPTXInches(1.4))
        tf=tb.text_frame; tf.clear(); tf.word_wrap=True
        p=tf.paragraphs[0]; p.alignment=PPTXAlign.LEFT
        _run(p,'Name:',28,bold=True,italic=True,underline=True,shadow=True)
        p2=tf.add_paragraph(); p2.alignment=PPTXAlign.LEFT
        _run(p2,r.alumno_nombre,20,italic=True)
        # tabla
        mats=r.materias_json or []
        tbl=slide.shapes.add_table(len(mats)+1,3,TX,PPTXInches(0.95),TW,PPTXInches(6.55)).table
        tblPr=tbl._tbl.find(pptx_qn('a:tblPr'))
        if tblPr is None: tblPr=pptx_etree.SubElement(tbl._tbl,pptx_qn('a:tblPr'))
        for at in ('bandRow','bandCol','firstRow','firstCol','lastRow','lastCol'): tblPr.set(at,'0')
        for el in tblPr.findall(pptx_qn('a:tableStyleId')): tblPr.remove(el)
        pptx_etree.SubElement(tblPr,pptx_qn('a:tableStyleId')).text='{2D5ABB26-0587-4C30-8999-92F81FD0307C}'
        tbl.columns[0].width=PPTXInches(2.0); tbl.columns[1].width=PPTXInches(1.7); tbl.columns[2].width=PPTXInches(4.8)
        def _cs(cell,txt,bold=False,align=PPTXAlign.CENTER):
            cell.text=txt; _borders(cell)
            cell.fill.solid(); cell.fill.fore_color.rgb=PPTXColor(255,255,255)
            p=cell.text_frame.paragraphs[0]; p.font.name='Arial'
            p.font.size=PPTXPt(18); p.font.bold=bold
            p.font.color.rgb=PPTXColor(0,0,0); p.alignment=align
        for i,h_ in enumerate(['Materia','Asignación','Comentario/Observación']):
            _cs(tbl.cell(0,i),h_,bold=True)
        for row,mat in enumerate(mats,start=1):
            _cs(tbl.cell(row,0),mat.get('materia',''),bold=True,align=PPTXAlign.CENTER)
            _cs(tbl.cell(row,1),mat.get('asignacion',''),bold=False,align=PPTXAlign.LEFT)
            _cs(tbl.cell(row,2),mat.get('comentario',''),bold=False,align=PPTXAlign.LEFT)
        buf=io.BytesIO(); prs.save(buf); buf.seek(0); return buf

    # ── determinar scope según coordinador ───────────────────────────────────
    email = request.user.email
    if request.user.is_superuser:
        qs_info = ReporteInformativo.objects.all()
        qs_cond = ReporteConductual.objects.all()
        qs_prog = ProgressReport.objects.all()
    elif email == 'cvarela@ana-hn.org':
        _q = _q_for_coord('C1')
        qs_info = ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='academico').filter(_q)
        qs_cond = ReporteConductual.objects.filter(area='bilingue').filter(_q)
        qs_prog = ProgressReport.objects.none()
    elif email == 'druiz@ana-hn.org':
        _q = _q_for_coord('C2')
        qs_info = ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='academico').filter(_q)
        qs_cond = ReporteConductual.objects.filter(area='bilingue').filter(_q)
        qs_prog = ProgressReport.objects.none()
    elif email == 'ialcerro@ana-hn.org':
        _q = _q_for_coord('C3')
        qs_info = (
            ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='conductual') |
            ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='academico').filter(_q)
        ).distinct().order_by('-fecha')
        qs_cond = ReporteConductual.objects.filter(area='bilingue').filter(_q)
        qs_prog = ProgressReport.objects.none()
    elif email == 'jmartinez@ana-hn.org':
        _q = _q_for_coord('C4')
        qs_info = ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='academico').filter(_q)
        qs_cond = ReporteConductual.objects.filter(area='bilingue').filter(_q)
        qs_prog = ProgressReport.objects.all()
    elif email == 'coordinacion_bl@ana-hn.org':
        qs_info = ReporteInformativo.objects.none()
        qs_cond = ReporteConductual.objects.none()
        qs_prog = ProgressReport.objects.all()
    elif request.user.groups.filter(name='coordinadores_colegio').exists():
        qs_info = ReporteInformativo.objects.filter(area='colegio')
        qs_cond = ReporteConductual.objects.filter(area='colegio')
        qs_prog = ProgressReport.objects.none()
    else:
        qs_info = ReporteInformativo.objects.filter(area='bilingue')
        qs_cond = ReporteConductual.objects.filter(area='bilingue')
        qs_prog = ProgressReport.objects.all()

    # ── construir ZIP ─────────────────────────────────────────────────────────
    mem = io.BytesIO()
    fecha = timezone.now().strftime('%Y%m%d_%H%M')
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf:
        for r in qs_info.order_by('area', 'alumno_nombre'):
            try:
                nombre = r.alumno_nombre.replace(' ', '_')
                grado  = r.grado.replace(' ', '_').replace('/', '-')
                fname  = f'informativo_{nombre}_{grado}.pdf'
                zf.writestr(f'Informativos/{r.area.capitalize()}/{fname}',
                            _pdf_informativo(r).getvalue())
            except Exception:
                pass
        for r in qs_cond.prefetch_related(
                'incisos_leve', 'incisos_grave', 'incisos_muygrave'
        ).order_by('area', 'alumno_nombre'):
            try:
                nombre = r.alumno_nombre.replace(' ', '_')
                grado  = r.grado.replace(' ', '_').replace('/', '-')
                fname  = f'conductual_{nombre}_{grado}.pdf'
                zf.writestr(f'Conductuales/{r.area.capitalize()}/{fname}',
                            _pdf_conductual(r).getvalue())
            except Exception:
                pass
        for r in qs_prog.order_by('alumno_nombre'):
            try:
                nombre = r.alumno_nombre.replace(' ', '_')
                grado  = r.grado.replace(' ', '_').replace('/', '-')
                fname  = f'progress_{nombre}_{grado}.pptx'
                zf.writestr(f'ProgressReports/{fname}',
                            _pptx_progress(r).getvalue())
            except Exception:
                pass

    mem.seek(0)
    response = HttpResponse(mem.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="reportes_{fecha}.zip"'
    return response


@login_required
def descargar_pdf_conductual_3_strikes(request, pk):
    from .models import ReporteConductual
    reporte = get_object_or_404(ReporteConductual, pk=pk)

    # <--- hecho por claude code: regla corregida — el reporte 3 strikes solo se genera
    # cuando el alumno acumula 3 reportes del MISMO tipo (3 leve, 3 grave o 3 muy grave).
    # Antes tomaba cualquier 3 reportes mezclados, lo cual era incorrecto.
    todos = list(ReporteConductual.objects.filter(
        area=reporte.area,
        alumno_id=reporte.alumno_id
    ).prefetch_related('incisos_leve', 'incisos_grave', 'incisos_muygrave').order_by('fecha'))

    leves     = [r for r in todos if r.incisos_leve.exists() and not r.incisos_grave.exists() and not r.incisos_muygrave.exists()]
    graves    = [r for r in todos if r.incisos_grave.exists() and not r.incisos_muygrave.exists()]
    muy_graves = [r for r in todos if r.incisos_muygrave.exists()]

    reportes = None
    if len(leves) >= 3:
        reportes = leves[:3]
    elif len(graves) >= 3:
        reportes = graves[:3]
    elif len(muy_graves) >= 3:
        reportes = muy_graves[:3]

    if reportes is None:
        # <--- hecho por claude code: mensaje de error como alerta Bootstrap en lugar
        # de texto plano (que tenía encoding roto y se veía mal).
        html = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Sin reporte 3 strikes</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex align-items-center justify-content-center" style="min-height:100vh;">
  <div class="card shadow p-4" style="max-width:480px;width:100%;">
    <div class="alert alert-warning mb-3">
      <strong>&#9888; Sin reporte 3 strikes</strong><br>
      Este alumno aún no acumula 3 reportes conductuales del mismo tipo
      (3 leve, 3 grave o 3 muy grave).
    </div>
    <a href="javascript:history.back()" class="btn btn-secondary w-100">&larr; Volver</a>
  </div>
</body>
</html>"""
        return HttpResponse(html, status=400)

    buf = io.BytesIO()
    w, h = letter
    pdf = canvas.Canvas(buf, pagesize=letter)
    pdf.setTitle("reporte_conductual_3_strikes.pdf")

    # Logo centrado
    width_logo = 35 * mm
    height_logo = 35 * mm
    x_logo = (w - width_logo) / 2
    logo_path = os.path.join(settings.STATIC_ROOT, "conducta/img/ana-transformed.png")
    if os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            x=x_logo,
            y=h-40*mm,
            width=width_logo,
            height=height_logo,
            mask='auto'
        )
    y_actual = h - 47 * mm

    # Título
    pdf.setFont("Helvetica-Bold", 16)
    titulo = "Nuevo Amanecer School" if reporte.area == "bilingue" else "C.E.M.N.G Nuevo Amanecer"
    pdf.drawCentredString(w/2, y_actual, titulo)
    y_actual -= 12*mm
    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(w/2, y_actual, "Reporte conductual – 3 Strikes")
    y_actual -= 10*mm

    # --- CADA REPORTE ---
    for idx, rep in enumerate(reportes, 1):
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(32*mm, y_actual, f"Reporte #{idx} ({', '.join(['Leve' if rep.incisos_leve.exists() else '', 'Grave' if rep.incisos_grave.exists() else '', 'Muy Grave' if rep.incisos_muygrave.exists() else '']).replace(',,',',').strip(', ')})")
        y_actual -= 8*mm

        # Fila: Nombre/Grado/Docente/Fecha
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(32*mm, y_actual, "Nombre:")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(60*mm, y_actual, rep.alumno_nombre)

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(120*mm, y_actual, "Grado:")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(140*mm, y_actual, rep.grado)
        y_actual -= 6*mm

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(32*mm, y_actual, "Docente/Materia:")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(75*mm, y_actual, rep.docente)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(120*mm, y_actual, "Fecha:")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(140*mm, y_actual, rep.fecha.strftime('%d/%m/%Y'))
        y_actual -= 7*mm

        # Incisos (párrafo)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(32*mm, y_actual, "Inciso:")
        y_actual -= 6*mm

        incisos = [i.descripcion for i in rep.incisos_leve.all()] + [i.descripcion for i in rep.incisos_grave.all()] + [i.descripcion for i in rep.incisos_muygrave.all()]
        if incisos:
            text_obj = pdf.beginText(38*mm, y_actual)
            text_obj.setFont("Helvetica-BoldOblique", 10)
            wrap_len = 95  # Ajusta a gusto (número de caracteres por línea)
            for inciso in incisos:
                lines = [inciso[i:i+wrap_len] for i in range(0, len(inciso), wrap_len)]
                for ln in lines:
                    text_obj.textLine(ln)
                    y_actual -= 5*mm
            pdf.drawText(text_obj)
            y_actual = text_obj.getY() - 1*mm
        else:
            pdf.setFont("Helvetica", 10)
            pdf.drawString(38*mm, y_actual, "-")
            y_actual -= 5*mm

        # Descripción (Comentario)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(32*mm, y_actual, "Descripción:")
        y_actual -= 5*mm
        if rep.comentario:
            text_obj = pdf.beginText(38*mm, y_actual)
            text_obj.setFont("Helvetica-Oblique", 10)
            for line in rep.comentario.split("\n"):
                text_obj.textLine(line)
                y_actual -= 5*mm
            pdf.drawText(text_obj)
            y_actual = text_obj.getY() - 1*mm
        else:
            pdf.setFont("Helvetica", 10)
            pdf.drawString(38*mm, y_actual, "-")
            y_actual -= 5*mm

        # Espacio entre reportes
        y_actual -= 4*mm
        pdf.setStrokeColor(colors.grey)
        pdf.line(30*mm, y_actual, w-30*mm, y_actual)
        y_actual -= 8*mm

    # FIRMAS PARA LLENAR EN FÍSICO
    y_firmas = 20*mm
    x_firma = [34*mm, 91*mm, 146*mm]
    if reporte.area == "colegio":
        etiquetas = ["Firma Padre de Familia", "Firma del Docente/Orientación", "Firma de Consejería"]
    else:
        etiquetas = ["Firma Padre de Familia", "Firma del Docente", "Firma del Coordinador"]

    for i in range(3):
        pdf.setStrokeColor(colors.black)
        pdf.line(x_firma[i], y_firmas, x_firma[i]+42*mm, y_firmas)
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(x_firma[i]+21*mm, y_firmas-5*mm, etiquetas[i])

    pdf.save()
    buf.seek(0)
    grado_slug = reporte.grado.replace(' ', '_').replace('/', '-')
    nombre_archivo = f"3strikes_{reporte.alumno_nombre.replace(' ', '_')}_{grado_slug}.pdf"
    response = HttpResponse(buf, content_type="application/pdf")
    response['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'
    return response

_REDIRECT_COORD_BL = {
    'cvarela@ana-hn.org':         'dashboard_c1',
    'druiz@ana-hn.org':           'dashboard_c2',
    'ialcerro@ana-hn.org':        'dashboard_c3',
    'jmartinez@ana-hn.org':       'dashboard_c4',
    'coordinacion_bl@ana-hn.org': 'dashboard_coordi_bl',
}

#--------------  DASHBOARD COORDINADOR -----------------
@login_required
def dashboard_coordinador(request, area):
    if area == 'bilingue':
        destino = _REDIRECT_COORD_BL.get(request.user.email)
        if destino:
            return redirect(destino)

        # coordi_bl: solo ve Progress Reports
        if request.user.email == _EMAIL_COORDI_BL:
            contexto = {
                'area': area,
                'reportes_informativo': ReporteInformativo.objects.none(),
                'reportes_conductual':  ReporteConductual.objects.none(),
                'reportes_progress':    ProgressReport.objects.all(),
                'strikes':              {},
                'today':                timezone.now().strftime('%Y-%m-%d'),
            }
            return render(request, 'conducta/dashboard_coordinador.html', contexto)

        reportes_informativo = ReporteInformativo.objects.filter(area='bilingue')
        reportes_conductual  = ReporteConductual.objects.filter(area='bilingue')
        reportes_progress    = ProgressReport.objects.all()

    elif area == 'colegio':
        reportes_informativo = ReporteInformativo.objects.filter(area='colegio')
        reportes_conductual  = ReporteConductual.objects.filter(area='colegio')
        reportes_progress    = []
    else:
        return redirect('menu')

    strikes = {}
    qs = reportes_conductual.values('alumno_id').annotate(total=Count('id')).filter(total__gte=3)
    for row in qs:
        strikes[row['alumno_id']] = row['total']

    coord_nombres = {
        cfg.codigo: cfg.nombre
        for cfg in ConfiguracionCoordinador.objects.filter(area='bilingue', activo=True)
    }
    contexto = {
        'area': area,
        'reportes_informativo': reportes_informativo,
        'reportes_conductual':  reportes_conductual,
        'reportes_progress':    reportes_progress,
        'strikes':              strikes,
        'today':                timezone.now().strftime('%Y-%m-%d'),
        'coord_nombres':        coord_nombres,
    }
    return render(request, 'conducta/dashboard_coordinador.html', contexto)

def _docentes_de_coord(codigo):
    docentes = set()
    for md in MateriaDocenteBilingue.objects.filter(activo=True):
        codigos = [c.strip() for c in md.coordinador.split(',')]
        if codigo in codigos:
            docentes.add(md.docente)
    return list(docentes)

@login_required
def dashboard_c1(request):
    q = _q_for_coord('C1')
    qs_info = ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='academico').filter(q)
    qs_cond = ReporteConductual.objects.filter(area='bilingue').filter(q)
    qs_prog = ProgressReport.objects.all()
    strikes = {r['alumno_id']: r['total'] for r in qs_cond.values('alumno_id').annotate(total=Count('id')).filter(total__gte=3)}
    reportes_nuevos_bl = (
        ReporteInformativo.objects.filter(area='bilingue', estado='enviado').count() +
        ReporteConductual.objects.filter(area='bilingue', estado='enviado').count() +
        ProgressReport.objects.filter(estado='enviado').count()
    )
    return render(request, 'conducta/dashboard_coordinador.html', {
        'area': 'bilingue', 'reportes_informativo': qs_info,
        'reportes_conductual': qs_cond, 'reportes_progress': qs_prog,
        'strikes': strikes, 'today': timezone.now().strftime('%Y-%m-%d'),
        'coord_codigo': 'C1',
        'mostrar_reportes_nuevos': True, 'reportes_nuevos_bl': reportes_nuevos_bl,
    })

@login_required
def dashboard_c2(request):
    q = _q_for_coord('C2')
    qs_info = ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='academico').filter(q)
    qs_cond = ReporteConductual.objects.filter(area='bilingue').filter(q)
    qs_prog = ProgressReport.objects.all()
    strikes = {r['alumno_id']: r['total'] for r in qs_cond.values('alumno_id').annotate(total=Count('id')).filter(total__gte=3)}
    return render(request, 'conducta/dashboard_coordinador.html', {
        'area': 'bilingue', 'reportes_informativo': qs_info,
        'reportes_conductual': qs_cond, 'reportes_progress': qs_prog,
        'strikes': strikes, 'today': timezone.now().strftime('%Y-%m-%d'),
        'coord_codigo': 'C2',
    })

@login_required
def dashboard_c3(request):
    q = _q_for_coord('C3')
    qs_info = (
        ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='conductual') |
        ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='academico').filter(q)
    ).distinct().order_by('-fecha')
    qs_cond = ReporteConductual.objects.filter(area='bilingue').filter(q)
    qs_prog = ProgressReport.objects.all()
    strikes = {r['alumno_id']: r['total'] for r in qs_cond.values('alumno_id').annotate(total=Count('id')).filter(total__gte=3)}
    return render(request, 'conducta/dashboard_coordinador.html', {
        'area': 'bilingue', 'reportes_informativo': qs_info,
        'reportes_conductual': qs_cond, 'reportes_progress': qs_prog,
        'strikes': strikes, 'today': timezone.now().strftime('%Y-%m-%d'),
        'coord_codigo': 'C3',
    })

@login_required
def dashboard_c4(request):
    q = _q_for_coord('C4')
    qs_info = ReporteInformativo.objects.filter(area='bilingue', tipo_reporte='academico').filter(q)
    qs_cond = ReporteConductual.objects.filter(area='bilingue').filter(q)
    qs_prog = ProgressReport.objects.all()
    strikes = {r['alumno_id']: r['total'] for r in qs_cond.values('alumno_id').annotate(total=Count('id')).filter(total__gte=3)}
    return render(request, 'conducta/dashboard_coordinador.html', {
        'area': 'bilingue', 'reportes_informativo': qs_info,
        'reportes_conductual': qs_cond, 'reportes_progress': qs_prog,
        'strikes': strikes, 'today': timezone.now().strftime('%Y-%m-%d'),
        'coord_codigo': 'C4',
    })

@login_required
def dashboard_coordi_bl(request):
    reportes_nuevos_bl = (
        ReporteInformativo.objects.filter(area='bilingue', estado='enviado').count() +
        ReporteConductual.objects.filter(area='bilingue', estado='enviado').count() +
        ProgressReport.objects.filter(estado='enviado').count()
    )
    return render(request, 'conducta/dashboard_coordinador.html', {
        'area': 'bilingue',
        'reportes_informativo': ReporteInformativo.objects.none(),
        'reportes_conductual':  ReporteConductual.objects.none(),
        'reportes_progress':    ProgressReport.objects.all(),
        'strikes': {}, 'today': timezone.now().strftime('%Y-%m-%d'),
        'mostrar_reportes_nuevos': True, 'reportes_nuevos_bl': reportes_nuevos_bl,
    })

@login_required
def historial_alumno_coordinador(request, alumno_id):
    """
    Devuelve el historial de reportes (informativo, conductual, progress)
    para un alumno específico. Se usa en el modal del dashboard coordinador.
    """
    informativos = ReporteInformativo.objects.filter(alumno_id=alumno_id).order_by('-fecha')
    conductuales = ReporteConductual.objects.filter(alumno_id=alumno_id).order_by('-fecha')
    progress = ProgressReport.objects.filter(alumno_id=alumno_id).order_by('-fecha')
    context = {
        'informativos': informativos,
        'conductuales': conductuales,
        'progress': progress,
    }
    html = render_to_string('conducta/lista_reportes.html', context)
    return HttpResponse(html)

# ----------- EDITOR DE REPORTES ( SOLO COORDINADOR) -----------
def es_coordinador(user):
    return user.is_staff or user.groups.filter(name__icontains="coordinador").exists()


# Cambia estos según tu lógica o roles
COORDINADORES_BL = [
     "Mr. Martinez",
     "Miss Alcerro",
     "Mr. Ruiz",
    "Mrs. Varela"

]
COORDINADORES_COLEGIO = [
    "Profe. Licona", 
    "Profe. Felipe", 
    "Profe. Gabriela"
    ]


# ─────────────────────────────────────────────────────────────
# subir_evidencia  <--- hecho por claude code
# View que recibe el POST del modal de evidencias del dashboard
# coordinador. Solo coordinadores pueden subir evidencias (chequeo
# con es_coordinador). Según el 'tipo' que llega en el POST,
# asigna la FK correcta del EvidenciaReporte y redirige al
# dashboard del área correspondiente.
# ─────────────────────────────────────────────────────────────
@login_required
def subir_evidencia(request):
    # Solo coordinadores pueden subir evidencias
    if not es_coordinador(request.user):
        return HttpResponseForbidden("Solo coordinadores pueden subir evidencias.")

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        reporte_id = request.POST.get('reporte_id')
        imagen = request.FILES.get('imagen')
        comentario = request.POST.get('comentario', '')
        # <--- hecho por claude code: se recibe el titulo para identificar la evidencia
        titulo = request.POST.get('titulo', '')

        # Validar que lleguen todos los datos mínimos
        if not imagen or not tipo or not reporte_id:
            messages.error(request, "Faltan datos para subir la evidencia.")
            return redirect(request.META.get('HTTP_REFERER', 'dashboard_maestro'))

        # Asignar la FK correcta según el tipo de reporte
        if tipo == 'conductual':
            reporte = get_object_or_404(ReporteConductual, pk=reporte_id)
            total_evidencias = EvidenciaReporte.objects.filter(reporte_conductual=reporte).count()
            area = reporte.area
        elif tipo == 'informativo':
            reporte = get_object_or_404(ReporteInformativo, pk=reporte_id)
            total_evidencias = EvidenciaReporte.objects.filter(reporte_informativo=reporte).count()
            area = reporte.area
        elif tipo == 'progress':
            reporte = get_object_or_404(ProgressReport, pk=reporte_id)
            total_evidencias = EvidenciaReporte.objects.filter(reporte_progress=reporte).count()
            area = 'bilingue'
        else:
            messages.error(request, "Tipo de reporte inválido.")
            return redirect('dashboard_maestro')

        # Máximo 2 evidencias por reporte
        if total_evidencias >= 2:
            messages.error(request, "Este reporte ya tiene el máximo de 2 evidencias permitidas.")
            return redirect('dashboard_coordinador', area=area)

        # Crear y guardar la evidencia
        ev = EvidenciaReporte(
            tipo=tipo,
            imagen=imagen,
            titulo=titulo,
            comentario=comentario,
            subido_por=request.user
        )

        if tipo == 'conductual':
            ev.reporte_conductual = reporte
        elif tipo == 'informativo':
            ev.reporte_informativo = reporte
        elif tipo == 'progress':
            ev.reporte_progress = reporte

        ev.save()
        messages.success(request, "Evidencia subida correctamente.")
        return redirect('dashboard_coordinador', area=area)

    # Si alguien accede por GET, redirigir al inicio
    return redirect('dashboard_maestro')


@login_required
def eliminar_evidencia(request, pk):
    if not es_coordinador(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)
    ev = get_object_or_404(EvidenciaReporte, pk=pk)
    try:
        ev.imagen.delete(save=False)
    except Exception:
        pass
    ev.delete()
    return JsonResponse({'ok': True})


# ================= DIRECTORIO DE TELÉFONOS =================
@login_required
def directorio_telefonos(request):
    user = request.user
    is_admin     = user.is_superuser
    is_coord_bl  = user.groups.filter(name='coordinador_bilingue').exists()
    is_coord_col = user.groups.filter(name__in=['coordinadores_colegio', 'coordinador_colegio', 'coordinadores']).exists()

    if is_admin:
        areas  = "N'PrimariaBL', N'ColegioBL', N'PreescolarBL', N'Colegio', N'Bachillerato'"
        titulo = 'Todos los Alumnos'
        area_dashboard = 'bilingue'
    elif is_coord_bl:
        areas  = "N'PrimariaBL', N'ColegioBL', N'PreescolarBL'"
        titulo = 'Alumnos Bilingüe'
        area_dashboard = 'bilingue'
    elif is_coord_col:
        areas  = "N'Colegio', N'Bachillerato'"
        titulo = 'Alumnos Colegio'
        area_dashboard = 'colegio'
    else:
        areas  = "N''"
        titulo = ''
        area_dashboard = 'bilingue'

    sql = f"""
      SELECT
        ISNULL(d.Apellido1,'')
          + CASE WHEN d.Apellido2 IS NOT NULL AND d.Apellido2 <> '' THEN ' ' + d.Apellido2 ELSE '' END
          + ', '
          + ISNULL(d.Nombre1,'')
          + CASE WHEN d.Nombre2 IS NOT NULL AND d.Nombre2 <> '' THEN ' ' + d.Nombre2 ELSE '' END AS Nombre,
        da.Descripcion AS Area,
        c.CrsoNumero,
        c.GrupoNumero,
        ISNULL(d.Tel1, '') AS Tel1,
        ISNULL(d.Tel2, '') AS Tel2
      FROM dbo.tblPrsDtosGen AS d
      JOIN dbo.tblPrsTipo           AS t  ON d.PersonaID = t.PersonaID
      JOIN dbo.tblEdcArea           AS a  ON t.IngrEgrID  = a.IngrEgrID
      JOIN dbo.tblEdcEjecCrso       AS ec ON a.AreaID     = ec.AreaID
      JOIN dbo.tblEdcCrso           AS c  ON ec.CrsoID    = c.CrsoID
      JOIN dbo.tblEdcDescripAreaEdc AS da ON a.DescrAreaEdcID = da.DescrAreaEdcID
      WHERE d.Alum = 1
        AND DATEPART(yy, c.FechaInicio) = DATEPART(yyyy, GETDATE())
        AND da.Descripcion IN ({areas})
        AND ec.Desertor    = 0
        AND ec.TrasladoPer = 0
      ORDER BY da.Descripcion, c.CrsoNumero, c.GrupoNumero, Nombre
    """

    import re as _re

    def _moviles(campo1, campo2):
        # Extrae (numero_8_digitos, label_pariente) de un campo de texto.
        # Soporta formatos como "9876-5217 mamá", "8963-1182 papá", "9876/8765".
        def _extraer(texto):
            resultado = []
            patron = r'(?:504[-\s]?)?(\d{4})[-\s./]?(\d{4})\s*([a-zA-ZÀ-ɏ]*)'
            for m in _re.finditer(patron, texto or ''):
                num = m.group(1) + m.group(2)
                label = m.group(3).strip().lower()
                if len(num) == 8 and not num.startswith('2'):
                    resultado.append((num, label))
            return resultado

        vistos = set()
        resultado = []
        for num, label in _extraer(campo1) + _extraer(campo2):
            if num not in vistos:
                vistos.add(num)
                resultado.append({
                    'num':   f'{num[:4]}-{num[4:]}',
                    'wa':    f'https://wa.me/504{num}',
                    'label': label,
                })
        return resultado

    alumnos = []
    try:
        with connections['padres_sqlserver'].cursor() as cursor:
            cursor.execute(sql)
            for nombre, area, crso, grupo, tel1, tel2 in cursor.fetchall():
                moviles = _moviles(tel1.strip(), tel2.strip())
                alumnos.append({
                    'nombre':  nombre.strip(),
                    'grado':   f'{area} {crso}-{grupo}',
                    'moviles': moviles,
                })
    except Exception:
        alumnos = []

    return render(request, 'conducta/directorio_telefonos.html', {
        'alumnos':         alumnos,
        'total':           len(alumnos),
        'titulo':          titulo,
        'area_dashboard':  area_dashboard,
    })

