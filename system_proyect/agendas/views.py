import io, os, re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

from .models import GradoAgenda, Agenda, ImagenAgenda

# ── Materias por tipo de grado ────────────────────────────────────────────────
MATERIAS_PRIMARIA = [
    "Math", "Phonics", "Reading", "Language",
    "Science", "Español", "CCSS", "Asociadas",
]
MATERIAS_COLEGIO = [
    "Math", "Spelling", "Reading", "Language", "Science",
    "Español", "CCSS", "Cívica", "Asociadas",
]
MATERIAS_COLEGIO_7_9 = [
    "Matemática", "Dibujo Técnico", "Español", "Ciencias Naturales",
    "Cívica", "Estudios Sociales", "Inglés", "Tecnología",
    "Artística", "Computación", "Orientación", "E. Física",
]
MATERIAS_COLEGIO_10 = [
    "Matemática", "Física Elemental", "Robótica", "Español",
    "Química", "Biología", "Sociología", "Psicología",
    "Historia de Honduras", "Inglés Básico", "Inglés Avanzado",
    "Educ. Física", "Informática",
]
MATERIAS_COLEGIO_11 = [
    "Matemática", "Física Elemental", "Dibujo Téc.", "Robótica",
    "Química", "Biología", "Español", "Historia Universal",
    "Economía", "Antropología", "Artística", "Filosofía",
    "Inglés", "Educ. Física",
]
_MATERIAS_MAP = {
    'colegio_bl':  MATERIAS_COLEGIO,
    'colegio_7_9': MATERIAS_COLEGIO_7_9,
    'colegio_10':  MATERIAS_COLEGIO_10,
    'colegio_11':  MATERIAS_COLEGIO_11,
}


def _materias_para_grado(grado_obj):
    return _MATERIAS_MAP.get(grado_obj.tipo_materias, MATERIAS_PRIMARIA)


def _areas_para_usuario(user, request=None):
    """Devuelve la lista de areas que el usuario puede ver, o None si ve todo."""
    if user.is_superuser:
        return None
    # Cualquier usuario con área seleccionada explícitamente en sesión
    if request and request.session.get("agenda_modo_maestro"):
        area = request.session.get("agenda_area_maestro", "bilingue")
        if area == "colegio":
            return ["colegio"]
        return ["primaria", "colegio_bl"]
    if user.groups.filter(name__in=['coordinador_bilingue', 'coord_progress_bl']).exists():
        return ['primaria', 'colegio_bl']
    if user.groups.filter(name__in=['coordinadores_colegio', 'coordinador_colegio', 'coordinadores']).exists():
        return ['colegio']
    if user.groups.filter(name='maestros_bilingue').exists():
        return ['primaria', 'colegio_bl']
    if user.groups.filter(name='maestros_colegio').exists():
        return ['colegio']
    return None


def _es_coordinador(user):
    return user.is_superuser or user.groups.filter(
        name__in=['coordinador_bilingue', 'coord_progress_bl',
                  'coordinadores_colegio', 'coordinadores']
    ).exists()


# Coordinadores que también son maestros y pueden alternar rol en Agendas
_COORD_MAESTROS = frozenset([
    'cvarela@ana-hn.org',
    'druiz@ana-hn.org',
    'ialcerro@ana-hn.org',
    'jmartinez@ana-hn.org',
])


def _es_coord_maestro(user):
    return user.email.lower() in _COORD_MAESTROS


def _modo_maestro(request):
    """True si el coord-maestro activó el modo maestro en la sesión."""
    return _es_coord_maestro(request.user) and bool(
        request.session.get('agenda_modo_maestro', False)
    )


def _es_coord_efectivo(request):
    """Coordinador efectivo: es coordinador Y NO está en modo maestro."""
    return _es_coordinador(request.user) and not _modo_maestro(request)


def _rol_ctx(request):
    """Contexto de rol que toda vista de agendas debe incluir en render()."""
    return {
        'es_coord':         _es_coord_efectivo(request),
        'es_coord_maestro': _es_coord_maestro(request.user),
        'modo_maestro':     _modo_maestro(request),
    }


# ── TOGGLE MODO MAESTRO / COORDINADOR ─────────────────────────────────────────
@login_required
def toggle_modo_maestro(request):
    if not _es_coord_maestro(request.user):
        return HttpResponseForbidden()
    actual = request.session.get('agenda_modo_maestro', False)
    request.session['agenda_modo_maestro'] = not actual
    if not actual:
        return redirect('agendas:historial_maestro')
    return redirect('agendas:dashboard_coordinador')


# ── FORMULARIO MAESTRO ────────────────────────────────────────────────────────
@login_required
def form_agenda(request):
    if _es_coord_efectivo(request):
        return redirect('agendas:dashboard_coordinador')

    areas = _areas_para_usuario(request.user, request)
    grados_qs = GradoAgenda.objects.filter(activo=True)
    if areas is not None:
        grados_qs = grados_qs.filter(area__in=areas)
    grados = grados_qs
    usuario_actual = request.user.get_full_name() or request.user.username

    grado_obj  = None
    materias   = []
    semana_ini = ''
    semana_fin = ''

    if request.method == 'POST':
        grado_id   = request.POST.get('grado_id')
        semana_ini = request.POST.get('semana_inicio', '')
        semana_fin = request.POST.get('semana_fin', '')
        grado_obj  = GradoAgenda.objects.filter(pk=grado_id, activo=True).first()

        if not grado_obj:
            messages.error(request, "Selecciona un grado válido.")
            return render(request, 'agendas/form_agenda.html', {'grados': grados, **_rol_ctx(request)})

        materias = _materias_para_grado(grado_obj)

        if not semana_ini or not semana_fin:
            return render(request, 'agendas/form_agenda.html', {
                'grados': grados, 'grado_obj': grado_obj,
                'materias': materias, 'semana_ini': semana_ini, 'semana_fin': semana_fin,
                **_rol_ctx(request),
            })

        # ── Construir materias_json ───────────────────────────────────────────
        materias_list = []
        for materia in materias:
            if materia == "Asociadas":
                nombres_aso = request.POST.getlist('materia_Asociadas[]')
                for nombre_aso in nombres_aso[:5]:
                    if not nombre_aso.strip():
                        continue
                    entrada = {
                        'materia':    nombre_aso.strip(),
                        'lunes':      request.POST.get(f'lunes_Asociadas_{nombre_aso}', ''),
                        'martes':     request.POST.get(f'martes_Asociadas_{nombre_aso}', ''),
                        'miercoles':  request.POST.get(f'miercoles_Asociadas_{nombre_aso}', ''),
                        'jueves':     request.POST.get(f'jueves_Asociadas_{nombre_aso}', ''),
                        'viernes':    request.POST.get(f'viernes_Asociadas_{nombre_aso}', ''),
                        'nota':       request.POST.get(f'nota_Asociadas_{nombre_aso}', ''),
                        'docente':    usuario_actual,
                        'es_asociada': True,
                    }
                    materias_list.append(entrada)
            else:
                lunes     = request.POST.get(f'lunes_{materia}', '')
                martes    = request.POST.get(f'martes_{materia}', '')
                miercoles = request.POST.get(f'miercoles_{materia}', '')
                jueves    = request.POST.get(f'jueves_{materia}', '')
                viernes   = request.POST.get(f'viernes_{materia}', '')
                nota      = request.POST.get(f'nota_{materia}', '')
                tiene_contenido = any([lunes, martes, miercoles, jueves, viernes, nota])
                materias_list.append({
                    'materia':   materia,
                    'lunes':     lunes,
                    'martes':    martes,
                    'miercoles': miercoles,
                    'jueves':    jueves,
                    'viernes':   viernes,
                    'nota':      nota,
                    'docente':   usuario_actual if tiene_contenido else '',
                })

        # Verificar que no exista ya una agenda para este grado en la misma semana
        from datetime import date as _date
        try:
            ini_d = _date.fromisoformat(str(semana_ini))
            fin_d = _date.fromisoformat(str(semana_fin))
        except ValueError:
            messages.error(request, "Fechas inválidas.")
            return render(request, 'agendas/form_agenda.html', {
                'grados': grados, 'grado_obj': grado_obj,
                'materias': materias, 'semana_ini': semana_ini, 'semana_fin': semana_fin,
                **_rol_ctx(request),
            })

        existe = Agenda.objects.filter(
            grado=grado_obj,
            semana_inicio__lte=fin_d,
            semana_fin__gte=ini_d,
        ).exists()
        if existe:
            messages.error(
                request,
                f"Ya existe una agenda para {grado_obj.nombre} en esa semana. "
                "Puedes editarla desde la lista de agendas."
            )
            return render(request, 'agendas/form_agenda.html', {
                'grados': grados, 'grado_obj': grado_obj,
                'materias': materias, 'semana_ini': semana_ini, 'semana_fin': semana_fin,
                **_rol_ctx(request),
            })

        Agenda.objects.create(
            usuario=request.user,
            grado=grado_obj,
            semana_inicio=semana_ini,
            semana_fin=semana_fin,
            materias_json=materias_list,
            creado_por=request.user,
        )
        messages.success(request, "¡Agenda registrada correctamente!")
        return redirect('agendas:form_agenda')

    return render(request, 'agendas/form_agenda.html', {
        'grados':     grados,
        'grado_obj':  grado_obj,
        'materias':   materias,
        'semana_ini': semana_ini,
        'semana_fin': semana_fin,
        **_rol_ctx(request),
    })


# ── EDITAR AGENDA ─────────────────────────────────────────────────────────────
@login_required
def editar_agenda(request, pk):
    agenda = get_object_or_404(Agenda, pk=pk)
    es_coord       = _es_coord_efectivo(request)
    usuario_actual = request.user.get_full_name() or request.user.username

    materias = agenda.materias_json or []

    # Imagen por materia (máx 1)
    imagenes_dict = {img.materia: img for img in agenda.imagenes.all() if img.materia}

    # Marcar editabilidad por materia
    for mat in materias:
        docente_guardado = mat.get('docente', '').strip()
        tiene_contenido  = any(mat.get(d, '').strip() for d in ['lunes','martes','miercoles','jueves','viernes','nota'])
        mat['editable'] = (
            es_coord
            or docente_guardado == usuario_actual
            or (not docente_guardado and not tiene_contenido)
        )
        mat['imagen'] = imagenes_dict.get(mat.get('materia', ''))

    materias_regulares = [m for m in materias if not m.get('es_asociada')]
    materias_asociadas = [m for m in materias if m.get('es_asociada')]

    if request.method == 'POST':
        nuevas_materias = []
        for mat in materias:
            nombre = mat.get('materia', '')
            if mat['editable']:
                lunes_n     = request.POST.get(f'lunes_{nombre}', '').strip()
                martes_n    = request.POST.get(f'martes_{nombre}', '').strip()
                miercoles_n = request.POST.get(f'miercoles_{nombre}', '').strip()
                jueves_n    = request.POST.get(f'jueves_{nombre}', '').strip()
                viernes_n   = request.POST.get(f'viernes_{nombre}', '').strip()
                nota_n      = request.POST.get(f'nota_{nombre}', '').strip()

                cambio_real = any([
                    lunes_n     != mat.get('lunes', ''),
                    martes_n    != mat.get('martes', ''),
                    miercoles_n != mat.get('miercoles', ''),
                    jueves_n    != mat.get('jueves', ''),
                    viernes_n   != mat.get('viernes', ''),
                    nota_n      != mat.get('nota', ''),
                ])
                mat['lunes']     = lunes_n
                mat['martes']    = martes_n
                mat['miercoles'] = miercoles_n
                mat['jueves']    = jueves_n
                mat['viernes']   = viernes_n
                mat['nota']      = nota_n

                if not es_coord and cambio_real:
                    tiene = any([lunes_n, martes_n, miercoles_n, jueves_n, viernes_n, nota_n])
                    mat['docente'] = usuario_actual if tiene else ''

            mat.pop('editable', None)
            mat.pop('imagen',   None)
            nuevas_materias.append(mat)

        # Nuevas Asociadas añadidas en el formulario
        ids_nuevas = request.POST.getlist('nueva_aso_ids[]')
        for idx in ids_nuevas:
            nombre_aso = request.POST.get(f'nueva_aso_nombre_{idx}', '').strip()
            if not nombre_aso:
                continue
            lu = request.POST.get(f'nueva_aso_lunes_{idx}',     '').strip()
            ma = request.POST.get(f'nueva_aso_martes_{idx}',    '').strip()
            mi = request.POST.get(f'nueva_aso_miercoles_{idx}', '').strip()
            ju = request.POST.get(f'nueva_aso_jueves_{idx}',    '').strip()
            vi = request.POST.get(f'nueva_aso_viernes_{idx}',   '').strip()
            no = request.POST.get(f'nueva_aso_nota_{idx}',      '').strip()
            nuevas_materias.append({
                'materia':    nombre_aso,
                'lunes':      lu, 'martes': ma, 'miercoles': mi,
                'jueves':     ju, 'viernes': vi, 'nota': no,
                'docente':    usuario_actual if any([lu,ma,mi,ju,vi,no]) else '',
                'es_asociada': True,
            })

        agenda.materias_json  = nuevas_materias
        agenda.modificado_por = request.user
        agenda.save()
        messages.success(request, "Agenda actualizada.")
        if es_coord:
            return redirect('agendas:dashboard_coordinador')
        return redirect('agendas:historial_maestro')

    return render(request, 'agendas/editar_agenda.html', {
        'agenda':             agenda,
        'materias_regulares': materias_regulares,
        'materias_asociadas': materias_asociadas,
        **_rol_ctx(request),
    })


# ── HISTORIAL MAESTRO ─────────────────────────────────────────────────────────
@login_required
def historial_maestro(request):
    if _es_coord_efectivo(request):
        return redirect('agendas:dashboard_coordinador')
    areas = _areas_para_usuario(request.user, request)
    agendas_qs = Agenda.objects.select_related('grado', 'usuario').order_by('-semana_inicio', 'grado__nombre')
    if areas is not None:
        agendas_qs = agendas_qs.filter(grado__area__in=areas)
    return render(request, 'agendas/historial_maestro.html', {
        'agendas': agendas_qs,
        **_rol_ctx(request),
    })


# ── DASHBOARD COORDINADOR ─────────────────────────────────────────────────────
@login_required
def dashboard_coordinador(request):
    if not _es_coordinador(request.user):
        return HttpResponseForbidden()
    areas = _areas_para_usuario(request.user, request)
    agendas_qs = Agenda.objects.select_related('grado', 'usuario').order_by('-semana_inicio', 'grado__nombre')
    if areas is not None:
        agendas_qs = agendas_qs.filter(grado__area__in=areas)
    return render(request, 'agendas/dashboard_coordinador.html', {
        'agendas': agendas_qs,
        'today':   timezone.now().strftime('%Y-%m-%d'),
        **_rol_ctx(request),
    })


# ── SUBIR IMAGEN ──────────────────────────────────────────────────────────────
@login_required
def subir_imagen(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    agenda_id   = request.POST.get('agenda_id')
    imagen      = request.FILES.get('imagen')
    descripcion = request.POST.get('descripcion', '')
    materia     = request.POST.get('materia', '')

    if not agenda_id or not imagen:
        return JsonResponse({'error': 'Datos incompletos'}, status=400)

    agenda = get_object_or_404(Agenda, pk=agenda_id)

    # Si ya existe imagen para esta materia, reemplazarla
    es_coord = _es_coordinador(request.user)
    if materia:
        ImagenAgenda.objects.filter(agenda=agenda, materia=materia).delete()

    img = ImagenAgenda.objects.create(
        agenda=agenda,
        imagen=imagen,
        descripcion=descripcion,
        materia=materia,
        subida_por=request.user,
    )
    return JsonResponse({'ok': True, 'url': img.imagen.url, 'id': img.pk})


# ── ELIMINAR IMAGEN ───────────────────────────────────────────────────────────
@login_required
def eliminar_imagen(request, pk):
    img = get_object_or_404(ImagenAgenda, pk=pk)
    es_coord = _es_coordinador(request.user)
    if img.subida_por != request.user and not es_coord:
        return HttpResponseForbidden()
    img.imagen.delete(save=False)
    img.delete()
    return JsonResponse({'ok': True})


# ── DOCX COLEGIO (Word, A4 horizontal) ──────────────────────────────────────
def _descargar_docx_colegio(agenda):
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor as DocxRGB
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
    from docx.oxml.ns import qn as dqn
    from docx.oxml import OxmlElement

    _MESES_ES = ['enero','febrero','marzo','abril','mayo','junio',
                 'julio','agosto','septiembre','octubre','noviembre','diciembre']

    def _fecha_es(d):
        return f"{d.day} de {_MESES_ES[d.month - 1]}"

    materias = agenda.materias_json or []

    doc = Document()

    section = doc.sections[0]
    section.orientation = 1       # landscape
    section.page_width   = Cm(29.7)
    section.page_height  = Cm(21.0)
    section.left_margin  = Cm(1.5)
    section.right_margin = Cm(1.5)
    section.top_margin   = Cm(1.5)
    section.bottom_margin = Cm(1.0)

    # Estilo de párrafo base
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)

    def _hdr_p(text, size=12, bold=False):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(2)
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.name = 'Calibri'
        return p

    _hdr_p('C. E. M. N. G. NUEVO AMANECER', size=14, bold=True)
    _hdr_p('AGENDA SEMANAL DE TAREAS', size=12, bold=True)

    # Grado y semana — tabla sin bordes de 1 fila / 2 celdas
    sem = (f"Semana del {_fecha_es(agenda.semana_inicio)} "
           f"al {_fecha_es(agenda.semana_fin)} de {agenda.semana_fin.year}")

    info = doc.add_table(rows=1, cols=2)
    info.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell in info.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = OxmlElement('w:tcBorders')
        for side in ('top','left','bottom','right','insideH','insideV'):
            el = OxmlElement(f'w:{side}')
            el.set(dqn('w:val'), 'nil')
            tcBorders.append(el)
        tcPr.append(tcBorders)

    c0, c1 = info.rows[0].cells
    r0 = c0.paragraphs[0].add_run(f'Grado: {agenda.grado.nombre}')
    r0.font.bold = True; r0.font.size = Pt(10); r0.font.name = 'Calibri'
    c1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r1 = c1.paragraphs[0].add_run(sem)
    r1.font.bold = True; r1.font.size = Pt(10); r1.font.name = 'Calibri'

    doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # Tabla de asignaturas
    headers = ['ASIGNATURA', 'LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES']
    tbl = doc.add_table(rows=len(materias) + 1, cols=6)
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    def _set_width(cell, twips):
        tcPr = cell._tc.get_or_add_tcPr()
        tcW  = OxmlElement('w:tcW')
        tcW.set(dqn('w:w'), str(int(twips)))
        tcW.set(dqn('w:type'), 'dxa')
        tcPr.append(tcW)

    def _shd(cell, fill_hex):
        tcPr = cell._tc.get_or_add_tcPr()
        shd  = OxmlElement('w:shd')
        shd.set(dqn('w:val'),   'clear')
        shd.set(dqn('w:color'), 'auto')
        shd.set(dqn('w:fill'),  fill_hex)
        tcPr.append(shd)

    # 1 cm ≈ 567 twips; A4 landscape usable ≈ 26.7 cm
    W_ASIG = int(4.2 * 567)
    W_DIA  = int((26.7 - 4.2) / 5 * 567)

    for ci, hdr in enumerate(headers):
        cell = tbl.cell(0, ci)
        _set_width(cell, W_ASIG if ci == 0 else W_DIA)
        _shd(cell, 'ADC6E0')
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(hdr)
        run.font.bold = True; run.font.size = Pt(10); run.font.name = 'Calibri'

    for ri, mat in enumerate(materias, start=1):
        vals = [mat.get('materia',''), mat.get('lunes',''), mat.get('martes',''),
                mat.get('miercoles',''), mat.get('jueves',''), mat.get('viernes','')]
        for ci, val in enumerate(vals):
            cell = tbl.cell(ri, ci)
            _set_width(cell, W_ASIG if ci == 0 else W_DIA)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            run = p.add_run(val or '')
            run.font.bold = (ci == 0)
            run.font.size = Pt(9); run.font.name = 'Calibri'

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    grado_slug = agenda.grado.nombre.replace(' ', '_')
    filename = f'agenda_col_{grado_slug}_{agenda.semana_inicio}.docx'
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── DESCARGA PPTX ─────────────────────────────────────────────────────────────
@login_required
def descargar_pptx_agenda(request, pk):
    if not _es_coord_efectivo(request):
        return HttpResponseForbidden()
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
    from pptx.oxml.ns import qn
    from lxml import etree

    agenda   = get_object_or_404(Agenda, pk=pk)
    es_coord = _es_coordinador(request.user)

    # ── Colegio: genera DOCX (Word) ──────────────────────────────────────────
    if agenda.grado.area == 'colegio':
        return _descargar_docx_colegio(agenda)


    materias = agenda.materias_json or []

    # Buscar imagen de plantilla subida por el usuario
    import glob as _glob
    from pptx.util import Cm
    _base_img  = '/home/admin2/techcare_project/system_proyect/agendas/static/agendas/img/'
    fondo_path = ''
    for _ext in ('jpg', 'jpeg', 'png'):
        _p = f'{_base_img}plantilla.{_ext}'
        if os.path.exists(_p):
            fondo_path = _p
            break
    if not fondo_path:
        _any = [f for f in _glob.glob(f'{_base_img}*')
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if _any:
            fondo_path = _any[0]

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _shadow(run):
        rPr = run._r.get_or_add_rPr()
        for ex in rPr.findall(qn('a:effectLst')): rPr.remove(ex)
        ef  = etree.SubElement(rPr, qn('a:effectLst'))
        os_ = etree.SubElement(ef,  qn('a:outerShdw'),
                               attrib={'blurRad':'40000','dist':'23000','dir':'5400000','rotWithShape':'0'})
        cl  = etree.SubElement(os_, qn('a:srgbClr'), val='000000')
        etree.SubElement(cl, qn('a:alpha'), val='40000')

    def _run(para, txt, size, bold=False, italic=False, underline=False,
             shadow=False, color=None):
        run = para.add_run()
        run.text = txt
        run.font.name      = 'Book Antiqua'
        run.font.size      = Pt(size)
        run.font.bold      = bold
        run.font.italic    = italic
        run.font.underline = underline
        if color:
            run.font.color.rgb = color
        if shadow:
            _shadow(run)
        return run

    def _borders(cell, w=19050):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        for tag in ('lnL','lnR','lnT','lnB'):
            for ex in tcPr.findall(qn(f'a:{tag}')): tcPr.remove(ex)
        for i, tag in enumerate(('lnL','lnR','lnT','lnB')):
            ln = etree.Element(qn(f'a:{tag}'), attrib={'w': str(w), 'cap':'flat','cmpd':'sng'})
            sf = etree.SubElement(ln, qn('a:solidFill'))
            etree.SubElement(sf, qn('a:srgbClr'), val='000000')
            tcPr.insert(i, ln)

    def _add_line(slide, x1, y1, x2, y2, hex_color='3D3620', w_pt=3):
        """Agrega una línea recta al slide vía XML (cxnSp)."""
        sp_tree = slide.shapes._spTree
        ids = [int(e.get('id', 0)) for e in sp_tree.iter() if e.get('id')]
        sp_id = (max(ids) if ids else 100) + 1
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        off_x  = min(x1, x2);  off_y  = min(y1, y2)
        ext_cx = abs(x2 - x1); ext_cy = abs(y2 - y1)
        fh = 'true' if x2 < x1 else 'false'
        fv = 'true' if y2 < y1 else 'false'
        xml = (
            f'<p:cxnSp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
            f' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<p:nvCxnSpPr><p:cNvPr id="{sp_id}" name="l{sp_id}"/>'
            f'<p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
            f'<p:spPr><a:xfrm flipH="{fh}" flipV="{fv}">'
            f'<a:off x="{off_x}" y="{off_y}"/>'
            f'<a:ext cx="{ext_cx}" cy="{ext_cy}"/></a:xfrm>'
            f'<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
            f'<a:noFill/>'
            f'<a:ln w="{int(w_pt*12700)}">'
            f'<a:solidFill><a:srgbClr val="{hex_color}"/></a:solidFill>'
            f'</a:ln></p:spPr></p:cxnSp>'
        )
        sp_tree.append(etree.fromstring(xml))

    _MESES_ES = ['enero','febrero','marzo','abril','mayo','junio',
                 'julio','agosto','septiembre','octubre','noviembre','diciembre']

    def _fecha_es(d):
        return f"{d.day} de {_MESES_ES[d.month - 1]}"

    # ── Slide con fondo Espiral (PNG como imagen de fondo) ────────────────────
    LEFT_X  = Inches(0.12)
    LEFT_W  = Inches(2.1)
    TAB_X   = Inches(2.35)
    TAB_W   = Inches(10.8)

    prs = Presentation()
    prs.slide_width  = Emu(12192000)
    prs.slide_height = Emu(6858000)
    slide  = prs.slides.add_slide(prs.slide_layouts[6])
    SLIDE_W = prs.slide_width
    SLIDE_H = prs.slide_height

    if fondo_path:
        slide.shapes.add_picture(fondo_path, 0, 0, width=SLIDE_W, height=SLIDE_H)
    else:
        bg = slide.background.fill; bg.solid()
        bg.fore_color.rgb = RGBColor(245, 245, 228)
        pan = slide.shapes.add_shape(1, 0, 0, TAB_X, SLIDE_H)
        pan.fill.solid(); pan.fill.fore_color.rgb = RGBColor(50, 44, 24)
        pan.line.fill.background()
        for _i in range(-3, 20):
            _y0 = Inches(_i * 0.52)
            _add_line(slide, x1=0, y1=_y0, x2=TAB_X, y2=_y0 + Inches(2.4),
                      hex_color='3A3318', w_pt=3)
        acc = slide.shapes.add_shape(1, TAB_X - Inches(0.15), 0, Inches(0.15), SLIDE_H)
        acc.fill.solid(); acc.fill.fore_color.rgb = RGBColor(130, 100, 45)
        acc.line.fill.background()

    # ── Texto panel izquierdo ─────────────────────────────────────────────────
    CLR_DARK  = RGBColor(30, 30, 30)    # negro para título y semana
    CLR_WHITE = RGBColor(255, 255, 255) # blanco para texto dentro de la flecha

    tb = slide.shapes.add_textbox(LEFT_X, Inches(0.1), LEFT_W, Inches(2.2))
    tb.fill.background(); tb.line.fill.background()
    tf = tb.text_frame; tf.clear(); tf.word_wrap = True
    p  = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
    _run(p, 'Agenda\nSemanal.', 30, bold=True, italic=True, shadow=True, color=CLR_DARK)

    sem = f"{_fecha_es(agenda.semana_inicio)} al {_fecha_es(agenda.semana_fin)}"
    tb = slide.shapes.add_textbox(LEFT_X, Inches(2.5), LEFT_W, Inches(2.0))
    tb.fill.background(); tb.line.fill.background()
    tf = tb.text_frame; tf.clear(); tf.word_wrap = True
    p  = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
    _run(p, 'Semana:', 19, bold=True, italic=True, underline=True, shadow=True, color=CLR_DARK)
    p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.LEFT
    _run(p2, sem, 17, italic=True, shadow=True, color=CLR_DARK)

    # Textbox transparente sobre la flecha roja de la plantilla
    tb = slide.shapes.add_textbox(Inches(0.05), Inches(5.0), Inches(2.25), Inches(0.75))
    tb.fill.background(); tb.line.fill.background()
    tf = tb.text_frame; tf.clear(); tf.word_wrap = False
    p  = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    _run(p, f'Grado: {agenda.grado.nombre}', 13, bold=True, italic=True, color=CLR_WHITE)

    # ── Tabla ─────────────────────────────────────────────────────────────────
    num_rows = len(materias) + 1
    tbl_shape = slide.shapes.add_table(num_rows, 7, TAB_X, Inches(0.05), TAB_W, SLIDE_H - Inches(0.1))
    tbl = tbl_shape.table

    # Sin bandas de estilo
    tblPr = tbl._tbl.find(qn('a:tblPr'))
    if tblPr is None:
        tblPr = etree.SubElement(tbl._tbl, qn('a:tblPr'))
    for _at in ('bandRow','bandCol','firstRow','firstCol','lastRow','lastCol'):
        tblPr.set(_at, '0')
    for _el in tblPr.findall(qn('a:tableStyleId')): tblPr.remove(_el)
    etree.SubElement(tblPr, qn('a:tableStyleId')).text = '{2D5ABB26-0587-4C30-8999-92F81FD0307C}'

    # Anchos columnas → total 10.8"
    for _i, _w in enumerate([Inches(1.3),
                              Inches(1.55), Inches(1.55), Inches(1.55),
                              Inches(1.55), Inches(1.55), Inches(1.75)]):
        tbl.columns[_i].width = _w

    def _cell(cell, txt, bold=False, align=PP_ALIGN.CENTER, header=False):
        # Limpiar retornos de carro Windows (\r) que generan "_x000D_" en PPTX
        txt = (txt or '').replace('\r\n', '\n').replace('\r', '')
        cell.text = txt
        _borders(cell)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(235, 238, 215) if header else RGBColor(255, 255, 255)
        tf   = cell.text_frame
        tf.word_wrap = True
        para = tf.paragraphs[0]
        para.font.name      = 'Arial'
        para.font.size      = Pt(11)
        para.font.bold      = bold
        para.font.color.rgb = RGBColor(0, 0, 0)
        para.alignment      = align
        # Encoger texto para que quepa en la altura fija de 1.8 cm
        txBody = cell._tc.find(qn('a:txBody'))
        if txBody is not None:
            bodyPr = txBody.find(qn('a:bodyPr'))
            if bodyPr is not None:
                for _t in (qn('a:noAutofit'), qn('a:normAutofit'), qn('a:spAutoFit')):
                    for _e in bodyPr.findall(_t): bodyPr.remove(_e)
                bodyPr.set('anchor', 'ctr')     # centrado vertical
                bodyPr.set('anchorCtr', '1')
                etree.SubElement(bodyPr, qn('a:normAutofit'))

    headers = ['Clase/Día', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Nota']
    for _i, _h in enumerate(headers):
        _cell(tbl.cell(0, _i), _h, bold=True, header=True)

    for _row, mat in enumerate(materias, start=1):
        _cell(tbl.cell(_row, 0), mat.get('materia',   ''), bold=True)
        _cell(tbl.cell(_row, 1), mat.get('lunes',     ''))
        _cell(tbl.cell(_row, 2), mat.get('martes',    ''))
        _cell(tbl.cell(_row, 3), mat.get('miercoles', ''))
        _cell(tbl.cell(_row, 4), mat.get('jueves',    ''))
        _cell(tbl.cell(_row, 5), mat.get('viernes',   ''))
        _cell(tbl.cell(_row, 6), mat.get('nota',      ''))

    # Altura fija 1.8 cm por fila (el texto se encoge si no cabe)
    for _i in range(num_rows):
        tbl.rows[_i].height = Cm(1.8)

    # ── Descarga ──────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    grado_slug = agenda.grado.nombre.replace(' ', '_')
    filename = f'agenda_{grado_slug}_{agenda.semana_inicio}.pptx'
    response = HttpResponse(buf.getvalue(),
                            content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── ELIMINAR AGENDA ───────────────────────────────────────────────────────────
@login_required
def eliminar_agenda(request, pk):
    if not _es_coordinador(request.user):
        return JsonResponse({'error': 'Sin permiso'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    agenda = get_object_or_404(Agenda, pk=pk)
    agenda.delete()
    return JsonResponse({'ok': True})
