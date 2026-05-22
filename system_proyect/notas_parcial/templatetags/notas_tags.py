from django import template

register = template.Library()

# Grupos para control de acceso en vistas
_GRUPOS_COORD   = {'coordinador_bilingue', 'coordinador_colegio', 'coordinadores_colegio', 'coordinadores', 'coord_notas_parcial', 'coord_progress_bl'}
_GRUPOS_MAESTRO = {'maestros_bilingue', 'maestros_colegio', 'maestros_notas_parcial'}

# Grupos específicos que activan el link en el sidebar
_GRUPO_COORD_NOTAS   = ('coord_notas_parcial', 'coord_notas_parcial_bl', 'coord_notas_parcial_col', 'coord_progress_bl', 'notas_revision', 'coord_revision')
_GRUPO_MAESTRO_NOTAS = ('maestros_notas_parcial', 'maestros_notas_parcial_bl', 'maestros_notas_parcial_col')


@register.filter
def nota_baja(value):
    """True si el valor numérico es menor a 70."""
    try:
        return float(value) < 70
    except (TypeError, ValueError):
        return False


@register.filter
def es_coord_notas(user):
    """Sidebar: staff/superuser con grupo coord_notas_parcial (superuser usa su propio bloque)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return False
    return user.groups.filter(name__in=_GRUPO_COORD_NOTAS).exists()


@register.filter
def es_solo_revision(user):
    """True si tiene coord_revision pero NO coord completo — solo puede ver carrusel."""
    if not user or not user.is_authenticated or user.is_superuser:
        return False
    grupos = set(user.groups.values_list('name', flat=True))
    _full = {'coord_notas_parcial', 'coord_notas_parcial_bl', 'coord_notas_parcial_col'}
    return 'coord_revision' in grupos and not (grupos & _full)


@register.filter
def es_maestro_notas(user):
    """Sidebar: usuarios con grupo maestros_notas_parcial."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return False
    return user.groups.filter(name__in=_GRUPO_MAESTRO_NOTAS).exists()
