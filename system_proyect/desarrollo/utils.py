# <--- hecho por claude code: helpers de desarrollo (validación de adjuntos, permisos).
import os
from django.core.exceptions import ValidationError

# Extensiones permitidas (PDF, imágenes, Word, Excel, texto). Nada ejecutable.
ADJUNTO_EXT_OK = {
    '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp',
    '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt',
}
ADJUNTO_MAX_BYTES = 10 * 1024 * 1024   # 10 MB


def validar_adjunto(archivo):
    """Valida extensión y tamaño de un archivo subido. Lanza ValidationError."""
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in ADJUNTO_EXT_OK:
        raise ValidationError(
            f'Tipo de archivo no permitido ({ext}). Permitidos: '
            'PDF, imágenes, Word, Excel, texto.')
    if archivo.size > ADJUNTO_MAX_BYTES:
        raise ValidationError('El archivo supera el límite de 10 MB.')
    return True


# ── Permisos (grupos Django, nunca is_staff como rol) ──
def es_admin_desarrollo(user):
    return user.is_superuser or user.groups.filter(name='desarrollo_admin').exists()


def es_dev_desarrollo(user):
    return (es_admin_desarrollo(user)
            or user.groups.filter(name='desarrollo_dev').exists())


def puede_entrar_desarrollo(user):
    """Quién puede entrar al módulo: dev/admin + el grupo staff 'desarrollo_solicitante'."""
    return (es_dev_desarrollo(user)
            or user.groups.filter(name='desarrollo_solicitante').exists())


def es_solo_solicitante(user):
    """Staff que SOLO crea requerimientos y ve su historial (sin roadmap/proyectos/todos)."""
    return puede_entrar_desarrollo(user) and not es_dev_desarrollo(user)


def puede_ver_requerimiento(user, req):
    """Admin/dev ven todo; el solicitante y el responsable ven el suyo.
    (Los dev pueden editar/mover cualquiera, así que también deben poder verlos.)"""
    if es_dev_desarrollo(user):
        return True
    return req.solicitante_id == user.id or req.responsable_id == user.id
