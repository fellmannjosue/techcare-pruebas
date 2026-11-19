# TechCare – Sistema de Gestión Institucional

Sistema web desarrollado en Django para la **Asociación Nuevo Amanecer (ANA)**. Centraliza la gestión de tickets, asistencia, conducta estudiantil, inventario, citas, enfermería, agendas docentes, notas parciales, finanzas y calculadoras internas.

- **Versión del sistema:** 7.10.0 (ver *Novedades* en el pie de página de la app)
- **URL de producción:** https://servicios.ana-hn.org:437
- **Servidor:** Apache + mod_wsgi
- **Stack:** Django 6.0.5 · Python 3.13.3 · MySQL + SQL Server
- **UI:** Tabler UI v1.0.0-beta19 + Tabler Icons Webfont v3.11.0
- **Admin:** Unfold Admin Theme

---

## Novedades recientes

> El detalle por versión se genera automáticamente en `core/changelog.json` (comando `manage.py gen_changelog`, disparado por el hook `post-commit`) y se muestra a cada usuario en una ventana la primera vez que entra tras un cambio de versión. Ver *"Versionado y novedades"* más abajo.

### v8.2.0 — Reloj (año laboral, horas trabajadas manuales, fecha de corte), reportes de Mantenimiento e Inventario, laboratorios, Seguridad por área y bloqueo por formulario según el área (17-nov-2026)

- **Reloj · Cálculo Compensatorio**: año laboral por aniversario de ingreso; días del cierre ANA = horas ÷ 8; los permisos «Compensatorio» ingresados suman a las horas trabajadas y el receso se resta de ellas; **horas trabajadas a mano** para quien no marca (ventana del lápiz, `CompensatorioTrabajadasManual`, hoy Santos); **«Fecha de corte»** editable junto a la fecha de ingreso en el tab de vacaciones (`CompensatorioFechaCorte`, mig reloj 0071, años ≥ 2000); se quitó el selector «Año» (usa el año actual o `?anio=`).
- **Mantenimiento**: reporte PDF/Excel de **Mantenimiento de computadoras** (falla, estado, solución y columna Fotos con «FALTA» en rojo); fichas de **laboratorio** en Entrega/Recogida con la lista de computadoras del lab y edición que conserva el laboratorio; hasta **10 fotos** en fichas de laboratorio (5 en las demás).
- **Inventario General**: pestañas por **tipo** con conteo, asignar tipo a varios artículos a la vez y **Reporte general** PDF/Excel agrupado por tipo (resumen tipo × estado + una tabla por tipo, firma de la auditora).
- **Seguridad · lista de correos permitidos**: clasificación por **área** (Dirección, Coordinación BL, Coordinación Col, BL, Col, CFP, Admin, Pruebas, Otros; automática por grupos o elegida a mano, campo `CorreoInstitucional.area`, mig accounts 0020) con filtro y conteos, y **toggle «Todos»** para habilitar/deshabilitar los visibles.
- **Bloqueo por formulario**: con un área concreta (Bilingüe/Colegio), quien pertenece a dos áreas solo queda bloqueado en lo del área elegida (`core.middleware._peticion_de_otra_area`: URL, parámetro `area` y área del modo maestro de Agendas).
- **Configuración → Sistema** (superusuario): **Respaldo y limpieza de módulos** (ZIP con JSON + archivos y borrado con candados, `core/limpieza_modulos.py`) y **Modo sin conexión (beta)** (`core/offline_beta.py`, constance `OFFLINE_BETA`).
- Formularios «Registrar» en ventana: el pie (Cancelar/Registrar) siempre visible (`tc_embed.css`).

### v8.1.0 — Rol Auditoría (solo lectura), Directorio único, manuales y documentación en PDF, y 2FA más claro (10-nov-2026)

- **Rol Auditoría** (grupo `auditoria`, cuenta `auditoria@ana-hn.org`): ve TechCare como el superusuario pero en **solo lectura**. `core/auditoria.py::AuditoriaMiddleware` lo trata como superusuario solo en memoria, corre cada GET en una transacción que se revierte y rechaza los envíos (403) salvo en los programas habilitados en **Configuración → Permisos → Rol Auditoría** (constance `AUDITORIA_EDITAR`). En pantalla los campos quedan deshabilitados (`core/js/auditoria.js`) y sale el aviso «Modo auditoría · solo lectura». Nunca entra a `/admin/`, «Iniciar sesión como», la pantalla del rol ni el Directorio. Bitácora en `logs/seguridad.log` (`auditoria_vista`, `auditoria_edicion`, `auditoria_bloqueo`). Pruebas: `core/tests_auditoria.py`.
- **Un solo Directorio de teléfonos**: `/conducta/directorio/` (alcance por grupo: superusuario y Enfermería = todo, coordinador BL = BL, coordinador Colegio = Colegio + Bachillerato). `/enfermeria/directorio/` redirige allí y todos los enlaces apuntan al único; «Volver» según quién entra.
- **Documentación**: descarga en **PDF** de cada documento o de una carpeta entera (WeasyPrint, CSS del disco), índice en **acordeón**, **Manual de usuario** y **Manual técnico** (`docs/manuales/`). Los planes y políticas de `docs/seguridad/` quedaron aprobados.
- **Verificación en dos pasos**: correo del código con diseño (código grande en el asunto, aviso «¿No fuiste tú?» con fecha). Arreglo: las peticiones en segundo plano ya no reciben la pantalla del código (respuesta 401 en JSON) ni cambian el destino después de verificar.

### v8.0.1 — Seguridad (revisión ISO 27001/COBIT), «Recordar mis datos», Registrar en ventana y programas por aplicación (09-nov-2026)

- **Login**: casilla **«Recordar mis datos»** (`accounts/js/recordar_login.js`). Límite de **20 intentos fallidos por IP pública en 15 min** (las IP internas no cuentan: casi todo llega por el gateway); el superusuario recibe esperas de 1 min cada 3 fallos, nunca el bloqueo total.
- **Recuperar contraseña con límite** (`accounts/recuperacion.py`: 3 por correo/hora, 10 por IP pública) y enlace válido 24 h.
- **Bitácora de seguridad** (`core/seguridad_eventos.py` → `logs/seguridad.log`, JSON): inicios de sesión, fallos, bloqueos, cambios de privilegios/grupos/contraseñas y ajustes de constance, sin guardar secretos. Errores 500 en `logs/errores.log`.
- **Evidencias de conducta** solo por `/conducta/evidencia/<pk>/ver/` con permiso del reporte; archivos nuevos con nombre uuid. Pendiente: cerrar `media/evidencias` en Apache (`docs/seguridad/infra/apache_media.conf`).
- Descargas (PDF/Excel/ZIP/adjuntos) con `Cache-Control: private, no-store` (`DescargasPrivadasMiddleware`); arreglos de XSS en Ruteo BL y el admin de Conducta.
- **Configuración → Documentación** (solo superusuario, `accounts/views_documentacion.py`): visor de `docs/` con el diagnóstico, matrices de riesgos y trazabilidad, guías de despliegue/respaldo/incidentes, planes de seguridad, continuidad y capacitación, proceso de alta de usuarios y borradores de políticas (acceso, contraseñas, información sensible, cambios, desarrollo). **No es una certificación.**
- **Programas por aplicación** (`core/canales.py`, constance `PROGRAMAS_POR_CANAL`): qué programas ofrece la Web, el .exe y la APK, con «Probar como» para el superusuario. Endpoint público `novedades.json` para la ventana de novedades del .exe.
- **Control y Servicio Técnico**: los formularios de «＋ Registrar» se abren dentro de la ventana (`?embed=1`, `tc_embed.js`). Inventario General: la categoría nueva se guarda sola al salir del campo.
- Pruebas aisladas: `settings_test.py` + `core/tests_seguridad.py` (27 pruebas con datos sintéticos).

### v7.80.1 — Período Escolar general, Dashboard del Coordinador por estados, pantallas nuevas del maestro e Ingreso de Notas en planilla (06-nov-2026)

- **Período Escolar general** (`/conducta/periodo-escolar/`, solo superusuario; `conducta/periodo_modulos.py`): un período por área con **7 interruptores** (Reportes informativos, conductuales, Agendas, Notas mitad de parcial, Salidas al Baño, Progress Report, Convocatoria/Tutorías) y línea de tiempo del año. Al cerrar un módulo se bloquea la escritura en ese módulo (`respuesta_si_cerrado`). **Salidas al Baño ya no tiene período propio** (usa el general, módulo `sal`). Migs conducta 0030 (`modulos`) y 0031 (estado «revisando» → «enviado»).
- **Dashboard del Coordinador (diseño B, lista + detalle)** en Académicos, Conductuales y Progress (Bilingüe y Colegio): estados **Enviado → Revisado → Aprobado** con botones rápidos (`reporte/estado/`).
- **Pantallas del maestro**: Historial de Reportes en línea de tiempo, Reporte Informativo con tarjeta del alumno y sus reportes recientes, Reporte Conductual con semáforo y vista previa.
- **Mantenimiento Mecánico**: para quien solo tiene ese módulo, su hub es el Panel Principal.
- **Ingreso de Notas (diseños A/B, `planilla.js`)**: Exámenes y Hábitos con promedios por alumno y del grupo; Tareas con las tareas del día en columnas (la Tarea N se bloquea hasta tener la N−1); Asistencias en matriz por fecha (5/10 días) con modal para quitar una falta. **Solo enteros**: exámenes 1–100, tareas y hábitos 1–10 (también validado en el servidor). Si el servidor rechaza una casilla, lo escrito queda en rojo con el motivo (ya no se borra). Arreglado el fallo intermitente al crear la nota de un parcial nuevo (`Fecha` smalldatetime redondeaba al minuto siguiente y chocaba con el CHECK `fecha<=getdate()`).

### v7.10.0 — Seguridad en todo el sistema: sesión obligatoria, archivos protegidos y permisos por área (auditoría y reparación del 05-nov-2026)

- **Sesión obligatoria en todo el sistema** (`core.middleware.TechCareLoginRequiredMiddleware`): ninguna pantalla queda pública por olvido; las públicas a propósito llevan `@login_not_required` (login, PWA, firma remota por token, formulario de tickets para el desbloqueo del login, enlace de Google del reloj).
- **Archivos subidos protegidos**: adjuntos de tickets y de Desarrollo, PDF firmados y fotos de Mantenimiento, fotos de Cámaras y de Mantenimiento Mecánico, planos de Red, imágenes de Agendas y el ruteo de Bilingüe ya no se abren por URL directa: salen por pantallas que revisan el permiso. En `/media/` PHP está apagado y los `.html/.svg` se descargan en vez de abrirse. Pillow ya no abre EPS/PostScript.
- **Permisos por área real del usuario** (no por lo que manda el navegador) en Conducta, Notas Mitad de Parcial, Ingresos de Notas, Agendas, Salidas al Baño, CFP Notas, Enfermería y Reloj; cada quien solo ve y modifica lo de su área.
- **Salidas al Baño**: cada coordinador en su ámbito; **Salidas CFP queda oculto** (Configuración → Seguridad → Programas activos, clave `salidas_cfp`).
- **Agendas**: áreas desde los grupos reales; fotos validadas (PNG/JPG/GIF/WEBP, también fotos HDR de celular); «Publicar en Moodle» solo para quien puede publicar.
- **Cámaras**: el enlace de firma remota caduca a los 7 días y es de un solo uso; la vista nueva `/inventario-camaras/app/` queda en pausa (la API es de solo lectura).
- **Mantenimiento Mecánico**: «Configurar», «Saldo inicial» y «Ajuste» solo para el superusuario; nadie borra registros, tampoco por `/admin/`.
- **Red**: las contraseñas de los equipos se ven solo con el ojo (y queda en la auditoría). **No cambiar nunca el `SECRET_KEY`**: esas contraseñas dejarían de leerse.
- **Ingresos de Notas**: «Trajo Excusa» se puede registrar por adelantado; un parcial cerrado en Notas Mitad de Parcial no se puede modificar.
- **Login**: el ticket de desbloqueo a los 5 intentos ya muestra el usuario correcto.
- Inventario: los botones Eliminar vuelven a funcionar (con confirmación) y el Asset ID se valida. Tickets: adjuntos con lista blanca de tipos y límite de envíos del formulario público.
- Informe completo de la auditoría (95 hallazgos, 82 cerrados, los 20 críticos cerrados) y reglas nuevas en `AGENTS.md` → sección «Seguridad · auditoría de 14 agentes…».

### v7.9.6 — Solicitud de DataShow con acceso por grupo, diésel en galones + décimas y límite de la Asignación en Progress Report (release menor)

> Release **menor** (novedades solo al superusuario). 34 archivos.

- **📽️ Solicitud de DataShow (módulo nuevo en producción).** Calendario de reservas de DataShow que **solo ven y usan los usuarios del grupo `datashow`** (o el superusuario); nadie más, aunque entre por la URL. Soporte sigue autorizando cada reserva. Nueva ventana **Configuración → Módulos → "Acceso a DataShow"** (solo superusuario): lista de usuarios con *checkbox*, buscador, "marcar/quitar visibles" y contador para asignar el grupo (flicona, mcarias, bespino, acruz…). Tarjeta en el Panel (Soporte y TI), enlace en el menú y en el dashboard.
- **⛽ Mantenimiento Mecánico · diésel en galones + décimas.** El formulario de "Nueva entrega" de **diésel** ahora registra la cantidad como **galones enteros + décimas** (ej. "10 galones 4/10" = 10.4 gal), con un selector de 0/10 a 9/10 y la muestra del total; el saldo y los reportes siguen en galones. Los demás insumos no cambian.
- **✏️ Progress Report (conducta Bilingüe) · Asignación acotada.** Los campos de **Asignación** (principal y asociadas, en crear y en el editor) se limitan a **20 caracteres**; al llegar al límite aparece el aviso *"Si desea escribir más, póngalo en comentarios."* Los campos de Comentario y Comentario General conservan su longitud.

### v7.9.1 — Préstamo de equipo, panel admin reorganizado, Código del sistema y correcciones en Mantenimiento (release menor)

> Release **menor** (novedades solo al superusuario). 35 archivos.

- **🔁 Mantenimiento · Préstamo de equipo (nuevo).** Ficha `ANAMAESPRE-` conectada al inventario: solicitante, cargo, área, motivo, fechas de entrega y devolución, dónde se usará, si sale de la institución y accesorios. PDF tipo carta (Tegucigalpa) con **4 firmas**: Solicitante y Dirección Ejecutiva a mano, Soporte Técnico y Auditoría fijas. Se sube la solicitud **firmada** (PDF) y el equipo queda *Prestado*; marca *vencido* si pasó la fecha de devolución. Página propia, tarjeta en el hub, reportes PDF/Excel.
- **🛠️ Panel admin (Unfold) reorganizado.** Menú lateral por programa (Soporte y TI · Académico · Administración · Sistema) armado solo desde los modelos registrados, con contadores (tickets abiertos, préstamos vencidos); inicio con indicadores (tickets, préstamos, agendas de la semana, Moodle), módulos por programa y últimos cambios de la auditoría; colores índigo de TechCare; listas mejoradas de Tickets, Fichas y Agendas.
- **📋 Todo en el admin.** Los modelos sin `admin.py` (77) se registran solos (`core/admin_auto.py`); bitácoras en solo lectura y campos cifrados ocultos.
- **📊 Configuración → Código del sistema.** Líneas por app (views, models, forms, admin, otros .py, HTML, CSS, JS), archivos y peso, de la más grande a la más pequeña; se recalcula sola al cambiar un archivo.
- **🐞 Correcciones.** Editar un Control que generó un cambio de equipo / reasignación ya no exige las preguntas (no dejaba agregar fotos); editar una ficha de **cambio de equipo** ya no borra el equipo anterior/nuevo (se recuperó ANAMAESCAM-001); Agendas reconoce el grupo `coordinador_colegio`.

### v7.9.0 — Agendas: Crear agenda y editor de diseño (vista previa, ajustes y PNG), publicación en Moodle por grado-sección y Mantenimiento Mecánico en litros

> Release **general** (novedades a todos). 51 archivos.

- **🗓️ Agendas · Crear agenda.** Pestaña nueva en el Dashboard del coordinador: elige la semana (se ajusta a lunes–viernes) y los grados, y se crea la agenda **vacía** de cada uno para que los maestros la llenen. Nunca se duplica (marca "ya creada").
- **🎨 Agendas · Editor de diseño.** Botón *Diseño* en cada agenda: vista previa igual al **PowerPoint de BL** y al **Word de Colegio**, con tamaño de letra general y por celda, alto de filas o *ajustar a la hoja*, ancho de columnas, ocultar clases vacías y corrección de textos en la misma hoja; se guarda solo y avisa si la tabla no cabe. **Descargar PNG** en alta resolución, que además queda como **imagen final** de la agenda. El PowerPoint y el Word salen con los mismos ajustes (y el PowerPoint vuelve a traer el fondo).
- **☁️ Agendas · Publicar en Moodle.** Botón de la nube en cada agenda: los cursos de Moodle agrupados por grado-sección (marcar el grado = todas sus clases, buscador), con el grado de la agenda ya marcado; usa la imagen final y publica curso por curso con avance. Plugin propio `local_techcareagenda` instalado en el Moodle de ANA.
- **👥 Agendas por área.** Quien da clases en BL y en Colegio ve las dos áreas; cada coordinador, solo las que coordina.
- **⛽ Mantenimiento Mecánico.** Gasolina y diésel se **compran en litros**: el formulario convierte a galones (el sistema sigue en galones). Aceites y coolant: **lectura aproximada del barril** (Lleno · ¾ · ½ · ¼ · Casi vacío · Vacío + barriles llenos) que se compara con el saldo calculado, sin cambiarlo.

### v7.8.1 — Inventario General, maestro guía en el PDF de notas, historial de Salidas al baño, directorio de Enfermería y login renovado (release menor)

> Release **menor** (novedades solo al superusuario). 34 archivos.

- **📦 Inventario General (nuevo).** Código automático `ANAGEN-0001`, **área** (Administración, Bilingüe, Colegio, Vocacional) y **categoría por área agregable** desde el formulario, descripción, ubicación, estado, foto (se reduce sola) y **comentario de la auditora** (solo Yeny Lagos o el superusuario). Filtro por área y su categoría, ficha PDF por artículo con la **firma fija de la auditora**, fichas de todos y Excel respetando el filtro. En el menú (Inventario → Inventario General) y en el hub de Servicio Técnico.
- **📊 Notas mitad de parcial.** **Maestro guía** por grado-sección y año (botón en la pantalla del coordinador); el PDF lleva su nombre sobre la línea "Firma del Maestro Guía". Un parcial cerrado ya no aparece ni se abre en *Mis Reportes* para nadie (coordinación lo maneja desde su pantalla).
- **🚻 Salidas al baño · Historial.** Pestaña nueva con filtros (período, fechas, área, grado, semáforo, quién registró, búsqueda, sin regreso), resumen, top 10 de alumnos y Excel. Coordinación ve todo; el maestro, solo lo que registró.
- **🩺 Enfermería.** El directorio de teléfonos salía vacío para la cuenta de Enfermería; ahora muestra a todos los alumnos (797).
- **🎨 Acceso.** El login, la selección de rol y las pantallas de recuperar contraseña recuperan el degradado azul→violeta (el tema lo tapaba y el título blanco no se leía). La pantalla de bienvenida es **75 % más rápida** (~5 s), con la paleta nueva, y se cierra con un clic o Esc.

### v7.8.0.001 — Menú en acordeón para todos los usuarios y tarjeta de "Sumar horas" (release menor)

> Release **menor** (novedades solo al superusuario). 7 archivos.

- **📋 Menú lateral en acordeón (corrección).** A los usuarios que no son superusuario el menú les seguía saliendo todo abierto: la clase `sidebar-static` (de un diseño anterior) forzaba los grupos abiertos y quitaba el clic de las cabeceras. Se retiró; ahora los grupos empiezan cerrados, se abren con clic y uno a la vez. El superusuario conserva su menú de siempre.
- **🧮 Calculadoras.** El ícono de la tarjeta *Sumar horas* se veía diminuto (usaba `icon-lg`, que no aplica a íconos de fuente); ahora tiene el mismo tamaño que las demás.

### v7.8.0 — Mantenimiento Mecánico (combustibles, aceites y vehículos), cierre de parciales en Notas, menú en acordeón e "Iniciar sesión como"

> Release **general** (novedades a todos). 59 archivos.

- **🛢️ Mantenimiento Mecánico (módulo nuevo).** Control de gasolina, diésel (tanque de 715 gal), aceite 40, aceite 50, aceite hidráulico y coolant (barriles de 55 gal): entregas con correlativo, entradas (compra, llenado, barril nuevo, ajuste), saldo calculado (nunca guardado), aviso de saldo bajo, ficha PDF por entrega, reporte tabla y general en PDF y Excel. Registra el grupo `mantenimiento_mecanico`; la auditoría (`mantenimiento_mecanico_lectura`) ve y comenta; editar es solo del superusuario y eliminar no existe.
- **🚗 Mantenimiento de vehículos** (dentro del mismo módulo). Formato de Access: flota con km actual, próximo mantenimiento y cuánto falta (semáforo), hoja de tareas (qué toca según el intervalo de cada tarea) para imprimir, historial de mantenimientos 2026 y lecturas de km. **Formulario para registrar vehículos** (marca, tipo, color, año, placa, chasis, motor, cuenta diésel, intervalo, km/millas/horas, tractor). El **diésel se carga por vehículo** (registra el km y la ficha del vehículo muestra sus cargas). **Aviso** al grupo `vehiculos_alertas` cuando faltan 100 o menos y cuando se vence. Grupos `vehiculos_registro`, `vehiculos_kilometraje`, `vehiculos_auditoria`.
- **🧭 Un solo sub-dashboard** en `/mantenimiento-mecanico/` con los saldos de cada insumo y el estado de la flota; una sola tarjeta, un solo grupo de menú y un solo ícono en el riel.
- **📊 Notas mitad de parcial.** Botones **Revocar permisos** y **Fecha de cierre** por grado-sección y **Cerrar Parcial N** (el parcial desaparece de *Mis Reportes* de los maestros y se bloquea la escritura en el servidor; se puede reabrir). Parcial 3/2026 cerrado en las 4 áreas y oculto en *Asignaciones de Maestros* (botón *Ver parciales cerrados*). Al pasar de alumno con *Siguiente* la pantalla ya no sube a las tarjetas. El superusuario ya no recibe el aviso emergente de notas.
- **🖥️ Mantenimiento · Reasignación de computadora.** La misma computadora pasa del maestro A al maestro B desde el Control de equipo (ficha `ANAMAESREA-`, inventario actualizado, PDF con 3 firmas).
- **📋 Menú y Panel.** El menú lateral funciona en **acordeón** (grupos cerrados, se abren con clic, uno a la vez). Tarjetas nuevas en el Panel: **Control y Servicio Técnico**, **CFP** y **Gestión de Desarrollo** para quien las tiene en el menú.
- **🔐 Iniciar sesión como** (solo superusuario, como el *Log in as* de Moodle): entra a la cuenta de un usuario para ver lo que él ve; bitácora de cada entrada y barra *Volver a mi cuenta*.
- **🔧 Otros.** Reloj: permiso de ajuste del bono para yzavala, ylagos y glorenzo. Red: campo *Texto* en la edición múltiple del plano. Coordinador: *Menú Principal* vuelve a su lanzador. La lista desplegable de la cabecera ya no se recorta.

### v7.7.1 — Diseño Horizon Split en todo el sistema, Tickets ↔ Gestión de Desarrollo, calculadoras de tiempo por grupo, refresco de notas parciales y ajustes de Reloj (release menor)

> Release **menor** (novedades solo al superusuario). 49 archivos.

- **🎨 Diseño Horizon Split (todo el sistema).** Nuevo shell elegido entre 5 propuestas: **riel de íconos** a la izquierda (un ícono por módulo, generado desde el menú de cada rol; el superusuario suma accesos directos a Tickets, Desarrollo, Servicio Técnico, Red, Reloj, Contabilidad y Académico), **panel contextual** con buscador que filtra el menú, ítem activo resaltado y grupo abierto automáticamente, y **cabecera degradada azul→violeta** en todas las páginas. Panel Principal del superusuario rediseñado: saludo con fecha, KPIs flotando sobre la cabecera, gráficas y los 13 módulos en cuadrícula con pestañas *Todos / Soporte / Académico / Administración*. Login y selección de rol con la misma paleta. En móvil el riel se oculta y queda el menú colapsable.
- **🎫🧩 Tickets ↔ Gestión de Desarrollo.** Un requerimiento puede abrir un ticket enlazado (casilla al crear, botón en el detalle) y un ticket se puede convertir en requerimiento desde el chat del técnico. El requerimiento manda: cada cambio de estado o responsable actualiza el ticket, deja un comentario del sistema en el chat y envía el correo; *Producción* resuelve el ticket. Esos tickets van **sin SLA** (no suenan en la alerta) y con distintivo "Desarrollo".
- **💬 Chat de tickets.** Los mensajes del sistema (pausas, reanudaciones, cambios de estado) se muestran como burbujas naranjas diferenciadas.
- **🧮 Calculadoras de tiempo.** Nuevo grupo `calculadoras_tiempo`: ve solo las 5 calculadoras de tiempo (sumar horas, entre dos horas, horas→días, fecha a fecha, minutos→horas) y su tarjeta en el panel; las demás siguen solo para el superusuario.
- **⏱️ Reloj · Cálculo compensatorio.** *Control adeudados* y *Adeudados 2* ya no suman los 3 días de permiso ni muestran horas de más (viven solo en el tab 4); Gabriela García entra al tab 4. Feriado Morazánico a 20 h y Cierre de Diciembre a 64 h (56 h para Yerisely Zavala).
- **📊 Notas mitad de parcial.** Caché de 10 min (antes 30) y botón **Actualizar datos del sistema académico** para el coordinador (en Bilingüe solo David Ruiz y Catherine Varela; en Colegio y Bachillerato todos los coordinadores). Asignaciones de BL y Colegio BL del 3.º parcial copiadas al 4.º.
- **🛡️ Auditoría.** Selector agrupado por programa (una opción por programa con todas sus tablas) e historial nuevo para las 10 tablas de CFP (notas y contabilidad CFP).
- **🔧 Correcciones.** El comentario del Reporte de Permisos mostraba `\u000D\u000A` literal (`|escapejs` dentro de `data-*`, retirado en 5 plantillas); cierre de sesión por inactividad aplicado también a las pantallas de Salidas al baño; en Control de equipo los interruptores *Caso especial* / *Cambio de equipo* aparecen también al editar.

### v7.7.0 — Control y Servicio Técnico (Inventario + Mantenimiento unidos), fichas por página, casos especiales y cambio de equipo, núcleo contable, capa responsiva y cierre de sesión por inactividad

> Release **general** (novedades a todos). 70 archivos.

- **🎧 Control y Servicio Técnico.** Inventario y Mantenimiento se unen en un solo hub (`/servicio-tecnico/`): KPIs, tiles de los 6 tipos de equipo y de los 8 tipos de ficha con conteo, alertas reales (tinta baja, controles en mal estado, computadoras sin control, fichas pendientes) y actividad reciente. Una sola tarjeta en Soporte y TI, en el menú y en el sidebar; los "Volver al panel" de ambos módulos regresan al hub. El *Panel de Inventario* de 8 tiles se retiró (`/inventario/` redirige al hub).
- **🔧 Fichas de Mantenimiento por página.** Cada tipo (Computadoras, Impresoras, Control de equipos, Inspecciones, Entregas, Recogidas, Casos especiales, Cambios de equipo) es una **página individual** con su título, sus KPIs, su tabla y su botón *Nuevo* fijo al tipo; usan la base común del sistema (sidebar, tema, responsivo). Rediseño visual del módulo (KPIs con acento, tabla a todo el ancho, buscador y paginación integrados).
- **🔁 Caso especial y Cambio de equipo.** Desde un Control de equipo (al crear y al editar) dos interruptores excluyentes: *Caso especial* reemplaza las preguntas por el checklist de recogida y crea la ficha `ANAMAESCE-`; *Cambio de equipo* muestra el equipo anterior y abre el formulario de la computadora para registrar el nuevo (modelo, serie, IP), crea la ficha `ANAMAESCAM-` con el antes/después y **actualiza el inventario** (mismo Asset ID, mismo maestro; nota en observaciones e historial). Comentario del técnico en Entrega/Recogida/Caso especial, en tabla, ficha PDF y reportes.
- **💼 Contabilidad · núcleo contable.** Catálogo de cuentas (con catálogo base de 150 cuentas para ONG hondureña, cargable sobre catálogo vacío), centros de costo, períodos (abrir/cerrar), partidas de partida doble con líneas dinámicas y cuadre en vivo (borrador → contabilizada → anulada, número `P-AAAA-0001` al contabilizar), mayor por cuenta, balanza de comprobación, balance general, estado de resultados y libro diario, todos con Excel. Grupo `contabilidad_contable`. (Pantallas provisionales: se rediseñarán al estilo QuickBooks.)
- **📱 Capa responsiva global.** Tablas con scroll en móvil, retícula sin breakpoint apilada, DataTables con controles apilados, cabecera con botones debajo del título, modales a pantalla completa en tablet, inputs a 16 px (sin zoom en iPhone) y menú lateral con scroll. En teléfonos, todo adjunto de imágenes ofrece **Tomar foto** (cámara) y **Galería**.
- **🔒 Cierre de sesión por inactividad.** Ahora también del lado del servidor: la sesión caduca sola si no hay actividad en el tiempo configurado (constance `SESION_INACTIVIDAD_MIN`, 4 h por defecto) aunque se cierre el navegador; antes la cookie duraba un año. Salidas al baño incluye el aviso.
- **📊 Notas mitad de parcial.** Habilitado el **4.º parcial**; las asignaciones de Colegio y Bachillerato del 3.º se copiaron al 4.º.
- **🌐 Red.** Switches corregidos según CDP (SwitchC1200-DTC-01, SwitchSG250-DTC-02 nuevo en .59, SF350-AULA22, SF350-LabBL, SF350 Casa Azul por confirmar), 43 puertos y 6 enlaces documentados.

### v7.6.5 — Red (Lista de IPs actuales), Reloj (compensatorio 47 min/día en 4 tabs), Mantenimiento (Entrega y Recogida de equipo) e Inventario compacto con PDF (release menor)

> Release **menor** (novedades solo al superusuario). La versión sí es general en el pie. **Aún falta** para una versión general (49 archivos < 50).

- **🌐 Red · Lista de IPs actuales.** Nueva pantalla del ANA Network Manager: inventario de las IPs en uso agrupado por categoría de equipo, con autoguardado por fila, filtro rápido y auditoría. Cada fila lleva IP actual, categoría, **VLAN implementada**, descripción, casilla *¿Tiene usuario?*, usuario y **contraseña cifrada** (solo la ve quien administra la red). La **IP asignada en la VLAN** se elige del IPAM con su nombre; si la VLAN está **en producción** se asigna sola la primera libre.
- **⏰ Reloj · Compensatorio de 47 min/día.** Cálculo Compensatorio cambia "Compensatorio por vacaciones" y "Tiempo diario" por **4 tabs**: *Vacaciones*, *Tiempo hecho y deuda*, *Cierre* (47 min por día hábil del 1-feb al 30-nov, matrícula 2026 del 30-nov al 18-dic a 12 min; descuenta lo ya hecho y da la **fecha en que termina contando desde hoy**) y *Con 3 días de permiso* (horas hechas, tomado de los 3 días y lo que le resta por tomar, como dato aparte). Editables: vacación acumulada, saldo para gastar, días que necesita, tiempo extra, tiempo tomado y tomado de los 3 días. Botón **"Pruebas"** en el panel de Reloj con su propio permiso.
- **🔧 Mantenimiento · Entrega y Recogida de equipo.** Dos tipos nuevos con numeración, pestaña, edición y ficha PDF propias: datos del equipo + lista de lo entregado o recibido (equipo, mouse y teclado, televisor indicando cuál, control con batería), firma elegida de la lista de maestros y fecha y hora. Reportes **PDF y Excel** en las pestañas Inspecciones, Entregas y Recogidas.
- **📦 Inventario.** En las seis tablas el detalle del equipo sale al pasar el mouse por **Modelo** y las tablas quedan compactas (el buscador sigue encontrando por serie, asignado o IP). En *Registros de inventario* se repararon los botones Todos / General / Lab BL / Lab COL / Lab CFP y se agregó **Descargar PDF** en las seis pestañas; en Computadoras, PDF y Excel exportan lo filtrado.
- **Agendas y Notas.** Un coordinador que también es maestro abre desde su tarjeta la ventana de crear agenda (no la de coordinador) y tiene "Mis notas" por área en el sidebar.

### v7.6.4 — CFP Contabilidad (planilla con monto manual, partidas reubicadas, PDFs en legal), Reloj (Compensatorio por vacaciones + Tiempo diario) y Programas ocultos en Seguridad (release menor)

> Release **menor** (novedades solo al superusuario). La versión sí es general en el pie. **Aún falta** para una versión general (31 archivos < 50).

- **⏰ Reloj · Cálculo Compensatorio: dos tabs nuevos.** **"Compensatorio por vacaciones"** (Saldo = Derecho − Vacación acumulada; Días que necesita = días no laborables ANA; Total = necesita + permisos extras; Días que debe compensar = Total − Saldo; y su equivalente en horas × 8.8) y **"Tiempo diario"** (min/día = deuda × 8.8 h ÷ días hábiles del periodo **1-feb → 26-nov**, configurable por año; con las mismas columnas y modales de *Adeudados 2*). *Vacación acumulada* y *permisos extras* editables por empleado. El *Tiempo tomado* = permiso compensatorio + tomado manual + receso, igual en todos los tabs.
- **🏫 CFP · Planilla administrativa con monto manual.** El monto de cada persona se escribe a mano (el "Disponible para la planilla" = 20% − capturados queda como referencia, con aviso *cuadra / faltan / se pasa*). Nuevo catálogo **"Personas por cargo"** (admin): al elegir el cargo se cargan solos el nombre y el DNI (consulta en vivo, sin recargar) y *Agregar persona* trae al siguiente cargo pendiente.
- **CFP · Partidas reubicadas.** *Seguro de Accidentes Personales (participantes)* pasó a **Materia Prima y Mantenimiento**; *Papel* y *Marcadores* pasaron a **Administración** (capturados); nuevas casillas **Gastos y viáticos** (Personal) y **Mantenimiento** (Materia Prima). Migración de datos que renombra las claves ya guardadas.
- **CFP · PDFs en papel legal.** La **planilla** ahora sale en legal, con 17 líneas numeradas para firmar y el bloque de firmas fijo al pie; el **informe contable** llena la hoja (se quitó el hueco grande al pie).
- **🔐 Seguridad · "Programas activos".** En *Configuración → Seguridad*, un interruptor por programa (19) que lo **oculta a todos los usuarios**: desaparece de los menús y sus rutas quedan bloqueadas con la pantalla *"Programa desactivado"*. El superusuario lo sigue viendo en su Panel Principal con la etiqueta *Oculto*.

### v7.6.3 — Tickets (SLA con pausas + correos de estado), Mantenimiento (Control de equipo e Inspección), Reloj compensatorio y calculadora (release menor)

> Release **menor** (novedades solo al superusuario). La versión sí es general en el pie. **Aún falta** para una versión general (40 archivos < 50).

- **🎫 Tickets · estados que pausan el SLA.** Nuevos estados **"En espera del usuario"** e **"Incompleto"** que **congelan el SLA** (no vencen mientras están pausados). El reloj se reanuda cuando el usuario comenta o el técnico regresa el ticket a *En Proceso*; historial de pausas (`TicketPausaSLA`), soporte de pausas múltiples y reanudación automática. Nuevo `tickets/estados.py`.
- **Tickets · SLA fuera de horario.** Un ticket creado fuera del horario laboral (L–V 7–16) **pausa el SLA** hasta la próxima apertura y al usuario se le avisa que "se recibió y se atenderá en horas laborables".
- **Tickets · correos en cada cambio de estado** (antes solo al Resolver): En Proceso, En espera / Incompleto (indicando lo que falta) y Resuelto. Plantilla `email/ticket_estado.html`.
- **Tickets · panel del técnico**: el SLA pausado se muestra **"Pausado"** (naranja), ya no "Incumplido"; columna de chat alineada; descripción como *hover* (popover).
- **🔧 Mantenimiento · Control de equipo** (3.er tipo, evaluación del equipo del maestro): preguntas de evaluación, **estado del equipo** (Buen estado / Regular / Mal estado / Fuera de servicio), fotos, firmas fijas (Soporte Técnico / Auditora) + firma digital del maestro y PDF con 3 firmas. **Inspección** (4.º tipo) con 4 chequeos Sí/No + firma del asignado. Pestañas por tipo (Computadoras / Impresoras / Control) con *hover* compacto.
- **⏰ Reloj · Cálculo Compensatorio**: "Días no laborables ANA" con **fecha por entrada** (el *Tiempo tomado* solo refleja los feriados ya ocurridos) y **días reales por feriado** (no derivados de las horas); **factor 8.8 h/día**; el **receso** (minutos de más) se suma al *Tiempo tomado*. Permiso provisional con **autoguardado + cuenta regresiva** y distintivo verde "Permiso activo" / rojo "Permiso denegado". "Tiempo tomado manual" editable para el grupo `reloj`.
- **🧮 Calculadoras**: nueva **"Sumar horas y minutos"**.

### v7.6.2 — Seguridad de dependencias + Red: acceso por grupos, monitoreo, migración VLAN, API REST (release menor)

> Release **menor/técnico** (novedades solo al superusuario). La versión sí es general en el pie.

- **🛡️ Seguridad de dependencias (respuesta a las 110 alertas de Dependabot).** Actualizados en producción: **Django 6.0.5→6.0.8**, **Pillow 12.2→12.3**, PyJWT 2.13, sqlparse 0.6, cryptography 50, idna 3.15, tablib 3.10 (46 avisos PYSEC cerrados). Se **retiraron del repo los prototipos Next.js `frontend/` y `frontend_super/`** (no estaban en producción; concentraban las 4 críticas y la mayoría de las altas; respaldados en `/home/admin2/backups`). Nuevo `.github/dependabot.yml` (PRs semanales de pip). Informe: `docs/SEGURIDAD_DEPENDENCIAS_2026-08-26.md`. Pendiente sin parche disponible: `weasyprint` (no explotable: solo plantillas internas).
- **Red · acceso por grupos.** El módulo ya no es solo superadmin: `_gate(request, escribir=…)` valida permisos. Grupos **`red`** (lectura + exportar; soporte/TI) y **`red_admin`** (administrar + aprobar migraciones). 33 vistas de escritura protegidas; entrada en el sidebar para no-superusers.
- **Red · monitoreo continuo.** Comando `manage.py ping_red` en **cron cada 15 min** (`logs/ping_red.log`): actualiza estado/latencia y notifica **solo en transiciones** (caída/recuperación) a superusers y `red_admin`.
- **Red · migración de VLAN real.** El planificador ahora **ejecuta**: selección de equipos, motivo obligatorio, confirmación explícita, permiso `aprobar_migracion`. Se procesa equipo por equipo en transacción (libera IP anterior en el IPAM, asigna la primera libre del destino, actualiza el equipo); si uno falla se revierte solo ese. Auditado.
- **Red · topología**: export **SVG** y **PDF** (además de PNG/Mermaid).
- **Red · API REST** de solo lectura en `/red/api/v1/` (vlans, ips, dispositivos, switches con puertos, enlaces, ubicaciones, gabinetes) con búsqueda/filtros y auth por sesión o **token** (`rest_framework.authtoken`).
- Docs: `red/README.md` (informe ejecutivo del módulo) y OT-E2-00 / OT-E2-02-A de la integración SQL Server (verificación de conexiones y metadatos de los 4 SP de maestros).

### v7.6.1 — Inventario: integración de LECTURA con SQL Server (Test2) + flujo guiado a 3 pasos + racks (release menor)

> Release **menor/técnico** (novedades solo al superusuario). La versión sí es general en el pie.

- **Inventario institucional (SQL Server · Test2) — Etapa 0–1, SOLO LECTURA.** Capa nueva `contabilidad/sqlserver_inventory/` (alias Django `inventario_test2` con `mssql-django`, guard de base/rol `Des_EquipoInventario`, router anti-migraciones, DTOs y 8 consultas de solo lectura: categorías, unidades, almacenes, artículos, proveedores, existencias, costo promedio y kardex). Validada con 20 pruebas. **No escribe** nada; la tarjeta de acceso está **apagada** por defecto (`INV_TEST2_MOSTRAR_TARJETA=0`). Documentada en `contabilidad/sqlserver_inventory/README.md`.
- **Flujo guiado de Inventario corregido a 3 pasos**: Proveedor → Producto → Compra. La **entrada al inventario la registra CONFIRMAR la compra** (ya no manda al Movimiento, que duplicaba el stock). El "Registrar movimiento" queda solo para saldo inicial, ajustes, mermas y donaciones.
- **Racks (ANA Network Manager) — refinamientos**: numeración estándar (U1 abajo → U42 arriba), **frente/atrás** del gabinete, tipos **Bandeja**, **NVR** y **Media converter**; el tamaño del marcador escala también el texto.

### v7.6.0 — ANA Network Manager: nuevo módulo de documentación y operación de red (Fases 1–5)

Módulo **`red`** (superadmin) para documentar y operar la infraestructura de red. Tablas `red_*` en MySQL `sponsors2`.

- **IPAM y catálogo (Fase 1–2)**: VLANs con capacidad real (rango asignable, reservas, DHCP, alertas), direcciones IP, dispositivos, switches, puertos y enlaces. Detección de duplicados de IP/MAC y de ciclos.
- **Mapa de campus (Fase 3)**: planos con **marcadores** (figuras de red: router, switch, servidor, AP, firewall, cámara, NVR, reloj marcador…), **tamaño/giro editable** (ícono + texto), **selección múltiple**, y **líneas** entre marcadores (recta u **ortogonal** con punto de referencia, con nombre). **Zoom, orientación y paneo** del plano (recordados por plano). Una línea puede apuntar a un **equipo concreto** del rack de destino.
- **Topología (Fase 3)**: vista Cytoscape de dispositivos/enlaces y también de los marcadores/líneas de un plano; export PNG y Mermaid.
- **Racks (elevación tipo draw.io)**: cada gabinete tiene su **rack por unidades (U)** con equipos apilables, reordenables por arrastre y vinculables al inventario. Datacenter modelado con **Rack 1 (internet/red general)** y **Rack 2 (cámaras/CCTV)**.
- **Panel avanzado (Fase 4)**: KPIs y gráficas (dispositivos por tipo/edificio, IPs por VLAN, capacidad, enlaces, ocupación de puertos).
- **Pruebas de conectividad (Fase 4)**: ping desde el servidor a dispositivos/switches con estado (en línea/caído/latencia) e histórico.
- **Migración de VLAN (Fase 4)**: análisis de impacto (solo lectura) al mover dispositivos entre VLAN.
- **Buscador global (Fase 5)**: IP, MAC, equipo, switch o VLAN en una sola caja (+ endpoint JSON `/red/api/buscar/`).
- **Exportar a Excel (Fase 5)**: inventario (dispositivos, switches, VLANs, IPs) en `.xlsx`.

Rutas principales bajo `/red/`: `dashboard`, `panel`, `vlans`, `ubicaciones`, `dispositivos`, `switches`, `enlaces`, `planos`, `topologia`, `racks`, `gabinete/<id>/rack`, `pruebas`, `migracion`, `buscar`, `export/excel`.

### v7.5.0 — Panel Principal nuevo, Contabilidad por roles + regalías, Tickets con SLA y horario compensatorio

Release **general** (50 archivos): novedades para todos.

- **Panel Principal (superusuario) rediseñado**: KPIs reales arriba, **gráficas de actividad** (Chart.js, accesos últimos 14 días + usuarios más activos), y módulos en **2 columnas** compactas por área. Se movieron los módulos administrativos (Calculadoras, Monitoreo, Permisos, Configuración, Mantenimiento) al sidebar; el dropdown de usuario volvió al pie del sidebar (solo superuser).
- **Contabilidad · Inventario por roles**: hub de Inventario y **3 roles** con grupos propios — Ventas (form de venta que descuenta stock y genera ingreso), Abastecimiento (productos/proveedores/compras) y Supervisión (reportes + **auditoría** del módulo). Proveedores y Compras viven dentro de Inventario de Uniformes.
- **Regalías de proveedores**: informe aparte (no se contabiliza) con reporte por proveedor.
- **Precios por proveedor + ISV 15% incluido**: form de precios con costo del proveedor, precio de venta e ISV 15% *dentro* del precio; columna **Proveedor en las salidas** del kardex por FIFO. Todo el dinero con **`L` y separador de millares**.
- **Tickets con SLA y urgencia**: el usuario elige **urgencia** (Bajo/Medio/Alto/Urgente) que define el **SLA en horas laborales** (L–V 7:00–16:00): 72/24/8/2 h. Semáforo SLA en el panel y **alerta sonora cada 10 min** para tickets sin atender.
- **Reloj · horario compensatorio por fecha**: reglas con vigencia (Nancy/Diego/Ana/Gabriela cambian desde el 24/08 sin alterar el histórico) y **excedente** de horas cuando el saldo deuda llega a 0.
- **Agendas (PPTX)**: fuentes/tamaños de la agenda semanal (Century Gothic, Book Antiqua) y posición del cuadro de grado.

### v7.4.2 — Dashboard Coordinador (acordeón + WhatsApp), CFP notas, accesos y limpieza

Release **general** (~60 archivos): novedades para todos.

- **Conducta · Dashboard Coordinador**
  - **Acordeón plegable** (DataTables RowGroup, conserva buscador/orden/selección/evidencias/editar): Informativo y Conductual **por fecha** (recientes primero), Progress **por grado** (1.º→9.º).
  - **Botón de WhatsApp por reporte**: abre WhatsApp con el teléfono del padre/madre (desde `padres_sqlserver` por `PersonaID`) y un **mensaje editable** según el reporte. Solo coordinadores/admin/enfermería.
  - **Historial de alumnado**: corregida la carga (ya no se queda cargando al entrar directo al tab).
  - **Descargar ZIP**: modal para **elegir qué reportes** (académico / conductual / progress / historial), **filtrado por el grado del coordinador** y **organizado en carpetas por grado**.
  - **Reenviar reportes**: selección de tipos.
  - Editor de Progress igual a Agendas; clase **Spelling** en primaria y colegio; corrección de `_x000D_` en el PowerPoint.
- **CFP · Notas/Horas**: carga de notas por intento (T1–T3 / P1–P3) y horas por mes; la grilla ya **no muestra decimales**.
- **Accesos / Login**
  - Inicio de sesión por **usuario o correo** (el admin entra como `jfellmann` o `admin`); **el superusuario nunca se bloquea** temporalmente.
  - **Enfermería** entra normal a su propio dashboard (antes caía en 403).
  - **Tickets**: los usuarios de *administración* ven **solo sus tickets** (se dejó de usar `is_staff` como rol; el acceso total es por permiso `tickets.view_ticket`).
- **Contabilidad** (módulo nuevo, **en pausa** esperando la estructura en SQL Server): inventario contable con kardex, **promedio ponderado**, proveedores y compras (todo en MySQL por ahora).
- **Responsive**: refuerzo global para verse bien en celular/tablet + Panel Principal más legible en móvil.
- **Limpieza**: eliminadas las apps sin uso **`camaras`** y **`atencion_padres`** (respaldadas antes de borrar).
- **Backups**: el paso *"actualiza todo"* ahora **sincroniza los backups (sistema + BD) a la PC del administrador** por SMB (`sync_backups.sh` + cron).

### v7.4.1.007.001 — Nuevo módulo: Gestión de Desarrollo (requerimientos y proyectos)

> Release **menor** (36 archivos, módulo nuevo aislado): la ventana de novedades solo la ve el superusuario.

**Gestión de Desarrollo** — el registro histórico oficial del ciclo de desarrollo de TechCare. App Django `desarrollo`, dentro de **Soporte y TI** (sidebar + acordeón del Panel Principal). Acceso: superusuario y grupos `desarrollo_admin` / `desarrollo_dev`.
- **Requerimientos** con código automático `REQ-AAAA-XXXX`: formulario, listado con filtros, detalle, edición/seguimiento, **historial automático**, **bitácora** de notas, **adjuntos** (PDF/imágenes/Office/texto, máx 10 MB) y **semáforo** 🟢🟡🔴⚪ (en tiempo / próximo / atrasado / sin fecha).
- **Proyectos** con código `TC-PRY-XXXX`: listado, ficha técnica, requerimientos asociados, timeline de actividad y **conversión requerimiento→proyecto**.
- **Dashboard**: KPIs, gráficos (estado/prioridad/tipo/área con Chart.js), panel de semáforos, próximos a vencer y actividad reciente.
- **Roadmap Kanban** con **arrastrar y soltar** para cambiar de estado, y **"Mis Requerimientos"** (asignados / solicitados).
- **Exportación a Excel** de los requerimientos (respeta filtros y permisos).
- Permisos por grupo: admin/dev ven y gestionan todo; solicitante/responsable ven lo suyo.

### v7.4.1.007 — Rediseño del Dashboard Coordinador + topbar (campana y usuario arriba)

> Release **menor** (14 archivos): la ventana de novedades solo la ve el superusuario.

**Dashboard Coordinador (BL y Colegio) — de una página pesada a un lanzador de apps:**
- Al entrar a "Coordinador BL/Colegio" se ve un **grid de apps** (Reportes Académicos · Conductuales · Progress · Historial); cada una abre **enfocada** (sin la barra de tabs, con "← Apps"). Aplica al superuser y a cada coordinador (`dashboard_c1..c4`).
- **Reportes Conductuales solo para C3** (Isabel Alcerro); C1/C2/C4 no lo ven.
- **Título con la identidad** de quien entra: *"Coordinador (Bilingüe) · Coordi 1 · Catherine Varela"*; "Prin" se muestra como **Principal**.
- **Filtro "por coordinador"** ahora lista solo C1–C4 (los que coordinan reportes); antes decía mal "Mr. Martinez" en C1.
- Se agregaron al menú del coordinador (Panel General **y** sidebar, consistentes): **Tutorías**, **Período Escolar** (vía `?app=periodo`) y **Ruteo**.

**Barra lateral y topbar:**
- **Sidebar estático** (submenús siempre abiertos) para staff/usuarios; el superusuario lo mantiene **colapsable** (su menú es muy largo).
- La **campanita de notificaciones** y el **usuario** (avatar+nombre) se movieron a la **esquina superior derecha** (topbar).
- **Modo oscuro** pasa de botón flotante a **interruptor** dentro del menú de usuario.
- Arreglo: el botón "Dashboard" en Tutorías vuelve al **home correcto** del usuario.

### v7.4.1.006 — Autoguardado en Editar Agenda (+ ajustes del Bono y receso)

> Novedad **general** (la ven todos los usuarios): autoguardado de agendas.

**Para los docentes (novedad visible):**
- **Editar Agenda ahora se guarda sola.** Se quitó el botón "Guardar"; cada vez que escribes o modificas una casilla, la agenda se guarda automáticamente (al salir de la casilla o ~1.2 s después de escribir), reduciendo el riesgo de perder información. Aparece un indicador "Se guarda solo → ✓ Guardado".

**Ajustes internos (Reloj / CFP, no salen en la novedad):**
- **Bono por Asistencia — reglas de dos niveles:** el límite de tardanza pasa a **06:59** (se toleran 2, pierde en la 3ra) y se agregó un **tope duro a las 07:00**: una marca a esa hora o después pierde el bono automáticamente. No afecta horarios especiales de maestros por hora ni vigilancia.
- **Receso:** ventana de detección ampliada a **11:00–16:00** para almuerzos tardíos, con tope de 90 min para no confundir la salida del día con un receso.
- **Salidas al Baño (CFP):** un instructor ve **solo su curso** asignado; coordinador/director ven todos.
- **PDF del Bono:** subtítulo dinámico *"…de {mes} para {mes siguiente} · valor Lps. 200"*.

### v7.4.0.005 — Botón "Volver a Historial de Reportes" en Editar Agenda

> Release **menor** (4 archivos): la ventana de novedades solo la ve el superusuario.

- **Agendas (lado maestro)**: al editar una agenda, se agregó arriba el botón **"← Volver a Historial de Reportes"**, que regresa al historial del maestro y **abre directamente la pestaña Agendas** (activación de pestaña por `#hash`). El coordinador conserva su botón de Descargar PPTX.

### v7.4.0.004 — Autoguardado de Horas CFP, filtro de tabs en Inventario y ventana de receso más amplia

> Release **menor** (7 archivos): la ventana de novedades solo la ve el superusuario.

- **CFP · Notas del curso — pestaña Horas**: ahora **se guarda sola** (se quitó el botón "Guardar horas"); guarda al salir de una casilla o 1 s tras dejar de escribir, sin recargar, con indicador de estado. Aplica a todos los cursos. Además la tabla es **más ancha y menos apretada** (casillas y letra más grandes, ocupa el ancho disponible).
- **Inventario · Computadoras**: los tabs **Todos / General / Lab BL / Lab COL / Lab CFP** volvieron a **filtrar** la tabla por prefijo del Asset ID (se había perdido el manejador en la extracción del JS).
- **Reloj · Receso**: se amplió la ventana de detección automática del almuerzo (11:00–15:30) para que tome los recesos que empiezan tarde sin tener que marcarlos a mano.
- **Cámaras**: se quitó el banner "Nueva vista interactiva" del inicio.

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
| `_crear_agenda.html` | Pestaña *Crear agenda* (grado + semana, varios grados) |
| `diseno_agenda.html` | Editor de diseño: vista previa PowerPoint BL / Word Colegio, ajustes y PNG final (`agendas/diseno.py`) |

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
| `crear-semana/` | `crear_semana` | Crear agendas vacías de una semana (coordinador) |
| `<pk>/diseno/` | `diseno` | Editor de diseño |
| `<pk>/diseno/guardar/` | `diseno_guardar` | Autoguardado de ajustes y textos (JSON) |
| `<pk>/imagen-final/` · `guardar/` | `imagen_final` · `imagen_final_guardar` | Ver / guardar la imagen final (PNG) |

**Moodle** (`/moodle-upload/`, app `moodle_upload`, solo superusuario + botón en el Dashboard para coordinadores): conexiones guardadas (Moodle real activo, Moodle de pruebas), publicar en cursos agrupados por grado-sección, historial y aviso de vencimiento del token. Plugin de Moodle en `moodle_plugin/local_techcareagenda`.

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
