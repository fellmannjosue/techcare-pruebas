# <--- hecho por claude code (seguridad 05-nov-2026): UN solo criterio de acceso a Inventario (vistas de inventario, hub de servicio_tecnico y, a pedido, el menú).
# El permiso que se revisaba antes, 'inventario.view_item', NO EXISTE (el modelo es InventoryItem), así que has_perm siempre daba False
# y en la práctica solo entraban el superusuario y el grupo 'inventario'. El permiso real es 'inventario.view_inventoryitem'; hoy solo lo
# tiene el propio grupo 'inventario' (glorenzo, ylagos), así que corregirlo no cambia quién entra.

PERMISO_INVENTARIO = 'inventario.view_inventoryitem'
GRUPO_INVENTARIO = 'inventario'


def puede_inventario(user):
    """Superusuario, permiso inventario.view_inventoryitem o grupo 'inventario'."""
    if not getattr(user, 'is_authenticated', False):
        return False
    return bool(user.is_superuser or user.has_perm(PERMISO_INVENTARIO)
                or user.groups.filter(name=GRUPO_INVENTARIO).exists())
