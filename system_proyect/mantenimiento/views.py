import datetime
import os
import textwrap
from io import BytesIO
from PIL import Image as PILImage

from django.urls import reverse
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


# <--- hecho por claude code: ID propio para Control de equipo (ANAMAESCTRL-001)
def _siguiente_record_id_control():
    prefix = 'ANAMAESCTRL-'
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


# <--- hecho por claude code (17-sep-2026): prefijos de Entrega / Recogida de equipo
PREFIJO_ENTREGA  = 'ANAMAESENT-'
PREFIJO_RECOGIDA = 'ANAMAESREC-'
PREFIJO_CASO     = 'ANAMAESCE-'    # <--- hecho por claude code (28-sep-2026): recogida por caso especial
PREFIJO_CAMBIO   = 'ANAMAESCAM-'   # <--- hecho por claude code (28-sep-2026): cambio de equipo
PREFIJO_REASIG   = 'ANAMAESREA-'   # <--- hecho por claude code (12-oct-2026): reasignación de computadora (maestro A → maestro B)
PREFIJO_PRESTAMO = 'ANAMAESPRE-'   # <--- hecho por claude code (16-oct-2026): préstamo de equipo
PREFIJO_MANT     = 'ANAMAESMANT-'  # <--- hecho por claude code (21-oct-2026): mantenimiento
PREFIJO_REP      = 'ANAMAESREP-'   # <--- hecho por claude code (21-oct-2026): reparación
TIPOS_PORTADOR_ACTUAL = ('control', 'inspeccion', 'entrega', 'recogida', 'caso_especial', 'cambio_equipo')   # maestro/grado SIEMPRE del inventario


def _siguiente_record_id_prefijo(prefix):
    ultimo = (MaintenanceRecord.objects.filter(record_id__startswith=prefix)
              .order_by('-record_id').values_list('record_id', flat=True).first())
    try:
        n = int(ultimo[len(prefix):]) if ultimo else 0
    except ValueError:
        n = 0
    return f"{prefix}{n+1:03d}"


# <--- hecho por claude code: ID propio para Inspección (ANAMAESINSP-001)
def _siguiente_record_id_inspeccion():
    prefix = 'ANAMAESINSP-'
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


# <--- hecho por claude code (28-sep-2026): una PÁGINA por tipo de ficha (antes 7 pestañas en un dashboard).
FICHAS_TIPOS = {   # slug de URL → (tipo_equipo, etiqueta, plantilla)
    'computadoras':     ('computadora',   'Computadoras',       'mantenimiento/fichas_computadoras.html'),
    'impresoras':       ('impresora',     'Impresoras',         'mantenimiento/fichas_impresoras.html'),
    'control':          ('control',       'Control de equipos', 'mantenimiento/fichas_control.html'),
    'inspecciones':     ('inspeccion',    'Inspecciones',       'mantenimiento/fichas_inspecciones.html'),
    'entregas':         ('entrega',       'Entregas',           'mantenimiento/fichas_entregas.html'),
    'recogidas':        ('recogida',      'Recogidas',          'mantenimiento/fichas_recogidas.html'),
    'casos-especiales': ('caso_especial', 'Casos especiales',   'mantenimiento/fichas_casos_especiales.html'),
    'cambios-equipo':   ('cambio_equipo', 'Cambios de equipo',   'mantenimiento/fichas_cambios_equipo.html'),
    'reasignaciones':   ('reasignacion',  'Reasignaciones',      'mantenimiento/fichas_reasignaciones.html'),   # <--- hecho por claude code (12-oct-2026)
    'prestamos':        ('prestamo',      'Préstamos de equipo', 'mantenimiento/fichas_prestamos.html'),        # <--- hecho por claude code (16-oct-2026)
    'mantenimientos':   ('mantenimiento', 'Mantenimientos',      'mantenimiento/fichas_mantenimientos.html'),    # <--- hecho por claude code (21-oct-2026)
    'reparaciones':     ('reparacion',    'Reparaciones',        'mantenimiento/fichas_reparaciones.html'),      # <--- hecho por claude code (21-oct-2026)
}
SLUG_POR_TIPO = {v[0]: k for k, v in FICHAS_TIPOS.items()}


def _redirect_fichas(tipo_equipo):
    """Vuelve a la página del tipo de ficha (computadora → /mantenimiento/computadoras/)."""
    return redirect('mantenimiento:fichas', tipo=SLUG_POR_TIPO.get(tipo_equipo, 'computadoras'))


def _aplicar_cambio_en_inventario(cam, obs_nueva=''):
    """<--- hecho por claude code (28-sep-2026): el Asset ID se queda con el maestro; se actualiza el HARDWARE de la
    computadora (modelo, serie, IP) con los datos del equipo nuevo. El historial de Computadora conserva lo anterior
    y en observaciones queda la nota con el número de ficha."""
    comp = cam.computadora
    if not comp:
        return
    fecha = cam.date.strftime('%d/%m/%Y') if cam.date else ''
    ant = ' · '.join(x for x in [cam.modelo_anterior, ('Serie ' + cam.serie_anterior) if cam.serie_anterior else '', ('IP ' + cam.ip_anterior) if cam.ip_anterior else ''] if x) or '—'
    nue = ' · '.join(x for x in [cam.modelo_nuevo, ('Serie ' + cam.serie_nuevo) if cam.serie_nuevo else '', ('IP ' + cam.ip_nuevo) if cam.ip_nuevo else ''] if x) or '—'
    nota = f'[{cam.record_id} · {fecha}] Cambio de equipo: {ant} → {nue}.'
    if cam.modelo_nuevo:
        comp.modelo = cam.modelo_nuevo
    comp.serie = cam.serie_nuevo
    if cam.ip_nuevo:
        comp.ip = cam.ip_nuevo
    comp.observaciones = '\n'.join(x for x in [(comp.observaciones or '').strip(), (obs_nueva or '').strip(), nota] if x)
    comp.save(update_fields=['modelo', 'serie', 'ip', 'observaciones'])


def _aplicar_reasignacion_en_inventario(rea):
    """<--- hecho por claude code (12-oct-2026): la MISMA computadora (Asset ID y hardware) pasa del maestro A al B.
    Se actualizan asignado/área/grado/edificio; el historial de Computadora conserva los datos anteriores y en
    observaciones queda la nota con el número de ficha."""
    comp = rea.computadora
    if not comp:
        return
    fecha = rea.date.strftime('%d/%m/%Y') if rea.date else ''
    nota = (f'[{rea.record_id} · {fecha}] Reasignación: {rea.asignado_anterior or "—"} ({rea.grado_anterior or "—"}) '
            f'→ {rea.asignado_nuevo} ({rea.grado_nuevo or rea.grado_anterior or "—"}).')
    comp.asignado_a = rea.asignado_nuevo
    if rea.area_nueva:
        comp.area = rea.area_nueva
    if rea.grado_nuevo:
        comp.grado = rea.grado_nuevo
    if rea.edificio_nuevo:
        comp.edificio = rea.edificio_nuevo
    comp.observaciones = '\n'.join(x for x in [(comp.observaciones or '').strip(), nota] if x)
    comp.save(update_fields=['asignado_a', 'area', 'grado', 'edificio', 'observaciones'])


def _crear_derivados_del_control(request, record, messages):
    """<--- hecho por claude code (28-sep-2026): un CONTROL con "cambio de equipo" / "caso especial" crea a la vez la ficha
    derivada (usado al crear Y al editar el control). Un control admite como máximo UNA de cada; si ya existe, no se duplica."""
    if record.tipo_equipo != 'control':
        return
    if request.POST.get('cambio_equipo') and (record.modelo_nuevo or record.serie_nuevo) and record.computadora_id:
        if record.casos_especiales.filter(tipo_equipo='cambio_equipo').exists():
            messages.info(request, f'El control {record.record_id} ya tiene un cambio de equipo registrado.')
        else:
            comp = record.computadora
            cam = MaintenanceRecord(
                tipo_equipo='cambio_equipo', record_id=_siguiente_record_id_prefijo(PREFIJO_CAMBIO),
                computadora=comp, model=comp.modelo or '', serie=comp.serie or '',
                modelo_anterior=comp.modelo or '', serie_anterior=comp.serie or '', ip_anterior=comp.ip or '',
                modelo_nuevo=record.modelo_nuevo, serie_nuevo=record.serie_nuevo, ip_nuevo=record.ip_nuevo,
                teacher_name=record.teacher_name, grade=record.grade,
                control_origen=record, obs_tecnico=record.obs_tecnico, firma_nombre=record.teacher_name or '',
                date=record.date, status='Completado', creado_por=getattr(record, 'creado_por', None))
            cam.save()
            for f in record.fotos.all():
                FotoMantenimiento.objects.create(registro=cam, imagen=f.imagen, orden=f.orden)
            _aplicar_cambio_en_inventario(cam, request.POST.get('obs_equipo_nuevo', ''))
            messages.success(request, f'Cambio de equipo {cam.record_id} creado junto con el control {record.record_id}. '
                                      f'Inventario actualizado: {comp.asset_id} ahora es {cam.modelo_nuevo or cam.serie_nuevo}.')
        MaintenanceRecord.objects.filter(pk=record.pk).update(modelo_anterior='', serie_anterior='', ip_anterior='',
                                                             modelo_nuevo='', serie_nuevo='', ip_nuevo='')
    # <--- hecho por claude code (12-oct-2026): REASIGNACIÓN — la computadora del control pasa al maestro B
    if request.POST.get('reasignacion') and (request.POST.get('asignado_nuevo') or '').strip() and record.computadora_id:
        if record.casos_especiales.filter(tipo_equipo='reasignacion').exists():
            messages.info(request, f'El control {record.record_id} ya tiene una reasignación registrada.')
        else:
            comp = record.computadora
            P = request.POST
            rea = MaintenanceRecord(
                tipo_equipo='reasignacion', record_id=_siguiente_record_id_prefijo(PREFIJO_REASIG),
                computadora=comp, model=comp.modelo or '', serie=comp.serie or '',
                asignado_anterior=comp.asignado_a or '', area_anterior=comp.area or '',
                grado_anterior=comp.grado or '', edificio_anterior=comp.edificio or '',
                asignado_nuevo=P.get('asignado_nuevo', '').strip()[:150],
                area_nueva=(P.get('area_nueva') or '').strip()[:100] or (comp.area or ''),
                grado_nuevo=(P.get('grado_nuevo') or '').strip()[:50] or (comp.grado or ''),
                edificio_nuevo=(P.get('edificio_nuevo') or '').strip()[:100] or (comp.edificio or ''),
                teacher_name=P.get('asignado_nuevo', '').strip()[:150],
                grade=(P.get('grado_nuevo') or '').strip()[:50] or (comp.grado or ''),
                control_origen=record, obs_tecnico=record.obs_tecnico, firma_nombre=P.get('asignado_nuevo', '').strip()[:150],
                date=record.date, status='Completado', creado_por=getattr(record, 'creado_por', None))
            rea.save()
            for f in record.fotos.all():
                FotoMantenimiento.objects.create(registro=rea, imagen=f.imagen, orden=f.orden)
            _aplicar_reasignacion_en_inventario(rea)
            messages.success(request, f'Reasignación {rea.record_id} creada junto con el control {record.record_id}. '
                                      f'Inventario actualizado: {comp.asset_id} pasó de {rea.asignado_anterior or "—"} a {rea.asignado_nuevo}.')
    # <--- hecho por claude code (21-oct-2026): MANTENIMIENTO (solo comentario) o REPARACIÓN (preguntas + asistido por + PDF firmado)
    if request.POST.get('mantenimiento') and record.computadora_id:
        P = request.POST
        es_rep = bool(P.get('es_reparacion'))
        tipo = 'reparacion' if es_rep else 'mantenimiento'
        if record.casos_especiales.filter(tipo_equipo=tipo).exists():
            messages.info(request, f'El control {record.record_id} ya tiene {"una reparación" if es_rep else "un mantenimiento"} registrado.')
        else:
            comp = record.computadora
            m = MaintenanceRecord(
                tipo_equipo=tipo, record_id=_siguiente_record_id_prefijo(PREFIJO_REP if es_rep else PREFIJO_MANT),
                computadora=comp, model=comp.modelo or '', serie=comp.serie or '',
                teacher_name=record.teacher_name, grade=record.grade, control_origen=record,
                mant_comentario=(P.get('mant_comentario') or '').strip()[:2000],
                date=record.date, status='Pendiente' if es_rep else 'Completado',
                creado_por=getattr(record, 'creado_por', None))
            if es_rep:
                m.rep_que_danado = (P.get('rep_que_danado') or '').strip()[:2000]
                m.rep_que_reparacion = (P.get('rep_que_reparacion') or '').strip()[:2000]
                m.rep_como_dano = (P.get('rep_como_dano') or '').strip()[:2000]
                m.rep_asistido_por = (P.get('rep_asistido_por') or '').strip()[:150]
            m.save()
            for f in record.fotos.all():
                FotoMantenimiento.objects.create(registro=m, imagen=f.imagen, orden=f.orden)
            messages.success(request, f'{"Reparación" if es_rep else "Mantenimiento"} {m.record_id} creado junto con el control {record.record_id}.'
                                      + (' Imprime la ficha, fírmala y sube el PDF firmado.' if es_rep else ''))
    if request.POST.get('caso_especial'):
        if record.casos_especiales.filter(tipo_equipo='caso_especial').exists():
            messages.info(request, f'El control {record.record_id} ya tiene una recogida por caso especial.')
        else:
            ce = MaintenanceRecord(
                tipo_equipo='caso_especial', record_id=_siguiente_record_id_prefijo(PREFIJO_CASO),
                computadora=record.computadora, model=record.model, serie=record.serie,
                teacher_name=record.teacher_name, grade=record.grade, control_origen=record,
                ent_equipo=record.ent_equipo, ent_mouse_teclado=record.ent_mouse_teclado,
                ent_televisor=record.ent_televisor, ent_control_tv=record.ent_control_tv, televisor=record.televisor,
                firma_nombre=record.firma_nombre, fecha_hora=record.fecha_hora, obs_tecnico=record.obs_tecnico,
                date=(record.fecha_hora.date() if record.fecha_hora else record.date), status='Completado',
                creado_por=getattr(record, 'creado_por', None))
            ce.save()
            for f in record.fotos.all():
                FotoMantenimiento.objects.create(registro=ce, imagen=f.imagen, orden=f.orden)
            messages.success(request, f'Recogida por caso especial {ce.record_id} creada junto con el control {record.record_id}.')
        # el control conserva su ficha limpia: el checklist vive en la recogida
        MaintenanceRecord.objects.filter(pk=record.pk).update(ent_equipo=False, ent_mouse_teclado=False, ent_televisor=False,
                                                             ent_control_tv=False, televisor=None, firma_nombre='', fecha_hora=None)


@login_required
def maintenance_dashboard(request, tipo='computadoras'):
    from django.http import Http404
    if tipo not in FICHAS_TIPOS:
        raise Http404('Tipo de ficha no disponible')
    tipo_equipo, tipo_label, plantilla = FICHAS_TIPOS[tipo]
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
                # <--- hecho por claude code: control de equipo lleva su propia numeración
                record.record_id = (_siguiente_record_id_control() if record.tipo_equipo == 'control'
                                    else _siguiente_record_id_inspeccion() if record.tipo_equipo == 'inspeccion'
                                    else _siguiente_record_id_prefijo(PREFIJO_ENTREGA) if record.tipo_equipo == 'entrega'
                                    else _siguiente_record_id_prefijo(PREFIJO_RECOGIDA) if record.tipo_equipo == 'recogida'
                                    else _siguiente_record_id_prefijo(PREFIJO_CASO) if record.tipo_equipo == 'caso_especial'
                                    else _siguiente_record_id_prefijo(PREFIJO_CAMBIO) if record.tipo_equipo == 'cambio_equipo'
                                    else _siguiente_record_id_prefijo(PREFIJO_PRESTAMO) if record.tipo_equipo == 'prestamo'
                                    else _siguiente_record_id())
                comp = record.computadora
                if comp:
                    # <--- hecho por claude code: el CONTROL/INSPECCIÓN evalúa al portador ACTUAL del
                    # equipo, así que maestro/grado se toman SIEMPRE del inventario (no del formulario).
                    if record.tipo_equipo in TIPOS_PORTADOR_ACTUAL:
                        record.teacher_name = comp.asignado_a or ''
                        record.grade = comp.grado or ''
                    else:
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
            _aplicar_prestamo(record, request.POST)   # <--- hecho por claude code (16-oct-2026)
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
            # <--- hecho por claude code (28-sep-2026): un CONTROL con "caso especial" crea a la vez la recogida
            # (tipo caso_especial) con el checklist, firma, fecha/hora y fotos capturados en el mismo formulario.
            _crear_derivados_del_control(request, record, messages)
        else:
            from django.contrib import messages
            errores = '; '.join(
                f"{field}: {', '.join(errs)}"
                for field, errs in form.errors.items()
                if field != '__all__'
            )
            messages.error(request, f'Error al guardar: {errores or "Verifica los campos requeridos."}')
            return _redirect_fichas(request.POST.get('tipo_equipo') or tipo_equipo)
        return _redirect_fichas(record.tipo_equipo)

    form = MaintenanceRecordForm()

    records = (MaintenanceRecord.objects.select_related('computadora', 'impresora', 'tipo_falla', 'televisor', 'control_origen')
               .prefetch_related('fotos', 'casos_especiales').order_by('-date'))

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
            # <--- hecho por claude code (28-sep-2026): para el modal "Equipo nuevo" del cambio de equipo
            'asset':    c.asset_id, 'ip': c.ip or '', 'edificio': c.edificio or '',
            'fecha':    c.fecha_instalado.strftime('%Y-%m-%d') if c.fecha_instalado else '',
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

    # <--- hecho por claude code: la tabla va en 3 pestañas por tipo de equipo
    records_comp = [r for r in records if r.tipo_equipo == 'computadora']
    records_imp  = [r for r in records if r.tipo_equipo == 'impresora']
    records_ctrl = [r for r in records if r.tipo_equipo == 'control']
    records_insp = [r for r in records if r.tipo_equipo == 'inspeccion']
    # <--- hecho por claude code (17-sep-2026): Entrega / Recogida de equipo
    records_ent  = [r for r in records if r.tipo_equipo == 'entrega']
    records_rec  = [r for r in records if r.tipo_equipo == 'recogida']
    records_ce   = [r for r in records if r.tipo_equipo == 'caso_especial']   # <--- hecho por claude code (28-sep-2026)
    records_cam  = [r for r in records if r.tipo_equipo == 'cambio_equipo']
    records_rea  = [r for r in records if r.tipo_equipo == 'reasignacion']   # <--- hecho por claude code (12-oct-2026)
    records_pre  = [r for r in records if r.tipo_equipo == 'prestamo']       # <--- hecho por claude code (16-oct-2026)
    records_man  = [r for r in records if r.tipo_equipo == 'mantenimiento']  # <--- hecho por claude code (21-oct-2026)
    records_rep  = [r for r in records if r.tipo_equipo == 'reparacion']
    from inventario.models import Televisor
    # <--- hecho por claude code (28-sep-2026): cada página es INDIVIDUAL: KPIs y "Nuevo" solo de su tipo
    regs_tipo = [r for r in records if r.tipo_equipo == tipo_equipo]
    iconos = {'computadora': 'ti-device-desktop', 'impresora': 'ti-printer', 'control': 'ti-clipboard-check', 'inspeccion': 'ti-zoom-check',
              'entrega': 'ti-package-export', 'recogida': 'ti-package-import', 'caso_especial': 'ti-alert-octagon', 'cambio_equipo': 'ti-replace', 'reasignacion': 'ti-arrows-exchange', 'prestamo': 'ti-transfer-out', 'mantenimiento': 'ti-tool', 'reparacion': 'ti-tools'}
    colores = {'computadora': '#206bc4', 'impresora': '#f76707', 'control': '#0ca678', 'inspeccion': '#f59f00',
               'entrega': '#2fb344', 'recogida': '#ae3ec9', 'caso_especial': '#d6336c', 'cambio_equipo': '#4263eb', 'reasignacion': '#0891b2', 'prestamo': '#7048e8', 'mantenimiento': '#0ca678', 'reparacion': '#e8590c'}
    return render(request, plantilla, {
        'tipo_actual':       tipo,
        'tipo_label':        tipo_label,
        'tipo_equipo':       tipo_equipo,
        'tipo_icon':         iconos.get(tipo_equipo, 'ti-tool'),
        'tipo_color':        colores.get(tipo_equipo, '#206bc4'),
        'crea_desde_control': tipo_equipo in ('caso_especial', 'cambio_equipo', 'reasignacion', 'mantenimiento', 'reparacion'),
        'kpi_total':         len(regs_tipo),
        'kpi_pendiente':     sum(1 for r in regs_tipo if r.status == 'Pendiente'),
        'kpi_proceso':       sum(1 for r in regs_tipo if r.status == 'En Proceso'),
        'kpi_completado':    sum(1 for r in regs_tipo if r.status == 'Completado'),
        'kpi_mes':           sum(1 for r in regs_tipo if r.date and r.date >= datetime.date.today().replace(day=1)),
        'form':              form,
        'records':           records,
        'records_comp':      records_comp,
        'records_imp':       records_imp,
        'records_ctrl':      records_ctrl,
        'records_insp':      records_insp,
        'records_ent':       records_ent,
        'records_rec':       records_rec,
        'records_ce':        records_ce,
        'records_cam':       records_cam,
        'records_rea':       records_rea,
        'records_pre':       records_pre,
        'records_man':       records_man,
        'records_rep':       records_rep,
        'next_record_id_pre': _siguiente_record_id_prefijo(PREFIJO_PRESTAMO),
        'hoy':               datetime.date.today(),
        'next_record_id_ce': _siguiente_record_id_prefijo(PREFIJO_CASO),
        'televisores':       Televisor.objects.order_by('asset_id'),
        # <--- hecho por claude code (17-sep-2026): la firma de entrega/recogida se ELIGE de la lista de maestros
        # (asignados del inventario + catálogo de Mantenimiento), no se escribe a mano.
        'firmantes':         sorted({(x or '').strip() for x in list(comps_qs.values_list('asignado_a', flat=True))
                                     + list(MaestroMantenimiento.objects.values_list('nombre', flat=True)) if (x or '').strip()},
                                    key=lambda x: x.lower()),
        'next_record_id_ent': _siguiente_record_id_prefijo(PREFIJO_ENTREGA),
        'next_record_id_rec': _siguiente_record_id_prefijo(PREFIJO_RECOGIDA),
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
        'next_record_id_ctrl': _siguiente_record_id_control(),
        'next_record_id_insp': _siguiente_record_id_inspeccion(),
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
    if record.es_prestamo:   # <--- hecho por claude code (16-oct-2026): la solicitud de préstamo es una CARTA con 4 firmas
        from .prestamo import pdf_solicitud
        return pdf_solicitud(record)
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=(f"Ficha de Control de Equipo - {record.record_id}" if record.es_control
               else f"Ficha de Inspección - {record.record_id}" if record.es_inspeccion
               else f"Ficha de Entrega de Equipo - {record.record_id}" if record.es_entrega
               else f"Ficha de Recogida de Equipo - {record.record_id}" if record.es_recogida
               else f"Ficha de Recogida por Caso Especial - {record.record_id}" if record.es_caso_especial
               else f"Ficha de Cambio de Equipo - {record.record_id}" if record.es_cambio
               else f"Ficha de Reasignación de Computadora - {record.record_id}" if record.es_reasignacion
               else f"Ficha de Reparación de Equipo - {record.record_id}" if record.es_reparacion
               else f"Ficha de Mantenimiento - {record.record_id}"),
    )

    styles = getSampleStyleSheet()
    ORANGE  = colors.HexColor("#c45d0a")
    GRAY_BG = colors.HexColor("#f5f5f5")
    GRAY_LT = colors.HexColor("#eeeeee")

    st_title = ParagraphStyle("title", fontSize=16, leading=19, fontName="Helvetica-Bold",   # <--- hecho por claude code (17-sep-2026): leading para que no se monte sobre el subtítulo
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
            Paragraph("Ficha de Control de Equipo" if record.es_control
                      else "Ficha de Inspección del Espacio de Trabajo" if record.es_inspeccion
                      else "Ficha de Entrega de Equipo" if record.es_entrega
                      else "Ficha de Recogida de Equipo" if record.es_recogida
                      else "Ficha de Recogida por Caso Especial" if record.es_caso_especial
                      else "Ficha de Cambio de Equipo" if record.es_cambio
                      else "Ficha de Reasignación de Computadora" if record.es_reasignacion
                      else "Ficha de Reparación de Equipo" if record.es_reparacion
                      else "Ficha de Mantenimiento de Equipo", st_title),
            Paragraph("Asociación Nuevo Amanecer – Sistema TechCare", st_sub),
        ],
        Paragraph(f"<b>ID:</b> {record.record_id}<br/>"
                  f"<b>Fecha:</b> {record.date.strftime('%d/%m/%Y')}<br/>"
                  + (f"<b>Estado del equipo:</b> {record.get_estado_equipo_display() or '—'}" if record.es_control
                     else f"<b>Estado:</b> {record.status}"),
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
    story.append(_st("Evaluación del Equipo" if record.es_control
                     else "Inspección del Espacio de Trabajo" if record.es_inspeccion
                     else "Equipo que se entrega al usuario" if record.es_entrega
                     else "Equipo que recibe Soporte Técnico" if record.es_recogida
                     else "Equipo que recibe Soporte Técnico (caso especial)" if record.es_caso_especial
                     else "Cambio de equipo" if record.es_cambio
                     else "Reasignación de computadora" if record.es_reasignacion
                     else "Reparación realizada" if record.es_reparacion
                     else "Mantenimiento realizado" if record.es_mantenimiento
                     else "Diagnóstico y Solución"))
    story.append(Spacer(1, 0.1*cm))

    # <--- hecho por claude code: diagnóstico según tipo (computadora / impresora / control)
    if record.es_reasignacion:
        # <--- hecho por claude code (12-oct-2026): reasignación — maestro A → maestro B (misma computadora)
        def _asig(n, g, a, e):
            return ' · '.join(x for x in [n or '', ('Grado ' + g) if g else '', a or '', ('Edificio ' + e) if e else ''] if x) or '—'
        comp = record.computadora
        diag_data = [field_row("Computadora (no cambia):", ' · '.join(x for x in [comp.asset_id if comp else '', record.model or '', ('Serie ' + record.serie) if record.serie else ''] if x) or '—'),
                     field_row("Asignada antes a:", _asig(record.asignado_anterior, record.grado_anterior, record.area_anterior, record.edificio_anterior)),
                     field_row("Se reasigna a:", _asig(record.asignado_nuevo, record.grado_nuevo, record.area_nueva, record.edificio_nuevo)),
                     field_row("Comentario del técnico:", record.obs_tecnico or "—"),
                     field_row("Originado en el control:", record.control_origen.record_id if record.control_origen else "—")]
    elif record.es_cambio:
        # <--- hecho por claude code (28-sep-2026): cambio de equipo — anterior → nuevo
        def _eq(m, s, ip):
            return ' · '.join(x for x in [m or '', ('Serie ' + s) if s else '', ('IP ' + ip) if ip else ''] if x) or '—'
        diag_data = [field_row("Asset ID (se conserva):", record.computadora.asset_id if record.computadora else '—'),
                     field_row("Equipo anterior:", _eq(record.modelo_anterior, record.serie_anterior, record.ip_anterior)),
                     field_row("Equipo nuevo:", _eq(record.modelo_nuevo, record.serie_nuevo, record.ip_nuevo)),
                     field_row("Comentario del técnico:", record.obs_tecnico or "—"),
                     field_row("Originado en el control:", record.control_origen.record_id if record.control_origen else "—")]
    elif record.es_movimiento:
        # <--- hecho por claude code (17-sep-2026): checklist de entrega/recogida (dice CUÁL equipo y CUÁL televisor)
        diag_data = [field_row(lbl + ":", ("Sí" + (f" — {det}" if det else "")) if ok else "No")
                     for lbl, ok, det in record.movimiento_respuestas]
        diag_data.append(field_row("Fecha y hora:", record.fecha_hora.strftime('%d/%m/%Y %H:%M') if record.fecha_hora else "—"))
        diag_data.append(field_row("Comentario del técnico:", record.obs_tecnico or "—"))   # <--- hecho por claude code (28-sep-2026)
        if record.es_caso_especial:
            diag_data.append(field_row("Originado en el control:", record.control_origen.record_id if record.control_origen else "—"))
    elif record.es_reparacion:
        # <--- hecho por claude code (21-oct-2026): reparación — preguntas + asistido por + comentarios
        diag_data = [field_row("¿Qué tiene dañado?", record.rep_que_danado or "—"),
                     field_row("¿Qué reparación se realizará?", record.rep_que_reparacion or "—"),
                     field_row("¿Cómo fue que se dañó?", record.rep_como_dano or "—"),
                     field_row("Asistido por:", record.rep_asistido_por or "—"),
                     field_row("Comentarios:", record.mant_comentario or "—"),
                     field_row("Originado en el control:", record.control_origen.record_id if record.control_origen else "—")]
    elif record.es_mantenimiento:
        # <--- hecho por claude code (21-oct-2026): mantenimiento general — solo comentarios
        diag_data = [field_row("Comentarios:", record.mant_comentario or "—"),
                     field_row("Originado en el control:", record.control_origen.record_id if record.control_origen else "—")]
    elif record.es_inspeccion:
        diag_data = [field_row(lbl, "Sí" if ok else "No") for lbl, ok in record.inspeccion_respuestas]
    elif record.es_control:
        fallas = record.get_eval_fallas_display() or "—"
        if record.eval_fallas == 'si' and (record.eval_fallas_detalle or '').strip():
            fallas += f" — {record.eval_fallas_detalle.strip()}"
        diag_data = [
            field_row("Estado del equipo:",                             record.get_estado_equipo_display() or "—"),
            field_row("¿Qué tal ha trabajado su equipo de trabajo?",   record.get_eval_trabajo_display() or "—"),
            field_row("¿Le ha presentado fallas su equipo de trabajo?", fallas),
            field_row("Observaciones de la auditora:",                  record.obs_auditora or "—"),
            field_row("Observaciones del técnico:",                     record.obs_tecnico or "—"),
        ]
    elif record.tipo_equipo == 'impresora':
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
    diag_tbl = Table(diag_data, colWidths=([6.5*cm, 10.8*cm] if record.es_control or record.es_inspeccion or record.es_movimiento or record.es_cambio or record.es_reasignacion or record.es_reparacion or record.es_mantenimiento
                                           else [4*cm, 13.3*cm]))
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

    if record.es_movimiento or record.es_cambio or record.es_reasignacion:
        # <--- hecho por claude code (17-sep-2026): firma = nombre ESCRITO por el usuario + Soporte Técnico (fija)
        st_fija_m = ParagraphStyle("ffm", fontSize=12, fontName="Helvetica-BoldOblique",
                                   textColor=colors.HexColor("#1f2937"), alignment=TA_CENTER)
        def _col_mov(nombre, titulo, sub):
            return [Spacer(1, 1.2*cm), Paragraph(nombre or "—", st_fija_m), Spacer(1, 0.15*cm),
                    HRFlowable(width="80%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.1*cm),
                    Paragraph(titulo, st_firma_lbl), Paragraph(sub, st_firma_sub)]
        n_t, c_t = MaintenanceRecord.FIRMA_TECNICO_FIJA
        _fh = record.fecha_hora.strftime('%d/%m/%Y %H:%M') if record.fecha_hora else ''
        if record.es_reasignacion:
            # <--- hecho por claude code (12-oct-2026): entrega el maestro A, recibe el maestro B, soporte da fe
            cols = [_col_mov(record.asignado_anterior, "Entrega (maestro anterior)", record.grado_anterior or ''),
                    _col_mov(record.asignado_nuevo, "Recibe (maestro nuevo)", record.grado_nuevo or ''),
                    _col_mov(n_t, "Soporte Técnico", c_t)]
            firmas_tbl = Table([cols], colWidths=[5.77*cm, 5.77*cm, 5.76*cm])
        elif record.es_entrega:
            cols = [_col_mov(n_t, "Entrega", c_t), _col_mov(record.firma_nombre, "Recibe (firma del usuario)", _fh)]
        else:
            cols = [_col_mov(record.firma_nombre, "Entrega (firma del usuario)", _fh), _col_mov(n_t, "Recibe", c_t)]
        if not record.es_reasignacion:
            firmas_tbl = Table([cols], colWidths=[8.65*cm, 8.65*cm])
    elif record.es_reparacion:
        # <--- hecho por claude code (21-oct-2026): TRES firmas A MANO en papel (nombres impresos): Soporte Técnico (Josué
        # Fellmann, fijo), Maestro (asignado del equipo) y Técnico que reparó (Ramón Lagos, fijo).
        st_fija_r = ParagraphStyle("ffr", fontSize=12, fontName="Helvetica-BoldOblique",
                                   textColor=colors.HexColor("#1f2937"), alignment=TA_CENTER)
        def _col_rep(nombre, titulo, sub):
            return [Spacer(1, 1.2*cm), Paragraph(nombre or "—", st_fija_r), Spacer(1, 0.15*cm),
                    HRFlowable(width="80%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.1*cm),
                    Paragraph(titulo, st_firma_lbl), Paragraph(sub, st_firma_sub)]
        n_t, c_t = MaintenanceRecord.FIRMA_TECNICO_FIJA
        n_r, c_r = MaintenanceRecord.FIRMA_TECNICO_REPARO
        cols = [_col_rep(n_t, "Soporte Técnico", c_t),
                _col_rep(record.teacher_name, "Maestro", record.grade or "Asignado del equipo"),
                _col_rep(n_r, "Técnico que reparó", c_r)]
        firmas_tbl = Table([cols], colWidths=[5.77*cm, 5.77*cm, 5.76*cm])
    elif record.es_mantenimiento:
        # <--- hecho por claude code (21-oct-2026): mantenimiento general — Soporte Técnico (fijo) + Maestro
        st_fija_mt = ParagraphStyle("ffmt", fontSize=12, fontName="Helvetica-BoldOblique",
                                    textColor=colors.HexColor("#1f2937"), alignment=TA_CENTER)
        def _col_mt(nombre, titulo, sub):
            return [Spacer(1, 1.2*cm), Paragraph(nombre or "—", st_fija_mt), Spacer(1, 0.15*cm),
                    HRFlowable(width="80%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.1*cm),
                    Paragraph(titulo, st_firma_lbl), Paragraph(sub, st_firma_sub)]
        n_t, c_t = MaintenanceRecord.FIRMA_TECNICO_FIJA
        cols = [_col_mt(n_t, "Soporte Técnico", c_t),
                _col_mt(record.teacher_name, "Maestro", record.grade or "Asignado del equipo")]
        firmas_tbl = Table([cols], colWidths=[8.65*cm, 8.65*cm])
    elif record.es_inspeccion:
        # <--- hecho por claude code: en la inspección la firma es el NOMBRE del asignado (impreso)
        st_fija_i = ParagraphStyle("ffi", fontSize=12, fontName="Helvetica-BoldOblique",
                                   textColor=colors.HexColor("#1f2937"), alignment=TA_CENTER)
        col_asig = [Spacer(1, 1.2*cm), Paragraph(record.teacher_name or "—", st_fija_i), Spacer(1, 0.15*cm),
                    HRFlowable(width="60%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.1*cm),
                    Paragraph("Firma del Maestro (Asignado del equipo)", st_firma_lbl),
                    Paragraph(record.grade or "", st_firma_sub)]
        firmas_tbl = Table([[col_asig]], colWidths=[17.3*cm])
    elif record.es_control:
        # <--- hecho por claude code: en el control las firmas de técnico y auditora son FIJAS (impresas)
        st_fija = ParagraphStyle("ffija", fontSize=11, fontName="Helvetica-BoldOblique",
                                 textColor=colors.HexColor("#1f2937"), alignment=TA_CENTER)
        def _col_fija(nombre, cargo, titulo):
            return [Spacer(1, 1.5*cm), Paragraph(nombre, st_fija), Spacer(1, 0.15*cm),
                    HRFlowable(width="80%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.1*cm),
                    Paragraph(titulo, st_firma_lbl), Paragraph(cargo, st_firma_sub)]
        n_t, c_t = MaintenanceRecord.FIRMA_TECNICO_FIJA
        n_a, c_a = MaintenanceRecord.FIRMA_AUDITORA_FIJA
        col_mae_ctrl = [_firma_img(record.firma) or Spacer(1, 2.3*cm), Spacer(1, 0.1*cm),
                        HRFlowable(width="80%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.1*cm),
                        Paragraph("Firma del Maestro (Digital)", st_firma_lbl),
                        Paragraph(sub_maestro, st_firma_sub)]
        firmas_tbl = Table([[_col_fija(n_t, c_t, "Firma del Técnico"), _col_fija(n_a, c_a, "Firma de la Auditora"), col_mae_ctrl]],
                           colWidths=[5.77*cm, 5.77*cm, 5.77*cm])
    else:
        # <--- hecho por claude code (21-oct-2026): computadora / impresora — Soporte Técnico FIJO (Josué Fellmann, impreso)
        # y el maestro firma A MANO en papel (si ya hay firma digital por WhatsApp, se muestra). Se imprime, firma y sube.
        st_fija_g = ParagraphStyle("ffg", fontSize=12, fontName="Helvetica-BoldOblique",
                                   textColor=colors.HexColor("#1f2937"), alignment=TA_CENTER)
        n_t, c_t = MaintenanceRecord.FIRMA_TECNICO_FIJA
        col_sop = [Spacer(1, 1.2*cm), Paragraph(n_t, st_fija_g), Spacer(1, 0.15*cm),
                   HRFlowable(width="80%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.1*cm),
                   Paragraph("Firma del Técnico (Soporte)", st_firma_lbl), Paragraph(c_t, st_firma_sub)]
        col_mae_g = [_firma_img(record.firma) or Spacer(1, 2.3*cm), Spacer(1, 0.1*cm),
                     HRFlowable(width="80%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.1*cm),
                     Paragraph("Firma del Maestro", st_firma_lbl),
                     Paragraph(sub_maestro or (record.teacher_name or ""), st_firma_sub)]
        firmas_tbl = Table([[col_sop, col_mae_g]], colWidths=[8.65*cm, 8.65*cm])
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
# <--- hecho por claude code: REPORTE CONSOLIDADO de Control de equipos (un solo PDF)
# ─────────────────────────────────────────────────────────────
@login_required
def control_reporte_pdf(request):
    """Un solo PDF con TODOS los controles de equipo: resumen por estado, tabla
    consolidada y las firmas fijas (técnico y auditora) al pie."""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, HRFlowable, Image as RLImage)
    from reportlab.lib.enums import TA_CENTER

    registros = (MaintenanceRecord.objects.filter(tipo_equipo='control')
                 .select_related('computadora').order_by('date', 'record_id'))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter),
                            leftMargin=1.2*cm, rightMargin=1.2*cm,
                            topMargin=1.2*cm, bottomMargin=1.2*cm,
                            title="Reporte de Control de Equipos")
    TEAL = colors.HexColor("#0ca678"); GRAY_LT = colors.HexColor("#eeeeee")
    st_title = ParagraphStyle("t", fontSize=15, fontName="Helvetica-Bold", textColor=TEAL, spaceAfter=5)
    st_sub   = ParagraphStyle("s", fontSize=9, fontName="Helvetica", textColor=colors.gray)
    st_cell  = ParagraphStyle("c", fontSize=7.5, fontName="Helvetica", leading=9)
    st_cellb = ParagraphStyle("cb", fontSize=7.5, fontName="Helvetica-Bold", leading=9)
    st_ctr   = ParagraphStyle("ct", fontSize=8, fontName="Helvetica-Oblique",
                              textColor=colors.gray, alignment=TA_CENTER)

    story = []
    logo_path = finders.find('mantenimiento/img/ana.jpg')
    from django.utils import timezone as _tz
    head = Table([[RLImage(logo_path, width=1.9*cm, height=1.9*cm) if logo_path else "",
                   [Paragraph("Reporte de Control de Equipos", st_title),
                    Paragraph("Asociación Nuevo Amanecer – Sistema TechCare · "
                              f"Generado el {_tz.now().strftime('%d/%m/%Y %H:%M')}", st_sub)]]],  # USE_TZ=False -> now() naive
                 colWidths=[2.3*cm, 22.3*cm])
    head.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(head); story.append(Spacer(1, 0.3*cm))

    # Resumen por estado del equipo
    conteo = {k: 0 for k, _ in MaintenanceRecord.ESTADO_EQUIPO_CHOICES}
    for r in registros:
        if r.estado_equipo in conteo:
            conteo[r.estado_equipo] += 1
    resumen = f"Total de controles: {len(registros)}   ·   " + "   ·   ".join(
        f"{lbl}: {conteo[k]}" for k, lbl in MaintenanceRecord.ESTADO_EQUIPO_CHOICES)
    story.append(Paragraph(resumen, ParagraphStyle("r", fontSize=9, fontName="Helvetica-Bold")))
    story.append(Spacer(1, 0.25*cm))

    if registros:
        filas = [[Paragraph(x, st_cellb) for x in
                  ["ID", "Equipo", "Maestro", "Grado", "Fecha", "Estado del equipo",
                   "¿Cómo ha trabajado?", "¿Fallas?", "Obs. auditora", "Obs. técnico", "Firma maestro"]]]
        for r in registros:
            fallas = r.get_eval_fallas_display() or "—"
            if r.eval_fallas == 'si' and (r.eval_fallas_detalle or '').strip():
                fallas += f": {r.eval_fallas_detalle.strip()}"
            filas.append([
                Paragraph(r.record_id, st_cell),
                Paragraph((r.computadora.asset_id if r.computadora else r.model) or "—", st_cell),
                Paragraph(r.teacher_name or "—", st_cell),
                Paragraph(r.grade or "—", st_cell),
                Paragraph(r.date.strftime('%d/%m/%Y'), st_cell),
                Paragraph(r.get_estado_equipo_display() or "—", st_cellb),
                Paragraph(r.get_eval_trabajo_display() or "—", st_cell),
                Paragraph(fallas, st_cell),
                Paragraph(r.obs_auditora or "—", st_cell),
                Paragraph(r.obs_tecnico or "—", st_cell),
                Paragraph("Firmado" if r.firmado_maestro else "Pendiente", st_cell),
            ])
        tabla = Table(filas, colWidths=[2.5*cm, 2.6*cm, 2.6*cm, 2.0*cm, 1.7*cm, 2.1*cm,
                                        2.0*cm, 3.4*cm, 3.0*cm, 3.0*cm, 1.7*cm], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), TEAL),
            ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, GRAY_LT]),
            ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
            ("VALIGN",       (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",  (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING",   (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ]))
        story.append(tabla)
    else:
        story.append(Paragraph("No hay controles de equipo registrados.", st_ctr))

    # Firmas fijas al pie
    story.append(Spacer(1, 1.0*cm))
    st_f  = ParagraphStyle("f", fontSize=11, fontName="Helvetica-BoldOblique",
                           textColor=colors.HexColor("#1f2937"), alignment=TA_CENTER)
    st_fl = ParagraphStyle("fl", fontSize=8, fontName="Helvetica-Bold", alignment=TA_CENTER)
    st_fs = ParagraphStyle("fs", fontSize=7, fontName="Helvetica-Oblique",
                           textColor=colors.gray, alignment=TA_CENTER)
    n_t, c_t = MaintenanceRecord.FIRMA_TECNICO_FIJA
    n_a, c_a = MaintenanceRecord.FIRMA_AUDITORA_FIJA
    linea = lambda: HRFlowable(width="70%", thickness=0.8, color=colors.gray, hAlign="CENTER")
    col_t = [Paragraph(n_t, st_f), Spacer(1, 0.12*cm), linea(), Spacer(1, 0.08*cm),
             Paragraph("Firma del Técnico", st_fl), Paragraph(c_t, st_fs)]
    col_a = [Paragraph(n_a, st_f), Spacer(1, 0.12*cm), linea(), Spacer(1, 0.08*cm),
             Paragraph("Firma de la Auditora", st_fl), Paragraph(c_a, st_fs)]
    firmas = Table([[col_t, col_a]], colWidths=[12.3*cm, 12.3*cm])
    firmas.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER")]))
    story.append(firmas)

    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="controles_de_equipo.pdf"'
    return resp


# ─────────────────────────────────────────────────────────────
# <--- hecho por claude code (17-sep-2026): reporte consolidado (PDF y Excel) de las pestañas
# Inspecciones, Entregas y Recogidas. Una sola definición de columnas por tipo para ambos formatos.
# ─────────────────────────────────────────────────────────────
_REPORTES_TIPO = {
    'inspeccion': {'titulo': 'Reporte de Inspecciones del Espacio de Trabajo', 'archivo': 'inspecciones', 'color': '#f76707'},
    'entrega':    {'titulo': 'Reporte de Entregas de Equipo',                  'archivo': 'entregas_de_equipo', 'color': '#2fb344'},
    'recogida':   {'titulo': 'Reporte de Recogidas de Equipo',                 'archivo': 'recogidas_de_equipo', 'color': '#ae3ec9'},
    'caso_especial': {'titulo': 'Reporte de Recogidas por Caso Especial',        'archivo': 'casos_especiales', 'color': '#d6336c'},   # <--- hecho por claude code (28-sep-2026)
    'cambio_equipo': {'titulo': 'Reporte de Cambios de Equipo',                  'archivo': 'cambios_de_equipo', 'color': '#4263eb'},
    'reasignacion':  {'titulo': 'Reporte de Reasignaciones de Computadora',      'archivo': 'reasignaciones', 'color': '#0891b2'},   # <--- hecho por claude code (12-oct-2026)
    'prestamo':      {'titulo': 'Reporte de Préstamos de Equipo',                'archivo': 'prestamos_de_equipo', 'color': '#7048e8'},   # <--- hecho por claude code (16-oct-2026)
    'mantenimiento': {'titulo': 'Reporte de Mantenimientos',                     'archivo': 'mantenimientos', 'color': '#0ca678'},   # <--- hecho por claude code (21-oct-2026)
    'reparacion':    {'titulo': 'Reporte de Reparaciones',                       'archivo': 'reparaciones', 'color': '#e8590c'},
}


def _reporte_tipo_datos(tipo):
    """(encabezados, filas, anchos_cm) del reporte de un tipo. Las filas son listas de texto plano."""
    regs = (MaintenanceRecord.objects.filter(tipo_equipo=tipo)
            .select_related('computadora', 'televisor', 'control_origen').order_by('id'))
    sn = lambda b: 'Sí' if b else 'No'
    base = lambda r: [r.record_id, (r.computadora.asset_id if r.computadora else '') or '—',
                      r.model or (r.computadora.modelo if r.computadora else '') or '—',
                      r.serie or (r.computadora.serie if r.computadora else '') or '—',
                      r.teacher_name or '—', r.grade or '—']
    if tipo == 'prestamo':
        # <--- hecho por claude code (16-oct-2026): préstamo de equipo
        enc = ['ID', 'Asset ID', 'Modelo', 'Serie', 'Solicitante', 'Cargo', 'Área', 'Motivo', 'Dónde se usará', 'Sale', 'Desde', 'Hasta', 'Estado', 'PDF firmado']
        anchos = [2.4, 2.0, 2.0, 1.7, 2.4, 1.7, 1.5, 2.8, 2.2, 0.9, 1.5, 1.5, 1.6, 1.3]   # suma 25.5 cm
        f = lambda d: d.strftime('%d/%m/%Y') if d else '—'
        filas = [[r.record_id, (r.computadora.asset_id if r.computadora else '') or '—', r.model or '—', r.serie or '—',
                  r.prest_solicitante or '—', r.prest_cargo or '—', r.prest_area or '—', r.prest_motivo or '—', r.prest_lugar or '—',
                  sn(r.prest_sale), f(r.prest_desde), f(r.prest_hasta), r.prestamo_estado[1], 'Sí' if r.prest_pdf else 'No'] for r in regs]
    elif tipo == 'reasignacion':
        # <--- hecho por claude code (12-oct-2026): maestro A → maestro B (misma computadora)
        enc = ['ID', 'Control', 'Asset ID', 'Modelo', 'Serie', 'Asignado antes', 'Grado antes', 'Área antes', 'Reasignado a', 'Grado nuevo', 'Área nueva', 'Fecha', 'Comentario técnico']
        anchos = [2.5, 2.5, 2.0, 2.2, 1.8, 2.6, 1.4, 1.6, 2.6, 1.4, 1.6, 1.5, 1.8]   # suma 25.5 cm
        filas = [[r.record_id, r.control_origen.record_id if r.control_origen else '—', (r.computadora.asset_id if r.computadora else '') or '—',
                  r.model or '—', r.serie or '—', r.asignado_anterior or '—', r.grado_anterior or '—', r.area_anterior or '—',
                  r.asignado_nuevo or '—', r.grado_nuevo or '—', r.area_nueva or '—',
                  r.date.strftime('%d/%m/%Y') if r.date else '—', r.obs_tecnico or '—'] for r in regs]
    elif tipo == 'cambio_equipo':
        # <--- hecho por claude code (28-sep-2026): equipo anterior → equipo nuevo
        enc = ['ID', 'Control', 'Asset ID', 'Modelo anterior', 'Serie anterior', 'IP anterior', 'Modelo nuevo', 'Serie nueva', 'IP nueva', 'Maestro', 'Grado', 'Fecha', 'Comentario técnico']
        anchos = [2.5, 2.5, 2.2, 2.4, 1.9, 1.7, 2.4, 1.9, 1.7, 2.3, 1.5, 1.5, 1.0]   # suma 25.5 cm
        filas = [[r.record_id, r.control_origen.record_id if r.control_origen else '—', (r.computadora.asset_id if r.computadora else '') or '—',
                  r.modelo_anterior or '—', r.serie_anterior or '—', r.ip_anterior or '—', r.modelo_nuevo or '—', r.serie_nuevo or '—', r.ip_nuevo or '—',
                  r.teacher_name or '—', r.grade or '—', r.date.strftime('%d/%m/%Y') if r.date else '—', r.obs_tecnico or '—'] for r in regs]
    elif tipo == 'mantenimiento':
        # <--- hecho por claude code (21-oct-2026): mantenimiento general (solo comentarios)
        enc = ['ID', 'Control', 'Asset ID', 'Modelo', 'Serie', 'Maestro', 'Grado', 'Fecha', 'Comentarios']
        anchos = [2.6, 2.6, 2.3, 2.6, 2.1, 3.0, 1.8, 1.7, 6.8]   # suma 25.5 cm
        filas = [[r.record_id, r.control_origen.record_id if r.control_origen else '—', (r.computadora.asset_id if r.computadora else '') or '—',
                  r.model or (r.computadora.modelo if r.computadora else '') or '—', r.serie or (r.computadora.serie if r.computadora else '') or '—',
                  r.teacher_name or '—', r.grade or '—', r.date.strftime('%d/%m/%Y') if r.date else '—', r.mant_comentario or '—'] for r in regs]
    elif tipo == 'reparacion':
        # <--- hecho por claude code (21-oct-2026): reparación (preguntas + asistido por + PDF firmado)
        enc = ['ID', 'Control', 'Asset ID', 'Maestro', '¿Qué dañado?', '¿Qué reparación?', '¿Cómo se dañó?', 'Asistido por', 'Fecha', 'Estado', 'Firmada']
        anchos = [2.3, 2.3, 1.9, 2.4, 3.3, 3.3, 3.0, 2.0, 1.4, 1.6, 1.0]   # suma 25.5 cm
        filas = [[r.record_id, r.control_origen.record_id if r.control_origen else '—', (r.computadora.asset_id if r.computadora else '') or '—',
                  r.teacher_name or '—', r.rep_que_danado or '—', r.rep_que_reparacion or '—', r.rep_como_dano or '—', r.rep_asistido_por or '—',
                  r.date.strftime('%d/%m/%Y') if r.date else '—', r.reparacion_estado[1], sn(bool(r.rep_pdf))] for r in regs]
    elif tipo == 'inspeccion':
        enc = ['ID', 'Equipo', 'Modelo', 'Serie', 'Maestro', 'Grado', 'Fecha',
               'Espacio limpio', 'Espacio ordenado', 'Cables en orden', 'Sin comida/bebidas', 'Firma (asignado)']
        anchos = [3.0, 2.4, 2.8, 2.2, 2.7, 1.9, 1.7, 1.5, 1.6, 1.5, 1.7, 2.5]   # suma 25.5 cm = ancho útil carta apaisada (ID ancho para que no se parta)
        filas = [base(r) + [r.date.strftime('%d/%m/%Y') if r.date else '—', sn(r.insp_limpio), sn(r.insp_ordenado),
                            sn(r.insp_cables), sn(r.insp_alimentos), r.teacher_name or '—'] for r in regs]
    else:
        verbo = 'Entregó' if tipo == 'entrega' else 'Recibió'
        enc = ['ID', 'Equipo', 'Modelo', 'Serie', 'Asignado', 'Grado', 'Fecha y hora',
               f'{verbo} equipo', 'Mouse y teclado', 'Televisor', 'Control TV + batería',
               'Firma de quien recibe' if tipo == 'entrega' else 'Firma de quien entrega', 'Comentario técnico']
        anchos = [2.8, 2.1, 2.3, 1.8, 2.3, 1.6, 2.0, 1.3, 1.3, 2.0, 1.5, 2.0, 2.5]   # suma 25.5 cm (28-sep-2026: + comentario)
        def _tv(r):
            if not r.ent_televisor:
                return 'No'
            return 'Sí' + (f' — {r.televisor.asset_id}' if r.televisor_id else '')
        filas = [base(r) + [r.fecha_hora.strftime('%d/%m/%Y %H:%M') if r.fecha_hora else '—', sn(r.ent_equipo),
                            sn(r.ent_mouse_teclado), _tv(r), sn(r.ent_control_tv), r.firma_nombre or '—', r.obs_tecnico or '—'] for r in regs]
        if tipo == 'caso_especial':   # <--- hecho por claude code (28-sep-2026): + control de origen
            enc = enc + ['Control origen']
            anchos = [2.6, 2.0, 2.2, 1.7, 2.2, 1.5, 1.9, 1.2, 1.2, 1.9, 1.4, 1.9, 2.3, 1.5]   # suma 25.5 cm
            filas = [f + [r.control_origen.record_id if r.control_origen else '—'] for f, r in zip(filas, regs)]
    return enc, filas, anchos


@login_required
def reporte_tipo_pdf(request, tipo):
    """PDF apaisado con todos los registros de la pestaña (inspeccion / entrega / recogida)."""
    from django.http import Http404
    if tipo not in _REPORTES_TIPO:
        raise Http404('Tipo de reporte no disponible')
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                    HRFlowable, Image as RLImage)
    from reportlab.lib.enums import TA_CENTER
    from django.utils import timezone as _tz
    meta = _REPORTES_TIPO[tipo]
    enc, filas, anchos = _reporte_tipo_datos(tipo)
    COLOR = colors.HexColor(meta['color']); GRAY_LT = colors.HexColor("#eeeeee")
    st_title = ParagraphStyle("t", fontSize=15, leading=18, fontName="Helvetica-Bold", textColor=COLOR, spaceAfter=5)
    st_sub   = ParagraphStyle("s", fontSize=9, fontName="Helvetica", textColor=colors.gray)
    st_cell  = ParagraphStyle("c", fontSize=7.5, fontName="Helvetica", leading=9)
    st_cellb = ParagraphStyle("cb", fontSize=7.5, fontName="Helvetica-Bold", leading=9, textColor=colors.white)
    st_ctr   = ParagraphStyle("ct", fontSize=8, fontName="Helvetica-Oblique", textColor=colors.gray, alignment=TA_CENTER)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), leftMargin=1.2*cm, rightMargin=1.2*cm,
                            topMargin=1.2*cm, bottomMargin=1.2*cm, title=meta['titulo'])
    story = []
    logo_path = finders.find('mantenimiento/img/ana.jpg')
    head = Table([[RLImage(logo_path, width=1.9*cm, height=1.9*cm) if logo_path else "",
                   [Paragraph(meta['titulo'], st_title),
                    Paragraph("Asociación Nuevo Amanecer – Sistema TechCare · "
                              f"Generado el {_tz.now().strftime('%d/%m/%Y %H:%M')}", st_sub)]]],   # USE_TZ=False -> now() naive
                 colWidths=[2.3*cm, 22.3*cm])
    head.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story += [head, Spacer(1, 0.3*cm),
              Paragraph(f"Total de registros: {len(filas)}", ParagraphStyle("r", fontSize=9, fontName="Helvetica-Bold")),
              Spacer(1, 0.25*cm)]
    if filas:
        data = [[Paragraph(x, st_cellb) for x in enc]] + [[Paragraph(str(v), st_cell) for v in f] for f in filas]
        tabla = Table(data, colWidths=[a*cm for a in anchos], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), COLOR),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, GRAY_LT]),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(tabla)
    else:
        story.append(Paragraph("No hay registros.", st_ctr))
    # Firmas fijas al pie: Soporte Técnico y Auditoría
    # <--- hecho por claude code (17-sep-2026): pedido del usuario — el reporte de inspecciones lleva la firma de la auditora
    st_f  = ParagraphStyle("f", fontSize=11, fontName="Helvetica-BoldOblique",
                           textColor=colors.HexColor("#1f2937"), alignment=TA_CENTER)
    st_fl = ParagraphStyle("fl", fontSize=8, fontName="Helvetica-Bold", alignment=TA_CENTER)
    st_fs = ParagraphStyle("fs", fontSize=7, fontName="Helvetica-Oblique", textColor=colors.gray, alignment=TA_CENTER)
    def _col_firma(nombre, titulo, cargo):
        return [Paragraph(nombre, st_f), Spacer(1, 0.12*cm),
                HRFlowable(width="70%", thickness=0.8, color=colors.gray, hAlign="CENTER"), Spacer(1, 0.08*cm),
                Paragraph(titulo, st_fl), Paragraph(cargo, st_fs)]
    n_t, c_t = MaintenanceRecord.FIRMA_TECNICO_FIJA
    story.append(Spacer(1, 1.0*cm))
    # (17-sep-2026) el usuario pidió la firma de Auditoría en los TRES reportes (inspecciones, entregas y recogidas)
    n_a, c_a = MaintenanceRecord.FIRMA_AUDITORA_FIJA
    firmas = Table([[_col_firma(n_t, "Firma del Técnico", c_t), _col_firma(n_a, "Firma de la Auditora", c_a)]],
                   colWidths=[12.75*cm, 12.75*cm])
    firmas.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER")]))
    story.append(firmas)
    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{meta["archivo"]}.pdf"'
    return resp


@login_required
def reporte_tipo_excel(request, tipo):
    """Excel (.xlsx) con todos los registros de la pestaña (inspeccion / entrega / recogida)."""
    from django.http import Http404
    if tipo not in _REPORTES_TIPO:
        raise Http404('Tipo de reporte no disponible')
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from django.utils import timezone as _tz
    meta = _REPORTES_TIPO[tipo]
    enc, filas, anchos = _reporte_tipo_datos(tipo)
    wb = Workbook(); ws = wb.active; ws.title = meta['archivo'][:31]
    ws.append([meta['titulo']]); ws.append([f"Asociación Nuevo Amanecer – TechCare · Generado el {_tz.now().strftime('%d/%m/%Y %H:%M')} · {len(filas)} registros"])
    ws.append([])
    ws.append(enc)
    for f in filas:
        ws.append(f)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(enc))
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(enc))
    ws['A1'].font = Font(bold=True, size=14, color=meta['color'].lstrip('#'))
    ws['A2'].font = Font(italic=True, size=9, color='666666')
    relleno = PatternFill('solid', fgColor=meta['color'].lstrip('#'))
    borde = Border(*(Side(style='thin', color='CCCCCC'),) * 4)
    for c in ws[4]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = relleno; c.border = borde
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for fila in ws.iter_rows(min_row=5, max_row=4 + len(filas)):
        for c in fila:
            c.border = borde; c.alignment = Alignment(vertical='top', wrap_text=True)
    for i, a in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = round(a * 6.2, 1)
    ws.row_dimensions[4].height = 30
    ws.freeze_panes = 'A5'
    if filas:
        ws.auto_filter.ref = f"A4:{get_column_letter(len(enc))}{4 + len(filas)}"
    buf = BytesIO(); wb.save(buf); buf.seek(0)
    resp = HttpResponse(buf.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="{meta["archivo"]}.xlsx"'
    return resp


# <--- hecho por claude code: TODAS las fichas de Control de equipo en un solo PDF
# (mismo estilo que la ficha individual: reutiliza download_maintenance_pdf por registro
# y une las páginas con pypdfium2 — cero duplicación del diseño).
@login_required
def control_fichas_pdf(request):
    import pypdfium2 as pdfium
    registros = (MaintenanceRecord.objects.filter(tipo_equipo='control')
                 .order_by('date', 'record_id'))
    if not registros:
        return HttpResponse('No hay controles de equipo registrados.', content_type='text/plain')
    destino = pdfium.PdfDocument.new()
    abiertos = []
    try:
        for r in registros:
            resp = download_maintenance_pdf(request, r.id)
            src = pdfium.PdfDocument(resp.content)
            abiertos.append(src)
            destino.import_pages(src)
        buf = BytesIO()
        destino.save(buf)
    finally:
        for d in abiertos:
            d.close()
        destino.close()
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="fichas_control_de_equipo.pdf"'
    return resp


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
        # <--- hecho por claude code: el modal de edición ya se adapta al tipo (computadora / impresora /
        # control) y envía los campos propios de cada uno; solo se preserva el tipo del registro.
        post = _resolver_post_tipo_falla(request).copy()
        post['tipo_equipo'] = record.tipo_equipo
        # <--- hecho por claude code (28-sep-2026): el modal de edición no manda control_origen; se preserva
        if record.control_origen_id:
            post['control_origen'] = str(record.control_origen_id)
        # <--- hecho por claude code (16-oct-2026): el modal de edición manda modelo/serie/ip _nuevo VACÍOS (son los hidden
        # del switch del Control); en una ficha de CAMBIO DE EQUIPO eso borraba el antes/después. Fuera de un Control
        # esos datos son una foto histórica: siempre se conservan los guardados.
        if record.tipo_equipo != 'control':
            for _c in ('modelo_anterior', 'serie_anterior', 'ip_anterior', 'modelo_nuevo', 'serie_nuevo', 'ip_nuevo'):
                post[_c] = getattr(record, _c) or ''
        form = MaintenanceRecordForm(post, request.FILES, instance=record)
        if form.is_valid():
            rec = form.save(commit=False)
            if rec.tipo_equipo == 'impresora':
                imp = rec.impresora
                if imp:
                    rec.model = imp.modelo or ''
                    rec.serie = imp.serie or ''
                    if not rec.teacher_name:
                        rec.teacher_name = imp.asignado_a or ''
            else:
                comp = rec.computadora
                if comp:
                    if rec.tipo_equipo in TIPOS_PORTADOR_ACTUAL:
                        # <--- hecho por claude code: sincroniza con el portador actual del inventario
                        rec.teacher_name = comp.asignado_a or ''
                        rec.grade = comp.grado or ''
                    else:
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
            _aplicar_prestamo(rec, request.POST)   # <--- hecho por claude code (16-oct-2026)
            _aplicar_mantenimiento(rec, request.POST)   # <--- hecho por claude code (21-oct-2026)
            rec.save()
            for f in request.FILES.getlist('fotos'):
                FotoMantenimiento.objects.create(registro=rec, imagen=f)
            _crear_derivados_del_control(request, rec, msg)   # <--- hecho por claude code (28-sep-2026): switches también al editar
            if rec.tipo_equipo == 'impresora' and rec.impresora_id and rec.tipo_mant_impresora == 'llenado_tinta':
                imp = rec.impresora
                if rec.estado_tinta:
                    imp.nivel_tinta = rec.get_estado_tinta_display()
                imp.ultima_vez_llenado = rec.date
                imp.save(update_fields=['nivel_tinta', 'ultima_vez_llenado'])
            msg.success(request, f'Registro {rec.record_id} actualizado correctamente.')
        else:
            errores = '; '.join(
                f"{field}: {', '.join(errs)}"
                for field, errs in form.errors.items() if field != '__all__'
            )
            msg.error(request, f'Error al actualizar: {errores or "Verifica los campos requeridos."}')
        return _redirect_fichas(record.tipo_equipo)

    # GET → devuelve JSON con los datos del registro para llenar el modal
    import json as _json
    data = {
        'id':           record.pk,
        'record_id':    record.record_id,
        'tipo_equipo':  record.tipo_equipo,   # <--- hecho por claude code: el modal de edición se adapta al tipo
        'eval_trabajo': record.eval_trabajo, 'eval_fallas': record.eval_fallas,
        'eval_fallas_detalle': record.eval_fallas_detalle, 'obs_auditora': record.obs_auditora,
        'obs_tecnico':  record.obs_tecnico, 'estado_equipo': record.estado_equipo,
        'insp_limpio': record.insp_limpio, 'insp_ordenado': record.insp_ordenado,
        'insp_cables': record.insp_cables, 'insp_alimentos': record.insp_alimentos,
        # <--- hecho por claude code (17-sep-2026): Entrega / Recogida
        'ent_equipo': record.ent_equipo, 'ent_mouse_teclado': record.ent_mouse_teclado,
        'ent_televisor': record.ent_televisor, 'ent_control_tv': record.ent_control_tv,
        'televisor': record.televisor_id, 'firma_nombre': record.firma_nombre,
        'control_origen': record.control_origen_id, 'control_origen_rid': record.control_origen.record_id if record.control_origen_id else '',   # <--- hecho por claude code (28-sep-2026)
        'computadora_rid': record.computadora.asset_id if record.computadora_id else '',
        'modelo_anterior': record.modelo_anterior, 'serie_anterior': record.serie_anterior, 'ip_anterior': record.ip_anterior,
        'modelo_nuevo': record.modelo_nuevo, 'serie_nuevo': record.serie_nuevo, 'ip_nuevo': record.ip_nuevo,
        # <--- hecho por claude code (28-sep-2026): fichas derivadas de un control (para los switches del modal de edición)
        'hijo_caso_especial': (record.casos_especiales.filter(tipo_equipo='caso_especial').values_list('record_id', flat=True).first() or '') if record.tipo_equipo == 'control' else '',
        'hijo_cambio_equipo': (record.casos_especiales.filter(tipo_equipo='cambio_equipo').values_list('record_id', flat=True).first() or '') if record.tipo_equipo == 'control' else '',
        # <--- hecho por claude code (12-oct-2026): reasignación
        'hijo_reasignacion': (record.casos_especiales.filter(tipo_equipo='reasignacion').values_list('record_id', flat=True).first() or '') if record.tipo_equipo == 'control' else '',
        'asignado_anterior': record.asignado_anterior, 'grado_anterior': record.grado_anterior, 'area_anterior': record.area_anterior, 'edificio_anterior': record.edificio_anterior,
        'asignado_nuevo': record.asignado_nuevo, 'grado_nuevo': record.grado_nuevo, 'area_nueva': record.area_nueva, 'edificio_nuevo': record.edificio_nuevo,
        'fecha_hora': record.fecha_hora.strftime('%Y-%m-%dT%H:%M') if record.fecha_hora else '',
        # <--- hecho por claude code (21-oct-2026): mantenimiento / reparación
        'mant_comentario': record.mant_comentario, 'rep_que_danado': record.rep_que_danado,
        'rep_que_reparacion': record.rep_que_reparacion, 'rep_como_dano': record.rep_como_dano, 'rep_asistido_por': record.rep_asistido_por,
        'hijo_mantenimiento': (record.casos_especiales.filter(tipo_equipo='mantenimiento').values_list('record_id', flat=True).first() or '') if record.tipo_equipo == 'control' else '',
        'hijo_reparacion': (record.casos_especiales.filter(tipo_equipo='reparacion').values_list('record_id', flat=True).first() or '') if record.tipo_equipo == 'control' else '',
        # <--- hecho por claude code (16-oct-2026): préstamo de equipo
        'prest_solicitante': record.prest_solicitante, 'prest_cargo': record.prest_cargo, 'prest_area': record.prest_area,
        'prest_motivo': record.prest_motivo, 'prest_lugar': record.prest_lugar, 'prest_sale': record.prest_sale,
        'prest_desde': record.prest_desde.isoformat() if record.prest_desde else '',
        'prest_hasta': record.prest_hasta.isoformat() if record.prest_hasta else '',
        'prest_accesorios': record.prest_accesorios,
        'computadora':  record.computadora_id,
        'impresora':    record.impresora_id, 'area': record.area,
        'tipo_mant_impresora': record.tipo_mant_impresora, 'estado_tinta': record.estado_tinta,
        'tipo_tinta':   record.tipo_tinta,
        'tinta_negra':  record.tinta_negra, 'tinta_magenta': record.tinta_magenta,
        'tinta_amarillo': record.tinta_amarillo, 'tinta_cyan': record.tinta_cyan,
        'teacher_name': record.teacher_name, 'grade': record.grade,
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
        'fotos':        [{'id': f.id, 'url': f.imagen.url,
                           'del': reverse('mantenimiento:foto_eliminar', args=[f.id])} for f in record.fotos.all()],   # <--- hecho por claude code (21-oct-2026): URL para borrar la foto
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
            MaintenanceRecord.objects.filter(tipo_equipo='control').order_by('id'), start=1
        ):
            nuevo_id = f"ANAMAESCTRL-{i:03d}"
            if r.record_id != nuevo_id:
                MaintenanceRecord.objects.filter(pk=r.pk).update(record_id=nuevo_id)
        for i, r in enumerate(
            MaintenanceRecord.objects.filter(tipo_equipo='inspeccion').order_by('id'), start=1
        ):
            nuevo_id = f"ANAMAESINSP-{i:03d}"
            if r.record_id != nuevo_id:
                MaintenanceRecord.objects.filter(pk=r.pk).update(record_id=nuevo_id)
        # <--- hecho por claude code (17-sep-2026): Entrega / Recogida renumeran con su prefijo
        for _tipo, _pref in (('entrega', PREFIJO_ENTREGA), ('recogida', PREFIJO_RECOGIDA), ('caso_especial', PREFIJO_CASO), ('cambio_equipo', PREFIJO_CAMBIO), ('reasignacion', PREFIJO_REASIG), ('prestamo', PREFIJO_PRESTAMO), ('mantenimiento', PREFIJO_MANT), ('reparacion', PREFIJO_REP)):
            for i, r in enumerate(MaintenanceRecord.objects.filter(tipo_equipo=_tipo).order_by('id'), start=1):
                nuevo_id = f"{_pref}{i:03d}"
                if r.record_id != nuevo_id:
                    MaintenanceRecord.objects.filter(pk=r.pk).update(record_id=nuevo_id)
        for i, r in enumerate(
            MaintenanceRecord.objects.exclude(tipo_equipo__in=['impresora', 'control', 'inspeccion', 'entrega', 'recogida', 'caso_especial', 'cambio_equipo', 'reasignacion', 'prestamo', 'mantenimiento', 'reparacion']).order_by('id'), start=1
        ):
            nuevo_id = f"ANAMAESCOMP{i:03d}"
            if r.record_id != nuevo_id:
                MaintenanceRecord.objects.filter(pk=r.pk).update(record_id=nuevo_id)
        msg.success(request, 'Registro eliminado y numeración reiniciada.')
        return _redirect_fichas(record.tipo_equipo)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ─────────────────────────────────────────────────────────────
# <--- hecho por claude code (16-oct-2026): PRÉSTAMO DE EQUIPO
# ─────────────────────────────────────────────────────────────
def _aplicar_prestamo(rec, post):
    """Copia los datos del préstamo del POST a la ficha. Solo si es préstamo Y los datos llegaron: así una edición
    que no los manda (u otra ficha) nunca los borra."""
    if rec.tipo_equipo != 'prestamo' or 'prest_solicitante' not in post:
        return
    for campo, largo in (('prest_solicitante', 150), ('prest_cargo', 100), ('prest_area', 100),
                         ('prest_lugar', 200), ('prest_accesorios', 255)):
        setattr(rec, campo, (post.get(campo) or '').strip()[:largo])
    rec.prest_motivo = (post.get('prest_motivo') or '').strip()[:2000]
    rec.prest_sale = post.get('prest_sale') == '1'
    for campo in ('prest_desde', 'prest_hasta'):
        try:
            setattr(rec, campo, datetime.date.fromisoformat(post.get(campo) or ''))
        except ValueError:
            pass


def _aplicar_mantenimiento(rec, post):
    """<--- hecho por claude code (21-oct-2026): copia los campos de mantenimiento/reparación del POST a la ficha, SOLO si
    la ficha es de ese tipo y llegaron (editar otra ficha nunca los borra)."""
    if rec.tipo_equipo not in ('mantenimiento', 'reparacion') or 'mant_comentario' not in post:
        return
    rec.mant_comentario = (post.get('mant_comentario') or '').strip()[:2000]
    if rec.tipo_equipo == 'reparacion':
        rec.rep_que_danado = (post.get('rep_que_danado') or '').strip()[:2000]
        rec.rep_que_reparacion = (post.get('rep_que_reparacion') or '').strip()[:2000]
        rec.rep_como_dano = (post.get('rep_como_dano') or '').strip()[:2000]
        rec.rep_asistido_por = (post.get('rep_asistido_por') or '').strip()[:150]


def _puede_prestamos(u):
    from servicio_tecnico.views import _puede_inventario, _puede_mantenimiento
    return _puede_inventario(u) or _puede_mantenimiento(u)


@login_required
def prestamo_pdf_subir(request, pk):
    """Recibe la solicitud ya FIRMADA en papel (escaneada en PDF). Si estaba pendiente, el equipo pasa a «Prestado»."""
    from django.contrib import messages as msg
    from django.core.exceptions import PermissionDenied
    if not _puede_prestamos(request.user):
        raise PermissionDenied
    rec = get_object_or_404(MaintenanceRecord, pk=pk, tipo_equipo='prestamo')
    if request.method != 'POST':
        return _redirect_fichas('prestamo')
    f = request.FILES.get('pdf')
    if not f:
        msg.error(request, 'Elige el PDF firmado.')
        return _redirect_fichas('prestamo')
    if f.size > 15 * 1024 * 1024:
        msg.error(request, 'El PDF pesa más de 15 MB.')
        return _redirect_fichas('prestamo')
    if not f.read(5).startswith(b'%PDF'):
        msg.error(request, 'El archivo no es un PDF.')
        return _redirect_fichas('prestamo')
    f.seek(0)
    anterior = rec.prest_pdf.name if rec.prest_pdf else ''
    rec.prest_pdf.save(f"{rec.record_id}_firmado_{timezone.now():%Y%m%d_%H%M%S}.pdf", f, save=False)
    rec.prest_pdf_en = timezone.now()
    rec.prest_pdf_por = request.user
    if rec.status == 'Pendiente':
        rec.status = 'En Proceso'   # firmado → prestado
    rec.modificado_por = request.user
    rec.save()
    if anterior and anterior != rec.prest_pdf.name:
        rec.prest_pdf.storage.delete(anterior)
    msg.success(request, f'Solicitud firmada de {rec.record_id} guardada. El equipo queda como prestado.')
    return _redirect_fichas('prestamo')


@login_required
def reparacion_pdf_subir(request, pk):
    """<--- hecho por claude code (21-oct-2026): recibe la ficha de reparación ya FIRMADA en papel (PDF). Pasa a «Firmada»."""
    from django.contrib import messages as msg
    from django.core.exceptions import PermissionDenied
    if not _puede_prestamos(request.user):
        raise PermissionDenied
    rec = get_object_or_404(MaintenanceRecord, pk=pk, tipo_equipo='reparacion')
    if request.method != 'POST':
        return _redirect_fichas('reparacion')
    f = request.FILES.get('pdf')
    if not f:
        msg.error(request, 'Elige el PDF firmado.')
        return _redirect_fichas('reparacion')
    if f.size > 15 * 1024 * 1024:
        msg.error(request, 'El PDF pesa más de 15 MB.')
        return _redirect_fichas('reparacion')
    if not f.read(5).startswith(b'%PDF'):
        msg.error(request, 'El archivo no es un PDF.')
        return _redirect_fichas('reparacion')
    f.seek(0)
    anterior = rec.rep_pdf.name if rec.rep_pdf else ''
    rec.rep_pdf.save(f"{rec.record_id}_firmado_{timezone.now():%Y%m%d_%H%M%S}.pdf", f, save=False)
    rec.rep_pdf_en = timezone.now()
    rec.rep_pdf_por = request.user
    rec.status = 'Completado'   # firmada
    rec.modificado_por = request.user
    rec.save()
    if anterior and anterior != rec.rep_pdf.name:
        rec.rep_pdf.storage.delete(anterior)
    msg.success(request, f'Reparación firmada de {rec.record_id} guardada.')
    return _redirect_fichas('reparacion')


@login_required
def reparacion_pdf_ver(request, pk):
    from django.core.exceptions import PermissionDenied
    from django.http import FileResponse, Http404
    if not _puede_prestamos(request.user):
        raise PermissionDenied
    rec = get_object_or_404(MaintenanceRecord, pk=pk, tipo_equipo='reparacion')
    if not rec.rep_pdf:
        raise Http404
    try:
        return FileResponse(rec.rep_pdf.open('rb'), content_type='application/pdf', filename=f'{rec.record_id}_firmado.pdf')
    except FileNotFoundError:
        raise Http404


@login_required
def firma_pdf_subir(request, pk):
    """<--- hecho por claude code (21-oct-2026): sube la ficha firmada en papel (PDF) de CUALQUIER tipo salvo préstamo/reparación.
    Mismo flujo que préstamo: imprimir, firmar a mano (Soporte Técnico va fijo en el PDF), escanear y subir."""
    from django.contrib import messages as msg
    from django.core.exceptions import PermissionDenied
    from django.http import Http404
    if not _puede_prestamos(request.user):
        raise PermissionDenied
    rec = get_object_or_404(MaintenanceRecord, pk=pk)
    if not rec.usa_firma_pdf:   # préstamo/reparación tienen su propia subida
        raise Http404
    destino = SLUG_POR_TIPO.get(rec.tipo_equipo, 'computadoras')
    if request.method != 'POST':
        return redirect('mantenimiento:fichas', tipo=destino)
    f = request.FILES.get('pdf')
    if not f:
        msg.error(request, 'Elige el PDF firmado.')
        return redirect('mantenimiento:fichas', tipo=destino)
    if f.size > 15 * 1024 * 1024:
        msg.error(request, 'El PDF pesa más de 15 MB.')
        return redirect('mantenimiento:fichas', tipo=destino)
    if not f.read(5).startswith(b'%PDF'):
        msg.error(request, 'El archivo no es un PDF.')
        return redirect('mantenimiento:fichas', tipo=destino)
    f.seek(0)
    anterior = rec.firma_pdf.name if rec.firma_pdf else ''
    rec.firma_pdf.save(f"{rec.record_id}_firmado_{timezone.now():%Y%m%d_%H%M%S}.pdf", f, save=False)
    rec.firma_pdf_en = timezone.now()
    rec.firma_pdf_por = request.user
    rec.status = 'Completado'   # <--- hecho por claude code (21-oct-2026): al publicar la firma la ficha queda completada
    rec.modificado_por = request.user
    rec.save()
    if anterior and anterior != rec.firma_pdf.name:
        rec.firma_pdf.storage.delete(anterior)
    msg.success(request, f'Ficha firmada de {rec.record_id} guardada. La ficha quedó como Completada.')
    return redirect('mantenimiento:fichas', tipo=destino)


@login_required
def firma_pdf_ver(request, pk):
    from django.core.exceptions import PermissionDenied
    from django.http import FileResponse, Http404
    if not _puede_prestamos(request.user):
        raise PermissionDenied
    rec = get_object_or_404(MaintenanceRecord, pk=pk)
    if not rec.firma_pdf:
        raise Http404
    try:
        return FileResponse(rec.firma_pdf.open('rb'), content_type='application/pdf', filename=f'{rec.record_id}_firmado.pdf')
    except FileNotFoundError:
        raise Http404


@login_required
def foto_eliminar(request, pk):
    """<--- hecho por claude code (21-oct-2026): borra una foto de evidencia (para quitar las duplicadas desde el editar)."""
    from django.http import JsonResponse, Http404
    if request.method != 'POST':
        raise Http404
    foto = get_object_or_404(FotoMantenimiento, pk=pk)
    rid = foto.registro.record_id if foto.registro_id else ''
    # <--- hecho por claude code (22-oct-2026): las fichas derivadas comparten el archivo con su control;
    # borra el archivo del disco SOLO si ninguna otra ficha lo referencia.
    nombre = foto.imagen.name if foto.imagen else ''
    foto.delete()
    if nombre and not FotoMantenimiento.objects.filter(imagen=nombre).exists():
        try:
            from django.core.files.storage import default_storage
            default_storage.delete(nombre)
        except Exception:
            pass
    return JsonResponse({'ok': True, 'id': pk, 'record_id': rid})


@login_required
def prestamo_pdf_ver(request, pk):
    """Abre la solicitud firmada (se sirve por la app; no depende de cómo se publique /media/)."""
    from django.core.exceptions import PermissionDenied
    from django.http import FileResponse, Http404
    if not _puede_prestamos(request.user):
        raise PermissionDenied
    rec = get_object_or_404(MaintenanceRecord, pk=pk, tipo_equipo='prestamo')
    if not rec.prest_pdf:
        raise Http404
    try:
        return FileResponse(rec.prest_pdf.open('rb'), content_type='application/pdf',
                            filename=f'{rec.record_id}_firmado.pdf')
    except FileNotFoundError:
        raise Http404
