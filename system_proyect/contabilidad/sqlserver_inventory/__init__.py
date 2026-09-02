# <--- hecho por claude code: capa de acceso de SOLO LECTURA al Inventario institucional
# en SQL Server (base Test2). Autoridad = SQL Server (Guía Técnica).
#
# Reglas duras de esta capa (Etapa 0-1):
#   * SOLO SELECT parametrizado sobre objetos autorizados (dbo.tblInv*, dbo.tblComProvd).
#   * NUNCA INSERT/UPDATE/DELETE ni llamadas a stored procedures / TVP / núcleo privado.
#   * NUNCA se recalcula existencia ni costo promedio en Python (se leen tal cual).
#   * Guard obligatorio antes de cualquier consulta: DB_NAME()='Test2' e
#     IS_ROLEMEMBER('Des_EquipoInventario')=1.
#   * Las views de Django NO contienen SQL: consumen `services`.
