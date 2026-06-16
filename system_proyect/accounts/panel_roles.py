# accounts/panel_roles.py
# <--- hecho por claude code: lógica del "panel general" para staff multi-rol.
"""Determina si un usuario staff debe ver el dashboard general (con todos sus
botones) y qué secciones/áreas le corresponden.

Reglas:
- Solo aplica a is_staff (no superuser, no usuarios normales).
- Ve el panel general si tiene 2+ "buckets" de rol, o si tiene maestro en
  ambas áreas (BL y Colegio) — ese es el único caso que activa el toggle.
"""

_GRUPOS_COORD_BL  = ('coordinador_bilingue', 'coordinador_bl', 'coord_progress_bl')
_GRUPOS_COORD_COL = ('coordinadores_colegio', 'coordinador_colegio', 'coordinadores', 'coordinador_col')


def _g(user, *names):
    return user.groups.filter(name__in=names).exists()


def panel_buckets(user):
    """Conjunto de 'buckets' de rol con dashboard propio que tiene el usuario."""
    b = set()
    if _g(user, 'administracion') or user.has_perm('tickets.view_ticket'):
        b.add('tickets')
    if _g(user, *_GRUPOS_COORD_BL) or _g(user, *_GRUPOS_COORD_COL):
        b.add('coordinador')
    if _g(user, 'maestros_bilingue', 'maestros_colegio'):
        b.add('maestro')
    if _g(user, 'reloj'):
        b.add('reloj')
    return b


def maestro_dos_areas(user):
    """True si es maestro en BL y Colegio (única condición del toggle de área)."""
    return _g(user, 'maestros_bilingue') and _g(user, 'maestros_colegio')


def es_multi_panel(user):
    """¿Debe este usuario ver el dashboard general en vez de un dashboard único?"""
    if not user.is_authenticated or user.is_superuser or not user.is_staff:
        return False
    return len(panel_buckets(user)) >= 2 or maestro_dos_areas(user)
