# <--- hecho por claude code (16-oct-2026): PDF de la SOLICITUD DE PRÉSTAMO DE EQUIPO (Control y Servicio Técnico).
# Carta con el formato de ANA: lugar y fecha, destinatario (Dirección Ejecutiva), asunto, cuerpo con los datos del
# préstamo, compromiso y 4 firmas: Solicitante y Dirección Ejecutiva se firman a mano en papel; Soporte Técnico y
# Auditoría van FIJAS (MaintenanceRecord.FIRMA_TECNICO_FIJA / FIRMA_AUDITORA_FIJA). Luego se escanea y se sube.
from io import BytesIO
from xml.sax.saxutils import escape

from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.utils import timezone

LUGAR = 'Tegucigalpa'   # <--- corregido 16-oct-2026 (pedido del usuario)
INSTITUCION = 'Asociación Nuevo Amanecer'
_MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
          'noviembre', 'diciembre']


def fecha_larga(d):
    return f'{d.day} de {_MESES[d.month - 1]} de {d.year}' if d else '____________'


def pdf_solicitud(record):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    e = lambda t: escape(str(t or '').strip())
    r = record
    comp = r.computadora if r.computadora_id else None
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                            topMargin=1.6 * cm, bottomMargin=1.5 * cm,
                            title=f'Solicitud de Préstamo de Equipo - {r.record_id}', author=INSTITUCION)
    ANCHO = 17.2 * cm
    ORANGE = colors.HexColor('#c45d0a')
    GRIS = colors.HexColor('#555555')
    st_tit = ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=15, leading=18, textColor=ORANGE)
    st_sub = ParagraphStyle('s', fontName='Helvetica', fontSize=8.5, textColor=colors.gray)
    st_hdr = ParagraphStyle('h', fontName='Helvetica', fontSize=8.5, leading=11)
    st = ParagraphStyle('b', fontName='Helvetica', fontSize=10.5, leading=15, alignment=TA_JUSTIFY)
    st_izq = ParagraphStyle('i', parent=st, alignment=TA_LEFT)
    st_der = ParagraphStyle('d', parent=st, alignment=2)
    st_lbl = ParagraphStyle('l', fontName='Helvetica-Bold', fontSize=8.5, leading=10.5, textColor=GRIS)
    st_val = ParagraphStyle('v', fontName='Helvetica', fontSize=9.5, leading=12)
    st_f_nom = ParagraphStyle('fn', fontName='Helvetica-BoldOblique', fontSize=11, alignment=TA_CENTER)
    st_f_tit = ParagraphStyle('ft', fontName='Helvetica-Bold', fontSize=9, alignment=TA_CENTER)
    st_f_sub = ParagraphStyle('fs', fontName='Helvetica', fontSize=8, alignment=TA_CENTER, textColor=GRIS)
    st_pie = ParagraphStyle('p', fontName='Helvetica-Oblique', fontSize=7.5, alignment=TA_CENTER, textColor=colors.gray)

    story = []
    # Encabezado (mismo estilo que las fichas de Mantenimiento)
    logo = finders.find('mantenimiento/img/ana.jpg')
    hdr = Table([[RLImage(logo, width=2.2 * cm, height=2.2 * cm) if logo else '',
                  [Paragraph('Solicitud de Préstamo de Equipo', st_tit),
                   Paragraph(f'{INSTITUCION} – Control y Servicio Técnico', st_sub)],
                  Paragraph(f'<b>ID:</b> {e(r.record_id)}<br/><b>Fecha:</b> {r.date:%d/%m/%Y}<br/>'
                            f'<b>Estado:</b> {e(r.prestamo_estado[1])}', st_hdr)]],
                colWidths=[2.6 * cm, 10.1 * cm, 4.5 * cm])
    hdr.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                             ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                             ('LEFTPADDING', (0, 0), (-1, -1), 7), ('TOPPADDING', (0, 0), (-1, -1), 6),
                             ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    story += [hdr, Spacer(1, 0.45 * cm)]

    # Lugar y fecha · destinatario · asunto
    story += [Paragraph(f'{LUGAR}, {fecha_larga(r.date)}', st_der), Spacer(1, 0.3 * cm),
              Paragraph('<b>Dirección Ejecutiva</b><br/>' + INSTITUCION, st_izq), Spacer(1, 0.3 * cm),
              Paragraph('<b>Asunto:</b> Solicitud de préstamo de equipo', st_izq), Spacer(1, 0.3 * cm)]

    quien = f'<b>{e(r.prest_solicitante) or "____________________"}</b>'
    if r.prest_cargo:
        quien += f', {e(r.prest_cargo)}'
    if r.prest_area:
        quien += f' del área de {e(r.prest_area)}'
    story += [Paragraph(f'Por medio de la presente, yo, {quien}, solicito de manera respetuosa el préstamo del '
                        f'siguiente equipo:', st), Spacer(1, 0.25 * cm)]

    # Datos del equipo (conectado al inventario)
    asset = comp.asset_id if comp else ''
    modelo = r.model or (getattr(comp, 'modelo', '') or '')
    serie = r.serie or (getattr(comp, 'serie', '') or '')
    filas = [[Paragraph('Equipo', st_lbl), Paragraph('Computadora', st_val), Paragraph('Código de inventario', st_lbl), Paragraph(e(asset) or '—', st_val)],
             [Paragraph('Marca / modelo', st_lbl), Paragraph(e(modelo) or '—', st_val), Paragraph('Número de serie', st_lbl), Paragraph(e(serie) or '—', st_val)],
             [Paragraph('Accesorios', st_lbl), Paragraph(e(r.prest_accesorios) or 'Ninguno', st_val), Paragraph('Cantidad', st_lbl), Paragraph('1', st_val)]]
    if r.teacher_name or r.grade:
        filas.append([Paragraph('Asignado en inventario', st_lbl), Paragraph(e(' · '.join(x for x in [r.teacher_name, r.grade] if x)), st_val), '', ''])
    t = Table(filas, colWidths=[3.4 * cm, 5.2 * cm, 3.4 * cm, 5.2 * cm])
    estilo = [('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')), ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f1f1')),
              ('BACKGROUND', (2, 0), (2, 2), colors.HexColor('#f1f1f1')), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
              ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]
    if len(filas) == 4:
        estilo.append(('SPAN', (1, 3), (3, 3)))
    t.setStyle(TableStyle(estilo))
    story += [t, Spacer(1, 0.35 * cm)]

    lugar = e(r.prest_lugar) or '____________________'
    sale = ('El equipo <b>saldrá de las instalaciones</b> de la institución.' if r.prest_sale
            else 'El equipo <b>permanecerá dentro</b> de las instalaciones de la institución.')
    story += [Paragraph(f'El equipo será utilizado para <b>{e(r.prest_motivo) or "____________________"}</b>, en <b>{lugar}</b>, '
                        f'durante el período comprendido del <b>{fecha_larga(r.prest_desde)}</b> al '
                        f'<b>{fecha_larga(r.prest_hasta)}</b>. {sale}', st), Spacer(1, 0.25 * cm),
              Paragraph('Me comprometo a hacer buen uso del equipo, a resguardarlo adecuadamente y a devolverlo en las mismas '
                        'condiciones en que fue entregado en la fecha indicada. En caso de daño o extravío, asumiré la '
                        'responsabilidad correspondiente según las políticas de la institución.', st), Spacer(1, 0.25 * cm)]
    if (r.observaciones or '').strip():
        story += [Paragraph(f'<b>Observaciones:</b> {e(r.observaciones)}', st), Spacer(1, 0.25 * cm)]
    story += [Paragraph('Agradezco de antemano su atención.', st), Spacer(1, 0.2 * cm), Paragraph('Atentamente,', st_izq),
              Spacer(1, 0.5 * cm)]

    # 4 firmas: solicitante y dirección a mano (en papel); soporte técnico y auditoría fijas
    n_t, c_t = r.FIRMA_TECNICO_FIJA
    n_a, c_a = r.FIRMA_AUDITORA_FIJA

    def firma(nombre, titulo, sub, fija):
        arriba = Paragraph(e(nombre), st_f_nom) if fija else Spacer(1, 0.45 * cm)
        return [Spacer(1, 1.0 * cm), arriba, Table([['']], colWidths=[6.6 * cm], rowHeights=[0.15 * cm],
                                                     style=[('LINEABOVE', (0, 0), (-1, -1), 0.8, colors.black)]),
                Paragraph(titulo, st_f_tit), Paragraph(sub, st_f_sub)]

    sol = e(r.prest_solicitante) or 'Nombre'
    if r.prest_cargo:
        sol += f' · {e(r.prest_cargo)}'
    firmas = Table([[firma('', 'Solicitante', sol, False), firma(n_t, 'Soporte Técnico', e(c_t), True)],
                    [firma('', 'Dirección Ejecutiva', 'Autoriza · Fecha: ______________', False), firma(n_a, 'Auditoría', e(c_a), True)]],
                   colWidths=[ANCHO / 2, ANCHO / 2])
    firmas.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'BOTTOM'), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
    story += [firmas, Spacer(1, 0.4 * cm),
              Paragraph(f'Generado por TechCare el {timezone.now():%d/%m/%Y %H:%M} · Firmar en papel, escanear y subir el PDF '
                        f'firmado en Control y Servicio Técnico → Préstamos de equipo.', st_pie)]
    doc.build(story)
    resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{r.record_id}_solicitud_prestamo.pdf"'
    return resp
