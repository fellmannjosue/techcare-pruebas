import base64
import json
import re
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied as _PermissionDenied
from functools import wraps as _wraps


# <--- hecho por claude code (seguridad): TODO el módulo de cámaras (incl. hub) tenía solo
# @login_required, así que cualquier maestro entraba por URL. Cámaras es de TI: acceso con
# el grupo 'inventario' o superusuario. is_staff YA NO basta.
def _camaras_required(view):
    @_wraps(view)
    @login_required
    def _w(request, *a, **k):
        u = request.user
        if u.is_superuser or u.groups.filter(name='inventario').exists():
            return view(request, *a, **k)
        raise _PermissionDenied('Acceso solo para el equipo de TI.')
    return _w

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from .models import (
    Servidor, NVR, Componente, Gabinete, Camara,
    TipoFallaCamara, MantenimientoCamara, FotoMantenimientoCamara,
)
from .forms import (
    ServidorForm, NVRForm, ComponenteForm, GabineteForm, CamaraForm,
    MantenimientoCamaraForm, FirmaTecnicoForm,
)

# URL pública del sistema (incluye el puerto :437). El link de firma del técnico
# DEBE llevar el puerto o no funciona; request.get_host() lo pierde detrás de Apache.
SITE_URL = 'https://servicios.ana-hn.org:437'


# ════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════
def _errores(form):
    return '; '.join(
        f"{form.fields[f].label or f}: {', '.join(e)}"
        for f, e in form.errors.items() if f != '__all__'
    ) or 'Verifica los campos requeridos.'


def _save_form(form, request):
    obj = form.save(commit=False)
    if hasattr(obj, 'creado_por_id') and not obj.creado_por_id:
        obj.creado_por = request.user
    if hasattr(obj, 'modificado_por_id'):
        obj.modificado_por = request.user
    obj.save()
    form.save_m2m()
    return obj


def _entity_page(request, *, Model, Form, template, order, extra_ctx=None):
    """GET: lista + form de alta. POST: crea."""
    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            obj = _save_form(form, request)
            messages.success(request, f'Registro guardado correctamente.')
        else:
            messages.error(request, f'Error al guardar: {_errores(form)}')
        return redirect(request.path)
    ctx = {
        'form':     Form(),
        'objetos':  Model.objects.all().order_by(*order),
        'total':    Model.objects.count(),
    }
    if extra_ctx:
        ctx.update(extra_ctx)
    return render(request, template, ctx)


def _entity_edit(request, pk, *, Model, Form, redirect_name, json_builder):
    obj = get_object_or_404(Model, pk=pk)
    if request.method == 'POST':
        form = Form(request.POST, instance=obj)
        if form.is_valid():
            _save_form(form, request)
            messages.success(request, 'Registro actualizado correctamente.')
        else:
            messages.error(request, f'Error al actualizar: {_errores(form)}')
        return redirect(reverse(redirect_name))
    return JsonResponse(json_builder(obj))


def _entity_delete(request, pk, *, Model, redirect_name):
    obj = get_object_or_404(Model, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Registro eliminado correctamente.')
        return redirect(reverse(redirect_name))
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ════════════════════════════════════════════════════════════
# HUB / Dashboard del módulo
# ════════════════════════════════════════════════════════════
@_camaras_required
def hub(request):
    ctx = {
        'n_servidores':  Servidor.objects.count(),
        'n_nvrs':        NVR.objects.count(),
        'n_gabinetes':   Gabinete.objects.count(),
        'n_componentes': Componente.objects.count(),
        'n_camaras':     Camara.objects.count(),
        'n_mant':        MantenimientoCamara.objects.count(),
        'mant_pend':     MantenimientoCamara.objects.filter(status='Pendiente').count(),
        'sin_firma':     MantenimientoCamara.objects.filter(firma_tecnico__isnull=True).count()
                         + MantenimientoCamara.objects.filter(firma_tecnico='').count(),
    }
    return render(request, 'inventario_camaras/hub.html', ctx)


# ════════════════════════════════════════════════════════════
# SERVIDORES
# ════════════════════════════════════════════════════════════
@_camaras_required
def servidores(request):
    return _entity_page(
        request, Model=Servidor, Form=ServidorForm,
        template='inventario_camaras/servidores.html', order=['server_id'],
    )

@_camaras_required
def servidor_editar(request, pk):
    return _entity_edit(
        request, pk, Model=Servidor, Form=ServidorForm,
        redirect_name='inventario_camaras:servidores',
        json_builder=lambda o: {
            'id': o.pk, 'server_id': o.server_id, 'nombre': o.nombre,
            'ubicacion': o.ubicacion, 'ip': o.ip or '', 'observaciones': o.observaciones or '',
        },
    )

@_camaras_required
def servidor_eliminar(request, pk):
    return _entity_delete(request, pk, Model=Servidor, redirect_name='inventario_camaras:servidores')


# ════════════════════════════════════════════════════════════
# NVRs
# ════════════════════════════════════════════════════════════
@_camaras_required
def nvrs(request):
    return _entity_page(
        request, Model=NVR, Form=NVRForm,
        template='inventario_camaras/nvrs.html', order=['nvr_id'],
    )

@_camaras_required
def nvr_editar(request, pk):
    return _entity_edit(
        request, pk, Model=NVR, Form=NVRForm,
        redirect_name='inventario_camaras:nvrs',
        json_builder=lambda o: {
            'id': o.pk, 'nvr_id': o.nvr_id, 'nombre': o.nombre, 'modelo': o.modelo,
            'serie': o.serie, 'ip': o.ip or '', 'canales': o.canales or '',
            'servidor': o.servidor_id or '', 'observaciones': o.observaciones or '',
        },
    )

@_camaras_required
def nvr_eliminar(request, pk):
    return _entity_delete(request, pk, Model=NVR, redirect_name='inventario_camaras:nvrs')


# ════════════════════════════════════════════════════════════
# COMPONENTES
# ════════════════════════════════════════════════════════════
@_camaras_required
def componentes(request):
    return _entity_page(
        request, Model=Componente, Form=ComponenteForm,
        template='inventario_camaras/componentes.html', order=['detalle', 'sub_detalle'],
    )

@_camaras_required
def componente_editar(request, pk):
    return _entity_edit(
        request, pk, Model=Componente, Form=ComponenteForm,
        redirect_name='inventario_camaras:componentes',
        json_builder=lambda o: {
            'id': o.pk, 'comp_id': o.comp_id, 'detalle': o.detalle, 'sub_detalle': o.sub_detalle,
        },
    )

@_camaras_required
def componente_eliminar(request, pk):
    return _entity_delete(request, pk, Model=Componente, redirect_name='inventario_camaras:componentes')


# ════════════════════════════════════════════════════════════
# GABINETES
# ════════════════════════════════════════════════════════════
@_camaras_required
def gabinetes(request):
    return _entity_page(
        request, Model=Gabinete, Form=GabineteForm,
        template='inventario_camaras/gabinetes.html', order=['gabinete_id'],
    )

@_camaras_required
def gabinete_editar(request, pk):
    return _entity_edit(
        request, pk, Model=Gabinete, Form=GabineteForm,
        redirect_name='inventario_camaras:gabinetes',
        json_builder=lambda o: {
            'id': o.pk, 'gabinete_id': o.gabinete_id, 'nombre': o.nombre,
            'ubicacion': o.ubicacion, 'nvr': o.nvr_id or '',
            'componentes': list(o.componentes.values_list('id', flat=True)),
            'observaciones': o.observaciones or '',
        },
    )

@_camaras_required
def gabinete_eliminar(request, pk):
    return _entity_delete(request, pk, Model=Gabinete, redirect_name='inventario_camaras:gabinetes')


# ════════════════════════════════════════════════════════════
# CÁMARAS
# ════════════════════════════════════════════════════════════
@_camaras_required
def camaras(request):
    return _entity_page(
        request, Model=Camara, Form=CamaraForm,
        template='inventario_camaras/camaras.html', order=['camara_id'],
    )

@_camaras_required
def camara_editar(request, pk):
    return _entity_edit(
        request, pk, Model=Camara, Form=CamaraForm,
        redirect_name='inventario_camaras:camaras',
        json_builder=lambda o: {
            'id': o.pk, 'camara_id': o.camara_id, 'modelo': o.modelo, 'serie': o.serie,
            'ubicacion': o.ubicacion, 'gabinete': o.gabinete_id or '', 'grupo': o.grupo,
            'estado': o.estado, 'version_actualizada': o.version_actualizada,
            'observaciones': o.observaciones or '',
        },
    )

@_camaras_required
def camara_eliminar(request, pk):
    return _entity_delete(request, pk, Model=Camara, redirect_name='inventario_camaras:camaras')


# ════════════════════════════════════════════════════════════
# MANTENIMIENTO DE CÁMARAS
# ════════════════════════════════════════════════════════════
def _grupos_camaras():
    """Lista de grupos distintos (no vacíos) existentes en las cámaras."""
    return list(Camara.objects.exclude(grupo='').order_by('grupo')
                .values_list('grupo', flat=True).distinct())


def _camaras_por_grupo_json():
    """{grupo: [ {camara_id, modelo, serie, ubicacion, gabinete, nvr}, ... ]}."""
    data = {}
    for c in Camara.objects.select_related('gabinete__nvr').exclude(grupo='').order_by('camara_id'):
        data.setdefault(c.grupo, []).append({
            'camara_id': c.camara_id, 'modelo': c.modelo, 'serie': c.serie or '',
            'ubicacion': c.ubicacion or '', 'estado': c.estado or '',
            'gabinete': str(c.gabinete) if c.gabinete else '',
            'nvr': str(c.nvr) if c.nvr else '',
        })
    return json.dumps(data)


@_camaras_required
def mantenimiento_dashboard(request):
    if request.method == 'POST':
        form = MantenimientoCamaraForm(request.POST, request.FILES)
        if form.is_valid():
            rec = form.save(commit=False)
            firma = request.POST.get('firma_responsable_data', '').strip()
            if firma:
                rec.firma_responsable = firma
            if not rec.creado_por_id:
                rec.creado_por = request.user
            rec.modificado_por = request.user
            rec.save()
            for f in request.FILES.getlist('fotos'):
                FotoMantenimientoCamara.objects.create(registro=rec, imagen=f)
            messages.success(request, f'Registro {rec.record_id} guardado correctamente.')
        else:
            messages.error(request, f'Error al guardar: {_errores(form)}')
        return redirect('inventario_camaras:mantenimiento')

    records = MantenimientoCamara.objects.select_related('tipo_falla').all().order_by('-date')
    return render(request, 'inventario_camaras/mantenimiento.html', {
        'form':              MantenimientoCamaraForm(),
        'records':           records,
        'total':             records.count(),
        'pendiente':         records.filter(status='Pendiente').count(),
        'en_proceso':        records.filter(status='En Proceso').count(),
        'completado':        records.filter(status='Completado').count(),
        'grupos':            _grupos_camaras(),
        'camaras_grupo_json': _camaras_por_grupo_json(),
        'tipos_falla':       TipoFallaCamara.objects.all().order_by('nombre'),
        'site_url':          SITE_URL,
    })


@_camaras_required
def mantenimiento_editar(request, pk):
    rec = get_object_or_404(MantenimientoCamara, pk=pk)
    if request.method == 'POST':
        form = MantenimientoCamaraForm(request.POST, request.FILES, instance=rec)
        if form.is_valid():
            rec = form.save(commit=False)
            firma = request.POST.get('firma_responsable_data', '').strip()
            if firma:
                rec.firma_responsable = firma
            rec.modificado_por = request.user
            rec.save()
            for f in request.FILES.getlist('fotos'):
                FotoMantenimientoCamara.objects.create(registro=rec, imagen=f)
            messages.success(request, f'Registro {rec.record_id} actualizado correctamente.')
        else:
            messages.error(request, f'Error al actualizar: {_errores(form)}')
        return redirect('inventario_camaras:mantenimiento')

    return JsonResponse({
        'id': rec.pk, 'record_id': rec.record_id, 'grupo': rec.grupo or '',
        'tipo_falla': rec.tipo_falla_id or '', 'date': rec.date.strftime('%Y-%m-%d') if rec.date else '',
        'status': rec.status, 'solucion': rec.solucion or '', 'observaciones': rec.observaciones or '',
        'responsable_nombre': rec.responsable_nombre or '',
    })


@_camaras_required
def mantenimiento_eliminar(request, pk):
    rec = get_object_or_404(MantenimientoCamara, pk=pk)
    if request.method == 'POST':
        rec.delete()
        messages.success(request, 'Registro eliminado correctamente.')
        return redirect('inventario_camaras:mantenimiento')
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ════════════════════════════════════════════════════════════
# FIRMA REMOTA DEL TÉCNICO (link público con token, sin login)
# ════════════════════════════════════════════════════════════
@csrf_protect
def firmar_publico(request, token):
    rec = get_object_or_404(MantenimientoCamara, token_firma=token)

    if rec.firmado:
        return render(request, 'inventario_camaras/firmar.html', {
            'rec': rec, 'ya_firmado': True,
        })

    if request.method == 'POST':
        form = FirmaTecnicoForm(request.POST)
        if form.is_valid():
            rec.tecnico_nombre = form.cleaned_data['tecnico_nombre']
            rec.firma_tecnico  = form.cleaned_data['firma_data']
            rec.firmado_en     = timezone.now()
            rec.save(update_fields=['tecnico_nombre', 'firma_tecnico', 'firmado_en', 'fecha_modificado'])
            return render(request, 'inventario_camaras/firmar.html', {
                'rec': rec, 'exito': True,
            })
    else:
        form = FirmaTecnicoForm()

    return render(request, 'inventario_camaras/firmar.html', {
        'rec': rec, 'form': form,
    })


@_camaras_required
def marcar_firma_solicitada(request, pk):
    """Marca que ya se mandó el link de firma al técnico (AJAX)."""
    rec = get_object_or_404(MantenimientoCamara, pk=pk)
    if request.method == 'POST':
        rec.firma_solicitada = True
        rec.save(update_fields=['firma_solicitada', 'fecha_modificado'])
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ════════════════════════════════════════════════════════════
# PDF de mantenimiento
# ════════════════════════════════════════════════════════════
def _firma_img(b64, RLImage, cm):
    from PIL import Image as PILImage
    b64 = re.sub(r'^data:image/[^;]+;base64,', '', b64)
    img_bytes = base64.b64decode(b64)
    pil_img = PILImage.open(BytesIO(img_bytes)).convert('RGBA')
    bg = PILImage.new('RGB', pil_img.size, (255, 255, 255))
    bg.paste(pil_img, mask=pil_img.split()[3])
    out = BytesIO()
    bg.save(out, format='PNG')
    out.seek(0)
    return RLImage(out, width=6 * cm, height=2.3 * cm)


@_camaras_required
def download_mantenimiento_pdf(request, pk):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import cm as _cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
        Image as RLImage,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from django.contrib.staticfiles import finders

    cm = _cm

    rec = get_object_or_404(MantenimientoCamara, pk=pk)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Mantenimiento de Cámara - {rec.record_id}",
    )

    ORANGE  = colors.HexColor("#c45d0a")
    GRAY_BG = colors.HexColor("#f5f5f5")
    GRAY_LT = colors.HexColor("#eeeeee")
    st_title = ParagraphStyle("title", fontSize=16, fontName="Helvetica-Bold", textColor=ORANGE, spaceAfter=2)
    st_sub   = ParagraphStyle("sub", fontSize=9, fontName="Helvetica", textColor=colors.gray, spaceAfter=6)
    st_label = ParagraphStyle("lbl", fontSize=9, fontName="Helvetica-Bold", textColor=colors.HexColor("#333333"))
    st_value = ParagraphStyle("val", fontSize=9, fontName="Helvetica", textColor=colors.black)
    st_center= ParagraphStyle("ctr", fontSize=8, fontName="Helvetica-Oblique", textColor=colors.gray, alignment=TA_CENTER)

    story = []
    logo_path = finders.find('mantenimiento/img/ana.jpg')
    header = [[
        RLImage(logo_path, width=2.5 * cm, height=2.5 * cm) if logo_path else "",
        [Paragraph("Ficha de Mantenimiento de Cámara", st_title),
         Paragraph("Asociación Nuevo Amanecer – Sistema TechCare", st_sub)],
        Paragraph(f"<b>ID:</b> {rec.record_id}<br/>"
                  f"<b>Fecha:</b> {rec.date.strftime('%d/%m/%Y') if rec.date else '—'}<br/>"
                  f"<b>Estado:</b> {rec.status}",
                  ParagraphStyle("hr", fontSize=9, fontName="Helvetica", alignment=TA_LEFT)),
    ]]
    htbl = Table(header, colWidths=[2.8 * cm, 10 * cm, 4.5 * cm])
    htbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), GRAY_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [htbl, Spacer(1, 0.4 * cm)]

    def _st(t):
        tbl = Table([[Paragraph(t, ParagraphStyle("sec", fontSize=10, fontName="Helvetica-Bold", textColor=colors.white))]], colWidths=[17.3 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ORANGE),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl

    def fr(label, value):
        return [Paragraph(label, st_label), Paragraph(str(value) if value else "—", st_value)]

    def _datatable(rows):
        t = Table(rows, colWidths=[4.3 * cm, 13 * cm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, GRAY_LT]),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#dddddd")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    cams = list(rec.camaras_grupo)
    story += [_st("Grupo de Cámaras"), Spacer(1, 0.1 * cm)]
    story += [_datatable([
        fr("Grupo:", rec.grupo or "—"),
        fr("Cantidad de cámaras:", len(cams)),
    ]), Spacer(1, 0.3 * cm)]

    th = ParagraphStyle("th", fontSize=9, fontName="Helvetica-Bold", textColor=colors.white)
    cam_rows = [[Paragraph(t, th) for t in ("ID", "Modelo", "Serie", "Ubicación", "Gabinete", "Estado")]]
    for c in cams:
        cam_rows.append([
            Paragraph(c.camara_id, st_value), Paragraph(c.modelo or "—", st_value),
            Paragraph(c.serie or "—", st_value), Paragraph(c.ubicacion or "—", st_value),
            Paragraph(str(c.gabinete) if c.gabinete else "—", st_value),
            Paragraph(c.estado or "—", st_value),
        ])
    if len(cam_rows) == 1:
        cam_rows.append([Paragraph("Sin cámaras en este grupo", st_value), "", "", "", "", ""])
    cam_tbl = Table(cam_rows, colWidths=[2.6 * cm, 3.6 * cm, 2.8 * cm, 3.3 * cm, 3 * cm, 2 * cm])
    cam_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_LT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [cam_tbl, Spacer(1, 0.4 * cm)]

    story += [_st("Diagnóstico y Solución"), Spacer(1, 0.1 * cm)]
    story += [_datatable([
        fr("Tipo de Falla:", str(rec.tipo_falla) if rec.tipo_falla else "—"),
        fr("Solución aplicada:", rec.solucion or "—"),
        fr("Observaciones:", rec.observaciones or "—"),
    ]), Spacer(1, 0.4 * cm)]

    # ── Firmas (responsable + técnico) ──
    story += [_st("Firmas de Conformidad"), Spacer(1, 0.3 * cm)]

    def _bloque_firma(b64, nombre, rol):
        cell = []
        if b64:
            try:
                cell.append(_firma_img(b64, RLImage, cm))
            except Exception:
                cell.append(Spacer(1, 2.3 * cm))
        else:
            cell.append(Spacer(1, 2.3 * cm))
        cell.append(HRFlowable(width="80%", thickness=1, color=colors.gray, hAlign="CENTER"))
        cell.append(Spacer(1, 0.1 * cm))
        cell.append(Paragraph(f"<b>{rol}</b>", st_center))
        cell.append(Paragraph(nombre or "—", st_center))
        return cell

    firmas_tbl = Table([[
        _bloque_firma(rec.firma_responsable, rec.responsable_nombre, "Responsable"),
        _bloque_firma(rec.firma_tecnico, rec.tecnico_nombre, "Técnico"),
    ]], colWidths=[8.65 * cm, 8.65 * cm])
    firmas_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story += [firmas_tbl, Spacer(1, 0.5 * cm)]

    story += [HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")), Spacer(1, 0.2 * cm)]
    story.append(Paragraph("Inventario y Mantenimiento de Cámaras – Asociación Nuevo Amanecer &nbsp;|&nbsp; TechCare", st_center))

    doc.build(story)
    buffer.seek(0)
    resp = HttpResponse(buffer.read(), content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="mantenimiento_camara_{rec.record_id}.pdf"'
    return resp


# ── App nueva (React/Next compilado a estático) ───────────────────────────
# <--- hecho por claude code: sirve el index.html del build de Next detrás del
# login de Django. Los assets los sirve Apache desde /static/. No hay proceso
# Node en producción: el build se genera en desarrollo y se copia a static/.
import os
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render


@_camaras_required
def app_spa(request):
    build = os.path.join(settings.BASE_DIR, 'inventario_camaras', 'static',
                         'inventario_camaras', 'app', 'index.html')
    try:
        with open(build, encoding='utf-8') as fh:
            return HttpResponse(fh.read())
    except FileNotFoundError:
        return render(request, 'inventario_camaras/app_pendiente.html', status=200)
