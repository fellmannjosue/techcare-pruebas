from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')

_COORD_COLOR = {
    'C1': '#c92a2a',
    'C2': '#1971c2',
    'C3': '#2f9e44',
    'C4': '#e67700',
}

@register.filter
def coord_color(codigo):
    return _COORD_COLOR.get(codigo, '#6c757d')
