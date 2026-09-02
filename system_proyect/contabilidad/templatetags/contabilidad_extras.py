# <--- hecho por claude code: filtros de formato de dinero para Contabilidad (Lempiras + millares)
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def lps(value):
    """Formatea un número como Lempiras con separador de millares: 1250 -> 'L 1,250.00'."""
    try:
        n = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    return 'L ' + f'{n:,.2f}'


@register.filter
def miles(value):
    """Solo separador de millares, sin símbolo: 1250 -> '1,250.00'."""
    try:
        n = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f'{n:,.2f}'
