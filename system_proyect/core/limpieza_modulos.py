"""<--- hecho por claude code (13-nov-2026): Configuración → Sistema → Respaldo y limpieza de módulos.

Paso 1 «Guardar JSON general»: arma un ZIP con el JSON de cada tabla de los módulos elegidos (datos + catálogos +
historial) y los archivos subidos (fotos, PDFs, evidencias). Se guarda en el servidor y se descarga.
Paso 2 «Limpiar BD»: borra SOLO las tablas de datos (y su historial) de los módulos de un respaldo existente.
Candados: superusuario real, contraseña, frase «BORRAR TODO», respaldo de menos de RESPALDO_HORAS y sin datos nuevos
desde el respaldo, y todo en una transacción que se deshace si el borrado en cascada toca otra tabla.
El Reloj, el Inventario, los usuarios y la configuración NO están en el registro: nunca se tocan.
"""
import io
import json
import os
import re
import zipfile
from datetime import datetime, timedelta

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.db import models, transaction
from django.db.models import Max

DIRECTORIO = '/home/admin2/backups/limpieza_modulos'
RESPALDO_HORAS = 12
FRASE = 'BORRAR TODO'
NOMBRE_RE = re.compile(r'^respaldo_\d{8}_\d{6}\.zip$')

# clave → título, ícono, tablas que se BORRAN, tablas que se CONSERVAN (solo van en el respaldo como referencia)
MODULOS = [
    {'clave': 'servicio', 'titulo': 'Servicio técnico · fichas de mantenimiento', 'icono': 'ti-tool', 'color': '#0ca678',
     'nota': 'Computadoras, impresoras, control, inspecciones, entregas, recogidas, casos especiales, cambios, reasignaciones, préstamos, mantenimientos y reparaciones. El inventario NO se toca.',
     'borrar': ['mantenimiento.MaintenanceRecord', 'mantenimiento.FotoMantenimiento'],
     'conservar': ['mantenimiento.TipoFalla']},
    {'clave': 'conducta', 'titulo': 'Coordinación Bilingüe y Colegio · conducta', 'icono': 'ti-clipboard-text', 'color': '#2563eb',
     'nota': 'Reportes conductuales, informativos, Progress Report, evidencias, tutorías y reforzamiento.',
     'borrar': ['conducta.ReporteConductual', 'conducta.ReporteInformativo', 'conducta.ProgressReport',
                'conducta.EvidenciaReporte', 'conducta.ConvocatoriaTutoria', 'conducta.ConvocatoriaAsignatura',
                'conducta.ConvocatoriaMarca', 'conducta.ConvocatoriaFirma', 'conducta.ReforzamientoMarca'],
     'conservar': ['conducta.IncisoConductual', 'conducta.MateriaDocenteBilingue', 'conducta.MateriaDocenteColegio',
                   'conducta.ConfiguracionCoordinador', 'conducta.ConfiguracionNotificacion',
                   'conducta.PeriodoEscolarConducta', 'conducta.VentanaProgressReport', 'conducta.TutoriaHorario',
                   'conducta.TutoriaGrupoMaestro', 'conducta.ReforzamientoConfig', 'conducta.ReforzamientoDocenteGrado']},
    {'clave': 'notas', 'titulo': 'Coordinación · Notas mitad de parcial', 'icono': 'ti-notes', 'color': '#7048e8', 'opcional': True,
     'nota': 'Comentarios de los maestros, revisiones, cierres y maestro guía. Las asignaciones de maestros se conservan.',
     'borrar': ['notas_parcial.NotaComentario', 'notas_parcial.RevisionFinalizada', 'notas_parcial.CierreNotas',
                'notas_parcial.MaestroGuia'],
     'conservar': ['notas_parcial.AsignacionMaestro']},
    {'clave': 'agendas', 'titulo': 'Coordinación · Agendas', 'icono': 'ti-calendar-week', 'color': '#e8590c', 'opcional': True,
     'nota': 'Agendas semanales y sus imágenes. Los grados y el bloqueo se conservan.',
     'borrar': ['agendas.Agenda', 'agendas.ImagenAgenda'],
     'conservar': ['agendas.GradoAgenda', 'agendas.AgendaBloqueoConfig']},
    {'clave': 'enfermeria', 'titulo': 'Enfermería', 'icono': 'ti-first-aid-kit', 'color': '#d63939',
     'nota': 'Atenciones médicas y uso de medicamentos. Médicos, proveedores, responsables, presentaciones e inventario de medicamentos se conservan.',
     'borrar': ['enfermeria.AtencionMedica', 'enfermeria.UsoMedicamento'],
     'conservar': ['enfermeria.Grado', 'enfermeria.Medico', 'enfermeria.Proveedor', 'enfermeria.Responsable',
                   'enfermeria.Presentacion', 'enfermeria.InventarioMedicamento']},
    {'clave': 'salidas', 'titulo': 'Salidas al baño', 'icono': 'ti-door-exit', 'color': '#1098ad',
     'nota': 'Salidas registradas y sus avisos. Los períodos y las clases de los maestros se conservan.',
     'borrar': ['salidas_bano.SalidaBano', 'salidas_bano.NotificacionSalida'],
     'conservar': ['salidas_bano.PeriodoEscolar', 'salidas_bano.MaestroClase']},
]
POR_CLAVE = {m['clave']: m for m in MODULOS}


def _modelo(label):
    return apps.get_model(label)


def _historial(model):
    h = getattr(model, 'history', None)
    return getattr(h, 'model', None)


def _label(model):
    return model._meta.label


def tablas_borrar(clave):
    """Modelos que se borran: los de datos + su historial (simple_history)."""
    out = []
    for lb in POR_CLAVE[clave]['borrar']:
        m = _modelo(lb)
        out.append(m)
        h = _historial(m)
        if h is not None:
            out.append(h)
    return out


def tablas_respaldo(clave):
    out = list(tablas_borrar(clave))
    for lb in POR_CLAVE[clave]['conservar']:
        m = _modelo(lb)
        out.append(m)
        h = _historial(m)
        if h is not None:
            out.append(h)
    return out


def resumen():
    """Para la pantalla: por módulo, conteo de cada tabla que se borra y de las que se conservan."""
    filas = []
    for m in MODULOS:
        borrar = [{'label': lb, 'nombre': _modelo(lb)._meta.verbose_name_plural, 'n': _modelo(lb).objects.count()} for lb in m['borrar']]
        hist = sum(h.objects.count() for h in (_historial(_modelo(lb)) for lb in m['borrar']) if h is not None)
        conservar = [{'nombre': _modelo(lb)._meta.verbose_name_plural, 'n': _modelo(lb).objects.count()} for lb in m['conservar']]
        filas.append(dict(m, tablas_borrar=borrar, total_borrar=sum(b['n'] for b in borrar), historial=hist,
                          tablas_conservar=conservar))
    return filas


def _archivos(model, qs):
    campos = [f.name for f in model._meta.fields if isinstance(f, models.FileField)]
    if not campos:
        return set()
    out = set()
    for vals in qs.values_list(*campos):
        for v in vals:
            if v:
                out.add(str(v))
    return out


def _huella(model):
    """Conteo + mayor pk (pk entero) o la lista de pks (UUID u otro): sirve para saber si entró algo después del respaldo."""
    qs = model._default_manager.all()
    if isinstance(model._meta.pk, (models.AutoField, models.BigAutoField, models.IntegerField)):
        return {'n': qs.count(), 'max_pk': qs.aggregate(mx=Max('pk'))['mx']}
    pks = [str(p) for p in qs.values_list('pk', flat=True)]
    return {'n': len(pks), 'pks': pks}


def _hay_nuevos(ahora, info):
    if 'pks' in ahora:
        return bool(set(ahora['pks']) - set(info.get('pks', [])))
    if ahora['max_pk'] is None:
        return False
    return info.get('max_pk') is None or ahora['max_pk'] > info['max_pk']


def crear_respaldo(claves, usuario):
    """Paso 1. Devuelve el nombre del ZIP guardado en DIRECTORIO."""
    claves = [c for c in claves if c in POR_CLAVE]
    if not claves:
        raise ValueError('Elige al menos un módulo.')
    os.makedirs(DIRECTORIO, exist_ok=True)
    ahora = datetime.now()
    nombre = ahora.strftime('respaldo_%Y%m%d_%H%M%S.zip')
    ruta = os.path.join(DIRECTORIO, nombre)
    tmp = ruta + '.parcial'
    manifiesto = {'fecha': ahora.isoformat(timespec='seconds'), 'usuario': usuario.get_username(),
                  'modulos': claves, 'tablas': {}, 'borrar': [], 'archivos': 0, 'archivos_faltantes': 0}
    media = set()
    try:
        with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as z:
            for c in claves:
                for model in tablas_respaldo(c):
                    lb = _label(model)
                    if lb in manifiesto['tablas']:
                        continue
                    qs = model._default_manager.all().order_by('pk')
                    manifiesto['tablas'][lb] = _huella(model)
                    with z.open(f'datos/{lb}.json', 'w') as fh:

                        txt = io.TextIOWrapper(fh, encoding='utf-8')
                        serializers.serialize('json', qs.iterator(chunk_size=2000), stream=txt, indent=1)
                        txt.flush()
                        txt.detach()
                    if not lb.split('.')[1].startswith('Historical'):
                        media |= _archivos(model, qs)
                for model in tablas_borrar(c):
                    manifiesto['borrar'].append(_label(model))
            raiz = str(settings.MEDIA_ROOT)
            for rel in sorted(media):
                p = os.path.normpath(os.path.join(raiz, rel))
                if not p.startswith(raiz + os.sep) or not os.path.isfile(p):
                    manifiesto['archivos_faltantes'] += 1
                    continue
                z.write(p, f'media/{rel}', compress_type=zipfile.ZIP_STORED)
                manifiesto['archivos'] += 1
            z.writestr('manifiesto.json', json.dumps(manifiesto, ensure_ascii=False, indent=1))
            z.writestr('LEEME.txt', (
                'Respaldo de TechCare antes de limpiar módulos.\n\n'
                'datos/   un JSON por tabla (formato de Django: manage.py loaddata).\n'
                'media/   fotos, PDFs y evidencias de esos registros (copiar dentro de system_proyect/media/).\n\n'
                'Restaurar (desde system_proyect/, TODOS los JSON en un solo comando):\n'
                '  ../venv/bin/python manage.py loaddata datos/*.json\n'
                '  sudo -u www-data cp -rn media/* /home/admin2/techcare_project/system_proyect/media/\n'))
        os.replace(tmp, ruta)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    with open(ruta[:-4] + '.json', 'w', encoding='utf-8') as f:   # manifiesto suelto para listar sin abrir el ZIP
        json.dump(manifiesto, f, ensure_ascii=False)
    for p in (ruta, ruta[:-4] + '.json'):   # admin2 y www-data (grupo) pueden leer y actualizar
        try:
            os.chmod(p, 0o664)
        except OSError:
            pass
    return nombre


def listar_respaldos():
    if not os.path.isdir(DIRECTORIO):
        return []
    out = []
    for n in sorted(os.listdir(DIRECTORIO), reverse=True):
        if not NOMBRE_RE.match(n):
            continue
        man = leer_manifiesto(n) or {}
        ruta = os.path.join(DIRECTORIO, n)
        fecha = datetime.fromisoformat(man['fecha']) if man.get('fecha') else None
        out.append({'nombre': n, 'mb': round(os.path.getsize(ruta) / 1048576, 1), 'fecha': fecha,
                    'usuario': man.get('usuario', ''), 'limpiado': man.get('limpiado'),
                    'modulos': [POR_CLAVE[c]['titulo'] for c in man.get('modulos', []) if c in POR_CLAVE],
                    'vigente': bool(fecha and datetime.now() - fecha <= timedelta(hours=RESPALDO_HORAS) and not man.get('limpiado'))})
    return out


def ruta_respaldo(nombre):
    if not NOMBRE_RE.match(nombre or ''):
        return None
    p = os.path.join(DIRECTORIO, nombre)
    return p if os.path.isfile(p) else None


def leer_manifiesto(nombre):
    p = ruta_respaldo(nombre)
    if not p:
        return None
    try:
        with open(p[:-4] + '.json', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


class Rechazo(Exception):
    pass


def limpiar(nombre):
    """Paso 2. Borra las tablas de datos del respaldo `nombre`. Devuelve {label: borrados}."""
    man = leer_manifiesto(nombre)
    if not man:
        raise Rechazo('No se encontró el respaldo.')
    if man.get('limpiado'):
        raise Rechazo('Ese respaldo ya se usó para limpiar. Guarda un JSON general nuevo.')
    fecha = datetime.fromisoformat(man['fecha'])
    if datetime.now() - fecha > timedelta(hours=RESPALDO_HORAS):
        raise Rechazo(f'El respaldo tiene más de {RESPALDO_HORAS} horas. Guarda un JSON general nuevo antes de limpiar.')
    borrar = man['borrar']
    # ¿Hay datos nuevos que no están en el respaldo?
    for lb in borrar:
        model = _modelo(lb)
        info = man['tablas'].get(lb) or {}
        ahora = _huella(model)
        if ahora['n'] > info.get('n', 0) or _hay_nuevos(ahora, info):
            raise Rechazo(f'Hay registros nuevos en «{model._meta.verbose_name_plural}» desde el respaldo. Guarda un JSON general nuevo.')
    permitidos = set(borrar)
    total = {}
    with transaction.atomic():
        base = [lb for lb in borrar if not lb.split('.')[1].startswith('Historical')]
        hist = [lb for lb in borrar if lb.split('.')[1].startswith('Historical')]
        for lb in base + hist:   # el historial al final: al borrar se crean filas «-» que también se van
            _n, detalle = _modelo(lb)._default_manager.all().delete()
            for k, v in detalle.items():
                total[k] = total.get(k, 0) + v
        ajenas = {k: v for k, v in total.items() if v and k not in permitidos}
        if ajenas:
            raise Rechazo('Se canceló sin borrar nada: el borrado en cascada alcanzaba otras tablas (' +
                          ', '.join(f'{k}: {v}' for k, v in ajenas.items()) + ').')
    man['limpiado'] = datetime.now().isoformat(timespec='seconds')
    man['borrados'] = total
    with open(ruta_respaldo(nombre)[:-4] + '.json', 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False)
    return total
