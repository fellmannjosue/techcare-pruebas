# <--- hecho por claude code: lógica de negocio del módulo de desarrollo (estados,
# historial, notificaciones). Mantiene las vistas delgadas.
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.models import User

from .models import RequerimientoDesarrollo, HistorialRequerimiento, ProyectoDesarrollo

MODULO = 'desarrollo'
_UNSET = object()   # centinela: distinguir "no tocar responsable" de "poner en None"


def _notificar(usuarios, mensaje, tipo='info'):
    """Envía una notificación TechCare a cada usuario (usa el sistema existente)."""
    from core.utils_notifications import crear_notificacion
    vistos = set()
    for u in usuarios:
        if u and u.id not in vistos:
            vistos.add(u.id)
            crear_notificacion(u, mensaje, MODULO, tipo=tipo)


def admins_desarrollo():
    """Usuarios que administran desarrollo (grupo desarrollo_admin + superusers)."""
    return list(User.objects.filter(is_active=True)
                .filter(Q(is_superuser=True) | Q(groups__name='desarrollo_admin'))
                .distinct())


@transaction.atomic
def registrar_cambio(req, usuario, *, nuevo_estado=None, nuevo_responsable=_UNSET,
                     nuevo_porcentaje=None, comentario=''):
    """Aplica cambios a un requerimiento y crea HistorialRequerimiento SOLO si cambió
    el estado, el responsable o el avance. Todo dentro de una transacción."""
    cambios = False
    h = HistorialRequerimiento(requerimiento=req, usuario=usuario, comentario=comentario,
                               estado_anterior=req.estado, estado_nuevo=req.estado)

    if nuevo_estado is not None and nuevo_estado != req.estado:
        h.estado_anterior = req.estado
        h.estado_nuevo = nuevo_estado
        req.estado = nuevo_estado
        cambios = True

    if nuevo_responsable is not _UNSET and nuevo_responsable != req.responsable:
        h.responsable_anterior = req.responsable
        h.responsable_nuevo = nuevo_responsable
        req.responsable = nuevo_responsable
        cambios = True

    if nuevo_porcentaje is not None and int(nuevo_porcentaje) != req.porcentaje_avance:
        h.porcentaje_anterior = req.porcentaje_avance
        h.porcentaje_nuevo = max(0, min(100, int(nuevo_porcentaje)))
        req.porcentaje_avance = h.porcentaje_nuevo
        cambios = True

    req.modificado_por = usuario
    req.save()

    if cambios or comentario:
        h.save()
    return cambios


def notificar_evento(req, evento):
    """Notificaciones de eventos importantes (sin saturar por cambios triviales)."""
    if evento == 'nuevo':
        _notificar(admins_desarrollo(), f'Nuevo requerimiento {req.codigo}: {req.titulo}', 'info')
    elif evento == 'aprobado':
        _notificar([req.solicitante], f'Tu requerimiento {req.codigo} fue aprobado.', 'exito')
    elif evento == 'asignado':
        _notificar([req.responsable], f'Te asignaron el requerimiento {req.codigo}: {req.titulo}', 'info')
    elif evento == 'pruebas':
        _notificar([req.solicitante], f'{req.codigo} pasó a pruebas.', 'info')
    elif evento == 'produccion':
        _notificar([req.solicitante], f'{req.codigo} ya está en producción.', 'exito')


@transaction.atomic
def convertir_en_proyecto(req, usuario, **datos_proyecto):
    """Crea un ProyectoDesarrollo desde un requerimiento aprobado y lo asocia.
    Evita duplicar: si el requerimiento ya tiene proyecto, lo devuelve."""
    if req.proyecto_id:
        return req.proyecto, False
    proy = ProyectoDesarrollo(
        nombre=datos_proyecto.get('nombre') or req.titulo,
        modulo=datos_proyecto.get('modulo') or req.modulo,
        area=datos_proyecto.get('area') or req.area,
        descripcion=datos_proyecto.get('descripcion') or req.descripcion,
        problema_que_resuelve=req.problema_actual,
        solicitado_por=req.solicitante,
        responsable=req.responsable,
        creado_por=usuario, modificado_por=usuario,
    )
    proy.save()   # genera TC-PRY-XXXX
    req.proyecto = proy
    req.save(update_fields=['proyecto'])
    HistorialRequerimiento.objects.create(
        requerimiento=req, usuario=usuario,
        estado_anterior=req.estado, estado_nuevo=req.estado,
        comentario=f'Convertido en proyecto {proy.codigo}')
    return proy, True
