import os
import textwrap
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.http import HttpResponse, JsonResponse

from reportlab.pdfgen import canvas
from reportlab.lib import colors

from inventario.models import Computadora
from .models import MaintenanceRecord, MaestroMantenimiento, GradoMantenimiento, FotoMantenimiento
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
            # Firma base64 desde el campo oculto
            firma_data = request.POST.get('firma_data', '').strip()
            if firma_data:
                record.firma = firma_data
            record.save()
            # Guardar fotos (hasta 5)
            for f in request.FILES.getlist('fotos'):
                FotoMantenimiento.objects.create(registro=record, imagen=f)
            return redirect('mantenimiento:maintenance_dashboard')
    else:
        form = MaintenanceRecordForm()

    records = MaintenanceRecord.objects.all().order_by('-date')

    import json
    computadoras_json = json.dumps({
        str(c.id): {'modelo': c.modelo, 'serie': c.serie or ''}
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
        'next_record_id':    _siguiente_record_id(),
    })


@login_required
def download_maintenance_pdf(request, record_id):
    record = get_object_or_404(MaintenanceRecord, id=record_id)

    buffer = BytesIO()
    card_w = 160 * 2.83465
    card_h =  55 * 2.83465

    pdf = canvas.Canvas(buffer, pagesize=(card_w, card_h))
    pdf.setTitle(f"Ficha de Mantenimiento - {record.record_id}")

    pdf.setFillColor(colors.HexColor("#f8f9fa"))
    pdf.rect(0, 0, card_w, card_h, fill=1)

    logo_path = finders.find('mantenimiento/img/ana.jpg')
    if logo_path:
        pdf.drawImage(logo_path, 10, card_h - 40, width=30, height=30)

    margin, line_h = 10, 12
    col1, col2 = margin + 40, card_w/2 + 10
    y1 = y2 = card_h - 20

    def draw_field(x, y, label, val):
        pdf.setFont("Helvetica-Bold", 9)
        pdf.setFillColor(colors.black)
        pdf.drawString(x, y, label)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x + 60, y, str(val))
        return y - line_h

    y1 = draw_field(col1, y1, "ID:",       record.record_id)
    y1 = draw_field(col1, y1, "Equipo:",   str(record.computadora or record.model))
    y1 = draw_field(col1, y1, "Modelo:",   record.model)
    y1 = draw_field(col1, y1, "Serie:",    record.serie or "—")
    y1 = draw_field(col1, y1, "Maestro:",  record.teacher_name)
    y1 = draw_field(col1, y1, "Grado:",    record.grade)

    y2 = draw_field(col2, y2, "Fecha:",    record.date.strftime('%d-%m-%Y'))
    y2 = draw_field(col2, y2, "Estado:",   record.status)

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(col2, y2, "Solución:")
    pdf.setFont("Helvetica", 9)
    wrap_w = int((card_w - col2 - margin) / 6)
    for line in textwrap.wrap(record.solucion or "-", wrap_w):
        y2 -= line_h
        pdf.drawString(col2 + 60, y2, line)
    y2 -= line_h

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(col2, y2, "Observaciones:")
    pdf.setFont("Helvetica", 9)
    for line in textwrap.wrap(record.observaciones or "-", wrap_w):
        y2 -= line_h
        pdf.drawString(col2 + 60, y2, line)

    sign_y = margin + 40
    pdf.setLineWidth(1)
    pdf.line(card_w/2 - 50, sign_y, card_w/2 + 50, sign_y)
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(card_w/2, sign_y - 12, "Firma:")

    pdf.setFont("Helvetica-Oblique", 8)
    pdf.setFillColor(colors.gray)
    pdf.drawCentredString(card_w/2, margin, "Sistema de Mantenimiento - Asociación Nuevo Amanecer")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="mantenimiento_{record.record_id}.pdf"'
    return response
