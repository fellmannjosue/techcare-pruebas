# AGENTS.md — Guía para agentes/IA en TechCare

Contexto operativo del proyecto para cualquier agente (Claude Code u otro). El
detalle funcional por módulo está en `README.md`; aquí va lo necesario para
**trabajar y desplegar** sin romper nada. **Este archivo NO contiene
credenciales** (contraseñas, tokens, claves). Nunca las agregues aquí ni a
ningún archivo versionado.

## Qué es
Sistema web Django para la **Asociación Nuevo Amanecer (ANA)**. Centraliza
tickets, asistencia (reloj), conducta, inventario, enfermería, agendas, notas
parciales, sponsors, mantenimiento, CFP y calculadoras.

- Producción: https://servicios.ana-hn.org:437 · Apache + mod_wsgi
- Stack: Django 6 · Python 3.13 (venv `venv`) · MySQL (principal) + SQL Server (reloj y datos de alumnos)
- UI: Tabler UI (beta19) + Tabler Icons webfont · Admin: Unfold

## Layout del repo
- Código: `system_proyect/` (una app Django por dominio: `accounts`, `conducta`, `reloj`, `core`, …).
- **Base canónica única `templates/base_app.html`** (desde v7): shell unificado (sidebar + topbar + footer + tema). Las 12 bases de módulo la extienden y solo aportan lo suyo por los bloques `vendor_head / head_js / breadcrumb / page_actions / vendor_js / module_js / extra_js / post_js`. `salidas_bano`, `mantenimiento` y las pantallas de login/reset son standalone (shell propio, pero con el tema `portal.css`). Sistema de diseño por tokens `--ps-*` en `portal_super/static/portal_super/css/portal.css` (cargado global). Componentes en `templates/ui/`.
- **OJO comentarios de plantilla:** `{# … #}` SIEMPRE en una sola línea y sin `{% %}`/`{{ }}` literales dentro — un comentario multilínea rompe el parser de Django (bloques duplicados / auto-include / fuga de texto).
- Estáticos servidos por Apache desde `system_proyect/staticfiles/` (generada por `collectstatic`).
- `media/` está en `.gitignore` — **datos de alumnos/config no se versionan** (ej. `media/conducta/routing_bl.json`).

## Ejecutar / verificar (siempre desde `system_proyect/`)
```bash
cd /home/admin2/techcare_project/system_proyect
../venv/bin/python manage.py check          # antes de dar por hecho cualquier cambio
../venv/bin/python manage.py makemigrations && ../venv/bin/python manage.py migrate
```
- **Test client:** pasar `SERVER_NAME='servicios.ana-hn.org'` (ALLOWED_HOSTS).
- Para módulos MySQL/SQL Server, correr contra la BD real (no hay fixtures).

## Desplegar (aplicar cambios en producción)
Cambios de **Python/settings/middleware** → reiniciar Apache. Cambios de
**templates** → normalmente basta el reinicio. Cambios de **JS/CSS** →
`collectstatic` + bump `?v=N` en el `<script>/<link>` + reiniciar.

```bash
../venv/bin/python manage.py collectstatic --noinput   # requiere sudo (archivos de www-data)
sudo systemctl restart apache2
# VERIFICAR que de verdad reinició (no basta `is-active`):
ps -eo pid,lstart,cmd | grep "apache2 -k start" | grep -v grep | head -1
```
⚠️ **Comprobar el reinicio por la hora de arranque del proceso.** Un
`systemctl restart` que falla (sudo sin clave, etc.) deja Apache corriendo con
el **código viejo** y `systemctl is-active` sigue diciendo `active`: se pierde
mucho tiempo depurando "cambios que no se aplican" que sí estaban bien. No
canalizar la salida del restart a `tail -0` / `/dev/null`.
La contraseña sudo del servidor **no** está aquí; el operador la conoce (o está
en la memoria privada del agente, nunca en el repo). Apache corre como
**`www-data`**: puede **leer** el repo pero **no** escribir archivos de admin2
ni ejecutar `git` en este repo. Scripts que deban escribir archivos de www-data
(ej. `media/conducta/routing_bl.json`) se corren con `sudo -u www-data`.

## Convenciones
- **Comentarios de autoría en templates:** `{# <--- hecho por claude code: ... #}` — **una sola línea**. Django no soporta `{# #}` multilínea: si no cierra en la misma línea, deja de ser comentario y **se imprime como texto en la página**. Para varias líneas usar `{% comment %}`.
- **Nada de JS ni CSS dentro del HTML.** Todo va a `<app>/static/<app>/js|css/`. Los valores de Django llegan por `data-*` en un div de config, o por islas JSON (`{{ x|json_script:"id" }}` / `<script type="application/json">`). Ojo al generar JSON desde plantillas: las comas finales de un `{% for %}` lo invalidan (usar `{% if not forloop.last %}`), los decimales salen con coma por la localización (usar `|unlocalize`) y `{{ lista|safe }}` imprime repr de Python con comillas simples (válido en JS, **inválido en JSON**). Validar con `node --check` y parseando la isla de la página renderizada.
- **Un identificador global por archivo JS.** Los `.js` no son módulos: se comparte el ámbito global. Toda página carga al menos dos (el de la base + el de la pantalla), así que dos archivos con `const CFG` provocan `SyntaxError: Identifier 'CFG' has already been declared` y **el segundo script no ejecuta nada**. Cada archivo usa su propio nombre (`CFG_MAESTRO`, `CFG_COORDINADOR`, con prefijo de app si el nombre de archivo se repite entre apps). Mismo cuidado con `CSRF`, `URL_*`, etc.: encerrarlos en un IIFE.
- **Al extraer JS de un template, mover TODA la lógica, no solo la config.** En la v6.0.2.0 el script de migración copió únicamente el bloque `data-*` y 12 pantallas quedaron sin código (ver v6.0.5.0). Contraste útil: comparar el nº de líneas del `.js` actual contra la mejor versión del archivo en el historial (`git log --format=%h` + `git show <c>:<ruta> | wc -l`) y revisar que cada plantilla cargue su `.js` **una sola vez**.
- **JSON en un atributo `data-*` va SIN `|safe`.** Con `|safe` la primera comilla doble del JSON cierra el atributo HTML y `JSON.parse` recibe `{` roto (bug real en Salidas al baño, v6.0.5.0.001). Sin `|safe` Django escapa las comillas y el navegador las restaura al leer `.dataset`. Para blobs grandes, preferir isla `{{ x|json_script:"id" }}`.
- **La config que un JS escribe (`window._X`) debe ser el MISMO global que lee el JS consumidor.** En Salidas al baño la config ponía `window._PAGE` pero `salidas_bano.js` leía `window._SB` → nada cargaba.
- **Nunca `{% %}` ni `{{ }}` dentro de un `.js`**: Django no procesa los `.js`, quedan como texto literal. Toda variable de Django entra por `data-*`/isla en el template.
- **Diagnóstico repetible del sistema** (usado en v6.0.5.0.001): renderizar las ~72 páginas como superuser y validar por página las islas JSON, los `data-*` JSON (tras `html.unescape`), `<script>` que dan 404 y los duplicados; más `node --check` a todos los `.js`, `{% extends %}` como primer tag, `onclick=`→función definida, y `{% static %}`→archivo existente.
- Variables Django→JS: preferir `data-*` en un `<div hidden>` o `|json_script`; evitar `<script>` con literales Django salvo casos heredados.
- Badges Tabler: `bg-blue-lt text-blue`, `bg-orange-lt text-orange`, `bg-green-lt text-green`, etc.
- Roles = **grupos de Django por nombre** (revisados en `core/context_processors.py`, `accounts/panel_roles.py`). Casi ninguno usa permisos de Django (excepción: `inventario`). Los permisos del Reloj vienen del modelo `reloj.RelojPermiso`.

## Versionado y novedades
- Versión y changelog en `core/changelog.json`; lo lee `core/version.py`, lo expone `version_context`, y `templates/_footer.html` pinta el pie (+ `_version_modal.html` para el modal).
- **Footer**: uno solo para todo el sistema (`templates/_footer.html`), sticky por Flexbox (`body` columna + `min-height:100vh`, `.page-body{flex:1 0 auto}`, `footer.tc-footer{margin-top:auto}`); nunca `position:fixed`. Tabler impone `.footer{padding:2rem 0}`, por eso se usa el selector `footer.tc-footer`. Al tocar `static/css/responsive_global.css` hay que **subir el `?v=N`** del `<link>` en las plantillas o el navegador sirve el CSS viejo.
- `manage.py gen_changelog` genera entradas desde `git log` y sube el build; lo dispara `.git/hooks/post-commit`. Marcador de rango en `.git/changelog_base` (local, sobrevive a `--amend`).
- `PerfilUsuario.version_vista` recuerda qué versión vio cada usuario.

## Ruteo de reportes Bilingüe (área activa reciente)
- Pantalla única `conducta/routing_bl.html` (`routing_bl_config`); config en `media/conducta/routing_bl.json` (no BD, no versionado).
- Decisión de coordinador: `_coord_bl(materia, docente, grado)` → override único fuerza → materia manda (C3/C4) → grupo/grado (C1 grados 1-3, C2 grados 4-9) → override múltiple restringe por grado. Un docente puede reportar a **varios** coordinadores (override = unión de sus cargas).
- Nombres/correos de coordinadores: C1 cvarela · C2 druiz · C3 ialcerro · C4 jmartinez.
- Permisos por coordinador (`coord_permisos`): `none` / `lectura` / `edit`; los endpoints de guardar usan `_puede_editar_ruteo`.

## CFP · Contabilidad (área activa reciente)
- **Distribución fija del curso**: 20% Personal (`dist_instr`) · 60% Materia Prima y Mantenimiento (`dist_seguro`) · 20% Administración (`dist_admin`). `EGRESO_GRUPOS` en `cfp/models.py` es la **fuente única**: el formulario y el PDF se generan de ahí, no hay listas duplicadas.
- **El 20% de Administración NO se reparte entero.** Primero se capturan a mano seguro/teléfono/otros (`ADMIN_CAPTURADOS`) y el resto (`admin_a_repartir`) se divide en **partes iguales** entre las personas de la **planilla** (`GastoAdministrativo`); el residuo de centavos va al último. Los 6 cargos (`CARGOS_ADMIN`) son de **solo lectura** en el informe: los escribe `sincronizar_cargos()`.
- El **monto por persona no se guarda**, se calcula en `reparto_planilla()`. Guardarlo dejaría cifras viejas cuando cambie el seguro.
- **PDFs con WeasyPrint**: el HTML se pasa como string, así que **no hay `base_url`** y un `<link>` a `/static/` se ignora en silencio (el PDF sale sin estilos y en A4). El CSS y el logo van por ruta de disco con `finders.find()` → `stylesheets=[CSS(filename=...)]` y `src="file://…"`. El **informe contable es el único PDF en papel legal**; la planilla va en carta.
- **Autoguardado** (`cfp/js/autoguardado.js`): mismo POST con `?ajax=1`, la vista devuelve JSON en vez de redirigir. Los selects "Agregar nueva…" solo catalogan cuando el JS manda `catalogar=1` (al salir del campo), si no el catálogo se llena de textos a medio escribir.
- **Datos compartidos por TODOS los cursos** en `CfpDatosGenerales` (registro único): localidad, dirección, instructor, horario, lugar, regional, centro-programa. Ojo al probar: un POST con esos campos vacíos los borra **para todos los cursos**.
- `no_ejecucion` **no es la llave** (la llave es el pk). Se genera solo con `generar_no_ejecucion()`: `CFP-ANA-001-26`, correlativo anual que salta huecos e ignora los códigos antiguos con otro formato.

## Ingresos de Notas (escribe en el sistema académico)
- App `ingresos_notas` (`/ingresos-notas/`). Es lo ÚNICO en TechCare que **escribe** en SQL Server; el resto de integraciones son de solo lectura.
- Cadena: `tblPrsDtosGen → tblPrsTipo → tblEdcArea → tblEdcEjecCrso → tblEdcMaterias<rama> → tblEdcEval<rama>`. Dos ramas vivas y simétricas: **BL** (PrimariaBL, ColegioBL) y **Acad** (Colegio, Bachillerato). La rama `Col1` está MUERTA (0 registros del año) y no se toca.
- Las filas de evaluación **ya existen** (se crean al matricular): ingresar una nota es un `UPDATE` de una columna. El legacy audita con `trg_Audit_tblEdcEval*` pero **solo en UPDATE**, por eso además se guarda todo en `EscrituraNota` (MySQL). **Nunca `DELETE`.**
- `spEdcNotasInsert*` **NO escribe nada** pese al nombre: son los generadores del boletín (79 mil caracteres de SELECT). No sirven para guardar.
- **Cuadro1..20 son evaluaciones normales y se usan** (hay clases con 19 y otras con 2) → la cantidad de columnas se detecta por clase. Las **Especial 1/2/3 son `Cuadro18/19/20`** (verificado contra Access con la misma fila); `ExamenFinal2/3/4` están vacíos y NO se usan. En las áreas con Especial los cuadros numerados llegan hasta **C17**, si no salen duplicados. `Nivelacion` está oculta a pedido del usuario.
- Permisos por área con grupos `ingreso notas bilingue` / `ingreso notas colegio` (+ `ingreso notas` como paraguas). **Las APIs validan el área**, no solo el desplegable.
- **Tab Asistencias** (`tblEdcAusencias<rama>`): grano materia + fecha (una fila por CLASE, no por día). Tipo desde `tblEdcDescripAusencias` (4) y razón desde `tblEdcDescripAusenciasRazon` (162 activas); **la razón va por ID**, no por el texto libre `Razon`. Solo se registra a quien faltó; **vaciar el tipo BORRA la fila** (único borrado del legacy en todo TechCare), con confirmación y registrado en la bitácora como `delete`.
- **Tab Tareas** (Record de Hábitos, `tblEdcRecordHabitos<rama>`): grano materia + hábito + fecha, Puntos 0-10 y Comentario. **El legacy no guarda identificador de tarea**: un alumno tiene varias el mismo día y solo las distingue el orden de inserción (la PK). Funciona porque dentro de una clase y un día todos tienen la misma cantidad de filas. Por eso se llena **una tarea a la vez** y el guardado rechaza insertar la tarea N si al alumno le faltan las anteriores. `Puntos` es NOT NULL → la nota va antes que el comentario.

## Reloj · Reporte de Permisos
- `ReportePermisoMensual` es **una fila por (emp_code, mes)** — por eso un campo ahí es "global por empleado" en ese mes. Ojo: `horario_comentario` es solo sobre la jornada; **`comentario`** es la nota general (endpoint `permiso_reporte_set_comentario`, permiso `reporte:editar`).
- Los tabs **No marcó entrada / No marcó salida** comparan la PRIMERA y la ÚLTIMA marca del día contra el horario asignado (`TOLERANCIA_MARCA_MIN`). **No sirve contar marcas**: un día normal son 2 y con receso 4, y se puede marcar dos veces por la mañana sin marcar la salida.

## Notificaciones (toast + campana)
- `core.utils_notifications.crear_notificacion(usuario, mensaje, modulo, tipo, extra, enviar_correo)` crea la fila; `accounts/js/notifications.js` la muestra sondeando.
- **TRAMPA**: `mostrarToastNotif()` hace `getElementById('tc-notif-global')` y si no existe **sale sin pintar nada** — sonaba el aviso y no se veía. El contenedor vive en `templates/base_app.html` (lo heredan las 12 bases) y en las standalone; **no duplicarlo** en las bases que ya extienden base_app.
- Agregar el módulo a `_MODULO_LABEL` o el toast muestra el nombre técnico ("Notas_parcial").

## Modo mantenimiento (dos niveles)
- **General**: `MAINTENANCE_MODE` + filtro por área (`all`/`staff`/`bilingue`/`colegio`) o lista de correos.
- **Por formulario**: `MAINTENANCE_MODULES` (constance, JSON) pone cada módulo en `normal` / `lectura` / `bloqueado`. `lectura` corta solo las escrituras. Funciona aunque el general esté apagado y respeta el mismo filtro de audiencia. Registro de módulos y rutas en `core/maintenance_modules.py`; el filtro compartido es `core.middleware._audiencia_afectada`.

## Notas mitad de parcial (área activa reciente)
- Lee de la base académica **REAL `AdmonANASQL`** (`Test2` es la copia). La base se elige **por área** con `_db(area)`, según `NOTAS_PARCIAL_DB` + `NOTAS_PARCIAL_AREAS_REAL` del `.env`; así se migra un área a la vez sin dejar en blanco a las que aún no tienen permisos. La **llave del caché incluye la base**, si no se sirve lo cacheado de la otra durante 8 h.
- Requiere en `AdmonANASQL`: `SELECT` sobre las 4 `tblEdcNotasInsert*` y `EXECUTE` sobre los 4 `spEdcNotasInsert*`. **Nada más**: los SP no escriben y, al ser todo de `dbo` y sin SQL dinámico, la cadena de propiedad cubre las 20 tablas que leen por dentro.
- **El SP va PRIMERO, la staging es solo respaldo** (3-ago-2026). `tblEdcNotasInsert*` es una FOTO que regenera Access: estaba congelada en el Parcial 2 y las notas nuevas no aparecían. En `AdmonANASQL` solo hay LECTURA, así que no se puede regenerar; el SP en cambio es un SELECT puro sobre las tablas reales. Caché de **30 min** (antes 8 h): es lo único que separa la pantalla de los datos vivos.
- Datos desde **SQL Server** vía SP (4-10 s) + caché Django (`_llamar_sp`). El SP de **bachillerato exige `@Curso`**: si no viene, `_llamar_sp` pide los dos cursos y los combina. En bachillerato el "grado" **es** el año (1ero→curso 1, 2do→curso 2) y se muestra como "1er Año / 2do Año".
- Coordinador: agrupar siempre por **grado + sección** (`alumno['grado_seccion']`). Agrupar solo por grado hacía que el banner de maestros tomara la sección del primer alumno y ocultaba a los de las demás.
- "Mis Reportes" (`maestro_notas`) muestra las asignaciones **del usuario**; un coordinador puede ver todas con `?todos=1`.
- El "Revisado" del coordinador se guarda en `RevisionFinalizada` (mismo modelo que el "Finalizado" del maestro, con el coordinador como dueño).
- PDF (`_dibujar_pagina`): un bloque por maestro, dos columnas automáticas y letra 9→6 pt según quepa. `simpleSplit` de reportlab **solo corta en espacios**, por eso `_envolver` parte también las palabras largas. Límite práctico: ~13 maestros por alumno.
- **Emojis en el PDF**: Helvetica (Type1/WinAnsi) no tiene glifos de emoji y los pintaba como cuadro negro (■). `notas_parcial/pdf_emoji.py` los dibuja como imagen a color sacada de `NotoColorEmoji.ttf` con Pillow, y expone `ancho()`/`dibujar()` (versiones de `stringWidth`/`drawString` que conocen el ancho del emoji) + `unidades()` para no partir banderas ni secuencias ZWJ al ajustar línea. **Dependencia del servidor: `apt install fonts-noto-color-emoji`**; si falta, el emoji ocupa 0 y no se dibuja (nunca vuelve el ■). El font es CBDT: FreeType solo acepta su rejilla de **109 px**, cualquier otro tamaño lanza `invalid pixel size`.
- Las notas se pintan **sin decimales**: pantalla con `floatformat:"0"`, PDF con `_nota_int` (`Decimal` + `ROUND_HALF_UP`, para que coincidan). Si cambias uno, cambia el otro. El rojo de nota baja (`nota_baja`, < 70) evalúa el valor **real**, no el redondeado.

## Datos legacy (sponsors)
Las tablas `tbl_gen_*` / `tbl_spn_*` son de un sistema anterior y van con `managed = False`. **Revisa el esquema real antes de tocar los modelos**: hay una columna `decription` (typo en la BD), otra llamada `check` (palabra reservada), y `Sponsor.city` es NOT NULL.

## Salidas al Baño (dos ámbitos)
- Un solo módulo, **dos pantallas independientes**: Colegio (`/salidas-bano/`, áreas `colegio`+`bachillerato`) y CFP (`/salidas-bano/cfp/`, área `cfp`). La misma vista `index(request, ambito=...)`; la config está en `AMBITOS` (`salidas_bano/views.py`).
- En CFP el eje es el **curso** (no el grado) y `SalidaBano.ingr_egr_id` guarda el **PersonaID**, no el IngrEgrID: son espacios de ID distintos, por eso **todo filtro debe incluir el área** (pasó en el historial).
- Grupos separados por ámbito; `'ambos'` significa Colegio+Bachillerato y **nunca** incluye CFP. El área que manda el navegador se valida contra el ámbito (antes no se validaba).

## Gotchas
- **Migraciones gitignoradas**: `system_proyect/.gitignore` excluye `*/migrations/*.py`. Viven solo en el servidor; un clon limpio del repo no las trae.
- **Reloj · Control Compensatorio**: todos los tabs de `compensatorio_calculo_list` se rigen por el mismo permiso `calculo_comp` (`can_edit_extra` = `editar`). Los inputs del template deben ir con `{% if can_edit_extra %}`, no con `is_superuser`: el endpoint `compensatorio_mensual_cell` ya valida `calculo_comp:editar`, así que usar `is_superuser` en la plantilla dejaba la UI más restrictiva que el backend.
- **Nunca** borrar/pisar `media/conducta/routing_bl.json` en pruebas: contiene la config real (alumnos, grupos, catálogo). Escribir solo vía la app o `sudo -u www-data`.
- **El vhost de Django DEBE llevar `WSGIApplicationGroup %{GLOBAL}`.** Sin ella mod_wsgi crea un sub-intérprete por nombre de host, y `lxml` (vía `pptx`, en conducta) falla con *"Interpreter change detected"* → 500 intermitentes tras cada reload de logrotate, disparados por cualquier robot que escanee con otro `Host`.
- **Páginas de error: son dos mundos.** `templates/404.html` y `500.html` las renderiza Django (**el 500 SIN contexto**: nada de `{% url %}` ni `user`). `static/errores/*.html` las sirve **Apache** por `ErrorDocument` cuando la app ni arranca, así que van sueltas con el estilo incrustado.
- **PDFs con WeasyPrint: el CSS SIEMPRE del disco, nunca por HTTP.** Con solo `base_url` la hoja se pide a `https://servicios…:437/static/…` y esa petición **no llega desde el propio servidor** (el nombre resuelve a la IP pública); falla en silencio y el PDF sale en A4 vertical con letra enorme aunque el CSS diga `landscape`. Patrón correcto: extraer los `<link>` del HTML y cargarlos con `finders.find()` → `stylesheets=[CSS(filename=…)]` (ver `reloj/views.py::_reporte_pdf`). Para verificarlo sin abrir el PDF, mirar su `/MediaBox`: 595x842 = A4 vertical = el CSS no se aplicó.
- **`.env`: permisos 640 con grupo `www-data`, nunca 600.** Apache corre como `www-data` y el archivo es de `admin2`; con 600 la app no arranca (se queda sin `DJANGO_SECRET_KEY`). Comprobar con `sudo -u www-data test -r ...` **antes** de reiniciar.
- **SQL Server oculta los objetos sobre los que no tienes permiso.** Un listado vacío de `sys.tables` **no** prueba que la tabla no exista: hay que consultarla y leer el error (`Invalid object name` = no existe; `The SELECT permission was denied` = existe y falta permiso).
- `git` en este repo se hace **directo a `main`** (flujo del proyecto). Rama principal = `main`.
- Al terminar código: `manage.py check` verde y, si corresponde, reiniciar Apache.
