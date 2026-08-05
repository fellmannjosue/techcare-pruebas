# TechCare – Sistema de Gestión Institucional

Sistema web desarrollado en Django para la **Asociación Nuevo Amanecer (ANA)**. Centraliza la gestión de tickets, asistencia, conducta estudiantil, inventario, citas, enfermería, agendas docentes, notas parciales, finanzas y calculadoras internas.

- **Versión del sistema:** 7.4.0.003 (ver *Novedades* en el pie de página de la app)
- **URL de producción:** https://servicios.ana-hn.org:437
- **Servidor:** Apache + mod_wsgi
- **Stack:** Django 6.0.5 · Python 3.13.3 · MySQL + SQL Server
- **UI:** Tabler UI v1.0.0-beta19 + Tabler Icons Webfont v3.11.0
- **Admin:** Unfold Admin Theme

---

## Novedades recientes

> El detalle por versión se genera automáticamente en `core/changelog.json` (comando `manage.py gen_changelog`, disparado por el hook `post-commit`) y se muestra a cada usuario en una ventana la primera vez que entra tras un cambio de versión. Ver *"Versionado y novedades"* más abajo.

### v7.4.0.003 — Auditoría de seguridad, panel de Seguridad y ajustes

> Release **menor** (31 archivos): la ventana de novedades solo la ve el superusuario.

**Seguridad (tres auditorías de caja negra + correcciones verificadas):**
- **SQL Injection** en Notas de Parcial (parámetro `curso` sin sanear) → corregido con `int()`.
- **Conducta cross-área**: un maestro/staff veía, creaba, editaba, borraba y descargaba reportes de menores de OTRA área → ahora se valida el área y el propietario en todas las vistas (crear, editar, eliminar, PDF, dashboard de coordinador). `is_staff` deja de contar como coordinador.
- **Inventario** y **Cámaras** abiertos a cualquier maestro por URL → candado por grupo.
- **Crear usuarios era público** y daba `is_staff` a coordinadores → ahora solo administradores, con interruptor ON/OFF y **lista blanca de correos institucionales** (validada en el servidor, no solo en el JS).
- Cookies `Secure` + `SameSite`, HSTS, `/admin/` restringido a la red interna, `int(curso)` blindado.

**Funciones nuevas:**
- **Panel de Seguridad** (Configuración → Seguridad, superusuario): interruptores de registro y 2FA, y gestión de la lista blanca de correos con **importar/exportar CSV · JSON · XLSX**.
- **2FA por correo periódico** (código de 6 dígitos): superusuario cada 15 días, staff 30, usuario 60. **Apagado por defecto** tras interruptor; se activa cuando el equipo lo decida.

**Otros ajustes:**
- **PDF de convocatoria a tutorías** salía sin estilos (WeasyPrint no cargaba el CSS) → corregido cargándolo del disco; aplica a las 3 vistas de PDF de tutorías.
- **Enfermería**: el correo del padre se autollena al elegir al alumno y la ficha se envía en PDF **al Guardar** (se quitó el botón de envío aparte).
- **Salidas al Baño (Colegio)**: un maestro ve **solo sus clases**; el coordinador ve todas. **CFP es caso aparte**: las instructoras siguen viendo todas.
- **CFP**: la etiqueta del taller pasa a **"Panadería / Repostería"**.

### v7.4.0.002 — Asistencias, sincronización real de notas y filtros en los reportes

> Release **menor** (19 archivos): la ventana de novedades solo la ve el superusuario.

- **Ingreso de Notas: nuevo tab "Asistencias".** Área → Grado → Clase → Fecha, con los 4 tipos del catálogo (Llegó tarde · No se presentó · Trajo Excusa · Pidió permiso salida temprana), las 162 razones activas y un campo libre. Solo se registra a quien faltó: el tipo vacío significa "asistió". Vaciarlo borra la fila —única forma de deshacer una falta puesta por error— con confirmación, porque estas filas alimentan los recargos por no asistencia; queda en la bitácora con acción `delete`.
- **Notas Mitad de Parcial ahora lee las notas en vivo.** Antes consultaba `tblEdcNotasInsert*`, una foto que regenera Access y que estaba congelada en el Parcial 2: las notas del Parcial 3 no aparecían. Como en `AdmonANASQL` solo hay permiso de lectura, no se puede regenerar esa tabla, así que el procedimiento (un `SELECT` puro) pasó a ser la fuente principal y la tabla quedó de respaldo. El caché bajó de 8 horas a 30 minutos.
- **"Revisado" pasó de ~27 minutos a instantáneo.** Guardaba las 5,448 cajas de comentario una por una esperando cada respuesta. Ahora solo guarda las que cambiaron y en paralelo.
- **Los comentarios ya no se bloquean al marcar Revisado**, que es justo cuando el coordinador encuentra qué corregir. Además se autoguardan al salir del campo, en las pantallas de coordinador y de maestro.
- **Carrusel de notas: se puede escribir el número** del alumno para saltar directo, en lugar de avanzar de uno en uno.
- **El envío del PDF va con copia a los coordinadores** del área correspondiente.
- **Reportes del reloj: filtro de mes o año en cada pestaña** (compensatorio, permiso mensual, adeudados, compensatorio general, instructores, receso, bono y vacaciones). Vacaciones tenía el año fijo en el código y ahora acepta `?anio=`.
- **Páginas de error propias** para 404, 500 y para cuando la aplicación no arranca (esta última la sirve Apache, sin depender de Django).

> **Cambios fuera del repositorio** (servidor): `WSGIApplicationGroup %{GLOBAL}` en el vhost —sin él, un robot con otro `Host` creaba un segundo sub-intérprete y `lxml` reventaba con 500 intermitentes—, `ErrorDocument` apuntando a las páginas nuevas, y `DJANGO_DEBUG=false`.

### v7.4.0.001 — Base académica real, Tareas y PDFs del reloj

> Release **menor** (17 archivos): la ventana de novedades solo la ve el superusuario. La versión sí sube para todos en el pie de página.

- **Notas Mitad de Parcial ahora lee la base académica REAL (`AdmonANASQL`)**, no la copia `Test2`. La migración es por área (`NOTAS_PARCIAL_DB` + `NOTAS_PARCIAL_AREAS_REAL` en el `.env`), así que se puede mover un área a la vez según los permisos que tenga `admin2` en SQL Server. Las cuatro áreas ya están migradas. La llave del caché incluye la base, para no servir datos de la otra.
- **Ingreso de Notas: nuevo tab "Tareas"** (Record de Hábitos). Área → Grado → Clase → Fecha, con puntos 0-10 y comentario, autoguardado por celda. Una tarea a la vez, porque el legacy no guarda identificador de tarea y solo el orden de inserción las distingue; incluye validación para no desalinear las tareas de un alumno al que le falten las anteriores.
- **Corrección importante en Ingreso de Notas:** las *Especial 1/2/3* son **`Cuadro18/19/20`**, no `ExamenFinal2/3/4`. Verificado contra el formulario de Access con la misma fila. En las áreas con Especial los cuadros numerados llegan hasta C17.
- **Reloj — regla de rebaja por tardanza:** pasado el último tramo ya no se queda plano en 1 h; se rebaja **1 hora por cada 60 minutos completos** (334 min → 5 h). Antes cualquier acumulado rebajaba lo mismo que 31 minutos.
- **PDFs del reloj arreglados y rediseñados.** El CSS nunca se aplicaba (WeasyPrint intentaba descargarlo por HTTP desde el propio servidor y fallaba en silencio), por eso salían en A4 vertical con letra enorme. Ahora se carga del disco: **los 6 PDFs del módulo** salen horizontales. El *Reporte Mensual de Permisos* y el *Tiempo compensatorio general* además se rediseñaron con encabezado de color, filas alternas, columnas resaltadas y pie con numeración de páginas.
- **Seguridad:** las contraseñas de las tres bases salieron de `settings.py` y ahora vienen solo del `.env` (que además quedó en `640`, legible únicamente por Apache). Se corrigió el desajuste de nombres (`MSSQL_DB_*` → `MSSQL_TEST2_DB_*`) que hacía que el `.env` nunca se leyera para SQL Server.
- **Notificaciones:** el toast de "reporte de notas terminado" ya no le llega a administración, contabilidad, enfermería ni dirección CFP. La causa era `is_staff`, que también les daba acceso al panel de coordinación de notas.
- **CFP:** la columna *No. Ejecución* pasó a llamarse **N° de Expediente**.

### v7.4.0 — Ingresos de Notas, control de marcas y avisos en tiempo real

> Release **general**: reúne todo lo publicado desde la v7.0.0.0, que hasta ahora solo había visto el superusuario en las versiones menores 7.0.0.0.001, 7.0.1.002 y 7.0.2.003. El detalle de cada una está más abajo.

**Lo nuevo de esta versión**
- **Reporte de Permisos** — columna **Comentario**: una nota general por empleado y mes, con aviso visual de quién tiene comentario. No va atada a un tipo de permiso.

**Lo que trae acumulado desde la v7.0.0.0**
- **Ingresos de Notas** (programa nuevo): ingresa notas directamente en el sistema académico, separado por área, con las columnas que use cada clase y permisos por encargada.
- **Salidas al Baño para CFP**, separado del Colegio y con sus propios permisos.
- **Salidas al Baño**: alerta con sonido cuando falta registrar el regreso de un alumno.
- **Reloj**: quién no marcó entrada y quién no marcó salida, con filtro de fechas; y una regla más del Bono por Asistencia.
- **CFP**: Planilla de Gastos Administrativos con su PDF para firma, e Informe Contable rediseñado con el formato oficial del INFOP.
- **Notas de Parcial**: aviso al coordinador cuando un maestro termina, emojis a color en el PDF y varias correcciones de texto.
- Arreglo de los avisos que sonaban pero no se veían en pantalla.

### v7.0.2.003 — Ingresos de Notas, alerta de regreso en Salidas al Baño y control de marcas en Reloj

> Release **menor**: las novedades solo se muestran al superusuario.

**📝 Ingresos de Notas (programa nuevo)**
- Programa nuevo en `/ingresos-notas/` para **ingresar notas directamente en el sistema académico** (SQL Server). Es lo primero en TechCare que **escribe** en esa base; hasta ahora todo era de solo lectura.
- Selectores en cascada **Área → Grado/Grupo → Clase → Parcial** y rejilla estilo CFP con **autoguardado por celda**: la columna del alumno queda fija al desplazar y `Enter` baja a la fila siguiente.
- **Las columnas dependen de la clase**: hay materias que usan 2 cuadros y otras que llegan a 19, así que se detecta el último con nota y se agrega uno en blanco. Las **Especial 1/2/3** (`ExamenFinal2/3/4`) solo salen de 7mo en adelante.
- Alumnos ordenados **primero las niñas y luego los varones**, alfabético por nombre. En Colegio y Bachillerato los grados se muestran como **7mo–11vo** aunque la base guarde 1ero/2do/3ero.
- **Seguridad al escribir**: lista blanca de columnas por área (nada fuera de ella se toca), rango 0–100, nunca `DELETE`, y **bitácora propia en MySQL** (`EscrituraNota`) con quién, cuándo y el valor anterior — el trigger del legacy solo audita los `UPDATE`.
- **Permisos por área**: grupos `ingreso notas bilingue` y `ingreso notas colegio`; cada encargada solo ve y escribe lo suyo, validado también en las APIs (no basta con ocultar el desplegable).

**🚻 Salidas al Baño — alerta de regreso sin registrar**
- Si un alumno lleva **más de 5 minutos** fuera sin que se registre su regreso, se abre un modal con **sonido en bucle** para registrarlo ahí mismo. El sonido se corta al tocar el modal y el aviso solo desaparece cuando el regreso queda registrado.
- La consulta va **al servidor cada 3 s**, así que el aviso también se va si el regreso lo registró otro maestro desde otra pantalla. Al registrar desde el modal, la fila de la tabla se repinta sin recargar.

**🕐 Reloj — quién no marcó entrada o salida**
- Dos tabs nuevos en el Reporte de Permisos con **filtro Desde/Hasta**. Como los relojes no distinguen entrada de salida (el 96% de las marcas llegan con el mismo estado), se compara la **primera y la última marca del día contra el horario asignado** del empleado.
- **Regla 5 del Bono por Asistencia**: cualquier día con marca faltante hace perder el bono, sin tolerancia (a diferencia de la tardanza, que perdona 2).

**📄 Notas de Parcial**
- Al marcar **"Finalizado"**, ahora le llega un **toast al coordinador** de su área avisando que el maestro terminó. Antes se armaba el aviso y no se enviaba a ningún lado.
- Textos del PDF corregidos: **"Área y Grado"** con tilde y el grado de Colegio como **7mo/8vo/9no** con la sección en mayúscula; **"Reporte de Notas a Mitad de Parcial"**; *"La Venta, Distrito Central."*; y el texto para los padres actualizado.

**🐞 Arreglos**
- **Los toast de notificación no se veían** fuera del menú y de tickets: `notifications.js` busca un contenedor por id y, si no lo encuentra, no pinta nada. Sonaba el aviso pero no aparecía. El contenedor pasó a `base_app.html` (lo heredan las 12 bases de módulo) y a las pantallas standalone.
- En el módulo CFP, "Disketes" pasó a **"Imprevistos"**.

### v7.0.1.002 — Salidas al Baño CFP, Planilla de Gastos Administrativos e Informe Contable rediseñado

> Release **menor**: las novedades solo se muestran al superusuario.

**🚻 Salidas al Baño para CFP**
- El módulo `salidas_bano` ahora atiende **dos ámbitos independientes**: **Colegio** (`/salidas-bano/`, con sus áreas Colegio y Bachillerato) y **CFP** (`/salidas-bano/cfp/`). Comparten semáforo, autoguardado, notificaciones e historial, pero **no comparten alumnos ni permisos**.
- Los participantes de CFP salen de la **misma base que Notas CFP** (`padres_sqlserver`, por `tblEdcIngrPrevisto`+`tblEdcTipoCrso`): el eje es el **curso** en vez del grado y la llave del alumno es `PersonaID` en vez de `IngrEgrID`.
- **Grupos de acceso propios**: `control baños cfp` y `control baño coord cfp` (comando `crear_grupos_sb`, reescrito porque creaba grupos que el módulo ya no consultaba).
- **Seguridad**: el endpoint de guardar salida **no validaba el área** que mandaba el navegador; ahora comprueba el ámbito. El historial tampoco filtraba por área, y `PersonaID`/`IngrEgrID` son espacios de ID distintos que podían colisionar.
- Destinatario de correo propio para la **alerta negra de CFP**.

**🧾 CFP · Planilla de Gastos Administrativos (nueva)**
- Pantalla y **PDF con columna de firma** (papel carta) para registrar quién cobra el 20% de Administración de cada curso: **nombre, DNI, cargo, curso, monto y firma**.
- Respeta el orden real del cálculo: primero se capturan **seguro, teléfono y otros** en el informe, y **solo el resto se reparte en partes iguales**; el residuo de centavos se asigna al último, igual que ya hacía el 20% de personal.
- El monto **no se guarda**, se calcula siempre: si cambia el seguro, todo se reajusta y no quedan copias desactualizadas.
- Los **6 cargos del informe** pasaron a ser de solo lectura, alimentados por la planilla (antes se podían escribir en dos sitios y contradecirse).

**📄 CFP · Informe Contable rediseñado (papel legal)**
- Réplica del formulario oficial del INFOP: encabezado institucional con logo, campos con línea de llenado, **casillas de un dígito** para Regional y Centro-Programa-Proyecto, cuadro de cuentas a 3 columnas y formato contable (el cero se imprime como `-`).
- **Bug de fondo**: la vista pasaba el HTML a WeasyPrint como string sin `base_url`, así que el `<link>` a `/static/` nunca se resolvía — **el PDF salía sin estilos y en A4**. Ahora la hoja y el logo se pasan por ruta de disco. Es el **único PDF del sistema en papel legal**.
- Egresos reagrupados a la distribución real del curso: **20% Personal · 60% Materia Prima y Mantenimiento · 20% Administración**; se eliminó *Amortización y Depreciación* y cada grupo muestra su porcentaje y el monto al que debe cuadrar.

**⚙️ CFP · Otros**
- **Autoguardado** en Informe Contable y Planilla (sin botón Guardar), con indicador de estado. Los selects *"Agregar nueva…"* solo catalogan al salir del campo, para no llenar el catálogo de textos a medio escribir.
- **No. de Ejecución automático**: `CFP-ANA-001-26`, correlativo anual que salta huecos y respeta los códigos antiguos escritos a mano.
- **Regional** y **Centro-Programa-Proyecto** pasaron a los datos generales compartidos: iguales para todos los cursos y de solo lectura en el informe.
- Los campos de gasto aceptan y muestran **separador de miles**; el parser del backend reventaba con `"5,460.00"` y guardaba 0.

**🐞 Arreglos varios**
- **Emojis a color en el PDF de notas de mitad de parcial**: Helvetica no tiene glifos de emoji y los pintaba como cuadro negro (■) en los 246 comentarios que ya los usaban. Ahora se dibujan como imagen desde `NotoColorEmoji.ttf`, sin descuadrar el ajuste de línea. **Requiere `fonts-noto-color-emoji` en el servidor.**
- **Notas sin decimales** en pantalla y PDF, con el mismo redondeo en ambos (`ROUND_HALF_UP`).
- **Reloj**: la columna "Tomado" del Control Compensatorio ahora se edita con el permiso `calculo_comp:editar` (la UI estaba más restrictiva que el backend).
- Paleta de colores personalizada en los grupos del panel del superusuario.

### v7.0.0.0.001 — Notas enteras, "Tomado" por permiso y colores del panel (release menor)

> Release **menor**: las novedades solo se muestran al superusuario.

- **Notas de Mitad de Parcial** — las notas se muestran **sin decimales** (`80.00` → `80`) tanto en las pantallas de **maestro** y **coordinador** como en el **PDF**. El redondeo del PDF (`_nota_int`) usa `ROUND_HALF_UP`, igual que `floatformat:"0"` en pantalla, para que ambos coincidan (`78.5` → `79`). El coloreado de nota baja (< 70) sigue evaluando el valor real, no el redondeado.
- **Reloj · Control Compensatorio** — la columna **"Tomado" (To)** de la matriz mensual ahora es editable por cualquier usuario con el permiso *Control Compensatorio → Editar* (antes solo el superusuario la veía editable, aunque el endpoint ya aceptaba ese mismo permiso).
- **Panel del superusuario** — paleta de colores de los 11 grupos personalizada (Soporte, Académico, Salidas, Reloj, Sponsors, Calculadoras, CFP, Monitoreo, Permisos, Configuración y Modo Mantenimiento).

### v7.0.0.0 — Nueva interfaz unificada, sidebar rediseñado y mejoras funcionales

> Release **mayor**: rediseño completo del frontend con una sola identidad visual, más varios ajustes funcionales pedidos por el usuario.

**🎨 Migración completa del frontend a un sistema de diseño único**
- **Base canónica `templates/base_app.html`** — un solo *shell* (sidebar + topbar + breadcrumb + footer + tema claro/oscuro) para todo el sistema. Las **12 bases de módulo** (inventario, reloj, agendas, conducta, enfermería, calculadoras, cámaras, notas de parcial, sponsors, tickets técnico/usuario y configuración) ahora la extienden, unificando el shell de las ~133 pantallas sin tocar vistas, rutas, permisos ni APIs.
- **Sistema de diseño por tokens** (`portal.css`) + **biblioteca de componentes** (`templates/ui/`: tile, stat, empty_state, field, save_bar, card, messages) + utilidades (`core/forms.py` mixin de widgets, `tc_datatable.js` init único de DataTables).
- **~48 archivos CSS de contenido** alineados a los tokens `--ps-*` (antes usaban colores claros fijos): ahora el interior de cada pantalla adopta la identidad nueva y **soporta modo oscuro**. El color de marca pasó de azul a índigo.
- **Sidebar estilo tarjeta** — fondo claro con texto oscuro (y superficie oscura con **texto blanco en modo oscuro**), ítem activo en píldora índigo, grupos como ítems normales (ya no MAYÚSCULAS diminutas) con submenús indentados.

**🧮 Calculadoras**
- Cada calculadora de tiempo es ahora su **propia página individual** (Entre dos horas, Horas→Días, Minutos→Horas, Fecha a Fecha).
- **Animación de engranajes "Calculando…"** al calcular, diseño con tokens (claro/oscuro), y botones **Volver a Calculadoras / Volver al Panel Principal**.
- **Calculadoras es exclusiva del superusuario** (nadie más la ve ni puede entrar por URL).

**🚻 Salidas al baño**
- **Autoguardado sin botón**: la salida se guarda sola al poner clase + hora; el alumno queda **"Afuera"** y el **semáforo se colorea al registrar el regreso** (no al salir).
- Corregidos: **maestros duplicados** en el select de clase y la confusión del campo de regreso (deshabilitado se veía editable).

**🗓️ Otros arreglos**
- **Agendas (docente)** — se recuperó el autoguardado al cambiar de grado (se había perdido en la extracción de JS): sin él la tabla de materias no cargaba y el docente **no podía registrar**.
- **Panel y sidebar** — **Calculadoras** y **Sponsors** quedaron en **grupos propios**, separados de "Reloj".
- **Inventario** — dashboard reconstruido con los componentes nuevos (tiles) como referencia del rediseño.

### v6.0.5.0.001 — Barrido de bugs de la extracción de JS (release menor)

> Release **menor**: las novedades solo se muestran al superusuario. Corrige secuelas de la migración *JS fuera del HTML* halladas con un diagnóstico automático de las 72 pantallas.

- **9 pantallas sin JavaScript** — La extracción había dejado 9 archivos con solo el bloque de configuración y **cero lógica**: modal de mantenimiento (`menu.js`), gráfica del reloj, edición de vacaciones, mantenimiento de cámaras, historial médico, editar agenda, revisión de comentarios e índice de notas, y el cierre por inactividad. Recuperados (~1,200 líneas) y validados uno por uno.
- **`window._SB` vs `window._PAGE`** — En *Salidas al baño* el JS que pinta la tabla lee `window._SB`, pero la config extraída lo escribía en `window._PAGE`: los alumnos no cargaban. Corregido.
- **JSON crudo en atributos `data-*`** — El alumnado (y otros bloques) se inyectaban con `|safe` dentro de `data-v="..."`, y la primera comilla del JSON cerraba el atributo → `JSON.parse` recibía `{` y fallaba. Afectaba Salidas al baño, Mantenimiento, Cámaras, Convocatorias y las gráficas del panel admin. Se quitó `|safe` (Django escapa las comillas y el navegador las restaura).
- **`abrirModalResumen` indefinida** — Las tarjetas resumen del Panel Principal (`onclick`) no hacían nada porque la función se perdió; reescrita con un modal Bootstrap propio (sin dependencia de SweetAlert).
- **`{% extends %}` no era el primer tag** — La página *Nuevo Sponsor* daba **error 500**; un comentario quedó antes del `extends`. Corregido.
- **Tags Django dentro de `.js`** — `medical_history.js` e `idle_logout.js` traían `{% url %}` literal (un `.js` no lo procesa Django); su config pasó a un `data-*` en el template.
- **Scripts duplicados** — `dt_guard.js` se cargaba dos veces (base + hijo) en 5 pantallas; y el `?v=` de 168 `<script>` se subió para romper la caché del navegador.
- **Un `const CFG` global por archivo** — Los 33 archivos extraídos declaraban la misma constante global; en cada página el segundo script moría con `SyntaxError`. Renombrados con prefijo de app.
- **Logo del PDF de inventario** — Ruta `inventory/` (inglés) → `inventario/`.
- **Notas mitad de parcial** — El comentario del maestro no se guardaba; *Vista Previa*, asignar a varios grados, agrupado por maestro, "Revisado" persistente, bachillerato con `@Curso`, y el PDF de comentarios en **dos columnas** (entran hasta 13 maestros por alumno).
- **Navegación de maestros de dos áreas** — Nayeli Gonzales / David Ruiz: una tarjeta de Notas por área, el dashboard recuerda el área elegida (antes solo funcionaba para una lista fija de usuarios) y *Volver* regresa al Panel General correcto. Un coordinador-maestro veía las asignaciones de todos como suyas.
- **Salidas al baño** — Período con fecha de fin anterior a la de inicio (2025 antes que 2026); corregido y con validación en el formulario.
- **Tickets / login / superusuario** — El panel de técnico ya no queda abierto a cualquier usuario; recuperados el ojito, el usuario sin dominio y el modo admin; el superusuario no se bloquea por intentos fallidos + comando `manage.py resetclave`.

### v6.0.5.0 — Recuperación del JS perdido, PDF de notas y sincronización de asignaciones

- **🔴 JS perdido en 12 pantallas** — La refactorización que sacó el JavaScript de los HTML (v6.0.2.0) copió **solo el bloque de configuración** y descartó la lógica: 12 archivos quedaron con `data-*` y **cero código**. Pantallas que no hacían nada: *Vista Previa* y carrusel del coordinador de notas, **guardar comentario del maestro**, asignaciones (fecha límite, eliminar, pre-cargar cache), Inventario (Registros, Computadoras, Editar monitor), Mantenimiento, Tickets (enviar y panel de técnico) y los modales de parcial/año. Recuperadas ~1,700 líneas desde el historial de git, cada una validada con `node --check`.
- **🔴 `SyntaxError: Identifier 'CFG' has already been declared`** — Los 33 archivos extraídos declaraban la **misma constante global**, y toda página carga al menos dos (el de la base + el de la pantalla): el segundo moría y **con él todo su código**. Cada archivo tiene ahora su propio nombre (`CFG_MAESTRO`, `CFG_COORDINADOR`…), con prefijo de app cuando dos apps comparten nombre de archivo. Además 24 plantillas cargaban su `.js` **dos veces**.
- **PDF de notas: comentarios ilegibles** — Los comentarios de todos los maestros se unían en un solo párrafo con `·`; un texto sin espacios **se salía de la hoja** (`simpleSplit` solo corta en espacios) y con más de 5 maestros el resto **desaparecía sin aviso**. Ahora: un bloque por maestro (nombre en negrita **en línea** con su texto), **dos columnas** automáticas, tamaño de letra que se ajusta solo (9→6 pt) y corte por carácter para palabras largas. Entran **13 maestros** por alumno con comentarios de 40 palabras; más allá avisa con *(continúa…)*. Tope de 600 caracteres en el servidor y en los textarea.
- **Bachillerato: "No se obtuvieron datos del SP"** — `spEdcNotasInsertBachillerato` exige `@Curso` y las tarjetas del maestro no lo mandaban (la asignación no guarda curso). Ahora se piden los dos cursos y se combinan; las tarjetas llevan el curso en el enlace.
- **Coordinador: maestros invisibles** — La lista agrupaba **solo por grado** y el banner de maestros tomaba la sección *del primer alumno*: en un grado con secciones a/b solo se veían los de la "a", y *Agregar* asignaba solo a esa. Ahora agrupa por **grado + sección** (en Colegio pasó de 3 banners a 6).
- **"Mis Reportes" desincronizado** — Un coordinador que además es maestro veía las asignaciones de **todo el mundo** como si fueran suyas (2 en la base, 12 tarjetas). Ahora ve las suyas, con enlace *Ver los de todos los maestros* para conservar la vista de coordinador.
- **"Revisado" no se guardaba** — El botón solo pintaba de verde; al recargar se perdía, igual que el check de cada comentario. Ambos se persisten y la pantalla vuelve a abrir marcada, con el envío por correo ya habilitado.
- **Asignar maestro a varios grados** — El desplegable *Grados* permite marcar varios grado-sección y asignar de una vez (la vista ya lo soportaba; faltaba la interfaz). La pantalla de Asignaciones se agrupa **por maestro** (116 filas sueltas → 24 bloques) con botón *Fecha a todos*.
- **Tercer parcial habilitado** — El aviso "no hemos llegado a ese parcial" queda solo para el 4º. El rango vive en dos constantes de `base_notas.js` (`PARCIAL_MAX` / `PARCIAL_MIN`).
- **🔒 Tickets: panel de técnico abierto** — `technician_dashboard` mostraba **todos los tickets del sistema** a cualquier usuario autenticado. Ahora exige `tickets.view_ticket`; los demás van al panel de usuario. Los instructores CFP pasaron al grupo `administracion` y el contador "Tickets abiertos" muestra solo los propios.
- **Login** — El ojito de la contraseña, escribir el usuario sin `@ana-hn.org` y el modo admin dejaron de funcionar porque la migración de JS **sobrescribió** `login.js` y cargaba el script solo cuando había bloqueo. Recuperado y separado en `login.js` + `login_bloqueo.js`.
- **Superusuario sin bloqueo de login** — Ya no se bloquea por intentos fallidos (si se bloqueaba, nadie podía desbloquear a los demás). Nuevo comando `manage.py resetclave <usuario> [--clave X] [--solo-desbloquear]`.
- **Reloj** — Pestaña de **ausentes sin permiso registrado** (días laborales sin marca, descontando feriados y permisos ya existentes) que abre el modal de *Registrar Permiso* ya rellenado; para **maestros por hora**, los sábados especiales suman sus horas al total del mes en una columna propia.
- **CFP** — Rol *Instructor* con cursos asignados (`InstructorCurso`): cada instructor ve solo los suyos. Permiso `contabilidad_cfp` para acceder únicamente a Contabilidad.
- **Inventario de cámaras** — API JSON (DRF, sesión de Django) y app **Next.js + Tailwind** con exportación estática servida por Apache (sin proceso Node en producción).

### v6.0.2.0 — JS/CSS fuera del HTML, notificaciones y tema

> Release **técnico**: las novedades de esta versión solo se le muestran al superusuario.

- **Cero JS y CSS dentro de los templates** — Se migraron **2,539 líneas** repartidas en **70 plantillas** (JS) y **31** (CSS) a archivos estáticos propios. Como un `.js` no lo procesa Django, los valores del servidor viajan por tres patrones: `data-*` en un div de config (URLs y banderas), **islas JSON** (`<script type="application/json">`, mismo patrón que `json_script`) para objetos y listas, y `{% if %}` de Django convertido a `if` de JavaScript donde había lógica de permisos. Cada archivo se validó con `node --check` y cada isla renderizando la página y parseando el JSON.
- **Notificaciones arregladas** — La campanita y su JS estaban **duplicados a mano en solo 3 plantillas**, así que en los otros 14 módulos las notificaciones se generaban pero **nadie las veía**. Ahora hay un parcial único (`accounts/_notificaciones.html`) incluido desde `_user_dropdown.html`, presente en los 17 módulos.
- **Modo oscuro retirado** — Quedaba a medias (la barra lateral se aclaraba, formularios y modales sin cubrir) y `menu.js` re-aplicaba el tema guardado en cada carga, así que no se podía volver a claro. Se eliminó el toggle, `theme.js`, `theme-init.js` y el CSS del tema oscuro: el sistema queda **siempre en claro**, conservando la barra lateral oscura del diseño original.
- **Versiones menores** — `gen_changelog --menor` sube un 5º segmento (`6.0.1.3.001`) y marca la entrada para que **solo el superusuario** vea la ventana de novedades; los releases normales se anuncian a todos.
- **Sponsors** — Botón *Volver* en las 13 pantallas (por defecto en la base del módulo) y estilos parejos en los 10 formularios mediante un mixin que asigna `form-select`/`form-control`/`form-check-input` según el tipo de campo.
- **Bloqueo por formulario** — *Solo lectura* ahora **deshabilita los campos** en pantalla (antes dejaba escribir y solo fallaba al guardar); pantalla propia con botón *Volver*; la tarjeta guarda también el área y los docentes seleccionados (antes esa selección no tenía efecto); aviso al restringir sin elegir docente y botón *Restaurar* con confirmación.
- **Correcciones** — Comentarios `{# … #}` multilínea que se imprimían como texto en pantalla (en Django son de una sola línea); `Correspondence.description` mapeada a la columna real `decription`; decimales con coma por localización y listas de Python que rompían el JSON.

### v6.0.1.3 — Sponsors, bloqueo por formulario y footer unificado

- **🔒 Sponsors: módulo era público** — Ninguna de sus 18 vistas exigía sesión, exponiendo **3,561 donantes** (correos, teléfonos, direcciones, fechas de nacimiento) y **30,045 ingresos** a cualquiera sin autenticar. Además `delete_sponsor` **borraba por GET**, sin CSRF ni confirmación, arrastrando en cascada ingresos y padrinazgos. Corregido: `@login_required` en todas, borrado solo por POST con confirmación.
- **Sponsors: bugs corregidos** — (1) dar de alta un sponsor fallaba con `IntegrityError` porque el form excluía `city` (NOT NULL) y la vista nunca lo asignaba; (2) `title`/`directed` se pedían obligatorios siendo `null=True`; (3) Correspondencia reventaba con `OperationalError 1054` — la columna real se llama `decription` (typo en la BD), ahora mapeada con `db_column`; (4) las pantallas de **Ingresos, Apadrinados y Correspondencia** eran plantillas **vacías** (página en blanco); (5) `Godfather` no mapeaba `spn_sponsored_id` ni `spn_descr_godfather_id`, así que un padrinazgo no podía indicar **a quién** apadrina.
- **Sponsors: rendimiento y vista** — Lista paginada (50) con buscador: **1.27 MB → 63 KB**; alta de sponsor **1.46 MB → 103 KB**; autocompletar limitado a 20 resultados distintos. Módulo migrado a **Tabler** con `base_sponsors.html` (sidebar + footer), reemplazando 9 CSS sueltos e iconos PNG.
- **Modo mantenimiento: bloqueo por formulario** — Además del bloqueo general, cada formulario puede quedar en **Normal / Solo lectura / Bloqueado**: Agendas, Reportes informativos, Reportes conductuales, Notas mitad de parcial, Convocatoria de tutorías, Progress Report y Tickets. *Solo lectura* deja consultar pero corta los POST. Respeta el mismo filtro de área/usuarios; el superusuario nunca se bloquea. Config en `MAINTENANCE_MODULES` (constance) y registro en `core/maintenance_modules.py`.
- **Menú admin: grupo "Salidas"** — "Salidas al baño" salió de *Académico* a su propio grupo, listo para sumar "Salidas con permisos".
- **Footer unificado y sticky** — Antes eran dos bloques separados (copyright y versión), descolgados del layout. Ahora es un solo footer con Flexbox: copyright a la izquierda, `TechCare vX · Novedades` a la derecha, pegado al fondo con `margin-top:auto` (sin `position:fixed`). Aplicado a **todas** las plantillas vía `templates/_footer.html`.

### v6.0.1.2 — Ruteo de reportes Bilingüe

- **Ruteo BL sin fugas** — Cada reporte académico/conductual del área Bilingüe llega **solo a su coordinador** (C1/C2/C3/C4). Regla combinada: la **materia manda** (C3/C4), si no el **grado/grupo** del alumno decide C1 (1–3) / C2 (4–9), y un **override por docente** desempata. Solo aplica a reportes nuevos.
- **Pantalla de Ruteo unificada** (`conducta/routing_bl.html`, solo superuser por defecto): mapeo de materias→coordinador, catálogo de docentes y portal de Grupos (grado-sección) en una sola hoja, con **autoguardado**. Configuración en `media/conducta/routing_bl.json` (no en BD; **no** se versiona).
- **Catálogo de docentes** — Cada docente con sus **materias** y **coordinador**; admite **varias cargas** por docente (los que **reportan a dos coordinadores**, ej. Miss Saravia → C1 y C3). Separadores: `,` = un paquete, `;` = cargas separadas. Filas agrupadas por coordinador.
- **Grupos** — Selección de las clases de cada docente por grupo con un **menú desplegable multi-select**; los alumnos se cargan desde SQL Server con "Refrescar alumnado".
- **Permisos por coordinador** — Cada coordinador puede tener acceso **Sin acceso / Solo lectura / Puede editar** a la pantalla de Ruteo (lo fija el superusuario).
- **Versión + Novedades** — Número de versión en el pie de página de toda la app y ventana de novedades por versión (ver sección dedicada).

### Anteriores

- **Convocatoria de Tutorías (Bilingüe)** — Módulo `conducta`. Los maestros bilingües crean convocatorias por alumno (carga automática de grado/sección, asignaturas por grado con días fijos del horario), generan un registro y lo ven en su Historial (tab *Tutorías*). Los coordinadores (tab *Tutorías*) ven/editan/eliminan y descargan el PDF (carta "Compromiso de Asistencia a Tutoría" con logo `encabezado.jpg`, una sola hoja, desprendible ACLARATORIA). Ruteo por grado: **C1** (grados 1–3, Catherine Varela) y **C2** (grados 4–9, David Ruiz) con notificación al coordinador. Matriz Grado×Día×Asignatura configurable por parcial. Modelos: `TutoriaHorario`, `ConvocatoriaTutoria`, `ConvocatoriaAsignatura`, `TutoriaGrupoMaestro`.
- **Bono por Asistencia** — Módulo `reloj`, tab del Reporte Mensual de Permisos (antes "Pierde Bono"). Cálculo **automático** con reglas configurables (modal *Reglas del bono*, solo superusuario): Otro Pagado, Enfermedad, hora máx. de entrada (6:57), y reglas extra. **Vigilancia** con dos turnos (19:00 → entrada máx 18:45; 00:00 → 23:45). **Maestros por hora** con horario especial por día (ej. Juan Pablo Chirinos lunes 11:30). **No Pagado y Compensatorio nunca pierden** el bono. Sub-tabs *Lista de empleados con bono* (solo conservan) y *Detalle*; override manual del superusuario; PDF de la lista. Modelos: `BonoConfig`, `BonoReglaExtra`, `BonoHorarioEmpleado` + `ReportePermisoMensual.bono_override`.
- **Tiempo receso** — Tab mensual en Reporte de Permisos: marcas de almuerzo (2ª/3ª) de empleados 07:00–15:48, minutos tomados, **minutos de más** sobre 30 y total; ajuste manual de marcas (solo superusuario). PDF incluido.
- **Vacaciones** — Los días disponibles ahora se muestran **en negativo** cuando se sobrepasa el saldo (ya no se topan en 0).
- **Auditoría** — Filtro por **rango de fechas** (desde/hasta).
- **Permisos Coordinadores** — El permiso "Eliminar" usa **fecha y hora seleccionable** (en vez de 24h fijas).
- **Tickets** — Chat con **adjuntos** (pegar/subir imagen/adjuntar documento, con auto-redimensión de imágenes), **sonido de notificación** al llegar mensaje o crear ticket, y **campanita + toasts** en todo el módulo.

---

## Stack técnico

| Componente | Versión |
|-----------|---------|
| Python | 3.13.3 |
| Django | 6.0.5 |
| Tabler UI | 1.0.0-beta19 |
| ReportLab | 4.5.0 |
| WeasyPrint | 68.1 |
| openpyxl | 3.1.5 |
| python-pptx | 1.0.2 |
| Base de datos principal | MySQL (`sponsors2` en `192.168.10.6`) |
| Base de datos secundaria | SQL Server (módulo Reloj y datos alumnos/padres) |

---

## Estructura del repositorio

```
techcare_project/
├── system_proyect/
│   ├── accounts/            # Autenticación, settings, panel principal
│   ├── agendas/             # Agendas semanales docentes
│   ├── calculadoras/        # Calculadoras utilitarias
│   ├── conducta/            # Reportes conductuales y académicos
│   ├── core/                # Context processors y utilidades compartidas
│   ├── enfermeria/          # Atención médica y medicamentos
│   ├── finanzas_personales/ # Finanzas personales internas
│   ├── inventario/          # Inventario de equipos y activos
│   ├── mantenimiento/       # Registro de mantenimientos
│   ├── notas_parcial/       # Notas de mitad de parcial
│   ├── querys/              # Consultas SQL directas
│   ├── reloj/               # Control de asistencia (SQL Server)
│   ├── sponsors/            # Gestión de patrocinadores
│   ├── tickets/             # Tickets de soporte técnico
│   ├── static/              # CSS/JS globales
│   ├── staticfiles/         # Carpeta collectstatic (no editar)
│   └── templates/           # Templates globales (403.html, admin/)
├── django_test/             # Entorno de pruebas
└── datos/                   # Scripts SQL y CSV de ejemplo
```

---

## Templates globales

| Archivo | Descripción |
|---------|-------------|
| `templates/403.html` | Página de error 403 personalizada estilo TechCare (ícono candado, botón inicio/volver) |
| `templates/admin/` | Overrides del panel de administración Unfold |

---

## Módulo: Accounts — Autenticación y Configuración

Login con redirección automática según rol. Sidebar unificado compartido por todos los módulos vía `accounts/templates/accounts/_sidebar.html`.

### Plantillas (`accounts/templates/accounts/`)

| Template | Descripción |
|----------|-------------|
| `login.html` | Formulario de inicio de sesión |
| `register.html` | Registro de usuarios (maestros / staff) |
| `seleccion_rol.html` | **RETIRADO** — la vista `seleccion_rol` ahora redirige al Panel General; el template ya no se usa |
| `dashboard_general.html` | **NUEVO** — Panel General para staff multi-rol: todos los botones por grupo + toggle Bilingüe/Colegio para maestro de ambas áreas |
| `menu.html` | Panel principal con tarjetas por módulo |
| `settings_base.html` | Layout base de la sección Settings con sidebar de tabs |
| `settings_perfil.html` | Edición de perfil del usuario |
| `settings_notificaciones.html` | Preferencias de notificaciones |
| `settings_usuarios.html` | Listado y gestión de usuarios |
| `settings_usuario_form.html` | Formulario crear/editar usuario |
| `settings_grupos.html` | Listado y gestión de grupos |
| `settings_grupo_form.html` | Formulario crear/editar grupo |
| `settings_actividad.html` | Log de actividad del sistema |
| `settings_logs.html` | Logs de errores del servidor |
| `settings_correos.html` | Configuración de correo SMTP |
| `settings_envio_login.html` | **NUEVO** — Envío masivo de instrucciones de inicio de sesión. Campos editables por sección, lista de destinatarios con checkbox + búsqueda, preview en iframe, envío por correo |
| `settings_coordinadores.html` | Gestión de configuraciones de coordinadores |
| `settings_notificaciones_conducta.html` | Configuración de notificaciones del módulo conducta |
| `settings_roles.html` | Asignación de roles a usuarios |
| `settings_reloj_permisos.html` | Permisos de acceso al módulo Reloj por usuario |
| `_sidebar.html` | Sidebar unificado (incluido en todas las apps) |
| `_user_dropdown.html` | Menú desplegable de usuario (avatar, logout) |
| `_welcome_overlay.html` | Overlay de bienvenida al primer login |
| `_notif_notas_toast.html` | Toast de notificación de notas parciales |
| `password_reset_form.html` | Solicitar reset de contraseña |
| `password_reset_done.html` | Confirmación de envío de email |
| `password_reset_confirm.html` | Nueva contraseña |
| `password_reset_complete.html` | Reset completado |

### Estáticos (`accounts/static/accounts/`)

| Archivo | Descripción |
|---------|-------------|
| `css/login.css` | Estilos de la pantalla de login |
| `css/menu.css` | Estilos del panel principal |
| `css/settings_base.css` | Estilos base de settings |
| `css/settings_correos.css` | Estilos de la sección de correos |
| `css/settings_envio_login.css` | **NUEVO** — Estilos del enviador masivo de instrucciones |
| `css/settings_logs.css` | Estilos de logs |
| `css/welcome_overlay.css` | Estilos del overlay de bienvenida |
| `js/menu.js` | Lógica del panel principal |
| `js/settings_envio_login.js` | **NUEVO** — Checkbox list, búsqueda, preview AJAX, envío con confirmación |
| `js/settings_usuarios.js` | Gestión AJAX de usuarios |
| `js/settings_grupos.js` | Gestión AJAX de grupos |
| `js/settings_coordinadores.js` | Gestión de coordinadores |
| `js/settings_notificaciones_conducta.js` | Configuración de notificaciones |
| `js/settings_reloj_permisos.js` | Permisos reloj por usuario |
| `js/settings_roles.js` | Asignación de roles |
| `js/settings_logs.js` | Visor de logs con filtros |
| `js/settings_actividad.js` | Log de actividad |
| `js/notifications.js` | Notificaciones en tiempo real |
| `js/notif_notas_toast.js` | Toast de notas parciales |
| `js/sidebar.js` | Comportamiento del sidebar |
| `js/user_dropdown.js` | Menú de usuario |
| `js/welcome_overlay.js` | Overlay de bienvenida |

### URLs (`/accounts/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `login/` | `login` | Inicio de sesión |
| `logout/` | `logout` | Cierre de sesión |
| `register/` | `register_maestro` | Registro de usuarios |
| `menu/` | `menu` | Panel principal |
| `panel/` | `panel_general` | **NUEVO** — Panel General para staff multi-rol |
| `seleccion-rol/` | `seleccion_rol` | **RETIRADO** — redirige al Panel General / menú |
| `aplicar-rol/<rol>/` | `aplicar_rol` | Aplicar rol seleccionado |
| `settings/` | `settings_perfil` | Perfil |
| `settings/notificaciones/` | `settings_notificaciones` | Notificaciones |
| `settings/usuarios/` | `settings_usuarios` | Usuarios |
| `settings/usuarios/crear/` | `settings_usuario_crear` | Crear usuario |
| `settings/usuarios/<pk>/editar/` | `settings_usuario_editar` | Editar usuario |
| `settings/usuarios/<pk>/eliminar/` | `settings_usuario_eliminar` | Eliminar usuario |
| `settings/grupos/` | `settings_grupos` | Grupos |
| `settings/grupos/crear/` | `settings_grupo_crear` | Crear grupo |
| `settings/grupos/<pk>/editar/` | `settings_grupo_editar` | Editar grupo |
| `settings/grupos/<pk>/eliminar/` | `settings_grupo_eliminar` | Eliminar grupo |
| `settings/actividad/` | `settings_actividad` | Actividad del sistema |
| `settings/logs/` | `settings_logs` | Logs del servidor |
| `settings/correos/` | `settings_correos` | Config. correo |
| `settings/correos/envio-login/` | `settings_envio_login` | **NUEVO** — Enviar instrucciones de login |
| `settings/correos/envio-login/preview/` | `settings_envio_login_preview` | **NUEVO** — Preview del correo (AJAX) |
| `settings/conducta/coordinadores/` | `settings_coordinadores` | Coordinadores conducta |
| `settings/conducta/notificaciones/` | `settings_notificaciones_conducta` | Notificaciones conducta |
| `settings/conducta/roles/` | `settings_roles` | Roles |
| `settings/reloj/permisos/` | `settings_reloj_permisos` | Permisos reloj |
| `password_reset/` | — | Recuperar contraseña |

### Roles y grupos

Los grupos funcionan como **marcadores de rol** que el código revisa por nombre
(en `core/context_processors.py`, `accounts/panel_roles.py`, `accounts/views.py`
y `notas_parcial/templatetags/notas_tags.py`). **Casi ninguno usa permisos de
Django** — la única excepción es `inventario` (18 permisos `add/change/view`).
Los permisos finos del módulo Reloj **no** vienen de grupos sino del modelo
`reloj.RelojPermiso` por usuario (Ver/Editar/Eliminar por módulo + toggle "Todos").

| Grupo | Configuración / efecto en código |
|-------|----------------------------------|
| `administracion` | `nav_tickets=True` · bucket **tickets** del panel · si es único rol → `dashboard_administracion`; si tiene otro rol → Panel General con sección Tickets |
| `tecnicos` | `nav_home_url` → `tickets_dashboard` |
| `reloj` | `nav_reloj` + `nav_calculadoras=True` · bucket **reloj** · único rol → `reloj_dashboard` |
| `coordinador_bilingue` | `nav_coord_bl=True` · bucket **coordinador** · home → `dashboard_coordinador area=bilingue` · ve Enfermería |
| `coordinador_colegio` / `coordinadores_colegio` / `coordinadores` | `nav_coord_col=True` · bucket **coordinador** · home → `dashboard_coordinador area=colegio` |
| `coord_progress_bl` | Cuenta como coord bilingüe (`nav_coord_bl`) · bucket coordinador |
| `coord_revision` | Solo en `notas_tags`: `es_solo_revision` → en Notas ve **solo Revisión** (sin Asignaciones) |
| `maestros_bilingue` | `nav_maestro_bl` · bucket **maestro** · home → `dashboard_maestro` |
| `maestros_colegio` | `nav_maestro_col` · bucket maestro |
| `maestros_bilingue` **+** `maestros_colegio` | **Activa el toggle Bilingüe/Colegio** en el Panel General |
| `coord_notas_parcial_bl` / `coord_notas_parcial_col` | `es_coord_notas` → Notas: Revisión **+ Asignaciones** |
| `maestros_notas_parcial_bl` / `maestros_notas_parcial_col` | `es_maestro_notas` → su página de notas |
| `inventario` | `nav_inventory=True` (+ 18 permisos Django de inventario) |
| `enfermeria` | `nav_enfermeria=True` → dashboard enfermería |
| `control baño coord` / `control baños col` | `is_salidas_bano=True` (menú Salidas Baño) |
| Superusuario | Acceso completo + herramientas admin (no usa el Panel General) |

### Panel General para staff multi-rol (`accounts/panel_roles.py`)

Los usuarios **staff con 2+ roles** (o maestro en ambas áreas) ya **no pasan por
la antigua ventana `seleccion_rol`** (retirada): aterrizan en un **Panel General**
(`accounts/templates/accounts/dashboard_general.html`, vista `panel_general`,
URL `/accounts/panel/`) con **todos sus botones en un solo lugar**, visibles según
el grupo.

- **Buckets de rol:** `tickets` (administracion / perm tickets) · `coordinador`
  (cualquier grupo coord) · `maestro` (maestros_bl/col) · `reloj`.
- **Va al Panel General** si `is_staff` **y** (tiene **2+ buckets** **o** es
  **maestro BL y Colegio**).
- **Toggle Bilingüe/Colegio** (client-side): aparece **solo** si el usuario tiene
  `maestros_bilingue` **Y** `maestros_colegio`; cambia únicamente los botones de
  la sección **Maestro** entre BL y Colegio.
- **Notas Mitad de Parcial** se muestra normal (sin toggle); los **usuarios
  no-staff** no se ven afectados.
- **Prioridad de `nav_home_url`:** superuser→menú · multi-rol→Panel General ·
  solo_progress→progress · maestro→dashboard_maestro · coord_col→coord colegio ·
  coord_bl→coord bilingüe · tecnicos→tickets · reloj→reloj · administracion→tickets · resto→menú.

---

## Módulo: Conducta — Reportes Académicos y de Conducta

Sistema de reportes para maestros con revisión por coordinadores. Áreas: Bilingüe y Colegio/CFP (flujos independientes).

### Tipos de reportes

| Tipo | Descripción |
|------|-------------|
| Informativo Académico | Comunicación académica general |
| Informativo Conductual | Información conductual sin acción formal |
| Conductual | Falta de conducta — genera PDF individual y PDF "3 Strikes" |
| Progress Report | Seguimiento académico (solo área bilingüe) |

### Plantillas (`conducta/templates/conducta/`)

| Template | Descripción |
|----------|-------------|
| `base_conducta.html` | Layout base del módulo |
| `dashboard_maestros.html` | Dashboard del maestro con tabs por área |
| `dashboard_coordinador.html` | Dashboard del coordinador con filtros, tabla de reportes y accesos rápidos. **NUEVO:** card de Materias-Docentes (solo superuser en área BL) |
| `lista_reportes.html` | **ACTUALIZADO** — Tabla de reportes con badges Tabler (`bg-blue-lt`, `bg-orange-lt`, `bg-red-lt`, `bg-purple-lt`) y modal de edición inline |
| `historial_maestro.html` | Historial de reportes del maestro |
| `materias_docentes_bl.html` | **NUEVO** — Tabla de Materias-Docentes Bilingüe (solo superuser). Buscador, stats cards por coordinador, tabla con badge de coordinador coloreado |
| `form_conductual.html` | Formulario de reporte conductual |
| `form_informativo.html` | Formulario de reporte informativo |
| `form_progress.html` | Formulario de Progress Report |
| `editor_conductual.html` | Editor de reporte conductual existente |
| `editor_informativo.html` | Editor de reporte informativo existente |
| `editor_progress.html` | Editor de Progress Report existente |
| `directorio_telefonos.html` | Directorio de teléfonos de alumnos |

### Estáticos (`conducta/static/conducta/`)

| Archivo | Descripción |
|---------|-------------|
| `css/materias_docentes_bl.css` | **NUEVO** — Estilos de la tabla Materias-Docentes BL |
| `js/materias_docentes_bl.js` | **NUEVO** — Búsqueda debounced 420ms, submit automático |
| `js/coordinador.js` | Lógica del dashboard coordinador |
| `js/dashboard_coordinador.js` | Tabs, filtros y acciones del coordinador |
| `js/editor_reporte.js` | Editor de reportes con evidencias |
| `js/formularios.js` | Validaciones de formularios |
| `js/historial.js` | Filtros e interacciones del historial |

### URLs (`/conducta/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `dashboard/maestro/` | `dashboard_maestro` | Dashboard maestro |
| `coordinador/<area>/` | `dashboard_coordinador` | Dashboard coordinador por área |
| `coordinador/historial/alumno/<id>/` | `historial_alumno_coordinador` | Historial del alumno |
| `coordinador/bl/c1/` … `c4/` | `dashboard_c1` … `c4` | Dashboards por coordinador BL |
| `coordinador/bl/progress/` | `dashboard_coordi_bl` | Dashboard coordinador Progress BL |
| `coordinador/bl/materias/` | `materias_docentes_bl` | **NUEVO** — Tabla Materias-Docentes BL |
| `routing-bl/` | `routing_bl_config` | **NUEVO** — Pantalla de Ruteo BL (mapeo + catálogo docentes + grupos). Acceso por permiso de coordinador |
| `routing-bl/guardar/` | `routing_bl_guardar` | Guarda mapeo/catálogo (materias C3/C4, grados, `docentes_catalogo`) |
| `routing-bl/refrescar/` | `routing_bl_refrescar` | Trae el alumnado BL desde SQL Server y reconstruye grupos |
| `routing-bl/visibilidad/` | `routing_bl_toggle_vis` | Fija el permiso de un coordinador (none/lectura/edit) — solo superuser |
| `routing-bl/descargar/` · `routing-bl/cargar/` | `routing_bl_descargar` · `routing_bl_cargar` | Exportar/importar el JSON (solo superuser) |
| `grupos-bl/guardar/` | `grupos_bl_guardar` | Guarda coordinador + clases de un grupo |
| `reporte/conductual/bilingue/` | `reporte_conductual_bilingue` | Crear reporte conductual BL |
| `reporte/informativo/bilingue/` | `reporte_informativo_bilingue` | Crear reporte informativo BL |
| `progress_report/bilingue/` | `progress_report_bilingue` | Crear progress report |
| `reporte-conductual/<pk>/pdf/` | `descargar_pdf_conductual` | PDF conductual |
| `reporte-conductual/<pk>/pdf-3strikes/` | `descargar_pdf_conductual_3_strikes` | PDF 3 Strikes |
| `reporte-informativo/<pk>/pdf/` | `descargar_pdf_informativo` | PDF informativo |
| `progress-report/<pk>/pdf/` | `descargar_pdf_progress` | PDF progress |
| `reporte/editar-ajax/` | `editar_reporte_ajax` | Edición inline AJAX |
| `descargar/zip/` | `descargar_zip_reportes` | ZIP de múltiples reportes |
| `directorio/` | `directorio_telefonos` | Directorio de teléfonos |

### Modelos (`conducta/models.py`)

| Modelo | Descripción |
|--------|-------------|
| `IncisoConductual` | Incisos del reglamento |
| `MateriaDocenteBilingue` | **Materia-Docente BL** con campo `coordinador` (códigos C1–C4) |
| `MateriaDocenteColegio` | Materia-Docente Colegio |
| `ConfiguracionCoordinador` | Config. por coordinador (código, nombre, usuario, área) |
| `ReporteConductual` | Reporte conductual con evidencias |
| `ReporteInformativo` | Reporte informativo/académico |
| `ProgressReport` | Progress report BL |
| `EvidenciaReporte` | Hasta 2 imágenes por reporte |
| `ConfiguracionNotificacion` | Destinatarios de correo por área |

---

## Módulo: Reloj — Control de Asistencia

Conecta con SQL Server para leer marcas del reloj biométrico. Gestiona horarios, compensatorios, permisos, feriados, vacaciones y genera reportes PDF.

### Plantillas (`reloj/templates/reloj/`)

| Template | Descripción |
|----------|-------------|
| `base_reloj.html` | Layout base del módulo |
| `dashboard.html` | Dashboard principal con stats |
| `reporte.html` | Reporte de asistencia con filtros y comentarios |
| `compensatorio_list.html` | **ACTUALIZADO** — Lista de tiempo compensatorio por día. Columna "Tiempo Extra Autorizado", resumen superior con total acumulado (incl. extras) actualizable sin recarga (`#resumen-total-min`, `#resumen-tiempo-txt`) |
| `compensatorio_form.html` | Formulario crear/editar compensatorio |
| `compensatorio_calculo_list.html` | **ACTUALIZADO** — Cálculo del saldo compensatorio por empleado. Nueva columna **T. Extra** con badge cyan + modal de entradas. Fórmula: `Saldo = Total − Compensado − T.Extra`. Badges editables inline para días adeudados, factor h/día, permisos extras, min/día, días no laborables |
| `compensatorio_calculo_form.html` | Formulario crear/editar calculo compensatorio |
| `compensatorio_authorize.html` | Autorización de tiempo extra |
| `horarios_list.html` | Listado de horarios asignados |
| `horario_form.html` | Formulario de horario |
| `feriados_list.html` | Listado de feriados |
| `feriado_form.html` | Formulario de feriado |
| `sabados_list.html` | Sábados especiales |
| `sabado_form.html` | Formulario de sábado especial |
| `permisos_list.html` | Listado de permisos de empleados |
| `permiso_form.html` | Formulario de permiso |
| `permiso_reporte.html` | Reporte mensual de permisos |
| `plantilla_list.html` | Plantillas de horario |
| `plantilla_form.html` | Formulario de plantilla |
| `regla_form.html` | Regla de plantilla |
| `grafica.html` | Gráfica circular de asistencia |
| `vacaciones_list.html` | Listado de vacaciones |
| `vacaciones_importar.html` | Importar vacaciones |
| `test_sql.html` | Diagnóstico de conexión SQL Server |

### Estáticos (`reloj/static/reloj/`)

| Archivo | Descripción |
|---------|-------------|
| `js/compensatorio_list.js` | **ACTUALIZADO** — Guarda tiempo extra por día (AJAX). `actualizarResumenTotales(delta)` actualiza al instante el total acumulado y la línea "incl. Xm extra" sin recargar |
| `js/compensatorio_calculo_list.js` | **ACTUALIZADO** — Modal de T. Extra múltiple: `renderTERows`, `updateTETotals` actualiza badge y recalcula saldo. Modales para días no lab., días adeudados, factor, permisos extras, min/día. Bulk actions |
| `js/reporte.js` | Filtros y notas del reporte |
| `js/grafica.js` | Gráfica circular (Chart.js) |
| `js/horario.js` | Lógica de horarios |
| `js/vacaciones_list.js` | Gestión de vacaciones |
| `css/reloj.css` | Estilos base del módulo |
| `css/reporte.css` | Estilos del reporte |
| `css/permiso_reporte.css` | Estilos del reporte de permisos |

### URLs (`/reloj/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `` | `reloj_dashboard` | Dashboard |
| `reporte/` | `reloj_reporte` | Reporte de asistencia |
| `pdf/` | `reloj_exportar_pdf` | Exportar PDF del reporte |
| `grafica/` | `reloj_grafica` | Gráfica circular |
| `overtime/authorize/` | `reloj_overtime_authorize` | Autorizar tiempo extra |
| `plantillas/` | `reloj_plantilla_list` | Plantillas de horario |
| `horarios/` | `horarios_list` | Horarios asignados |
| `feriados/` | `reloj_feriados_list` | Feriados |
| `sabados/` | `reloj_sabados_list` | Sábados especiales |
| `compensatorio/` | `reloj_compensatorio_list` | Compensatorio por día |
| `compensatorio/set-extra/` | `reloj_compensatorio_set_extra` | Guardar tiempo extra por día (AJAX) |
| `compensatorio-calculo/` | `reloj_compensatorio_calculo_list` | Cálculo de saldo compensatorio |
| `compensatorio-calculo/<pk>/tiempo-extra/` | `reloj_compensatorio_calculo_get_te` | **NUEVO** — GET entradas de T. Extra (AJAX) |
| `compensatorio-calculo/<pk>/tiempo-extra/add/` | `reloj_compensatorio_calculo_add_te` | **NUEVO** — Agregar entrada T. Extra (AJAX) |
| `compensatorio-te/<te_pk>/delete/` | `reloj_compensatorio_calculo_del_te` | **NUEVO** — Eliminar entrada T. Extra (AJAX) |
| `compensatorio-calculo/<pk>/set-dias-adeudados/` | `reloj_compensatorio_set_dias_adeudados` | Editar días adeudados |
| `compensatorio-calculo/<pk>/set-factor/` | `reloj_compensatorio_set_factor` | Editar factor h/día |
| `compensatorio-calculo/<pk>/set-permisos-extras/` | `reloj_compensatorio_set_permisos_extras` | Editar permisos extras |
| `compensatorio-calculo/<pk>/set-min-dia/` | `reloj_compensatorio_calculo_set_min_dia` | Editar min. autorizados/día |
| `compensatorio-calculo/<pk>/dias-no-lab/` | `reloj_compensatorio_dias_no_lab_get` | GET días no laborables |
| `compensatorio-calculo/<pk>/dias-no-lab/add/` | `reloj_compensatorio_dias_no_lab_add` | Agregar día no laborable |
| `compensatorio-dias-no-lab/<dia_pk>/delete/` | `reloj_compensatorio_dias_no_lab_delete` | Eliminar día no laborable |
| `permisos/` | `reloj_permisos_list` | Permisos de empleados |
| `permisos/reporte/` | `reloj_permiso_reporte` | Reporte mensual de permisos |
| `vacaciones/` | `reloj_vacaciones_list` | Vacaciones |
| `google/compensatorio/ingresar/` | `compensatorio_google_hook` | Hook Google Forms |

### Modelos (`reloj/models.py`)

| Modelo | Descripción |
|--------|-------------|
| `ScheduleTemplate` | Plantilla de horario |
| `ScheduleRule` | Regla dentro de una plantilla |
| `EmployeeScheduleAssignment` | Asignación de plantilla a empleado |
| `OvertimeRequest` | Solicitud de tiempo extra |
| `Feriado` / `FeriadoAsignacion` | Feriados y asignación a empleados |
| `SabadoEspecial` / `SabadoAsignacion` | Sábados especiales y asignaciones |
| `TiempoCompensatorio` | Registro de compensatorio manual |
| `CompensatorioCalculo` | Cálculo del saldo (días adeudados, factor, permisos, fecha fin) |
| `DiaNoLaborableANA` | Días no laborables de la institución por empleado |
| `TiempoExtraDia` | **NUEVO** — Entradas de tiempo extra autorizado por empleado/fecha. `unique_together = [("emp_code", "fecha")]` |
| `ReporteNota` | Nota en el reporte de asistencia |
| `ReporteComentario` | Comentario en el reporte |
| `PermisoEmpleado` | Permiso de empleado |
| `ReportePermisoMensual` | Reporte mensual de permisos |
| `PermisoReporte` | Ítem individual en el reporte mensual |
| `VacacionConfig` | Configuración de vacaciones |
| `RelojPermiso` | Permisos de acceso al módulo por usuario |

### Lógica de saldo compensatorio

```
Saldo = max(0, Total_a_compensar − Compensado_hasta_hoy − Tiempo_Extra_autorizado)

Donde:
  Total_a_compensar    = (Días_adeudados × Factor_h/día) + Permisos_extras
  Compensado_hasta_hoy = Días hábiles transcurridos × Min_autorizados_día
  Tiempo_Extra         = SUM(TiempoExtraDia.minutos) por emp_code
```

---

## Módulo: Agendas — Agendas Semanales Docentes

### Plantillas (`agendas/templates/agendas/`)

| Template | Descripción |
|----------|-------------|
| `base_agendas.html` | Layout base |
| `form_agenda.html` | Formulario de agenda con imágenes |
| `historial_maestro.html` | Historial de agendas del maestro |
| `dashboard_coordinador.html` | Dashboard del coordinador por área |
| `editar_agenda.html` | Edición de agenda existente |

### URLs (`/agendas/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `form/` | `form_agenda` | Registrar agenda |
| `historial/` | `historial_maestro` | Historial propio |
| `coordinador/` | `dashboard_coordinador` | Dashboard coordinador |
| `<pk>/editar/` | `editar_agenda` | Editar agenda |
| `<pk>/pptx/` | `descargar_pptx` | Descargar PPTX (BL) / DOCX (Colegio) |
| `<pk>/eliminar/` | `eliminar_agenda` | Eliminar agenda |
| `modo/toggle/` | `toggle_modo` | Alternar modo maestro/coordinador |
| `imagen/subir/` | `subir_imagen` | Subir imagen a agenda |

**Acceso:** grupos `coordinador_bilingue` y `coord_progress_bl` tienen acceso a agendas de coordinador.

---

## Módulo: Notas Parcial — Notas de Mitad de Parcial

Sistema de revisión de notas con caché de 8 horas (`DatabaseCache`), flujo de 3 capas (caché → staging → SP SQL Server).

### Plantillas (`notas_parcial/templates/notas_parcial/`)

| Template | Descripción |
|----------|-------------|
| `base_notas.html` | Layout base |
| `index.html` | Vista principal de notas por maestro |
| `maestro.html` | Vista de maestro (ver notas de su grado) |
| `coordinador.html` | Vista de coordinador (carrusel de grados) |
| `asignaciones.html` | Gestión de asignaciones maestro-grado |
| `revision_comentarios.html` | Revisión de comentarios por coordinador |

### URLs (`/notas-parcial/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `` | `notas_parcial_index` | Vista principal |
| `pdf/` | `notas_parcial_pdf` | Generar PDF |
| `coordinador/` | `notas_parcial_coordinador` | Vista coordinador |
| `maestro/` | `notas_parcial_maestro` | Vista maestro |
| `asignaciones/` | `notas_parcial_asignaciones` | Gestión asignaciones |
| `precargar-cache/` | `notas_parcial_precargar` | Precargar caché |
| `enviar-pdf-email/` | `notas_parcial_enviar_email` | Enviar PDF por correo |
| `marcar-revisado/` | `notas_parcial_marcar_revisado` | Guarda el estado *Revisado* del coordinador (persiste al recargar) |
| `comentario/` | `notas_parcial_comentario` | Guardar comentario (máx. 40 palabras / 600 caracteres) |

### Modelos

| Modelo | Descripción |
|--------|-------------|
| `NotaComentario` | Comentario de coordinador sobre nota |
| `AsignacionMaestro` | Asignación de maestro a grado/sección |
| `RevisionFinalizada` | Marca de revisión completada |

---

## Módulo: Calculadoras

Calculadoras utilitarias de uso interno.

### Plantillas (`calculadoras/templates/calculadoras/`)

| Template | Descripción |
|----------|-------------|
| `base_calculadoras.html` | Layout base |
| `dashboard.html` | Panel de acceso rápido a todas las calculadoras |
| `tiempo.html` | **ACTUALIZADO** — Calculadoras de tiempo: **Entre dos horas** (nueva), Horas→Días, Minutos→Horas, Fecha a Fecha |
| `divisas.html` | Conversión de divisas (USD/EUR/CHF → Lempira) |
| `almacenamiento.html` | Conversión de almacenamiento (MB→GB, etc.) |
| `ip.html` | Calculadora de subredes IP |

### Estáticos (`calculadoras/static/calculadoras/`)

| Archivo | Descripción |
|---------|-------------|
| `js/tiempo.js` | **ACTUALIZADO** — Añade calculadora "Entre dos horas": ingresa HH:MM inicio/fin, muestra resultado en "X horas Y minutos", horas decimales y minutos totales. Error si fin < inicio |
| `js/divisas.js` | Conversión de divisas con tasas de BD |
| `js/almacenamiento.js` | Conversión de almacenamiento |
| `js/ip.js` | Cálculo de subredes |

### URLs (`/calculadoras/`)

| Ruta | Nombre | Descripción |
|------|--------|-------------|
| `` | `calculadoras_dashboard` | Panel principal |
| `tiempo/` | `calculadoras_tiempo` | Calculadoras de tiempo |
| `divisas/` | `calculadoras_divisas` | Divisas |
| `almacenamiento/` | `calculadoras_almacenamiento` | Almacenamiento |
| `ip/` | `calculadoras_ip` | Subredes IP |
| `tasa/actualizar/` | `calculadoras_tasa_actualizar` | Actualizar tasa de cambio |

### Modelos

| Modelo | Descripción |
|--------|-------------|
| `TasaCambio` | Tasas de cambio (USD, EUR, CHF) actualizables manualmente o via API |

---

## Módulo: Inventario

| Plantilla | Descripción |
|-----------|-------------|
| `base_inventario.html` | Layout base |
| `dashboard.html` | Panel con conteos por categoría |
| `inventario_computadoras.html` | Listado de computadoras |
| `inventario_televisores.html` | Listado de televisores |
| `inventario_impresoras.html` | Listado de impresoras |
| `inventario_routers.html` | Listado de routers |
| `inventario_datashows.html` | Listado de datashows |
| `inventario_monitores.html` | Listado de monitores |
| `inventario_por_categoria.html` | Vista unificada por categoría |
| `inventario_registros.html` | Registro de movimientos |
| `item_pdf_template.html` | PDF de ficha de equipo |
| `edit_*.html` | Formularios de edición inline (x6 categorías) |

---

## Módulo: Enfermería

| Plantilla | Descripción |
|-----------|-------------|
| `base_enfermeria.html` | Layout base |
| `dashboard.html` | Panel principal |
| `atencion_form.html` | Registro de atención médica |
| `inventario_list.html` | Inventario de medicamentos |
| `medical_history.html` | Historial médico de alumnos |
| `directorio_telefonos.html` | Directorio con links WhatsApp (SQL Server) |
| `enviar_correo.html` | Enviar correo de atención |

---

## Módulo: Tickets — Soporte Técnico

| Plantilla | Descripción |
|-----------|-------------|
| `base_tickets.html` | Layout base (técnico) |
| `base_tickets_user.html` | Layout base (usuario) |
| `submit_ticket.html` | Crear ticket |
| `technician_dashboard.html` | Panel de técnicos |
| `ticket_comments_tech.html` | Chat del ticket (técnico) |
| `ticket_comments_user.html` | Chat del ticket (usuario) |
| `mis_tickets.html` | Mis tickets (usuario) |
| `email/email_notification.html` | Correo de notificación |

---

## Módulo: Finanzas Personales

Módulo de finanzas personales internas (categorías, transacciones, presupuestos, metas de ahorro, pendientes).

| Plantilla | Descripción |
|-----------|-------------|
| `index.html` | SPA de finanzas con panel lateral y gráficas |

---

## Módulo: Sponsors

Gestión de patrocinadores y padrinos institucionales.

**URLs:** `/sponsors/dashboard/` · `/sponsors/add/` · `/sponsors/list/` · `/sponsors/edit/<id>/`

---

## Módulo: Mantenimiento

Registro de mantenimientos preventivos/correctivos con generación de reportes PDF.

**URLs:** `/mantenimiento/` · `/mantenimiento/download/<id>/` · `/mantenimiento/<pk>/editar/` · `/mantenimiento/<pk>/eliminar/`

---

## Versionado y novedades

El sistema muestra su **versión en el pie de página** y una **ventana de novedades** que se abre **una vez por versión** para cada usuario.

- **Footer único (`templates/_footer.html`)** — incluido por todas las plantillas base. Una sola fila: copyright a la izquierda, `TechCare vX · Novedades` a la derecha. Es *sticky* por Flexbox (`body` en columna con `min-height:100vh`, `.page-body` con `flex:1`, `footer.tc-footer` con `margin-top:auto`); **no** usa `position:fixed/absolute`. Estilos en `static/css/responsive_global.css` (enlazado con `?v=N` para romper caché al cambiarlo).
- **Modal (`templates/_version_modal.html`)** — lo incluye el footer; su JS espera al evento `load` porque el footer se renderiza antes que los `<script>` de Bootstrap.

- **Fuente de datos:** `core/changelog.json` (`{version, entradas:[{version, fecha, commit, cambios[]}]}`). Lo lee `core/version.py`; lo expone el context processor `core.context_processors.version_context`.
- **Generación automática:** el comando `manage.py gen_changelog` toma los mensajes de commit nuevos (`git log`), **sube el build** (`6.0.1.2` → `6.0.1.3`) y agrega una entrada. Se dispara con el hook `.git/hooks/post-commit` (Apache/`www-data` **no** puede ejecutar git en este repo, por eso el hook corre como el dueño y la app solo **lee** el JSON).
- **Marcador de rango:** `.git/changelog_base` (local, no se commitea) guarda el último commit incluido; sobrevive a `git commit --amend`.
- **Fijar versión mayor manualmente:** `manage.py gen_changelog --set-version 6.1.0.0`.
- **"Visto" por usuario:** `PerfilUsuario.version_vista`; al cerrar el modal se marca vía `POST /core/api/version/visto/` (`marcar_version_vista`).

### Comando "actualízalo todo"

Al pedir *"actualiza todo"* el flujo es: (1) `manage.py check` · (2) actualizar `README.md` · (3) actualizar `AGENTS.md` (contexto del proyecto para agentes, **sin credenciales**) · (4) `git add` revisado + commit · (5) el hook regenera el changelog → `git commit --amend --no-edit` para incluirlo · (6) `git push`.

---

## Convenciones de código

### Templates
- Comentario de autoría: `{# <--- hecho por claude code: descripción #}` (nunca `<!--{# ... #}-->`)
- Variables Django → JS: usar `<div id="page-config" hidden data-*="{{ valor }}">` (nunca `<script>` inline con valores Django, excepto `window._PAGE` en casos heredados)
- Badges Tabler: `bg-blue-lt text-blue` · `bg-red-lt text-red` · `bg-orange-lt text-orange` · `bg-green-lt text-green` · `bg-purple-lt text-purple` · `bg-cyan-lt text-cyan`

### JavaScript
- Los archivos JS viven en `<app>/static/<app>/js/<nombre>.js`
- Deben copiarse también a `staticfiles/<app>/js/` con `sudo cp` (no hay `collectstatic` automático)
- Agregar `?v=N` al `<script src>` en el template al actualizar un JS (cache-bust del navegador)

### Archivos estáticos en producción
- Apache sirve desde `staticfiles/` (generada por `collectstatic`)
- Al editar un `.js` o `.css`, sincronizar manualmente:
```bash
sudo cp system_proyect/<app>/static/<app>/js/archivo.js system_proyect/staticfiles/<app>/js/archivo.js
```
- Luego agregar `?v=N` al tag `<script src>` o `<link href>` correspondiente

---

## Variables de entorno (`.env`)

```env
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False

# MySQL (base de datos principal)
DB_NAME=sponsors2
DB_USER=admin3
DB_PASSWORD=...
DB_HOST=192.168.10.6
DB_PORT=3306

# SQL Server — datos de alumnos (Test2)
MSSQL_TEST2_DB_NAME=...
MSSQL_TEST2_DB_USER=...
MSSQL_TEST2_DB_PASSWORD=...
MSSQL_TEST2_DB_HOST=...
MSSQL_TEST2_DB_PORT=1433

# SQL Server — módulo Reloj (zkbiotime)
MSSQL_ZKBIO_DB_NAME=...
MSSQL_ZKBIO_DB_USER=...
MSSQL_ZKBIO_DB_PASSWORD=...
MSSQL_ZKBIO_DB_HOST=...
MSSQL_ZKBIO_DB_PORT=14332

# Base academica REAL: de donde lee "Notas Mitad de Parcial".
# Se migra area por area; requiere permisos de admin2 en AdmonANASQL.
MSSQL_REAL_DB_NAME=AdmonANASQL
NOTAS_PARCIAL_DB=academico_real
NOTAS_PARCIAL_AREAS_REAL=bl,colegio_bl,colegio,bachillerato

# Correo (Gmail SMTP)
EMAIL_HOST_USER=techcare.app2024@gmail.com
EMAIL_HOST_PASSWORD=...
```

---

## Comandos frecuentes

```bash
# Conectar al servidor
ssh admin2@192.168.10.6

# Activar entorno virtual
cd techcare_project
source venv/bin/activate
cd system_proyect

# Reiniciar Apache (aplica cambios Python y templates)
echo 'PASSWORD' | sudo -S systemctl restart apache2

# Sincronizar archivo estático sin collectstatic
sudo cp reloj/static/reloj/js/archivo.js staticfiles/reloj/js/archivo.js

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Shell interactiva
python manage.py shell

# Verificar configuración
python manage.py check

# Crear superusuario
python manage.py createsuperuser

# Cambiar la contraseña de un usuario y quitarle el bloqueo por intentos fallidos
python manage.py resetclave usuario@ana-hn.org              # pide la clave por teclado
python manage.py resetclave usuario@ana-hn.org --solo-desbloquear

# Precargar caché de notas parciales
python manage.py shell -c "from notas_parcial.views import _precargar_notas; _precargar_notas()"
```

---

## Despliegue

El proyecto corre con **Apache + mod_wsgi** en producción.

```bash
# Recargar código Python (sin reiniciar Apache completo)
touch system_proyect/wsgi.py

# Reinicio completo (necesario para cambios en settings, middleware, etc.)
sudo systemctl restart apache2

# Actualizar archivo estático en producción
sudo cp <app>/static/<path>/archivo.js staticfiles/<path>/archivo.js
# Agregar ?v=N al <script src> en el template correspondiente
```

---

*© 2025 Soporte Técnico – Asociación Nuevo Amanecer*
