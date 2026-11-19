import io
import os
import datetime
import logging
from functools import wraps as _wraps
from xml.sax.saxutils import escape as _xml_escape

from django.shortcuts           import render, redirect, get_object_or_404
from django.conf                import settings
from django.urls                import reverse
from django.contrib.auth.decorators import login_required
from django.core.exceptions     import PermissionDenied
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST
from django.core.mail           import EmailMessage
from django.http                import HttpResponse, JsonResponse
from django.contrib.staticfiles import finders
from django.db.models           import Sum, Q
from django.db                  import connections, transaction
from django.utils.html          import escape as _html_escape

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Frame, Table, TableStyle
from reportlab.lib.pagesizes import letter

from reportlab.lib.styles import ParagraphStyle

from .models import (
    AtencionMedica,
    InventarioMedicamento,
    UsoMedicamento,
    TblPrsDtosGen,
    Grado,
)
from .forms  import (
    AtencionMedicaForm,
    InventarioMedicamentoForm,
    UsoMedicamentoForm,
)

_log = logging.getLogger(__name__)


# ================= CANDADO DEL MÓDULO =================
# <--- hecho por claude code (seguridad 05-nov-2026): candado por GRUPO con el MISMO criterio que el menú (sidebar nav_enfermeria = superusuario/enfermeria; sección Coordinador BL y show_enfermeria del Panel = coordinador_bilingue/coordinador_bl/coord_progress_bl). Antes bastaba la sesión: cualquier maestro leía las atenciones médicas de los menores.
GRUPOS_ENFERMERIA = ('enfermeria', 'coordinador_bilingue', 'coordinador_bl', 'coord_progress_bl')


def puede_enfermeria(user):
    """True si el usuario puede usar el módulo: superusuario o alguno de GRUPOS_ENFERMERIA."""
    return bool(user is not None and user.is_authenticated and (
        user.is_superuser or user.groups.filter(name__in=GRUPOS_ENFERMERIA).exists()))


def _enfermeria_required(view):
    """@login_required (anónimo → login) + candado por grupo (sin grupo → 403)."""
    @_wraps(view)
    @login_required
    def _w(request, *args, **kwargs):
        if puede_enfermeria(request.user):
            return view(request, *args, **kwargs)
        raise PermissionDenied('No tiene acceso al módulo de Enfermería.')
    return _w


@_enfermeria_required
def enfermeria_dashboard(request):
    # <--- hecho por claude code (04-nov-2026): 2 KPIs reales para el tile destacado (Opción B)
    from django.utils import timezone
    hoy = timezone.now().date()
    ctx = {
        'kpi_atenciones_hoy': AtencionMedica.objects.filter(fecha_hora__date=hoy).count(),
        'kpi_medicamentos': InventarioMedicamento.objects.count(),
    }
    return render(request, 'enfermeria/dashboard.html', ctx)


# ================= ALUMNOS (SQL Server, solo lectura) =================
# Alumnos BL activos del año en curso: la lista del formulario de atención.
# <--- hecho por claude code (seguridad 05-nov-2026): trae Email/Email2/Email3 por separado para validar en el servidor a quién se manda la ficha (antes solo el primero, para autollenar).
_SQL_ALUMNOS_BL = """
  SELECT
    d.PersonaID,
    ISNULL(d.Nombre1,'')
      + CASE WHEN d.Nombre2 IS NOT NULL AND d.Nombre2 <> '' THEN ' ' + d.Nombre2 ELSE '' END
      + ' ' +
    ISNULL(d.Apellido1,'')
      + CASE WHEN d.Apellido2 IS NOT NULL AND d.Apellido2 <> '' THEN ' ' + d.Apellido2 ELSE '' END
      AS NombreCompl,
    da.Descripcion    AS AreaDesc,
    c.CrsoNumero,
    c.GrupoNumero,
    d.Email,
    d.Email2,
    d.Email3
  FROM dbo.tblPrsDtosGen AS d
  JOIN dbo.tblPrsTipo           AS t  ON d.PersonaID = t.PersonaID
  JOIN dbo.tblEdcArea           AS a  ON t.IngrEgrID  = a.IngrEgrID
  JOIN dbo.tblEdcEjecCrso       AS ec ON a.AreaID     = ec.AreaID
  JOIN dbo.tblEdcCrso           AS c  ON ec.CrsoID     = c.CrsoID
  JOIN dbo.tblEdcDescripAreaEdc AS da ON a.DescrAreaEdcID = da.DescrAreaEdcID
  WHERE d.Alum = 1
    AND DATEPART(yy, c.FechaInicio) = DATEPART(yyyy, GETDATE())
    AND da.Descripcion IN (N'PrimariaBL', N'ColegioBL', N'PreescolarBL')
    AND ec.Desertor    = 0
    AND ec.TrasladoPer = 0
  ORDER BY
    da.Descripcion,
    c.CrsoNumero,
    c.GrupoNumero,
    NombreCompl
"""


def _alumnos_bl():
    """[{id, label, grado, correos}] de los alumnos BL activos del año (solo lectura)."""
    with connections['padres_sqlserver'].cursor() as cursor:
        cursor.execute(_SQL_ALUMNOS_BL)
        filas = cursor.fetchall()
    alumnos = []
    for pid, nombre, area, crso, grupo, e1, e2, e3 in filas:
        correos = []
        for e in (e1, e2, e3):
            e = (e or '').strip()
            if e and e.lower() not in [c.lower() for c in correos]:
                correos.append(e)
        alumnos.append({
            'id':      pid,
            'label':   (nombre or '').strip(),
            'grado':   f"{area} {crso}-{grupo}",
            'correos': correos,   # el primero es el que se propone al elegir al alumno
        })
    return alumnos


def _correo_registrado(email, correos):
    """El correo registrado del alumno (tal como está guardado) que coincide con `email` sin
    distinguir mayúsculas, o '' si no es uno de sus correos registrados."""
    e = (email or '').strip().lower()
    if not e:
        return ''
    for c in correos:
        if (c or '').strip().lower() == e:
            return (c or '').strip()
    return ''


# ================= FICHA EN PDF Y CORREO =================
def _pdf_atencion(rec):
    """Ficha de atención médica en PDF (bytes)."""
    # <--- hecho por claude code (seguridad 05-nov-2026): los textos del usuario van ESCAPADOS en el Paragraph de reportlab; sin escapar, un motivo con <img src="http://…"/> hacía que el servidor pidiera esa URL o leyera un archivo local (SSRF) y un "<" o "&" suelto rompía el PDF con 500.
    e = _xml_escape
    buf = io.BytesIO()
    w, h = letter   # carta
    pdf = canvas.Canvas(buf, pagesize=letter)
    pdf.setTitle(f"ficha_de_atencion_{rec.estudiante.replace(' ', '_')}")

    # 2) Fondo claro
    pdf.setFillColor(colors.HexColor("#f8f9fa"))
    pdf.rect(0, 0, w, h, fill=1, stroke=0)

    # 3) Encabezado informativo
    pdf.setFont("Helvetica-Oblique", 12)
    pdf.setFillColor(colors.darkgray)
    pdf.drawCentredString(
        w/2,
        h - 15*mm,
        "Este es un mensaje de nuestro departamento de enfermería"
    )

    # 4) Título principal
    pdf.setFont("Helvetica-Bold", 20)
    pdf.setFillColor(colors.black)
    pdf.drawCentredString(
        w/2,
        h - 30*mm,
        "Ficha de Atención Médica"
    )

    # 5) Párrafo informativo con negritas
    texto = f"""
        Estimado padre / madre de familia:<br/><br/>
        El motivo de la ficha es para notificarle que su hij@ <b>{e(rec.estudiante)}</b>
        del grado <b>{e(rec.grado.nombre)}</b> fue atendido el día
        <b>{rec.fecha_hora.strftime('%d/%m/%Y')}</b> a las
        <b>{rec.fecha_hora.strftime('%H:%M')}</b> por el coordinador
        <b>{e(rec.atendido_por.nombre)}</b>, ya que no se sentía bien y presentaba:
        <b>{e(rec.motivo)}</b>. Se le trató con: <b>{e(rec.tratamiento)}</b>.
    """
    style = ParagraphStyle(
        'texto_principal',
        fontName='Helvetica',
        fontSize=12,
        leading=18,  # más espacio entre líneas
        textColor=colors.black,
    )
    paragraph = Paragraph(texto, style)
    ancho_texto = w - 40*mm
    _, alto_parrafo = paragraph.wrap(ancho_texto, h)

    # Colocar párrafo con separación extra
    y_parrafo = (h - 30*mm) - 15*mm - alto_parrafo
    paragraph.drawOn(pdf, 20*mm, y_parrafo)

    # 6) Subtítulo de la tabla
    y_subt = y_parrafo - 15*mm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(
        w/2,
        y_subt,
        "Detalle de la atención brindada"
    )

    # 7) Tabla con datos (celdas de texto plano: reportlab no interpreta marcas aquí)
    datos = [
        ["Estudiante:",   rec.estudiante],
        ["Grado:",        rec.grado.nombre],
        ["Fecha y Hora:", rec.fecha_hora.strftime("%d-%m-%Y %H:%M")],
        ["Motivo:",       rec.motivo],
        ["Tratamiento:",  rec.tratamiento],
    ]
    tabla = Table(datos, colWidths=[50*mm, 120*mm])
    tabla.setStyle(TableStyle([
        ('GRID',          (0,0), (-1,-1), 0.25, colors.grey),
        ('FONTSIZE',      (0,0), (-1,-1), 12),
        ('FONTNAME',      (0,0), (-1,-1), 'Helvetica'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    _, alto_tabla = tabla.wrap(ancho_texto, h)

    # Dibujar tabla con separación
    y_tabla_top = y_subt - 15*mm
    tabla.drawOn(pdf, 20*mm, y_tabla_top - alto_tabla)

    # 8) Línea de firma con etiqueta "Firma" y nombre centrado
    y_base  = y_tabla_top - alto_tabla
    y_linea = y_base - 30*mm
    largo   = 80 * mm
    x0      = (w/2) - (largo/2)
    x1      = x0 + largo

    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(0.5)
    pdf.line(x0, y_linea, x1, y_linea)

    pdf.setFont("Helvetica-Bold", 12)
    # Etiqueta "Firma" a la izquierda de la línea
    pdf.drawString(x0, y_linea + 5*mm, "Firma:")
    # Nombre del atendido por centrado sobre la línea
    pdf.drawCentredString(w/2, y_linea + 5*mm, rec.atendido_por.nombre)

    # 9) Finalizar
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def _textos_correo(atencion):
    """(asunto, cuerpo HTML) FIJOS del correo de la ficha."""
    # <--- hecho por claude code (seguridad 05-nov-2026): asunto y cuerpo los fija el servidor (antes enviar_correo los tomaba del POST: cualquiera mandaba HTML libre con el dominio de la escuela).
    asunto = f'Ficha médica de {atencion.estudiante}'
    cuerpo = (f'Estimado/a padre/madre de {_html_escape(atencion.estudiante)},<br><br>'
              'Adjuntamos la ficha médica de la atención registrada.<br><br>Saludos.')
    return asunto, cuerpo


# <--- hecho por claude code: envía la ficha médica en PDF al correo indicado, con copia fija a enfermeria@ana-hn.org y a los usuarios con el toggle de enfermería; devuelve True/False y no lanza excepciones (el guardado no debe romperse por un fallo de correo).
# <--- hecho por claude code (seguridad 05-nov-2026): aquí había un @login_required que en realidad le tocaba a atencion_form (quedó separado por estos comentarios) y la vista respondía SIN SESIÓN con el padrón de alumnos, los correos de los padres y las atenciones médicas.
# <--- hecho por claude code (seguridad 05-nov-2026): el error SMTP ya no vuelve al navegador (va al log de Apache); quien llama valida ANTES que el destino sea un correo registrado del alumno.
def _enviar_ficha_por_correo(atencion, email_destino):
    try:
        from accounts.models import DestinatarioEmail
        _FIJO_ENF = 'enfermeria@ana-hn.org'
        extras = list(DestinatarioEmail.objects.filter(enfermeria=True)
                      .exclude(user__email='').values_list('user__email', flat=True))
        cc_list = list({_FIJO_ENF} | set(extras) - {email_destino})

        asunto, cuerpo = _textos_correo(atencion)
        correo = EmailMessage(
            subject=asunto, body=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_destino], cc=cc_list)
        correo.content_subtype = 'html'
        correo.attach(f'ficha_{atencion.pk}.pdf', _pdf_atencion(atencion), 'application/pdf')
        correo.send(fail_silently=False)
        return True
    except Exception:
        _log.exception('Enfermería: no se pudo enviar la ficha de la atención %s', atencion.pk)
        return False


# ================= ATENCIÓN MÉDICA =================
@_enfermeria_required  # <--- hecho por claude code (seguridad 05-nov-2026): antes solo @login_required (y hasta hoy, ni eso)
def atencion_form(request):
    # <--- hecho por claude code (seguridad 05-nov-2026): ?delete=<pk> YA NO BORRA (era un GET sin CSRF ni confirmación en el servidor); el borrado es POST a atencion_eliminar. ?edit solo acepta dígitos ASCII 0-9 (un texto daba 500, y con isdigit() a secas también '²' o '¹²').
    edit_id = request.GET.get('edit') or ''
    if not (edit_id.isascii() and edit_id.isdigit()):
        edit_id = ''

    # 1) Alumnos BL del año (SQL Server)
    students = _alumnos_bl()
    alumnos_por_id = {str(s['id']): s for s in students}

    # 2) Si es POST, procesamos
    instancia = get_object_or_404(AtencionMedica, pk=edit_id) if edit_id else None
    if request.method == 'POST':
        # 2a) el alumno tiene que ser uno de la lista (antes se aceptaba cualquier PersonaID)
        persona_id = (request.POST.get('estudiante') or '').strip()
        alumno = alumnos_por_id.get(persona_id)

        # 2b) cloneamos el POST y eliminamos esos dos campos
        post_data = request.POST.copy()
        post_data.pop('estudiante', None)
        post_data.pop('grado', None)

        form = AtencionMedicaForm(post_data, instance=instancia)
        if persona_id and alumno is None:
            form.add_error(None, 'El alumno seleccionado no es válido: elígelo de la lista.')
        elif not persona_id and instancia is None:
            form.add_error(None, 'Selecciona un alumno de la lista.')

        if form.is_valid():
            obj = form.save(commit=False)

            if alumno is not None:
                # 2c) nombre completo desde la ficha de la persona (igual que antes)
                try:
                    persona = TblPrsDtosGen.objects.using('padres_sqlserver') \
                                                   .get(PersonaID=alumno['id'])
                    partes = filter(None, (
                        persona.Nombre1,   persona.Nombre2,
                        persona.Apellido1, persona.Apellido2,
                    ))
                    obj.estudiante = " ".join(partes)
                except TblPrsDtosGen.DoesNotExist:
                    obj.estudiante = alumno['label']

                # 2d) el grado sale del SERVIDOR (antes del POST: cualquier texto creaba un Grado);
                # al editar sin cambiar el grado se conserva el del registro, como antes.
                grado_txt = alumno['grado']
                if (instancia is not None and instancia.grado_id
                        and request.POST.get('grado') == instancia.grado.nombre):
                    grado_txt = instancia.grado.nombre
                obj.grado, _ = Grado.objects.get_or_create(nombre=grado_txt)

            # <--- hecho por claude code (seguridad 05-nov-2026): los campos de auditoría los pone el servidor (el formulario ya no los acepta del POST; antes los dejaba en blanco en cada guardado).
            if instancia is None:
                obj.creado_por = request.user
            obj.modificado_por = request.user
            obj.save()
            form.save_m2m()

            # <--- hecho por claude code: el correo se envía AL GUARDAR (antes era un botón aparte); si se eligió un correo se manda la ficha en PDF, si se deja vacío solo se guarda, y el guardado nunca falla por un problema de correo.
            # <--- hecho por claude code (seguridad 05-nov-2026): solo a los correos REGISTRADOS del alumno (Email/Email2/Email3); antes cualquier dirección = relay de correo con el dominio de la escuela.
            email_post = (request.POST.get('email') or '').strip()
            email_destino = _correo_registrado(email_post, alumno['correos'] if alumno else [])
            if not email_post:
                msg = 'Ficha guardada correctamente.'
            elif not email_destino:
                msg = ('Ficha guardada, pero el correo no se envió: la ficha solo se envía a los '
                       'correos registrados del alumno en el sistema académico.')
            elif _enviar_ficha_por_correo(obj, email_destino):
                msg = f'Ficha guardada y enviada a {email_destino}.'
            else:
                msg = 'Ficha guardada, pero el correo no se pudo enviar. Intenta de nuevo más tarde.'
            request.session['mensaje_exito'] = msg
            return redirect('enfermeria:atencion_form')
    else:
        form = AtencionMedicaForm(instance=instancia)

    # 3) Finalmente rendereamos
    registros = AtencionMedica.objects.select_related('grado', 'atendido_por').order_by('-fecha_hora')
    year      = datetime.datetime.now().year
    contexto  = {
        'form':          form,
        'records':       registros,
        'edit_id':       edit_id,
        'year':          year,
        'students':      students,
        'mensaje_exito': request.session.pop('mensaje_exito', None),
    }
    return render(request, 'enfermeria/atencion_form.html', contexto)


# <--- hecho por claude code (seguridad 05-nov-2026): borrar una atención es POST (CSRF) + candado del módulo; antes era GET ?delete=<id> en atencion_form.
@_enfermeria_required
@require_POST
def atencion_eliminar(request, pk):
    rec = get_object_or_404(AtencionMedica, pk=pk)
    # <--- hecho por claude code (09-nov-2026, ISO 27001 · registro): queda en la bitácora de seguridad QUIÉN borró
    # qué atención (solo el id y la fecha; nunca datos médicos). simple_history también guarda el registro borrado.
    from core.seguridad_eventos import evento
    evento('enfermeria_atencion_eliminada', request, objetivo='AtencionMedica#%s' % rec.pk,
           fecha_atencion=getattr(rec, 'fecha_hora', None))
    rec.delete()
    request.session['mensaje_exito'] = 'Atención eliminada.'
    return redirect('enfermeria:atencion_form')


# <--- hecho por claude code (seguridad 05-nov-2026): candado del módulo (antes cualquier sesión bajaba la ficha de cualquier menor por pk) y SAMEORIGIN en vez de xframe_options_exempt: solo la incrusta la vista previa de enviar_correo (mismo sitio).
@xframe_options_sameorigin
@_enfermeria_required
def atencion_download_pdf(request, pk):
    rec = get_object_or_404(AtencionMedica.objects.select_related('grado', 'atendido_por'), pk=pk)
    return HttpResponse(_pdf_atencion(rec), content_type='application/pdf')


# <--- hecho por claude code (seguridad 05-nov-2026): candado del módulo; destino SOLO entre los correos registrados del alumno de ESTA atención (antes el select traía el padrón completo de alumnos con correos y teléfonos), asunto/cuerpo fijos y sin error SMTP crudo.
@_enfermeria_required
def enviar_correo(request, atencion_id):
    atencion = get_object_or_404(AtencionMedica, pk=atencion_id)
    pdf_url  = reverse('enfermeria:atencion_pdf', args=[atencion.pk])
    asunto, _cuerpo = _textos_correo(atencion)
    mensaje = (f"Estimado/a padre/madre de {atencion.estudiante}:\n\n"
               "Adjuntamos la ficha médica de la atención registrada.\n\nSaludos.")

    # correos registrados del alumno (mismo criterio de nombre que preselecciona al alumno al editar)
    correos = []
    for s in _alumnos_bl():
        if s['label'] == atencion.estudiante:
            for c in s['correos']:
                if c.lower() not in [x.lower() for x in correos]:
                    correos.append(c)

    error_msg = None
    if request.method == 'POST':
        email_destino = _correo_registrado(request.POST.get('email'), correos)
        if not email_destino:
            error_msg = 'Elige uno de los correos registrados del alumno en el sistema académico.'
        elif _enviar_ficha_por_correo(atencion, email_destino):
            request.session['mensaje_exito'] = f'Ficha enviada a {email_destino}.'
            return redirect('enfermeria:atencion_form')
        else:
            error_msg = 'No se pudo enviar el correo. Intenta de nuevo más tarde.'

    return render(request, 'enfermeria/enviar_correo.html', {
        'atencion':  atencion,
        'correos':   correos,
        'pdf_url':   pdf_url,
        'asunto':    asunto,
        'mensaje':   mensaje,
        'error_msg': error_msg,
    })

# ================= INVENTARIO MEDICAMENTOS =================
# <--- hecho por claude code (seguridad 05-nov-2026): todo el inventario con el candado del módulo (antes solo la sesión) y las escrituras solo por POST.
@_enfermeria_required
def inventario_list(request):
    items = InventarioMedicamento.objects.order_by('-fecha_ingreso')
    year = datetime.datetime.now().year
    return render(request, 'enfermeria/inventario_list.html', {
        'items': items,
        'year':  year,
        # <--- hecho por claude code (seguridad 05-nov-2026): el aviso se consume aquí (antes se leía sin sacarlo de la sesión y, ahora que la Atención pinta sus avisos, aparecía ahí de rebote)
        'mensaje_exito': request.session.pop('mensaje_exito', None),
    })

@_enfermeria_required
def inventario_create(request):
    form = InventarioMedicamentoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.modificado_por = request.user
        item.save()
        request.session['mensaje_exito'] = 'Medicamento agregado correctamente'
        return redirect('enfermeria:inventario_list')
    year = datetime.datetime.now().year
    return render(request, 'enfermeria/inventario_form.html', {
        'form':  form,
        'title': 'Agregar Medicamento',
        'year':  year,
    })

@_enfermeria_required
def inventario_edit_cantidad(request, pk):
    item = get_object_or_404(InventarioMedicamento, pk=pk)
    form = InventarioMedicamentoForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.modificado_por = request.user
        item.save()
        request.session['mensaje_exito'] = 'Cantidad actualizada correctamente'
        return redirect('enfermeria:inventario_list')
    year = datetime.datetime.now().year
    return render(request, 'enfermeria/inventario_form.html', {
        'form':  form,
        'title': f'Editar Medicamento – {item.nombre}',
        'year':  year,
    })

@_enfermeria_required
def uso_create(request):
    form = UsoMedicamentoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        uso = form.save(commit=False)
        # <--- hecho por claude code (seguridad 05-nov-2026): el descuento de existencias va en transaction.atomic() con select_for_update; antes dos registros simultáneos leían el mismo saldo y uno se perdía (o el saldo quedaba por debajo de lo usado).
        with transaction.atomic():
            med = InventarioMedicamento.objects.select_for_update().get(pk=uso.medicamento_id)
            alcanza = uso.cantidad_usada <= med.cantidad_existente
            if alcanza:
                med.cantidad_existente -= uso.cantidad_usada
                med.save()
                uso.medicamento = med
                uso.save()
        if alcanza:
            request.session['mensaje_exito'] = 'Uso registrado correctamente'
            return redirect('enfermeria:atencion_form')
        form.add_error('cantidad_usada', 'Cantidad excede lo disponible.')
    year = datetime.datetime.now().year
    return render(request, 'enfermeria/uso_form.html', {
        'form':  form,
        'title': 'Registrar Uso de Medicamento',
        'year':  year,
    })

@_enfermeria_required
def inventario_pdf(request, pk):
    med = get_object_or_404(InventarioMedicamento, pk=pk)
    usos = med.usos.order_by('-fecha_uso')
    total_usado = usos.aggregate(total=Sum('cantidad_usada'))['total'] or 0

    buf = io.BytesIO()
    w, h = 210 * mm, 297 * mm
    pdf = canvas.Canvas(buf, pagesize=(w, h))
    pdf.setTitle(f"Medicamento_{med.pk}")
    pdf.setFillColor(colors.HexColor("#f8f9fa"))
    pdf.rect(0, 0, w, h, fill=1)

    logo = finders.find('accounts/img/ana-transformed.png')
    if logo:
        pdf.drawImage(logo, 15*mm, h-45*mm, width=30*mm, height=30*mm)

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(w/2, h-25*mm, "Reporte de Medicamento")

    y = h-60*mm
    for label, val in [
        ("Nombre:",           med.nombre),
        ("Proveedor:",        med.proveedor.nombre),
        ("Presentación:",     med.presentacion.nombre if med.presentacion else "—"),
        ("Fecha de Ingreso:", med.fecha_ingreso.strftime("%d-%m-%Y")),
        ("Disponible:",       med.cantidad_existente),
        ("Total Usado:",      total_usado),
        ("Modificado por:",   med.modificado_por.username if med.modificado_por else "—"),
    ]:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(20*mm, y, label)
        pdf.setFont("Helvetica", 12)
        pdf.drawString(65*mm, y, str(val))
        y -= 10*mm

    pdf.showPage()
    pdf.save()
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type='application/pdf')

@_enfermeria_required
def historial_uso(request, pk):
    med = get_object_or_404(InventarioMedicamento, pk=pk)
    usos = med.usos.order_by('-fecha_uso')
    return render(request, 'enfermeria/historial_uso.html', {
        'medicamento': med,
        'usos':        usos,
    })


# ================= DIRECTORIO DE TELÉFONOS =================
# <--- hecho por claude code (10-nov-2026): hay UN solo Directorio, el de /conducta/directorio/ (mismo alcance por
# grupo: superusuario/enfermería = todo, coordinador BL = BL, coordinador Colegio = Colegio+Bachillerato). Esta ruta
# vieja de Enfermería se conserva solo para los enlaces guardados y redirige allá.
@login_required
def directorio_telefonos(request):
    return redirect('directorio_telefonos')


# ================= HISTORIAL MÉDICO =================
@_enfermeria_required  # <--- hecho por claude code (seguridad 05-nov-2026): antes solo la sesión: cualquier maestro veía el historial médico de todos los menores
def medical_history(request):
    # <--- hecho por claude code: historial médico — tabla global + tabla agrupada por alumno
    from django.db.models import Count, Max

    hoy = datetime.date.today()

    # Todos los registros ordenados por fecha desc
    atenciones = (
        AtencionMedica.objects
        .select_related('grado', 'atendido_por')
        .order_by('-fecha_hora')
    )

    total_atenciones = atenciones.count()
    total_alumnos    = AtencionMedica.objects.values('estudiante').distinct().count()
    este_mes         = AtencionMedica.objects.filter(
        fecha_hora__year=hoy.year, fecha_hora__month=hoy.month
    ).count()
    hoy_count        = AtencionMedica.objects.filter(fecha_hora__date=hoy).count()

    # Agrupado por alumno: total visitas + última visita + último grado
    # Ordenado por última visita descendente
    agrupado_qs = (
        AtencionMedica.objects
        .values('estudiante')
        .annotate(total_visitas=Count('id'), ultima_visita=Max('fecha_hora'))
        .order_by('-ultima_visita')
    )
    # Agregar el grado de la última atención a cada alumno
    # (hacemos un dict pk→grado desde la query completa)
    ultima_por_alumno = {}
    for a in atenciones.order_by('estudiante', '-fecha_hora'):
        if a.estudiante not in ultima_por_alumno:
            ultima_por_alumno[a.estudiante] = a.grado.nombre

    alumnos_agrupados = []
    for row in agrupado_qs:
        alumnos_agrupados.append({
            'estudiante':    row['estudiante'],
            'total_visitas': row['total_visitas'],
            'ultima_visita': row['ultima_visita'],
            'grado':         ultima_por_alumno.get(row['estudiante'], '—'),
        })

    return render(request, 'enfermeria/medical_history.html', {
        'atenciones':        atenciones,
        'alumnos_agrupados': alumnos_agrupados,
        'total_atenciones':  total_atenciones,
        'total_alumnos':     total_alumnos,
        'este_mes':          este_mes,
        'hoy_count':         hoy_count,
        'year':              hoy.year,
    })

@_enfermeria_required  # <--- hecho por claude code (seguridad 05-nov-2026): antes solo la sesión: ?student=<nombre> devolvía motivo y tratamiento de cualquier menor
def get_medical_history_data(request):
    student_name = request.GET.get('student')
    if not student_name:
        return JsonResponse({'error': 'Falta parámetro student'}, status=400)

    registros = (
        AtencionMedica.objects
        .filter(estudiante=student_name)
        .select_related('grado', 'atendido_por')
        .order_by('-fecha_hora')
    )

    history = []
    for rec in registros:
        history.append({
            'pk':         rec.pk,
            'student':    rec.estudiante,
            'grade':      rec.grado.nombre,
            'date_time':  rec.fecha_hora.strftime('%d/%m/%Y %H:%M'),
            'reason':     rec.motivo,
            'treatment':  rec.tratamiento,
            'attendant':  rec.atendido_por.nombre,
        })

    return JsonResponse({'history': history})
