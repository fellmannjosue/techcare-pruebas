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

@register.filter
def grado_num(value):
    """<--- hecho por claude code: número de grado desde 'PrimariaBL 3ero-_2' → 3."""
    if not value:
        return None
    m = re.search(r'(\d+)(?:ero|do|to|mo|vo|no)', str(value), re.IGNORECASE)
    return int(m.group(1)) if m else None


@register.simple_tag
def reporte_png_url(tipo, pk):
    """<--- hecho por claude code: URL absoluta con token firmado al PNG del reporte (para WhatsApp)."""
    from django.core import signing
    from django.urls import reverse
    tok = signing.dumps({'t': tipo, 'pk': pk}, salt='reporte-png-v1')
    return 'https://servicios.ana-hn.org:437' + reverse('reporte_png', args=[tok])


@register.filter
def orden_grado(value):
    """<--- hecho por claude code: clave de orden por grado+sección para agrupar (acordeón)
    en el dashboard. 'PrimariaBL 3ero-_2' → '03-02'; 'ColegioBL 7mo-_1' → '07-01'."""
    if not value:
        return 'zz'
    m = re.search(r'(\d+)(?:ero|do|to|mo|vo|no)-_(\d+)', str(value), re.IGNORECASE)
    if m:
        return f'{int(m.group(1)):02d}-{int(m.group(2)):02d}'
    return str(value)


# <--- hecho por claude code: mapa grado→coordinador para Progress (orden por grado).
# El filtrado por coordinador se hace por USERNAME (identidad real), no por el código,
# porque en el sistema Lorena=C5 y Johannys=C6, pero la etiqueta pedida es la de la lista.
_PROG_COORD_ORDEN = [
    ('C6', 'Lorena López',    'Primero (1 y 2)',           {1},       'llopez@ana-hn.org'),
    ('C5', 'Johannys Zelaya', 'Segundo (1 y 2)',           {2},       'jzelaya@ana-hn.org'),
    ('C1', 'Catherine Varela','Tercero (1 y 2)',           {3},       'cvarela@ana-hn.org'),
    ('C3', 'Isabel Alcerro',  'Cuarto (1 y 2)',            {4},       'ialcerro@ana-hn.org'),
    ('C4', 'Josué Martínez',  'Quinto y Sexto',            {5, 6},    'jmartinez@ana-hn.org'),
    ('C2', 'David Ruiz',      'Séptimo, Octavo y Noveno',  {7, 8, 9}, 'druiz@ana-hn.org'),
]


@register.simple_tag
def progress_por_coordinador(reportes, usuario=None):
    """Agrupa los progress reports por coordinador (grado). Si el usuario es un
    coordinador (no superusuario), devuelve SOLO su grupo; el superusuario ve todos."""
    def _num(g):
        m = re.search(r'(\d+)(?:ero|do|to|mo|vo|no)', str(g or ''), re.IGNORECASE)
        return int(m.group(1)) if m else None
    lst = list(reportes or [])
    grupos, usados = [], set()
    for cod, nom, rango, grados, username in _PROG_COORD_ORDEN:
        rs = [r for r in lst if _num(getattr(r, 'grado', '')) in grados]
        for r in rs:
            usados.add(id(r))
        grupos.append({'cod': cod, 'nombre': nom, 'rango': rango, 'reportes': rs, 'username': username})
    sin = [r for r in lst if id(r) not in usados]
    if sin:
        grupos.append({'cod': '—', 'nombre': 'Sin coordinador asignado', 'rango': 'Otros grados',
                       'reportes': sin, 'username': None})

    # Un coordinador ve SOLO su grupo (por username). Superuser / Principal / otros → todos.
    if usuario is not None and getattr(usuario, 'is_authenticated', False) and not usuario.is_superuser:
        propios = [g for g in grupos if g['username'] and g['username'] == usuario.username]
        if propios:
            return propios
    return grupos


_COORD_COLOR = {
    'C1': '#c92a2a',
    'C2': '#1971c2',
    'C3': '#2f9e44',
    'C4': '#e67700',
    'C5': '#9c36b5',
    'C6': '#0c8599',
}

@register.filter
def coord_color(codigo):
    return _COORD_COLOR.get(codigo, '#6c757d')
