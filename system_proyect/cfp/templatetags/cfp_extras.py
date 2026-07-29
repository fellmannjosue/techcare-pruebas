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
def money_c(value):
    """<--- hecho por claude code: formato contable del informe INFOP — el cero se
    imprime como un guion, igual que en la hoja de Excel original."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return value or ''
    return '-' if n == 0 else f"{n:,.2f}"


@register.filter
def get(d, key):
    """Acceso a dict por clave variable en templates."""
    try:
        return d.get(key, '')
    except AttributeError:
        return ''
