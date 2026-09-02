# <--- hecho por claude code: autorización del módulo Contabilidad (backend, no solo UI).
# Nunca se usa is_staff como rol: se valida por permisos Django del app 'contabilidad'.

PERM_APP = 'contabilidad'


def puede(user, codename):
    """True si el usuario tiene la capacidad 'contabilidad.<codename>' (superuser siempre)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    return user.has_perm(f'{PERM_APP}.{codename}')


def puede_ver_contabilidad(user):
    """Acceso al módulo (dashboard). Requisito mínimo para entrar."""
    return puede(user, 'ver_contabilidad')


def es_admin_contabilidad(user):
    """Puede administrar la configuración contable del módulo."""
    return puede(user, 'administrar_configuracion')
