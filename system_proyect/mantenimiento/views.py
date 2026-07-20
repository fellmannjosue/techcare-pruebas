import os
import textwrap
from io import BytesIO
from PIL import Image as PILImage

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from reportlab.pdfgen import canvas
from reportlab.lib import colors

from inventario.models import Computadora, Impresora
from .models import MaintenanceRecord, MaestroMantenimiento, GradoMantenimiento, FotoMantenimiento, TipoFalla
from .forms import MaintenanceRecordForm, FirmaMaestroForm

# URL pública del sistema (incluye el puerto :437). El link de firma del maestro
# DEBE llevar el puerto o no funciona; request.get_host() lo pierde detrás de Apache.
SITE_URL = 'https://servicios.ana-hn.org:437'


def _siguiente_record_id():
    prefix = 'ANAMAESCOMP'
    ultimo = (MaintenanceRecord.objects
              .filter(record_id__startswith=prefix)
              .exclude(record_id__startswith='ANAMAESIMP')  # no mezclar con el prefijo de impresora
              .order_by('-record_id').values_list('record_id', flat=True).first())
    if ultimo:
        try:
            n = int(ultimo[len(prefix):])
        except ValueError:
            n = 0
    else:
        n = 0
    return f"{prefix}{n+1:03d}"


# <--- hecho por claude code: ID propio para mantenimientos de impresora (ANAMAESIMP-001)
def _siguiente_record_id_impresora():
    prefix = 'ANAMAESIMP-'
    ultimo = (MaintenanceRecord.objects
              .filter(record_id__startswith=prefix)
              .order_by('-record_id').values_list('record_id', flat=True).first())
    if ultimo:
        try:
            n = int(ultimo[len(prefix):])
        except ValueError:
            n = 0
    else:
        n = 0
    return f"{prefix}{n+1:03d}"


def _resolver_post_tipo_falla(request):
    """Si se eligió 'Agregar nueva falla…' (tipo_falla='__nueva__'), crea el TipoFalla
    con el texto escrito y lo deja resuelto en una copia del POST."""
    post = request.POST
    if post.get('tipo_falla') == '__nueva__':
        post = post.copy()
        nombre = (post.get('tipo_falla_nueva') or '').strip()
        if nombre:
            tf, _ = TipoFalla.objects.get_or_create(nombre=nombre)
            post['tipo_falla'] = str(tf.id)
        else:
            post['tipo_falla'] = ''
    return post


@login_required
def maintenance_dashboard(request):
    if request.method == 'POST':
        form = MaintenanceRecordForm(_resolver_post_tipo_falla(request), request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            # <--- hecho por claude code: rama impresora vs computadora
            if record.tipo_equipo == 'impresora':
                record.record_id = _siguiente_record_id_impresora()
                imp = record.impresora
                if imp:
                    record.model        = imp.modelo or ''
                    record.serie        = imp.serie or ''
                    if not record.teacher_name:
                        record.teacher_name = imp.asignado_a or ''
            else:
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
            firma_tec = request.POST.get('firma_tecnico_data', '').strip()
            if firma_tec:
                record.firma_tecnico = firma_tec
            record.save()
            for f in request.FILES.getlist('fotos'):
                FotoMantenimiento.objects.create(registro=record, imagen=f)
            # <--- hecho por claude code: al llenar tinta, reflejar en el inventario de la impresora
            if record.tipo_equipo == 'impresora' and record.impresora_id and record.tipo_mant_impresora == 'llenado_tinta':
                imp = record.impresora
                if record.estado_tinta:
                    imp.nivel_tinta = record.get_estado_tinta_display()
                imp.ultima_vez_llenado = record.date
                imp.save(update_fields=['nivel_tinta', 'ultima_vez_llenado'])
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
    # Solo computadoras de general (excluye laboratorios)
    comps_qs = Computadora.objects.exclude(asset_id__icontains='LAB').order_by('asset_id')
    computadoras_json = json.dumps({
        str(c.id): {
            'modelo':   c.modelo,
            'serie':    c.serie or '',
            'asignado': c.asignado_a or '',
            'area':     c.area or '',
            'grado':    c.grado or '',
        }
        for c in comps_qs
    })

    # <--- hecho por claude code: datos de impresoras para el auto-llenado del formulario
    imps_qs = Impresora.objects.order_by('asset_id')
    impresoras_json = json.dumps({
        str(i.id): {
            'modelo':   i.modelo,
            'serie':    i.serie or '',
            'asignado': i.asignado_a or '',
            'nivel_tinta': i.nivel_tinta or '',
        }
        for i in imps_qs
    })

    return render(request, 'mantenimiento/maintenance_dashboard.html', {
        'form':              form,
        'records':           records,
        'site_url':          SITE_URL,
        'total':             records.count(),
        'pendiente':         records.filter(status='Pendiente').count(),
        'en_proceso':        records.filter(status='En Proceso').count(),
        'completado':        records.filter(status='Completado').count(),
        'computadoras':      comps_qs,
        'computadoras_json': computadoras_json,
        'impresoras':        imps_qs,
        'impresoras_json':   impresoras_json,
        'maestros':          MaestroMantenimiento.objects.all(),
        'grados':            GradoMantenimiento.objects.all(),
        'tipos_falla':       TipoFalla.objects.all().order_by('nombre'),
        'next_record_id':    _siguiente_record_id(),
        'next_record_id_imp':_siguiente_record_id_impresora(),
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

    # <--- hecho por claude code: datos del equipo según tipo (computadora / impresora)
    if record.tipo_equipo == 'impresora':
        imp = record.impresora
        equipo_data = [
            field_row("ID de Activo:",   imp.asset_id if imp else "—"),
            field_row("Modelo:",         record.model or (imp.modelo if imp else "—")),
            field_row("Serie:",          record.serie or (imp.serie if imp else "—")),
            field_row("Asignado a:",     record.teacher_name or (imp.asignado_a if imp else "—")),
            field_row("Área:",           record.area or "—"),
        ]
    else:
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

    # <--- hecho por claude code: diagnóstico según tipo (computadora / impresora)
    if record.tipo_equipo == 'impresora':
        colores = [n for n, ok in (
            ("Negra", record.tinta_negra), ("Magenta", record.tinta_magenta),
            ("Amarillo", record.tinta_amarillo), ("Cyan", record.tinta_cyan)) if ok]
        diag_data = [
            field_row("Tipo de mantenimiento:", record.get_tipo_mant_impresora_display() or "—"),
            field_row("Estado de la tinta:",    record.get_estado_tinta_display() or "—"),
            field_row("Colores rellenados:",    ", ".join(colores) if colores else "—"),
            field_row("Tipo de tinta:",         record.tipo_tinta or "—"),
            field_row("Solución aplicada:",     record.solucion or "—"),
            field_row("Observaciones:",         record.observaciones or "—"),
        ]
    else:
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

    # ── Sección: Fotos de evidencia (hecho por claude code: siempre se adjuntan) ──
    fotos = list(record.fotos.all())
    story.append(_st("Fotos de Evidencia"))
    story.append(Spacer(1, 0.15*cm))

    def _foto_flowable(foto, max_w=8.3*cm, max_h=6*cm):
        """RLImage escalada (respeta proporción) desde el archivo de la foto, o '' si falla."""
        try:
            p = foto.imagen.path
            with PILImage.open(p) as im:
                iw, ih = im.size
            ratio = min(max_w / float(iw), max_h / float(ih))
            return RLImage(p, width=iw * ratio, height=ih * ratio)
        except Exception:
            return ""

    celdas = [c for c in (_foto_flowable(f) for f in fotos) if c]
    if celdas:
        filas = []
        for i in range(0, len(celdas), 2):
            fila = celdas[i:i+2]
            if len(fila) == 1:
                fila.append("")   # completar la última fila
            filas.append(fila)
        fotos_tbl = Table(filas, colWidths=[8.65*cm, 8.65*cm])
        fotos_tbl.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN",        (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ("BOX",          (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
            ("INNERGRID",    (0,0), (-1,-1), 0.3, colors.HexColor("#eeeeee")),
        ]))
        story.append(fotos_tbl)
    else:
        story.append(Paragraph("Sin fotos adjuntas.", st_center))
    story.append(Spacer(1, 0.4*cm))

    # ── Sección: Firmas (Técnico y Maestro) ───────────────────────
    story.append(_st("Firmas de Conformidad"))
    story.append(Spacer(1, 0.4*cm))

    def _firma_img(b64):
        """Devuelve un RLImage de la firma base64 sobre fondo blanco, o '' si no hay."""
        if not (b64 or '').strip():
            return ""
        try:
            raw = re.sub(r'^data:image/[^;]+;base64,', '', b64)
            pil_img = PILImage.open(BytesIO(base64.b64decode(raw))).convert('RGBA')
            bg = PILImage.new('RGB', pil_img.size, (255, 255, 255))
            bg.paste(pil_img, mask=pil_img.split()[3])
            out_buf = BytesIO(); bg.save(out_buf, format='PNG'); out_buf.seek(0)
            return RLImage(out_buf, width=6*cm, height=2.3*cm)
        except Exception:
            return ""

    st_firma_lbl = ParagraphStyle("flbl", fontSize=8, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#333333"), alignment=TA_CENTER)
    st_firma_sub = ParagraphStyle("fsub", fontSize=7, fontName="Helvetica-Oblique",
                                  textColor=colors.gray, alignment=TA_CENTER)

    linea = HRFlowable(width="80%", thickness=0.8, color=colors.gray, hAlign="CENTER")
    sub_maestro = (f"{record.teacher_name}" if record.teacher_name else "")
    if record.firmado_en:
        sub_maestro += f" · {record.firmado_en.strftime('%d/%m/%Y %H:%M')}"

    col_tec = [_firma_img(record.firma_tecnico) or Spacer(1, 2.3*cm), Spacer(1, 0.1*cm),
               linea, Spacer(1, 0.1*cm),
               Paragraph("Firma del Técnico (Soporte)", st_firma_lbl)]
    col_mae = [_firma_img(record.firma) or Spacer(1, 2.3*cm), Spacer(1, 0.1*cm),
               HRFlowable(width="80%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.1*cm),
               Paragraph("Firma del Maestro (Evidencia)", st_firma_lbl),
               Paragraph(sub_maestro, st_firma_sub)]

    firmas_tbl = Table([[col_tec, col_mae]], colWidths=[8.65*cm, 8.65*cm])
    firmas_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "BOTTOM"),
        ("ALIGN",  (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(firmas_tbl)
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
        # <--- hecho por claude code: el modal de edición es de computadora; preservamos el
        # tipo de equipo y los campos específicos del registro para no borrarlos al guardar.
        post = _resolver_post_tipo_falla(request).copy()
        post['tipo_equipo'] = record.tipo_equipo
        if record.tipo_equipo == 'impresora':
            post['impresora']           = record.impresora_id or ''
            post['area']                = record.area
            post['tipo_mant_impresora'] = record.tipo_mant_impresora
            post['estado_tinta']        = record.estado_tinta
            post['tipo_tinta']          = record.tipo_tinta
            for cb, val in (('tinta_negra', record.tinta_negra), ('tinta_magenta', record.tinta_magenta),
                            ('tinta_amarillo', record.tinta_amarillo), ('tinta_cyan', record.tinta_cyan)):
                if val:
                    post[cb] = 'on'
                else:
                    post.pop(cb, None)
        form = MaintenanceRecordForm(post, request.FILES, instance=record)
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
            firma_tec = request.POST.get('firma_tecnico_data', '').strip()
            if firma_tec:
                rec.firma_tecnico = firma_tec
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
        'firma_tecnico':record.firma_tecnico or '',
        # <--- hecho por claude code: fotos existentes para mostrarlas en el modal de edición
        'fotos':        [{'id': f.id, 'url': f.imagen.url} for f in record.fotos.all()],
    }
    return JsonResponse(data)


# ─────────────────────────────────────────────────────────────
# FIRMA REMOTA DEL MAESTRO (link público con token, sin login)
# ─────────────────────────────────────────────────────────────
@csrf_protect
def firmar_publico(request, token):
    rec = get_object_or_404(MaintenanceRecord, token_firma=token)

    # El token es de un solo uso: solo se considera "ya firmado" cuando se firmó
    # por este link (firmado_en). Así el enlace vence tras usarse y se protege.
    if rec.firmado_en:
        return render(request, 'mantenimiento/firmar.html', {'rec': rec, 'ya_firmado': True})

    if request.method == 'POST':
        form = FirmaMaestroForm(request.POST)
        if form.is_valid():
            rec.firma      = form.cleaned_data['firma_data']
            rec.firmado_en = timezone.now()
            rec.save(update_fields=['firma', 'firmado_en'])
            return render(request, 'mantenimiento/firmar.html', {'rec': rec, 'exito': True})
    else:
        form = FirmaMaestroForm()

    return render(request, 'mantenimiento/firmar.html', {'rec': rec, 'form': form})


@login_required
def tipo_falla_crear(request):
    """AJAX: crea un nuevo Tipo de Falla y lo devuelve."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    nombre = (request.POST.get('nombre', '') or '').strip()
    if not nombre:
        return JsonResponse({'ok': False, 'error': 'Nombre requerido'}, status=400)
    obj, _ = TipoFalla.objects.get_or_create(nombre=nombre)
    return JsonResponse({'ok': True, 'id': obj.id, 'nombre': obj.nombre})


@login_required
def marcar_firma_solicitada(request, pk):
    """Marca que ya se mandó el link de firma al maestro (AJAX)."""
    rec = get_object_or_404(MaintenanceRecord, pk=pk)
    if request.method == 'POST':
        rec.firma_solicitada = True
        rec.save(update_fields=['firma_solicitada'])
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ─────────────────────────────────────────────────────────────
# Eliminar registro y renumerar desde 001
# ─────────────────────────────────────────────────────────────
@login_required
def eliminar_mantenimiento(request, pk):
    from django.contrib import messages as msg
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    if request.method == 'POST':
        record.delete()
        # <--- hecho por claude code: renumerar por separado computadora (ANAMAESCOMP###) e impresora (ANAMAESIMP-###)
        for i, r in enumerate(
            MaintenanceRecord.objects.filter(tipo_equipo='impresora').order_by('id'), start=1
        ):
            nuevo_id = f"ANAMAESIMP-{i:03d}"
            if r.record_id != nuevo_id:
                MaintenanceRecord.objects.filter(pk=r.pk).update(record_id=nuevo_id)
        for i, r in enumerate(
            MaintenanceRecord.objects.exclude(tipo_equipo='impresora').order_by('id'), start=1
        ):
            nuevo_id = f"ANAMAESCOMP{i:03d}"
            if r.record_id != nuevo_id:
                MaintenanceRecord.objects.filter(pk=r.pk).update(record_id=nuevo_id)
        msg.success(request, 'Registro eliminado y numeración reiniciada.')
        return redirect('mantenimiento:maintenance_dashboard')
    return JsonResponse({'error': 'Método no permitido'}, status=405)
