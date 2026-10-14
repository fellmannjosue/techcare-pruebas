# <--- hecho por claude code (12-oct-2026): MANTENIMIENTO DE VEHÍCULOS — ventana aparte (/mantenimiento-vehiculos/).
# Formato de Access con datos en sponsors2 (vehiculos_db.py; copiados de AdmonANASQL con importar_mant_vehiculos).
# Flujo: 1) se registra el km/horas, 2) se muestra hasta qué km toca el mantenimiento y cuánto falta, 3) hoja de tareas.
# Permisos PROPIOS (grupos): vehiculos_registro = km + mantenimiento · vehiculos_kilometraje = solo km ·
# vehiculos_auditoria = ver y comentar · vehiculos_alertas = recibe el aviso cuando toca mantenimiento. Nadie elimina.
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from . import vehiculos_db as VS
from .models import (Comentario, FIRMA_AUDITORA, GRUPO_VEH_ALERTAS, GRUPO_VEH_AUDITORIA, GRUPO_VEH_KM,
                     GRUPO_VEH_REGISTRO)
from .views import _encabezado, _fecha, _logo_file, _pdf, _wb, _xlsx_response


def _g(user, *grupos):
    return user.groups.filter(name__in=grupos).exists()


def puede_ver(user):
    return user.is_superuser or _g(user, GRUPO_VEH_REGISTRO, GRUPO_VEH_KM, GRUPO_VEH_AUDITORIA)


def puede_km(user):
    return user.is_superuser or _g(user, GRUPO_VEH_REGISTRO, GRUPO_VEH_KM)


def puede_mant(user):
    return user.is_superuser or _g(user, GRUPO_VEH_REGISTRO)


def puede_registrar(user):
    """<--- hecho por claude code (12-oct-2026): dar de alta un vehículo = superusuario o vehiculos_registro."""
    return puede_mant(user)


def puede_editar_vehiculo(user):
    """Corregir los datos de un vehículo ya registrado = SOLO el superusuario (misma regla que el resto del módulo)."""
    return user.is_superuser


def puede_comentar(user):
    return user.is_superuser or _g(user, GRUPO_VEH_AUDITORIA)


def _gate(request, prueba=puede_ver):
    if not prueba(request.user):
        raise PermissionDenied('No tienes permiso para esta acción en Mantenimiento de vehículos.')


def _perms(user):
    return {'puede_km': puede_km(user), 'puede_mant': puede_mant(user), 'puede_comentar': puede_comentar(user),
            'puede_registrar': puede_registrar(user), 'puede_editar_veh': puede_editar_vehiculo(user)}


AVISO_FALTAN = 100   # <--- hecho por claude code (12-oct-2026): pedido del usuario "cuando le falten 100 km que mande una notificación"


def _etapa_aviso(v):
    """0 = nada · 1 = faltan AVISO_FALTAN o menos · 2 = vencido."""
    f = v.get('falta')
    if f is None:
        return 0
    if f <= 0:
        return 2
    return 1 if f <= AVISO_FALTAN else 0


def _avisar(v_antes, v_despues, origen):
    """Aviso (campana/toast) al grupo vehiculos_alertas SOLO al cruzar a "faltan ≤ 100" o a "vencido"
    (el semáforo naranja de ≤ 10 % sigue siendo solo visual)."""
    if _etapa_aviso(v_despues) <= _etapa_aviso(v_antes):
        return 0
    from core.utils_notifications import crear_notificacion
    if _etapa_aviso(v_despues) == 2:
        txt = f"Mantenimiento VENCIDO: {v_despues['nombre']} va en {v_despues['estado_actual']:,} {v_despues['unidad']} (tocaba a los {v_despues['proximo']:,})."
    else:
        txt = f"Mantenimiento próximo: {v_despues['nombre']} va en {v_despues['estado_actual']:,} {v_despues['unidad']}; toca a los {v_despues['proximo']:,} (faltan {v_despues['falta']:,})."
    txt = txt.replace(',', '.') + f' Registrado por {origen}.'
    n = 0
    for u in get_user_model().objects.filter(groups__name=GRUPO_VEH_ALERTAS, is_active=True).distinct():
        try:
            crear_notificacion(u, txt, modulo='vehiculos', tipo='advertencia',
                               extra=reverse('vehiculos:detalle', args=[v_despues['id']]), enviar_correo=False)
            n += 1
        except Exception as e:
            print('[vehiculos] no se pudo notificar a', u, e)
    return n


def _veh(vid):
    v = VS.vehiculo(vid)
    if not v:
        raise Http404('Vehículo no encontrado.')
    return v


@login_required
def flota(request):
    _gate(request)
    todos = request.GET.get('todos') == '1'
    vehs = VS.vehiculos(incluir_fuera_de_uso=todos)
    orden = {'vencido': 0, 'pronto': 1, 'ok': 2, 'sin_dato': 3}
    vehs.sort(key=lambda v: (orden[v['semaforo']], v['falta'] if v['falta'] is not None else 10**9))
    ctx = _perms(request.user)
    ctx.update({'vehs': vehs, 'todos': todos,
                'kpi_total': len(vehs), 'kpi_vencidos': sum(1 for v in vehs if v['semaforo'] == 'vencido'),
                'kpi_pronto': sum(1 for v in vehs if v['semaforo'] == 'pronto')})
    return render(request, 'mantenimiento_mecanico/vehiculos_flota.html', ctx)


@login_required
def detalle(request, vid):
    _gate(request)
    v = _veh(vid)
    tareas = VS.tareas_para(v)
    hist = VS.historial(vid)
    coms = {}
    for c in Comentario.objects.filter(mant_vehic_id__in=[h['id'] for h in hist]).select_related('autor').order_by('creado'):
        coms.setdefault(c.mant_vehic_id, []).append({'autor': (c.autor.get_full_name() or c.autor.username) if c.autor else '—',
                                                    'fecha': c.creado.strftime('%d/%m/%Y %H:%M'), 'texto': c.texto})
    for h in hist:
        h['comentarios'] = coms.get(h['id'], [])
    # <--- hecho por claude code (12-oct-2026): cargas de diésel del vehículo (formato de Access: Gasto, Estado km, Fecha, Comentario)
    from .models import Entrega
    cargas = list(Entrega.objects.filter(vehiculo_id=vid, insumo__clave='diesel').order_by('-fecha', '-hora', '-id')[:30])
    ctx = _perms(request.user)
    ctx.update({'cargas_diesel': cargas, 'puede_diesel': request.user.is_superuser or _g(request.user, 'mantenimiento_mecanico', 'mantenimiento_mecanico_lectura')})
    ctx.update({'v': v, 'tareas': tareas, 'hist': hist, 'lecturas': VS.lecturas(vid),
                'personas': VS.personas(), 'hoy': datetime.date.today(),
                'n_toca': sum(1 for t in tareas if t['toca']),
                'comentarios_json': {str(h['id']): h['comentarios'] for h in hist}})
    return render(request, 'mantenimiento_mecanico/vehiculo_detalle.html', ctx)


def _valor(request):
    raw = (request.POST.get('valor') or '').strip().replace(',', '').replace('.', '')
    return int(raw) if raw.isdigit() else None


@login_required
@require_POST
def lectura_crear(request, vid):
    _gate(request, puede_km)
    v = _veh(vid)
    valor, fecha = _valor(request), _fecha(request.POST.get('fecha'))
    if valor is None or not fecha:
        messages.error(request, 'Escribe el km/horas y la fecha.')
    elif fecha > datetime.date.today():
        messages.error(request, 'La fecha no puede ser futura.')
    elif v['estado_actual'] is not None and valor < v['estado_actual'] and not v.get('SinTacometro'):
        messages.error(request, f'El valor ({valor:,}) es menor al estado actual ({v["estado_actual"]:,}).'.replace(',', '.'))
    else:
        VS.registrar_lectura(vid, valor, fecha, request.user)
        n = _avisar(v, VS.vehiculo(vid), request.user.get_full_name() or request.user.username)
        if n:
            messages.warning(request, f'Le toca mantenimiento: se avisó a {n} persona(s).')
        prox = v['proximo']
        extra = f' Próximo mantenimiento a los {prox:,} {v["unidad"]} (faltan {prox - valor:,}).'.replace(',', '.') if prox else ''
        messages.success(request, f'Lectura registrada: {valor:,} {v["unidad"]}.'.replace(',', '.') + extra)
    return redirect('vehiculos:detalle', vid=vid)


@login_required
@require_POST
def mant_crear(request, vid):
    _gate(request, puede_mant)
    v = _veh(vid)
    valor, fecha = _valor(request), _fecha(request.POST.get('fecha'))
    persona = (request.POST.get('persona') or '').strip()
    tareas = VS.tareas_para(v)
    ids_validos = {t['id'] for t in tareas}
    hechas = {int(x) for x in request.POST.getlist('hecho') if x.isdigit() and int(x) in ids_validos}
    err = []
    if valor is None:
        err.append('Escribe el km/horas del mantenimiento.')
    if not fecha or fecha > datetime.date.today():
        err.append('La fecha es obligatoria y no puede ser futura.')
    if not persona.isdigit() or int(persona) not in {p['id'] for p in VS.personas()}:
        err.append('Elige quién hizo el mantenimiento.')
    if valor is not None and v['KmUltMant'] is not None and valor < v['KmUltMant'] and not v.get('SinTacometro'):
        err.append(f'El valor ({valor:,}) es menor al del último mantenimiento ({v["KmUltMant"]:,}).'.replace(',', '.'))
    if not hechas:
        err.append('Marca al menos una tarea como hecha.')
    if err:
        for e in err:
            messages.error(request, e)
        return redirect('vehiculos:detalle', vid=vid)
    mid = VS.registrar_mantenimiento(vid, valor, fecha, int(persona), hechas, [t['id'] for t in tareas], request.user)
    prox = valor + v['intervalo'] if v['intervalo'] else None
    messages.success(request, f'Mantenimiento registrado ({len(hechas)} de {len(tareas)} tareas hechas).'
                     + (f' Próximo a los {prox:,} {v["unidad"]}.'.replace(',', '.') if prox else ''))
    return redirect(reverse('vehiculos:detalle', args=[vid]) + f'#mant-{mid}')


@login_required
@require_POST
def mant_comentario(request, mid):
    _gate(request, puede_comentar)
    m = VS.mantenimiento(mid)
    if not m:
        raise Http404
    texto = (request.POST.get('texto') or '').strip()
    if len(texto) < 2:
        messages.error(request, 'Escribe el comentario.')
    else:
        Comentario.objects.create(mant_vehic_id=mid, autor=request.user, texto=texto[:2000])
        messages.success(request, 'Comentario agregado.')
    return redirect(reverse('vehiculos:detalle', args=[m['GenVehiculoID']]) + f'#mant-{mid}')


# ── PDF y Excel ──────────────────────────────────────────────────────────────────────────────
def _hoja(v):
    return {'v': v, 'tareas': VS.tareas_para(v)}


@login_required
def hoja_pdf(request, vid):
    """Hoja de tareas para imprimir y llenar a mano (formato de Access): una página."""
    _gate(request)
    ctx = {'hojas': [_hoja(_veh(vid))], 'logo': _logo_file(), 'auditora': FIRMA_AUDITORA, 'hoy': datetime.date.today()}
    return _pdf(request, 'mantenimiento_mecanico/pdf/hojas_vehiculos.html', ctx, f'hoja_mantenimiento_{vid}.pdf')


@login_required
def hojas_pdf(request):
    """Todas las hojas de la flota en uso, una página por vehículo (como el reporte de Access)."""
    _gate(request)
    ctx = {'hojas': [_hoja(v) for v in VS.vehiculos()], 'logo': _logo_file(),
           'auditora': FIRMA_AUDITORA, 'hoy': datetime.date.today()}
    return _pdf(request, 'mantenimiento_mecanico/pdf/hojas_vehiculos.html', ctx, 'hojas_mantenimiento_vehiculos.pdf')


@login_required
def mant_pdf(request, mid):
    """Ficha de un mantenimiento ya registrado, con lo que se marcó como hecho."""
    _gate(request)
    m = VS.mantenimiento(mid)
    if not m:
        raise Http404
    v = _veh(m['GenVehiculoID'])
    ctx = {'m': m, 'v': v, 'logo': _logo_file(), 'auditora': FIRMA_AUDITORA,
           'comentarios': Comentario.objects.filter(mant_vehic_id=mid).select_related('autor').order_by('creado'),
           'proximo': (m['KmReal_Horas'] + v['intervalo']) if v['intervalo'] else None, 'num': str(mid)}
    return _pdf(request, 'mantenimiento_mecanico/pdf/mant_vehiculo.html', ctx, f'mantenimiento_{mid}.pdf')


@login_required
def historial_xlsx(request, vid):
    _gate(request)
    v = _veh(vid)
    wb, est = _wb()
    ws = wb.active
    ws.title = 'Historial'
    ws['A1'] = f'Historial de mantenimiento · {v["nombre"]}'
    ws['A1'].font = est['b']
    ws['A2'] = ' · '.join(x for x in [f'Placa {v["Placa"]}' if v.get('Placa') else '', f'Intervalo {v["intervalo"]} {v["unidad"]}'] if x)
    _encabezado(ws, 4, ['Nº registro', 'Fecha', f'{v["unidad"].upper()}', 'Realizado por', 'Tareas hechas', 'Tareas totales', 'Registró'], est)
    f = 5
    for h in VS.historial(vid, limite=5000):
        for i, val in enumerate([h['id'], h['Fecha'] or '', h['KmReal_Horas'], h['persona'], h['hechas'] or 0, h['tareas'], h['Usuario']], 1):
            ws.cell(row=f, column=i, value=val)
        ws.cell(row=f, column=2).number_format = 'DD/MM/YYYY'
        f += 1
    ws2 = wb.create_sheet('Tareas hoy')
    _encabezado(ws2, 1, ['Nº', 'Tarea', 'Intervalo', 'Última vez', 'Nunca hecho', 'Toca hacer esta vez'], est)
    for r, t in enumerate(VS.tareas_para(v), 2):
        for i, val in enumerate([t['n'], t['Tarea'], t['Intervalo'], t['ultima_fecha'] or '',
                                 'X' if t['nunca'] else '', 'X' if t['toca'] else ''], 1):
            ws2.cell(row=r, column=i, value=val)
        ws2.cell(row=r, column=4).number_format = 'DD/MM/YYYY'
    for w_, cols in ((ws, zip('ABCDEFG', (12, 12, 12, 22, 14, 14, 16))), (ws2, zip('ABCDEF', (6, 70, 10, 12, 12, 18)))):
        for col, wd in cols:
            w_.column_dimensions[col].width = wd
    nombre = ''.join(ch if ch.isalnum() else '_' for ch in v['nombre'])
    return _xlsx_response(wb, f'historial_{nombre}.xlsx')


# ── Alta y edición de vehículos (12-oct-2026) ───────────────────────────────
_CAMPOS_TXT = (('marca', 50), ('tipo', 50), ('color', 50), ('placa', 20), ('chasis', 50), ('motor', 50), ('cuenta_diesel', 50))


def _leer_vehiculo(request, obj):
    """Llena `obj` (VehiculoMant) desde el POST. Devuelve (errores, lectura_inicial)."""
    P, errores = request.POST, []
    for campo, largo in _CAMPOS_TXT:
        setattr(obj, campo, (P.get(campo) or '').strip()[:largo])
    if obj.placa:
        obj.placa = obj.placa.upper()
    if not obj.marca:
        errores.append('La marca es obligatoria.')
    anio = (P.get('anio') or '').strip()
    if anio:
        try:
            obj.anio = int(anio)
            if not 1950 <= obj.anio <= datetime.date.today().year + 1:
                errores.append('El año no es válido.')
        except ValueError:
            errores.append('El año debe ser un número.')
    else:
        obj.anio = None
    try:
        obj.intervalo = int((P.get('intervalo') or '').replace('.', '').replace(',', ''))
        if obj.intervalo <= 0:
            raise ValueError
    except ValueError:
        errores.append('El intervalo de mantenimiento es obligatorio (km, horas o millas entre cada mantenimiento).')
    unidad = P.get('unidad') or 'km'
    obj.por_horas, obj.millas = unidad == 'h', unidad == 'mi'
    obj.agricultura = P.get('clase') == 'tractor'
    obj.sin_tacometro = P.get('sin_tacometro') == '1'
    obj.no_en_uso = P.get('no_en_uso') == '1'
    from .models import VehiculoMant
    if obj.placa and VehiculoMant.objects.filter(placa__iexact=obj.placa).exclude(pk=obj.pk).exists():
        errores.append(f'Ya existe un vehículo con la placa {obj.placa}.')
    lectura = None
    li = (P.get('lectura_inicial') or '').strip().replace('.', '').replace(',', '')
    if li:
        try:
            lectura = int(li)
            if lectura < 0:
                raise ValueError
        except ValueError:
            errores.append('La lectura inicial debe ser un número entero.')
    return errores, lectura


def _form_vehiculo(request, obj, nuevo):
    ctx = _perms(request.user)
    ctx.update({'obj': obj, 'nuevo': nuevo, 'hoy': datetime.date.today(),
                'unidad': 'h' if obj.por_horas else ('mi' if obj.millas else 'km'), 'post': request.POST})
    return render(request, 'mantenimiento_mecanico/vehiculo_form.html', ctx)


@login_required
def vehiculo_nuevo(request):
    _gate(request, puede_registrar)
    from .models import VehiculoMant
    obj = VehiculoMant()
    if request.method == 'POST':
        errores, lectura = _leer_vehiculo(request, obj)
        if errores:
            for e in errores:
                messages.error(request, e)
            return _form_vehiculo(request, obj, True)
        obj.save()
        if lectura is not None:
            VS.registrar_lectura(obj.pk, lectura, _fecha(request.POST.get('fecha_lectura'), datetime.date.today()), request.user)
        messages.success(request, f'Vehículo «{obj.nombre}» registrado.')
        return redirect('vehiculos:detalle', vid=obj.pk)
    return _form_vehiculo(request, obj, True)


@login_required
def vehiculo_editar(request, vid):
    _gate(request, puede_editar_vehiculo)
    from .models import VehiculoMant
    obj = VehiculoMant.objects.filter(pk=vid).first()
    if not obj:
        raise Http404('Vehículo no encontrado.')
    if request.method == 'POST':
        errores, _ = _leer_vehiculo(request, obj)
        if errores:
            for e in errores:
                messages.error(request, e)
            return _form_vehiculo(request, obj, False)
        obj.save()
        messages.success(request, 'Datos del vehículo actualizados.')
        return redirect('vehiculos:detalle', vid=obj.pk)
    return _form_vehiculo(request, obj, False)
