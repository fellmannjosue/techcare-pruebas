import os
import textwrap
from io import BytesIO
from PIL import Image as PILImage

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.http import HttpResponse, JsonResponse

from reportlab.pdfgen import canvas
from reportlab.lib import colors

from inventario.models import Computadora
from .models import MaintenanceRecord, MaestroMantenimiento, GradoMantenimiento, FotoMantenimiento, TipoFalla
from .forms import MaintenanceRecordForm


def _siguiente_record_id():
    prefix = 'ANAMAESCOMP'
    ultimo = MaintenanceRecord.objects.filter(
        record_id__startswith=prefix
    ).order_by('-record_id').values_list('record_id', flat=True).first()
    if ultimo:
        try:
            n = int(ultimo[len(prefix):])
        except ValueError:
            n = 0
    else:
        n = 0
    return f"{prefix}{n+1:03d}"


@login_required
def maintenance_dashboard(request):
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.record_id = _siguiente_record_id()
            comp = record.computadora
            if comp:
                if not record.teacher_name:
                    record.teacher_name = comp.asignado_a or ''
                if not record.grade:
                    record.grade = comp.grado or ''
            firma_data = request.POST.get('firma_data', '').strip()
            if firma_data:
                record.firma = firma_data
            record.save()
            for f in request.FILES.getlist('fotos'):
                FotoMantenimiento.objects.create(registro=record, imagen=f)
            from django.contrib import messages
            messages.success(request, f'Registro {record.record_id} guardado correctamente.')
        else:
            from django.contrib import messages
            errores = '; '.join(
                f"{field}: {', '.join(errs)}"
                for field, errs in form.errors.items()
                if field != '__all__'
            )
            messages.error(request, f'Error al guardar: {errores or "Verifica los campos requeridos."}')
        return redirect('mantenimiento:maintenance_dashboard')

    form = MaintenanceRecordForm()

    records = MaintenanceRecord.objects.all().order_by('-date')

    import json
    computadoras_json = json.dumps({
        str(c.id): {
            'modelo':   c.modelo,
            'serie':    c.serie or '',
            'asignado': c.asignado_a or '',
            'area':     c.area or '',
            'grado':    c.grado or '',
        }
        for c in Computadora.objects.all().order_by('asset_id')
    })

    return render(request, 'mantenimiento/maintenance_dashboard.html', {
        'form':              form,
        'records':           records,
        'total':             records.count(),
        'pendiente':         records.filter(status='Pendiente').count(),
        'en_proceso':        records.filter(status='En Proceso').count(),
        'completado':        records.filter(status='Completado').count(),
        'computadoras':      Computadora.objects.all().order_by('asset_id'),
        'computadoras_json': computadoras_json,
        'maestros':          MaestroMantenimiento.objects.all(),
        'grados':            GradoMantenimiento.objects.all(),
        'tipos_falla':       TipoFalla.objects.all().order_by('nombre'),
        'next_record_id':    _siguiente_record_id(),
    })


@login_required
def download_maintenance_pdf(request, record_id):
    import base64, re
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    record = get_object_or_404(MaintenanceRecord, id=record_id)
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Ficha de Mantenimiento - {record.record_id}",
    )

    styles = getSampleStyleSheet()
    ORANGE  = colors.HexColor("#c45d0a")
    GRAY_BG = colors.HexColor("#f5f5f5")
    GRAY_LT = colors.HexColor("#eeeeee")

    st_title = ParagraphStyle("title", fontSize=16, fontName="Helvetica-Bold",
                               textColor=ORANGE, spaceAfter=2)
    st_sub   = ParagraphStyle("sub",   fontSize=9,  fontName="Helvetica",
                               textColor=colors.gray, spaceAfter=6)
    st_label = ParagraphStyle("lbl",   fontSize=9,  fontName="Helvetica-Bold",
                               textColor=colors.HexColor("#333333"))
    st_value = ParagraphStyle("val",   fontSize=9,  fontName="Helvetica",
                               textColor=colors.black)
    st_center= ParagraphStyle("ctr",   fontSize=8,  fontName="Helvetica-Oblique",
                               textColor=colors.gray, alignment=TA_CENTER)

    story = []

    # ── Encabezado ───────────────────────────────────────────────
    logo_path = finders.find('mantenimiento/img/ana.jpg')
    header_data = [[
        RLImage(logo_path, width=2.5*cm, height=2.5*cm) if logo_path else "",
        [
            Paragraph("Ficha de Mantenimiento de Equipo", st_title),
            Paragraph("Asociación Nuevo Amanecer – Sistema TechCare", st_sub),
        ],
        Paragraph(f"<b>ID:</b> {record.record_id}<br/>"
                  f"<b>Fecha:</b> {record.date.strftime('%d/%m/%Y')}<br/>"
                  f"<b>Estado:</b> {record.status}",
                  ParagraphStyle("hdr_r", fontSize=9, fontName="Helvetica",
                                 alignment=TA_LEFT)),
    ]]
    header_tbl = Table(header_data, colWidths=[2.8*cm, 10*cm, 4.5*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND",  (0,0), (-1,-1), GRAY_BG),
        ("BOX",         (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Sección: Datos del equipo ─────────────────────────────────
    def section_title(txt):
        return Table([[Paragraph(txt, ParagraphStyle("sec", fontSize=10,
                        fontName="Helvetica-Bold", textColor=colors.white))]],
                     colWidths=[17.3*cm])

    def _st(t):
        tbl = section_title(t)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1), ORANGE),
            ("LEFTPADDING",(0,0),(-1,-1), 8),
            ("TOPPADDING",(0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]))
        return tbl

    def field_row(label, value):
        return [Paragraph(label, st_label), Paragraph(str(value) if value else "—", st_value)]

    story.append(_st("Datos del Equipo"))
    story.append(Spacer(1, 0.1*cm))

    comp = record.computadora
    equipo_data = [
        field_row("ID de Activo:",   comp.asset_id if comp else "—"),
        field_row("Modelo:",         record.model or (comp.modelo if comp else "—")),
        field_row("Serie:",          record.serie or (comp.serie if comp else "—")),
        field_row("Asignado a:",     comp.asignado_a if comp else "—"),
        field_row("Área:",           comp.area if comp else "—"),
        field_row("Grado:",          record.grade or (comp.grado if comp else "—")),
    ]
    equipo_tbl = Table(equipo_data, colWidths=[4*cm, 13.3*cm])
    equipo_tbl.setStyle(TableStyle([
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.white, GRAY_LT]),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("BOX",         (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
        ("LINEBELOW",   (0,0), (-1,-2), 0.3, colors.HexColor("#dddddd")),
    ]))
    story.append(equipo_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Sección: Diagnóstico ──────────────────────────────────────
    story.append(_st("Diagnóstico y Solución"))
    story.append(Spacer(1, 0.1*cm))

    tipo_falla = str(record.tipo_falla) if record.tipo_falla else "—"
    diag_data = [
        field_row("Tipo de Falla:",   tipo_falla),
        field_row("Solución aplicada:", record.solucion or "—"),
        field_row("Observaciones:",    record.observaciones or "—"),
    ]
    diag_tbl = Table(diag_data, colWidths=[4*cm, 13.3*cm])
    diag_tbl.setStyle(TableStyle([
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.white, GRAY_LT]),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("BOX",         (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
        ("LINEBELOW",   (0,0), (-1,-2), 0.3, colors.HexColor("#dddddd")),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
    ]))
    story.append(diag_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Sección: Firma ────────────────────────────────────────────
    story.append(_st("Firma de Conformidad"))
    story.append(Spacer(1, 0.4*cm))

    if record.firma:
        try:
            # Decodificar base64 y componer sobre fondo blanco (canvas genera RGBA)
            b64 = re.sub(r'^data:image/[^;]+;base64,', '', record.firma)
            img_bytes = base64.b64decode(b64)
            pil_img = PILImage.open(BytesIO(img_bytes)).convert('RGBA')
            bg = PILImage.new('RGB', pil_img.size, (255, 255, 255))
            bg.paste(pil_img, mask=pil_img.split()[3])
            out_buf = BytesIO()
            bg.save(out_buf, format='PNG')
            out_buf.seek(0)
            firma_img = RLImage(out_buf, width=6*cm, height=2.5*cm)
            firma_tbl = Table([[firma_img]], colWidths=[17.3*cm])
            firma_tbl.setStyle(TableStyle([
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ]))
            story.append(firma_tbl)
        except Exception as e:
            story.append(Spacer(1, 2*cm))
    else:
        story.append(Spacer(1, 2*cm))

    story.append(HRFlowable(width="40%", thickness=1, color=colors.gray,
                             hAlign="CENTER"))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("Firma del responsable", st_center))
    story.append(Spacer(1, 0.6*cm))

    # ── Pie de página ─────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "Sistema de Mantenimiento – Asociación Nuevo Amanecer &nbsp;|&nbsp; TechCare",
        st_center
    ))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="mantenimiento_{record.record_id}.pdf"'
    return response


# ─────────────────────────────────────────────────────────────
# Editar registro de mantenimiento
# ─────────────────────────────────────────────────────────────
@login_required
def editar_mantenimiento(request, pk):
    from django.contrib import messages as msg
    record = get_object_or_404(MaintenanceRecord, pk=pk)

    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            rec = form.save(commit=False)
            comp = rec.computadora
            if comp:
                if not rec.teacher_name:
                    rec.teacher_name = comp.asignado_a or ''
                if not rec.grade:
                    rec.grade = comp.grado or ''
            firma_data = request.POST.get('firma_data', '').strip()
            if firma_data:
                rec.firma = firma_data
            rec.save()
            for f in request.FILES.getlist('fotos'):
                FotoMantenimiento.objects.create(registro=rec, imagen=f)
            msg.success(request, f'Registro {rec.record_id} actualizado correctamente.')
        else:
            errores = '; '.join(
                f"{field}: {', '.join(errs)}"
                for field, errs in form.errors.items() if field != '__all__'
            )
            msg.error(request, f'Error al actualizar: {errores or "Verifica los campos requeridos."}')
        return redirect('mantenimiento:maintenance_dashboard')

    # GET → devuelve JSON con los datos del registro para llenar el modal
    import json as _json
    data = {
        'id':           record.pk,
        'record_id':    record.record_id,
        'computadora':  record.computadora_id,
        'model':        record.model,
        'serie':        record.serie,
        'tipo_falla':   record.tipo_falla_id,
        'date':         record.date.strftime('%Y-%m-%d') if record.date else '',
        'status':       record.status,
        'solucion':     record.solucion or '',
        'observaciones':record.observaciones or '',
        'firma':        record.firma or '',
    }
    return JsonResponse(data)


# ─────────────────────────────────────────────────────────────
# Eliminar registro y renumerar desde 001
# ─────────────────────────────────────────────────────────────
@login_required
def eliminar_mantenimiento(request, pk):
    from django.contrib import messages as msg
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    if request.method == 'POST':
        record.delete()
        # Renumerar registros restantes desde 001
        PREFIX = 'ANAMAESCOMP'
        for i, r in enumerate(
            MaintenanceRecord.objects.all().order_by('id'), start=1
        ):
            nuevo_id = f"{PREFIX}{i:03d}"
            if r.record_id != nuevo_id:
                MaintenanceRecord.objects.filter(pk=r.pk).update(record_id=nuevo_id)
        msg.success(request, 'Registro eliminado y numeración reiniciada.')
        return redirect('mantenimiento:maintenance_dashboard')
    return JsonResponse({'error': 'Método no permitido'}, status=405)
