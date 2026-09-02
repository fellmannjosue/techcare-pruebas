# Inventario institucional (SQL Server · Test2) — Punto de control estable · Etapa 0–1

> Acta del punto de control **aprobado** de la integración de **solo lectura** entre TechCare
> (app `contabilidad`) y el Inventario institucional en SQL Server, base **`Test2`**.
> Este documento no contiene credenciales, host, cadenas de conexión ni datos personales.

---

## 1. Objetivo de la integración
Leer, **sin escribir**, el Inventario institucional que vive en SQL Server (base `Test2`),
que es la **única autoridad** de artículos, categorías, unidades, almacenes, existencias,
Kardex, costo promedio, movimientos, idempotencia y concurrencia. La app `contabilidad`
actúa solo como consumidor de lectura; la lógica de negocio permanece en SQL Server.
Alcance de esta etapa: conexión segura + guard + health check + DTOs + **8 consultas SELECT**
+ integración mínima con Django. **No** migra datos, **no** escribe, **no** implementa
compras/ventas/apertura/ajustes/devoluciones/reversos.

## 2. Arquitectura utilizada
- **Alias Django `inventario_test2`** (independiente; no reutiliza otros aliases).
- Backend **`mssql-django`** (ENGINE `mssql`), accedido por **`django.db.connections`**
  (`connections['inventario_test2'].cursor()`), con consultas **parametrizadas**.
- **Guard obligatorio de base y rol** antes de cada lectura: valida
  `DB_NAME() = 'Test2'` e `IS_ROLEMEMBER('Des_EquipoInventario') = 1`; si falla, **bloquea**.
- **Router anti-migraciones** (`contabilidad/db_router.py`): `allow_migrate` devuelve `False`
  para el alias `inventario_test2` (jamás se crean/alteran objetos ahí) y no rutea el ORM a
  esa base.
- **Capa encapsulada** `contabilidad/sqlserver_inventory/`: `config`, `guard`, `connection`,
  `dto`, `errors`, `queries`, `health`, `services`. **Las views no contienen SQL.**

## 3. Estado validado
- ✅ Conexión a **`Test2`** exitosa.
- ✅ Membresía en **`Des_EquipoInventario`** confirmada (`EsDesarrollo = 1`).
- ✅ **20 pruebas aprobadas** (unitarias + estáticas + integración).
- ✅ Las **8 consultas de lectura** funcionan (ejecutan y devuelven filas / 0 filas sin error).
- ℹ️ Las tablas de inventario (`tblInv*`) están **actualmente vacías** en `Test2` (instalación
  validada estructuralmente, aún sin datos cargados) → las lecturas devuelven 0 filas.
- ✅ **`tblComProvd`** (catálogo institucional de proveedores) disponible y consultable.

## 4. Fuentes oficiales (autoridad de lectura)
| Dato | Objeto SQL Server |
|---|---|
| Artículos y **costo promedio** | `dbo.tblInvArticulo` (`CostoPromedioActual`) |
| **Existencias** | `dbo.tblInvExistencia` (`CantidadActual`) |
| **Kardex** | `dbo.tblInvMovimiento` + `dbo.tblInvMovimientoDetalle` |
| Categorías / Unidades / Almacenes | `dbo.tblInvCategoria` / `dbo.tblInvUnidadMedida` / `dbo.tblInvAlmacen` |
| **Proveedores** | `dbo.tblComProvd` |

Existencia y costo se **leen tal cual**; nunca se recalculan en Python.

## 5. Restricciones (invariantes de la capa)
- **Cero DML directo** (sin `INSERT` / `UPDATE` / `DELETE`) sobre `tblInv*`.
- **No** llamar `spInvMovimientoAplicarInterno` (núcleo privado).
- **No** calcular existencia ni costo promedio en Python.
- **No** usar `float` para cantidades, costos, precios ni existencias (siempre `Decimal`).
- **No** ejecutar migraciones sobre el alias `inventario_test2`.
- **No** integrar Facturación.
- **No** avanzar a operaciones de escritura sin autorización explícita.

## 6. Variables de entorno requeridas (solo nombres, sin valores)
Definidas en el `.env` (fuera del repositorio):
- `INV_TEST2_DB_NAME`
- `INV_TEST2_DB_USER`
- `INV_TEST2_DB_PASSWORD`
- `INV_TEST2_DB_HOST`
- `INV_TEST2_DB_PORT`
- `INV_TEST2_ODBC_DRIVER`
- `INV_TEST2_ENCRYPT` *(pendiente de la política TLS del DBA)*
- `INV_TEST2_TRUST_CERT` *(pendiente de la política TLS del DBA)*
- `INV_TEST2_MOSTRAR_TARJETA`

> Si las `INV_TEST2_DB_*` no están definidas, el alias cae a las variables `MSSQL_TEST2_*`
> ya existentes. No se documentan valores aquí.

## 7. Comandos seguros de validación (no destructivos)
```bash
# 1) Chequeo del proyecto
python manage.py check

# 2) Pruebas unitarias, estáticas e integración (no destructivas)
python -m unittest \
  contabilidad.sqlserver_inventory.tests.test_unit \
  contabilidad.sqlserver_inventory.tests.test_static \
  contabilidad.sqlserver_inventory.tests.test_integration
```
El health check corre siempre (SELECT de identidad, sin tocar `tblInv*`); las lecturas de
integración solo se ejecutan si el guard pasa (Test2 + rol), de lo contrario se saltan y
reportan el bloqueo.

## 8. Flag `INV_TEST2_MOSTRAR_TARJETA`
Controla la aparición de la tarjeta "Inventario institucional (SQL Server)" en el hub de
Inventario. **Apagado por defecto** (`0`). Encenderlo (`1`) es una decisión de interfaz;
no afecta la capa de datos ni el guard.

## 9. Estado de la interfaz
- Tarjeta "Inventario institucional (SQL Server)" **oculta** (`INV_TEST2_MOSTRAR_TARJETA=0`).
- **Apache no reiniciado**: los cambios están en código y tomarán efecto en el próximo
  reinicio que se autorice.

## 10. Próximo paso pendiente
**Etapa 2** — registrar categorías, unidades, almacenes y artículos mediante los **stored
procedures públicos aprobados**. Requiere **autorización explícita de Dirección**. No se
cargan datos ni se implementa hasta recibirla.

---

## Fuera de esta integración
Los siguientes cambios **no** pertenecen a este punto de control y se gestionan aparte:
- **Reasignaciones de usuarios o grupos** (p. ej. roles de Abastecimiento/Ventas/Auditoría).
- **Modificaciones del flujo guiado** de Inventario (número de pasos, retorno al dashboard).
- **Cambios del módulo `red`** (ANA Network Manager, racks, etc.).
- **Cualquier cambio del Inventario MySQL existente** (modelos, servicios, vistas de escritura).
