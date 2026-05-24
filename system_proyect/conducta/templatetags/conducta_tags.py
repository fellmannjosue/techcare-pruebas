import re
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')


# <--- hecho por claude code: filtro para convertir el grado del DB a formato legible
# 'PrimariaBL 1ero-_2' → 'Primero 2'   |  'ColegioBL 7mo-_1' → 'Séptimo 1'
_GRADO_NUMERO = {
    '1ero': 'Primero',
    '2do':  'Segundo',
    '3ero': 'Tercero',
    '4to':  'Cuarto',
    '5to':  'Quinto',
    '6to':  'Sexto',
    '7mo':  'Séptimo',
    '8vo':  'Octavo',
    '9no':  'Noveno',
    '10mo': 'Décimo',
    '11vo': 'Undécimo',
    '12vo': 'Duodécimo',
}

@register.filter
def formato_grado(value):
    """
    Convierte el grado almacenado en DB a texto legible.
    'PrimariaBL 1ero-_2' → 'Primero 2'
    'ColegioBL 7mo-_1'   → 'Séptimo 1'
    Devuelve el valor original si el formato no es reconocido.
    """
    if not value:
        return value
    s = str(value).strip()
    m = re.search(r'(\d+(?:ero|do|to|mo|vo|no))-_(\d+)', s, re.IGNORECASE)
    if m:
        grado_key = m.group(1).lower()
        seccion   = m.group(2)
        nombre    = _GRADO_NUMERO.get(grado_key)
        if nombre:
            return f'{nombre} {seccion}'
    return s

_COORD_COLOR = {
    'C1': '#c92a2a',
    'C2': '#1971c2',
    'C3': '#2f9e44',
    'C4': '#e67700',
}

@register.filter
def coord_color(codigo):
    return _COORD_COLOR.get(codigo, '#6c757d')
