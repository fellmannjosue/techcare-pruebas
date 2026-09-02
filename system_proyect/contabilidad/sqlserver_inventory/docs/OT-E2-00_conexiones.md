# OT-E2-00 — Verificación de conexiones (Etapa 2 · preparación)

> Tarea de **verificación por lectura de código**. No se ejecutó ninguna escritura, SP ni
> migración. Secretos enmascarados (usuario visible, `password ***`, `host ***`).
> Repo: `/home/admin2/techcare_project` · Django project: `system_proyect/` (manage.py) ·
> Capa: `system_proyect/contabilidad/sqlserver_inventory/`.

## Tarea A — Inventario de conexiones

`DATABASES` en `system_proyect/system_proyect/settings.py` (5 alias):

| Alias | Motor | Servidor | Base | Login | Apps que lo usan | ¿Solo lectura? | ¿Alcanza `Test2`? | ¿Toca `tblInv*`/`typInv*`/`spInv*`? |
|---|---|---|---|---|---|---|---|---|
| `default` | mysql | `***` | `sponsors2` | `***` | TODAS (ORM por defecto) | No (RW) | No | No |
| **`padres_sqlserver`** | mssql | `***` | **`Test2`** | `***` | conducta, enfermeria, ingresos_notas, notas_parcial, cfp, salidas_bano | Sí (raw `SELECT` con `%s`) | **🔴 SÍ** | **No** (lee `tblEdc*`/`tblPrs*`) |
| `academico_real` | mssql | `***` | `AdmonANASQL` | `***` | notas_parcial (selección dinámica `_db(area)`) | Sí | No | No |
| `zkbio_sqlserver` | mssql | `***` | `zkbiotime` | `***` | reloj (marcaje biométrico) | Sí | No | No |
| **`inventario_test2`** | mssql | `***` | **`Test2`** | `***` | **solo** `contabilidad/sqlserver_inventory/` (+ `db_router.py`) | Sí (con **guard**) | SÍ (por diseño) | **SÍ** (autorizado, solo lectura) |

Usos reales verificados (`connections[...]` / `.using(...)`): `padres_sqlserver` = 26 usos en 6 apps;
`zkbio_sqlserver` = 30 usos en `reloj`; `inventario_test2` = solo en `settings.py`, `db_router.py`
y `sqlserver_inventory/{connection,health,config,errors}.py`. **No hay `pyodbc` directo ni cadenas
`SERVER=`/`DATABASE=` crudas fuera de `settings.py`.**

### Marcas en ROJO
- **🔴 `padres_sqlserver` apunta a `Test2`.** Dos alias llegan a la base `Test2`. **Aclaración
  imprescindible:** `Test2` es una base **compartida** que aloja DOS esquemas: el **académico**
  (`tblEdc*`/`tblPrs*`) y el de **inventario** (`tblInv*`). `padres_sqlserver` lee **únicamente**
  objetos académicos y **NUNCA** `tblInv*`/`typInv*`/`spInv*`.
- **Ningún alias distinto de `inventario_test2` referencia `tblInv*`/`typInv*`/`spInv*`.**
  Verificado en todo el repo: las únicas 2 apariciones de `tblInv` fuera de la capa están en
  **comentarios** (`settings.py:243`, `db_router.py:5`), no en SQL.

### Estado del invariante
- Invariante **fuerte** ("ningún alias ajeno toca objetos de inventario"): **✅ SE CUMPLE**.
- Invariante **literal** ("un solo alias alcanza `Test2`"): **⚠️ NO** — `padres_sqlserver` también
  llega a `Test2`, pero a un esquema distinto (académico). El aislamiento del inventario se
  garantiza por **objetos** (nadie más consulta `tblInv*`) + el **guard** de rol, no por servidor/base.

## Tarea B — Router y migraciones
- `contabilidad/db_router.py`: `allow_migrate(db, ...)` → **`return False` si `db == 'inventario_test2'`**
  (líneas 25–26). `db_for_read`/`db_for_write` → `None` (no rutea ORM al alias). **✅ Correcto.**
- **No existen modelos Django sobre `tblInv*`** (ningún `db_table='tblInv...'`, ningún `managed=False`
  en `contabilidad/`). La capa usa consultas puras, sin ORM sobre objetos institucionales.
- **Ninguna migración menciona `inventario_test2`** ni objetos `tblInv*`.

## Tarea C — Alcance de las pruebas estáticas
`contabilidad/sqlserver_inventory/tests/test_static.py`:
- **Rutas que barre:** `PAQUETE = <dir de sqlserver_inventory>`; `_archivos_py()` recorre los `.py`
  bajo esa carpeta **excluyendo `tests/`**. **No** recorre otras apps.
- **Patrones prohibidos:** `insert into dbo.tblInv`, `update dbo.tblInv`, `delete from dbo.tblInv`,
  `spInvMovimientoAplicarInterno`, `exec dbo.spInv`, `\bfloat\s*\(`; y patrones de secreto
  (`password=`, `pwd=`, `UID=`).
- **¿Barrería código legítimo de otras apps?** **No.** Al restringirse a `sqlserver_inventory/`, el
  SQL crudo de solo lectura de `conducta`/`enfermeria` sobre `tblEdc*`/`tblPrs*` **no genera hallazgos**. ✅

### Desviación vs. alcance correcto (NO corregida — se propone)
El alcance correcto pedido es **`sqlserver_inventory/` + las views de `contabilidad` que consumen la
capa**. La prueba actual **NO** barre `contabilidad/views_inventario_sql.py` (está fuera de `PAQUETE`),
y los patrones **no** incluyen `typInv*` (TVPs). **Cobertura incompleta** (bajo riesgo: esa view no
contiene SQL, solo llama a `services`). **Diff propuesto (pendiente de aprobación del chat 00):**

```diff
--- a/contabilidad/sqlserver_inventory/tests/test_static.py
+++ b/contabilidad/sqlserver_inventory/tests/test_static.py
@@ PROHIBIDOS
     r'spInvMovimientoAplicarInterno',
     r'exec\s+dbo\.spInv',
+    r'exec\s+dbo\.typInv',      # TVPs tampoco se invocan desde esta etapa
     r'\bfloat\s*\(',
@@ def _archivos_py():
     for raiz, _dirs, files in os.walk(PAQUETE):
         if os.path.basename(raiz) == 'tests':
             continue
         for f in files:
             if f.endswith('.py'):
                 yield os.path.join(raiz, f)
+    # además, la view de contabilidad que consume la capa
+    extra = os.path.join(os.path.dirname(PAQUETE), 'views_inventario_sql.py')
+    if os.path.exists(extra):
+        yield extra
```

## Tarea D — Higiene del repositorio
1. **Ruta del proyecto:** repo root `/home/admin2/techcare_project`; `manage.py` en
   `system_proyect/manage.py`; paquete de settings en `system_proyect/system_proyect/`;
   capa en `/home/admin2/techcare_project/system_proyect/contabilidad/sqlserver_inventory/`.
2. **`.env` en `.gitignore`:** ✅ (`.gitignore` líneas 14–15: `.env`, `.env.*`). **No está trackeado**
   hoy (`git ls-files | grep .env` → vacío).
3. **🔴 `.env` EN EL HISTORIAL:** `git log --all --diff-filter=A` muestra que **`system_proyect/.env`
   se agregó en el commit `98e6320` (2025-03-18)**. Contiene **10 asignaciones `CLAVE=valor`**, entre
   ellas **`DJANGO_SECRET_KEY`, `DB_PASSWORD`, `EMAIL_HOST_PASSWORD`** (nombres; valores NO impresos).
   Se retiró del tracking después, pero **permanece recuperable en la historia**. → **BLOQUEO** (ver abajo).
4. **Credenciales en el árbol trackeado:** todos los `PASSWORD`/`SECRET_KEY`/`ODBC`/driver provienen de
   `os.getenv(...)` — **no hay secretos embebidos** en código trackeado (evidencia enmascarada). `SECRET_KEY`
   se toma de env y **falla si falta** (`settings.py:20-23`). ✅
5. **`CLAUDE.md` en la raíz:** **NO existe.** (No se pudo verificar "sin credenciales" porque el archivo
   no está presente.)

## Comandos ejecutados
- `python manage.py check` → **System check identified no issues (1 silenced).**
- `python -m unittest ...test_unit ...test_static ...test_integration` → **Ran 20 tests · OK.**

---

## Bloque de Cierre
```
ARCHIVOS NUEVOS: contabilidad/sqlserver_inventory/docs/OT-E2-00_conexiones.md
ARCHIVOS MODIFICADOS: (ninguno)
INVARIANTES VERIFICADOS:
  1  Sin INSERT/UPDATE/DELETE ni SP en Test2 ......... OK (no se ejecutó ninguna escritura)
  2  Sin spInvMovimientoAplicarInterno ............... OK (0 referencias en todo el repo)
  3  Sin crear/aplicar migraciones ................... OK
  4  Sin modificar código fuera de sqlserver_inventory OK (solo el .md entregable)
  5  Sin tocar settings/.env/config .................. OK
  6  Sin exponer secretos ............................ OK (todo enmascarado)
  7  Sin refactorizar/reformatear .................... OK
  8  Flags sin cambios (MOSTRAR_TARJETA/ESCRITURA=0) . OK (no se tocaron)
  9  Alias que tocan objetos de inventario ........... OK — solo inventario_test2
  10 padres_sqlserver alcanza Test2 .................. OBSERVACIÓN 🔴 (base compartida; NO toca tblInv*)
  11 Router allow_migrate=False para el alias ........ OK
  12 test_static no marca apps ajenas (conducta) ..... OK — pero NO cubre views_inventario_sql.py (diff propuesto)
PRUEBAS EJECUTADAS Y RESULTADO:
  manage.py check → OK (0 issues)
  unittest (test_unit, test_static, test_integration) → 20 tests OK
SUPUESTOS TOMADOS:
  - "Test2" es una base COMPARTIDA (esquema académico + inventario); el aislamiento del inventario
    se garantiza por objetos (nadie más lee tblInv*) y por el guard de rol, no por base/servidor.
  - Valores de host/usuario/password no se citan por política; se confirmó su origen (os.getenv).
BLOQUEOS / PENDIENTES PARA DIRECCIÓN:
  - 🔴 SECRETO EN HISTORIAL: system_proyect/.env fue commiteado en 98e6320 (2025-03-18) con
    DJANGO_SECRET_KEY, DB_PASSWORD y EMAIL_HOST_PASSWORD, entre otras. Aunque ya está ignorado y
    des-trackeado, sigue recuperable desde la historia. Recomendación (requiere autorización de
    Dirección/DBA, NO ejecutado aquí): ROTAR esas credenciales y planificar limpieza de historial
    (git filter-repo/BFG) fuera de esta OT. No se reescribió historial.
  - ⚠️ padres_sqlserver comparte la base Test2; si Dirección quiere el invariante LITERAL de "un solo
    alias a Test2", requeriría separar el inventario a otra base/instancia (decisión de DBA).
  - ⚠️ test_static no cubre views_inventario_sql.py: diff propuesto arriba, pendiente de aprobación.
  - CLAUDE.md no existe en la raíz (informativo).
```
