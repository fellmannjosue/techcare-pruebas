# <--- hecho por claude code: filtros de presentación (colores de estado/prioridad/semáforo).
from django import template

register = template.Library()

_ESTADO_COLOR = {
    'recibido': 'secondary', 'evaluacion': 'yellow', 'pendiente_aprob': 'orange',
    'aprobado': 'lime', 'rechazado': 'red', 'planificado': 'cyan',
    'desarrollo': 'blue', 'pruebas': 'purple', 'listo_prod': 'teal',
    'produccion': 'green', 'pausado': 'muted', 'cancelado': 'dark',
}
_PRIORIDAD_COLOR = {'critica': 'red', 'alta': 'orange', 'media': 'blue', 'baja': 'secondary'}
_ESTADO_PROY_COLOR = {
    'activo': 'green', 'en_desarrollo': 'blue', 'produccion': 'teal',
    'pausado': 'yellow', 'archivado': 'secondary',
}
_SEMAFORO = {
    'verde':    ('🟢', 'En tiempo',        'green'),
    'amarillo': ('🟡', 'Próximo a vencer', 'yellow'),
    'rojo':     ('🔴', 'Atrasado',         'red'),
    'gris':     ('⚪', 'Sin fecha',        'secondary'),
}


@register.filter
def estado_color(estado):
    return _ESTADO_COLOR.get(estado, 'secondary')


@register.filter
def prioridad_color(prioridad):
    return _PRIORIDAD_COLOR.get(prioridad, 'secondary')


@register.filter
def estado_proy_color(estado):
    return _ESTADO_PROY_COLOR.get(estado, 'secondary')


@register.filter
def semaforo_emoji(clave):
    return _SEMAFORO.get(clave, _SEMAFORO['gris'])[0]


@register.filter
def semaforo_texto(clave):
    return _SEMAFORO.get(clave, _SEMAFORO['gris'])[1]


# <--- hecho por claude code (seguridad 05-nov-2026): la URL del proyecto se pintaba en href tal cual (un "javascript:" quedaba como XSS almacenado); solo se enlaza una ruta interna (/…) o http(s)://
@register.filter
def url_segura(url):
    u = (url or '').strip()
    if not u or '\\' in u or any(ord(c) < 33 for c in u):
        return ''
    if u.startswith('/') and not u.startswith('//'):
        return u
    if u.lower().startswith(('http://', 'https://')):
        return u
    return ''
