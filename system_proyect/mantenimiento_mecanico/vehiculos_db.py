# <--- hecho por claude code (12-oct-2026): MANTENIMIENTO DE VEHÍCULOS sobre sponsors2 (MySQL).
# Reemplaza a vehiculos_sql.py (que leía/escribía en Test2). Los datos se copiaron de Access (AdmonANASQL) con
# `manage.py importar_mant_vehiculos`; desde el cambio se registra solo aquí. Devuelve diccionarios con las MISMAS
# claves que usaba la versión de SQL Server, para que plantillas y PDF no cambien.
# Reglas de Access (verificadas con su historial):
#   · Aplica: tractor (agricultura) → Todo+Tract+Tract/Vehic · motor/planta (por horas) → Todo · vehículo → Todo+Vehic+Tract/Vehic
#   · Próximo = km/horas del último mantenimiento + intervalo del vehículo · Falta = próximo − estado actual
#   · "Toca hacer esta vez": nunca hecha, o (mantenimientos desde la última vez + 1) ≥ intervalo de la tarea
import datetime

from django.db import transaction
from django.db.models import OuterRef, Subquery

from .models import (LecturaVehiculo, MantenimientoVehiculo, MantenimientoVehiculoTarea, TareaMantVehiculo,
                     TecnicoVehiculo, VehiculoMant)

# <--- hecho por claude code (12-oct-2026): ARRANQUE LIMPIO. Se borró el historial de mantenimientos de Access y solo se
# conservaron las lecturas de km. Mientras un vehículo no tenga mantenimientos en TechCare, el próximo se cuenta desde su
# última lectura IMPORTADA (registrado_por vacío; las de TechCare llevan quién las registró) + el intervalo. Con el primer mantenimiento manda la regla normal.
INICIO_LIMPIO = datetime.date(2026, 10, 12)

_APLICA = {'tractor': {'todo', 'tract', 'tract/vehic'}, 'motor': {'todo'}, 'vehiculo': {'todo', 'vehic', 'tract/vehic'}}


def categoria(v):
    if v.agricultura:
        return 'tractor'
    if v.por_horas:
        return 'motor'
    return 'vehiculo'


def _qs():
    ult_l = LecturaVehiculo.objects.filter(vehiculo=OuterRef('pk')).order_by('-fecha', '-id')
    ult_m = MantenimientoVehiculo.objects.filter(vehiculo=OuterRef('pk')).order_by('-fecha', '-id')
    return VehiculoMant.objects.annotate(
        km_lectura=Subquery(ult_l.values('valor')[:1]), fecha_lectura=Subquery(ult_l.values('fecha')[:1]),
        km_ult_mant=Subquery(ult_m.values('valor')[:1]), fecha_ult_mant=Subquery(ult_m.values('fecha')[:1]),
        km_base=Subquery(LecturaVehiculo.objects.filter(vehiculo=OuterRef('pk'), registrado_por__isnull=True, fecha__lte=INICIO_LIMPIO).order_by('-fecha', '-id').values('valor')[:1]),
        fecha_base=Subquery(LecturaVehiculo.objects.filter(vehiculo=OuterRef('pk'), registrado_por__isnull=True, fecha__lte=INICIO_LIMPIO).order_by('-fecha', '-id').values('fecha')[:1]),
        # <--- hecho por claude code (12-oct-2026): vehículo dado de alta en TechCare (sin lecturas de Access) → la base es su PRIMERA lectura
        km_primera=Subquery(LecturaVehiculo.objects.filter(vehiculo=OuterRef('pk')).order_by('fecha', 'id').values('valor')[:1]),
        fecha_primera=Subquery(LecturaVehiculo.objects.filter(vehiculo=OuterRef('pk')).order_by('fecha', 'id').values('fecha')[:1]))


def _dict(v):
    d = {'id': v.pk, 'obj': v, 'nombre': v.nombre, 'categoria': categoria(v), 'Placa': v.placa, 'Anio': v.anio,
         'NoEnUso': v.no_en_uso, 'SinTacometro': v.sin_tacometro, 'KmLectura': v.km_lectura, 'FechaLectura': v.fecha_lectura,
         'KmUltMant': v.km_ult_mant, 'FechaUltMant': v.fecha_ult_mant,
         'unidad': 'h' if v.por_horas else ('mi' if v.millas else 'km'), 'intervalo': v.intervalo or 0}
    lect, mant = d['KmLectura'], d['KmUltMant']
    d['estado_actual'] = max(x for x in (lect, mant) if x is not None) if (lect is not None or mant is not None) else None
    # base del conteo: el último mantenimiento; si aún no hay, la última lectura del arranque limpio
    # (y para un vehículo registrado en TechCare, su primera lectura)
    km_b, f_b = (v.km_base, v.fecha_base) if v.km_base is not None else (v.km_primera, v.fecha_primera)
    d['base_es_lectura'] = mant is None and km_b is not None
    d['KmBase'] = mant if mant is not None else km_b
    d['FechaBase'] = v.fecha_ult_mant if mant is not None else f_b
    base = d['KmBase']
    d['proximo'] = (base + d['intervalo']) if (base is not None and d['intervalo']) else None
    d['falta'] = (d['proximo'] - d['estado_actual']) if (d['proximo'] is not None and d['estado_actual'] is not None) else None
    d['excedido'] = (-d['falta']) if (d['falta'] is not None and d['falta'] <= 0) else None
    d['semaforo'] = semaforo(d['falta'], d['intervalo'])
    d['pct'] = (max(0, min(100, int((d['intervalo'] - max(d['falta'], 0)) * 100 / d['intervalo'])))
                if (d['falta'] is not None and d['intervalo']) else 0)
    return d


def semaforo(falta, intervalo):
    if falta is None:
        return 'sin_dato'
    if falta <= 0:
        return 'vencido'
    if intervalo and falta <= intervalo * 0.1:
        return 'pronto'
    return 'ok'


def vehiculos(incluir_fuera_de_uso=False):
    qs = _qs() if incluir_fuera_de_uso else _qs().filter(no_en_uso=False)
    return [_dict(v) for v in qs]


def vehiculo(vid):
    v = _qs().filter(pk=vid).first()
    return _dict(v) if v else None


def tareas_para(v):
    aplica = _APLICA[v['categoria']]
    cat = [t for t in TareaMantVehiculo.objects.filter(activo=True).order_by('numero', 'id') if (t.aplica or '').strip().lower() in aplica]
    mants = list(MantenimientoVehiculo.objects.filter(vehiculo_id=v['id']).order_by('-fecha', '-id').values('id', 'fecha', 'valor'))
    orden = {m['id']: i for i, m in enumerate(mants)}
    porid = {m['id']: m for m in mants}
    ultima = {}
    for tid, mid in MantenimientoVehiculoTarea.objects.filter(mantenimiento__vehiculo_id=v['id'], hecho=True).values_list('tarea_id', 'mantenimiento_id'):
        if tid not in ultima or orden[mid] < orden[ultima[tid]]:
            ultima[tid] = mid
    out = []
    for i, t in enumerate(cat, 1):
        mid = ultima.get(t.pk)
        desde = orden[mid] if mid else None
        intervalo = t.intervalo or 1
        out.append({'id': t.pk, 'n': i, 'Numero': t.numero, 'Tarea': t.tarea, 'Aplica': t.aplica, 'Intervalo': intervalo,
                    'ultima_fecha': porid[mid]['fecha'] if mid else None, 'ultima_km': porid[mid]['valor'] if mid else None,
                    'nunca': mid is None, 'toca': (mid is None) or ((desde + 1) >= intervalo),
                    'faltan': None if mid is None else max(0, intervalo - (desde + 1))})
    return out


def personas():
    return [{'id': t.pk, 'nombre': t.nombre} for t in TecnicoVehiculo.objects.filter(activo=True).order_by('nombre')]


def _persona(m):
    return m.tecnico.nombre if m.tecnico_id else ''


def historial(vid, limite=60):
    qs = (MantenimientoVehiculo.objects.filter(vehiculo_id=vid).select_related('tecnico', 'registrado_por')
          .order_by('-fecha', '-id')[:limite])
    out = []
    for m in qs:
        tareas = list(m.tareas.values_list('hecho', flat=True))
        out.append({'id': m.pk, 'Fecha': m.fecha, 'KmReal_Horas': m.valor, 'persona': _persona(m),
                    'tareas': len(tareas), 'hechas': sum(1 for h in tareas if h), 'FchaReg': m.creado,
                    'Usuario': (m.registrado_por.get_full_name() or m.registrado_por.username) if m.registrado_por_id else m.usuario})
    return out


def lecturas(vid, limite=15):
    return [{'id': l.pk, 'EstadoKm_Horas': l.valor, 'Fecha': l.fecha,
             'Usuario': (l.registrado_por.get_full_name() or l.registrado_por.username) if l.registrado_por_id else l.usuario}
            for l in LecturaVehiculo.objects.filter(vehiculo_id=vid).select_related('registrado_por').order_by('-fecha', '-id')[:limite]]


def mantenimiento(mid):
    m = MantenimientoVehiculo.objects.select_related('tecnico', 'registrado_por').filter(pk=mid).first()
    if not m:
        return None
    return {'id': m.pk, 'GenVehiculoID': m.vehiculo_id, 'Fecha': m.fecha, 'KmReal_Horas': m.valor, 'persona': _persona(m),
            'Usuario': (m.registrado_por.get_full_name() or m.registrado_por.username) if m.registrado_por_id else m.usuario,
            'FchaReg': m.creado,
            'tareas': [{'Numero': t.tarea.numero, 'Tarea': t.tarea.tarea, 'Intervalo': t.tarea.intervalo, 'Aplica': t.tarea.aplica, 'Hecho': t.hecho}
                       for t in m.tareas.select_related('tarea').order_by('tarea__numero', 'id')]}


def registrar_lectura(vid, valor, fecha, usuario):
    LecturaVehiculo.objects.create(vehiculo_id=vid, valor=int(valor), fecha=fecha, registrado_por=usuario,
                                   usuario=(usuario.first_name or usuario.username)[:50])


def registrar_mantenimiento(vid, valor, fecha, persona_id, hechas_ids, tareas_ids, usuario):
    with transaction.atomic():
        m = MantenimientoVehiculo.objects.create(vehiculo_id=vid, tecnico_id=int(persona_id), valor=int(valor), fecha=fecha,
                                                 registrado_por=usuario, usuario=(usuario.first_name or usuario.username)[:50])
        MantenimientoVehiculoTarea.objects.bulk_create([MantenimientoVehiculoTarea(mantenimiento=m, tarea_id=int(t), hecho=int(t) in hechas_ids)
                                                        for t in tareas_ids])
        if not LecturaVehiculo.objects.filter(vehiculo_id=vid, valor=int(valor), fecha=fecha).exists():
            registrar_lectura(vid, valor, fecha, usuario)   # como en Access: el mantenimiento deja la lectura del día
    return m.pk
