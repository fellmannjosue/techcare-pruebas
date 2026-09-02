# <--- hecho por claude code: router que BLINDA el alias `inventario_test2` (Inventario
# institucional SQL Server, base Test2, SOLO LECTURA).
#
# La Guía Técnica prohíbe que las migraciones de Django creen/alteren/eliminen objetos en
# Test2 (ni objetos institucionales dbo.tblInv*/typInv*/spInv*, ni las tablas propias de
# Django). Este router garantiza que `manage.py migrate` NUNCA toque ese alias, y que el
# ORM no rutee lecturas/escrituras ahí por accidente: el acceso es exclusivamente por la
# capa `contabilidad.sqlserver_inventory` con `connections['inventario_test2'].cursor()`.
ALIAS = 'inventario_test2'


class InventarioTest2Router:
    def db_for_read(self, model, **hints):
        # No se rutea ningún modelo ORM a Test2; las lecturas van por cursor explícito.
        return None

    def db_for_write(self, model, **hints):
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Jamás migrar nada en el alias del Inventario institucional.
        if db == ALIAS:
            return False
        # Para el resto de aliases, comportamiento por defecto.
        return None
