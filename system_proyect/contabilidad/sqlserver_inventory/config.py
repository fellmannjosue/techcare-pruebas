# <--- hecho por claude code: constantes de la capa de Inventario SQL Server (Test2).
# NO contiene credenciales ni cadenas de conexión (esas viven en el alias Django + .env).

# Alias Django (settings.DATABASES) usado exclusivamente por esta capa.
ALIAS = 'inventario_test2'

# Nombre de aplicación que identifica app/ambiente en la auditoría SQL (se fija en el
# `extra_params` del alias). Aquí solo como referencia informativa.
APP_NAME = 'ANA-Inventario-Python-Test2'

# Ambiente autorizado: la capa se niega a operar si DB_NAME() != DB_ESPERADA.
DB_ESPERADA = 'Test2'

# Rol de desarrollo requerido en Test2 (IS_ROLEMEMBER debe devolver 1).
ROL_DESARROLLO = 'Des_EquipoInventario'

# (Sin ORIGEN_SISTEMA en esta etapa: NO hay escrituras.)
