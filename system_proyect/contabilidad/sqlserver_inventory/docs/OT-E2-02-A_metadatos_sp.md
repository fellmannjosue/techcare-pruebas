# OT-E2-02-A — Metadatos de los 4 SP de maestros y sus tablas (SOLO LECTURA)

> Extraído del catálogo de **`Test2`** vía el alias `inventario_test2` **con guard previo**
> (`DB_NAME()='Test2'`, `IS_ROLEMEMBER('Des_EquipoInventario')=1`). **Ningún SP fue ejecutado**;
> solo se leyeron `sys.sql_modules`, `sys.parameters`, `sys.columns`, `sys.indexes`,
> `sys.check_constraints` y `sys.foreign_keys`. Sin escrituras, sin secretos.
>
> **Permiso VIEW DEFINITION: OK** — las 4 definiciones (`m.definition`) llegaron **no nulas**
> (3 000–4 196 caracteres cada una). No hubo bloqueo.

---

## 1. Firmas de los 4 SP (definición leída del cuerpo)

Los defaults **sí existen en el cuerpo T-SQL** aunque `sys.parameters.has_default_value` devuelva
`0` (limitación conocida: SQL Server no expone defaults de T-SQL en el catálogo). Todas las firmas
**coinciden con la Guía Técnica §5.1**. Ningún parámetro es `OUTPUT`.

```sql
dbo.spInvCategoriaGuardar   (@CategoriaID INT = NULL, @Codigo VARCHAR(20), @Nombre NVARCHAR(80),
                             @Activo BIT = 1, @RV BINARY(8) = NULL)
dbo.spInvUnidadMedidaGuardar(@UnidadMedidaID INT = NULL, @Codigo VARCHAR(10), @Nombre NVARCHAR(50),
                             @DecimalesCantidad TINYINT = 0, @Activo BIT = 1, @RV BINARY(8) = NULL)
dbo.spInvAlmacenGuardar     (@AlmacenID INT = NULL, @Codigo VARCHAR(20), @Nombre NVARCHAR(80),
                             @EsPredeterminado BIT = 0, @Activo BIT = 1, @RV BINARY(8) = NULL)
dbo.spInvArticuloGuardar    (@ArticuloID INT = NULL, @Codigo VARCHAR(30), @Descripcion NVARCHAR(150),
                             @CategoriaID INT, @UnidadMedidaID INT, @Activo BIT = 1,
                             @Observacion NVARCHAR(250) = NULL, @RV BINARY(8) = NULL)
```

Comportamientos comunes observados en el cuerpo (los 4 SP):
- `SET NOCOUNT ON; SET XACT_ABORT ON;` + opciones ANSI fijadas por ejecución.
- **Normalización:** `@Codigo = UPPER(LTRIM(RTRIM(@Codigo)))`; nombre/descripción con `LTRIM/RTRIM`.
- **Crear:** ID y RV `NULL`. **Modificar:** exige ID **y** RV (si falta RV → 513x1); compara RV con la
  fila actual (si difiere → 513x3/51325/51335 *"cambió desde que fue leído"*).
- **Retorno:** un `SELECT` de la **fila completa** (incluye `RV` nuevo y campos de auditoría).
  Para artículo incluye `CostoPromedioActual` (**Python nunca lo envía**).

## 2. Parámetros (sys.parameters) — orden, tipo, precisión, OUTPUT, default

`max_length` de `nvarchar` está en **bytes** (÷2 = caracteres). `has_default` = valor del catálogo
(siempre `0`); el default **real** está en la columna "Default (cuerpo)".

| SP | # | Parámetro | Tipo | Long/Prec | OUTPUT | Default (cuerpo) |
|---|---|---|---|---|---|---|
| spInvCategoriaGuardar | 1 | @CategoriaID | int | 10 | No | NULL |
|  | 2 | @Codigo | varchar | 20 | No | — |
|  | 3 | @Nombre | nvarchar | 80 (160 B) | No | — |
|  | 4 | @Activo | bit | — | No | 1 |
|  | 5 | @RV | binary | 8 | No | NULL |
| spInvUnidadMedidaGuardar | 1 | @UnidadMedidaID | int | 10 | No | NULL |
|  | 2 | @Codigo | varchar | 10 | No | — |
|  | 3 | @Nombre | nvarchar | 50 (100 B) | No | — |
|  | 4 | @DecimalesCantidad | tinyint | 3 | No | 0 |
|  | 5 | @Activo | bit | — | No | 1 |
|  | 6 | @RV | binary | 8 | No | NULL |
| spInvAlmacenGuardar | 1 | @AlmacenID | int | 10 | No | NULL |
|  | 2 | @Codigo | varchar | 20 | No | — |
|  | 3 | @Nombre | nvarchar | 80 (160 B) | No | — |
|  | 4 | @EsPredeterminado | bit | — | No | 0 |
|  | 5 | @Activo | bit | — | No | 1 |
|  | 6 | @RV | binary | 8 | No | NULL |
| spInvArticuloGuardar | 1 | @ArticuloID | int | 10 | No | NULL |
|  | 2 | @Codigo | varchar | 30 | No | — |
|  | 3 | @Descripcion | nvarchar | 150 (300 B) | No | — |
|  | 4 | @CategoriaID | int | 10 | No | — |
|  | 5 | @UnidadMedidaID | int | 10 | No | — |
|  | 6 | @Activo | bit | — | No | 1 |
|  | 7 | @Observacion | nvarchar | 250 (500 B) | No | NULL |
|  | 8 | @RV | binary | 8 | No | NULL |

## 3. DDL de las 4 tablas

Auditoría común en las 4: `CreadoFecha datetime2 NOT NULL default sysdatetime()`,
`CreadoPor nvarchar(100) NOT NULL default CONVERT(nvarchar(100), suser_sname())`,
`ModificadoFecha datetime2 NULL`, `ModificadoPor nvarchar(100) NULL`, `RV rowversion (timestamp) NOT NULL`.
**No hay columnas computadas.** Todas las PK son `IDENTITY` clustered.

### 3.1 `dbo.tblInvCategoria`
| Col | Tipo | Nulo | Identity | Default |
|---|---|---|---|---|
| CategoriaID | int | No | **Sí** | — |
| Codigo | varchar(20) | No | | — |
| Nombre | nvarchar(80) | No | | — |
| Activo | bit | No | | 1 |
| (+ auditoría, RV) | | | | |

Índices: `PK_tblInvCategoria` (clustered, CategoriaID) · **`UQ_tblInvCategoria_Codigo` UNIQUE (Codigo)**.
CHECK: ninguno. FK: ninguna.

### 3.2 `dbo.tblInvUnidadMedida`
| Col | Tipo | Nulo | Identity | Default |
|---|---|---|---|---|
| UnidadMedidaID | int | No | **Sí** | — |
| Codigo | varchar(10) | No | | — |
| Nombre | nvarchar(50) | No | | — |
| DecimalesCantidad | tinyint | No | | 0 |
| Activo | bit | No | | 1 |
| (+ auditoría, RV) | | | | |

Índices: `PK_tblInvUnidadMedida` (UnidadMedidaID) · **`UQ_tblInvUnidadMedida_Codigo` UNIQUE (Codigo)**.
CHECK: **`CK_tblInvUnidadMedida_DecimalesCantidad`** `DecimalesCantidad BETWEEN 0 AND 3`. FK: ninguna.

### 3.3 `dbo.tblInvAlmacen`
| Col | Tipo | Nulo | Identity | Default |
|---|---|---|---|---|
| AlmacenID | int | No | **Sí** | — |
| Codigo | varchar(20) | No | | — |
| Nombre | nvarchar(80) | No | | — |
| EsPredeterminado | bit | No | | 0 |
| Activo | bit | No | | 1 |
| (+ auditoría, RV) | | | | |

Índices: `PK_tblInvAlmacen` (AlmacenID) · **`UQ_tblInvAlmacen_Codigo` UNIQUE (Codigo)** ·
**`UX_tblInvAlmacen_UnPredeterminado` UNIQUE FILTRADO (EsPredeterminado) WHERE EsPredeterminado = 1**
→ garantiza **máximo un almacén predeterminado** a nivel de índice.
CHECK: **`CK_tblInvAlmacen_PredeterminadoActivo`** `EsPredeterminado = 0 OR Activo = 1`
(un predeterminado debe estar activo). FK: ninguna.

### 3.4 `dbo.tblInvArticulo`
| Col | Tipo | Nulo | Identity | Default |
|---|---|---|---|---|
| ArticuloID | int | No | **Sí** | — |
| Codigo | varchar(30) | No | | — |
| Descripcion | nvarchar(150) | No | | — |
| CategoriaID | int | No | | — |
| UnidadMedidaID | int | No | | — |
| Activo | bit | No | | 1 |
| Observacion | nvarchar(250) | Sí | | — |
| **CostoPromedioActual** | **decimal(19,6)** | No | | **0** |
| (+ auditoría, RV) | | | | |

Índices: `PK_tblInvArticulo` (ArticuloID) · **`UQ_tblInvArticulo_Codigo` UNIQUE (Codigo)**.
CHECK: **`CK_tblInvArticulo_CostoPromedioActual`** `CostoPromedioActual >= 0`.
FK: `FK_tblInvArticulo_tblInvCategoria` (CategoriaID → tblInvCategoria, NO ACTION) ·
`FK_tblInvArticulo_tblInvUnidadMedida` (UnidadMedidaID → tblInvUnidadMedida, NO ACTION).

### Resumen de índices ÚNICOS (is_unique = 1)
| Tabla | Índice | Columnas | Filtro |
|---|---|---|---|
| tblInvCategoria | UQ_tblInvCategoria_Codigo | Codigo | — |
| tblInvUnidadMedida | UQ_tblInvUnidadMedida_Codigo | Codigo | — |
| tblInvAlmacen | UQ_tblInvAlmacen_Codigo | Codigo | — |
| tblInvAlmacen | UX_tblInvAlmacen_UnPredeterminado | EsPredeterminado | `EsPredeterminado = 1` |
| tblInvArticulo | UQ_tblInvArticulo_Codigo | Codigo | — |
(+ las 4 PK clustered.) Un código repetido producirá **2601/2627** (violación de índice único).

## 4. THROW 51xxx por SP (extraídos del cuerpo)

| SP | Nº | Mensaje |
|---|---|---|
| spInvCategoriaGuardar | 51300 | Código y nombre son obligatorios. |
|  | 51301 | ROWVERSION es obligatorio para modificar. |
|  | 51302 | Categoría inexistente. |
|  | 51303 | La categoría cambió desde que fue leída. Recargue y reintente. |
| spInvUnidadMedidaGuardar | 51310 | Datos de unidad de medida inválidos. |
|  | 51311 | ROWVERSION es obligatorio para modificar. |
|  | 51312 | Unidad de medida inexistente. |
|  | 51313 | La unidad cambió desde que fue leída. Recargue y reintente. |
| spInvAlmacenGuardar | 51320 | Código y nombre son obligatorios. |
|  | 51321 | El almacén predeterminado debe estar activo. |
|  | 51322 | Ya existe un almacén predeterminado. |
|  | 51323 | ROWVERSION es obligatorio para modificar. |
|  | 51324 | Almacén inexistente. |
|  | 51325 | El almacén cambió desde que fue leído. Recargue y reintente. |
| spInvArticuloGuardar | 51330 | Código y descripción son obligatorios. |
|  | 51331 | Categoría inexistente o inactiva. |
|  | 51332 | Unidad de medida inexistente o inactiva. |
|  | 51333 | ROWVERSION es obligatorio para modificar. |
|  | 51334 | Artículo inexistente. |
|  | 51335 | El artículo cambió desde que fue leído. Recargue y reintente. |
|  | 51336 | El código del artículo es estable y no puede modificarse. |

Coincide **1:1** con el catálogo de errores de la Guía §5.1. Los códigos **51303/51313/51325/51335**
son *conflicto ROWVERSION* (recargar y pedir decisión al usuario); **2601/2627** = código duplicado.

## 5. Implicaciones para la Etapa 2 (para el diseño, no implementado)
- Python envía **Decimal/bytes/bool** exactos; el RV devuelto (8 bytes) debe **conservarse** para editar.
- Códigos se normalizan en SQL a **mayúsculas y sin espacios** → mostrar el valor devuelto, no el tecleado.
- Longitudes efectivas: Codigo 20/10/20/30; Nombre 80/50/80; Descripcion 150; Observacion 250.
- El **código del artículo es inmutable** (51336) y **`CostoPromedioActual` no se envía nunca**.
- **Solo un almacén predeterminado** (índice filtrado + 51322) y debe estar **activo** (CHECK + 51321).
- `DecimalesCantidad` 0..3 (CHECK + 51310).
- FKs `NO ACTION` en artículo → una categoría/unidad **en uso no se puede borrar** (no aplica: no hay SP de borrado).

---

## Bloque de Cierre
```
ARCHIVOS NUEVOS: contabilidad/sqlserver_inventory/docs/OT-E2-02-A_metadatos_sp.md
ARCHIVOS MODIFICADOS: (ninguno)
INVARIANTES VERIFICADOS:
  1  Sin ejecutar ningún SP ......................... OK (solo lectura de catálogo sys.*)
  2  Sin spInvMovimientoAplicarInterno ............... OK
  3  Sin migraciones ................................. OK
  4  Sin modificar código ............................ OK (solo el .md entregable)
  5  Sin tocar settings/.env/flags ................... OK
  6  Sin exponer secretos ............................ OK
  7  Guard previo (Test2 + rol) antes de leer ........ OK (cursor_test2(verificar=True))
  8  VIEW DEFINITION disponible (definition no NULL) . OK (4/4)
  9  Firmas coinciden con la Guía §5.1 ............... OK (1:1, defaults en cuerpo)
  10 Índices únicos identificados .................... OK (5 UQ/UX + 4 PK)
  11 THROW 51xxx extraídos ........................... OK (21 códigos, coinciden con la Guía)
  12 has_default_value=0 en catálogo ................. OBSERVACIÓN (limitación SQL Server; defaults leídos del cuerpo)
PRUEBAS EJECUTADAS Y RESULTADO:
  Consultas de catálogo (sys.sql_modules, sys.parameters, sys.columns, sys.indexes,
  sys.check_constraints, sys.foreign_keys) con guard → OK. Sin escrituras.
SUPUESTOS TOMADOS:
  - nvarchar max_length del catálogo está en bytes; se reporta en caracteres (÷2), verificado contra el cuerpo del SP.
  - No se transcriben los cuerpos completos de los SP en el informe (3-4 KB c/u); se resumen firma, normalización,
    retorno y THROW. Los cuerpos íntegros están disponibles en Test2 vía sys.sql_modules.
BLOQUEOS / PENDIENTES PARA DIRECCIÓN:
  - Ninguno para esta OT. (Los bloqueos de higiene —.env en historial— quedaron reportados en OT-E2-00.)
  - La Etapa 2 (escritura por estos 4 SP) sigue SIN autorización; este documento es insumo de diseño.
```
