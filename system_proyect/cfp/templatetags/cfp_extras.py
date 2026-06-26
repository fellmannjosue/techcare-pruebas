from django import template

register = template.Library()


@register.filter
def money(value):
    """Formatea un número como 1,234.50 (sin símbolo)."""
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return value


@register.filter
def get(d, key):
    """Acceso a dict por clave variable en templates."""
    try:
        return d.get(key, '')
    except AttributeError:
        return ''
