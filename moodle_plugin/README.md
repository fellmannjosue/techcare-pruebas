# Plugin de Moodle "TechCare · Agendas" (`local_techcareagenda`) — v0.2 (seguridad reforzada)

Publica la imagen de la agenda semanal en la sección **General** de un curso de Moodle y la **reemplaza** cada semana
(una sola "Área de texto y medios" marcada con idnumber `techcare_agenda`). No toca ninguna otra actividad del curso.

- Función de servicio web: `local_techcareagenda_publicar(courseid, filename, filecontent[base64], alttext)` → `{cmid, creado, url}`.
- Servicio "TechCare Agendas" (`techcare_agendas`): **solo usuarios autorizados**, sin descarga ni subida genérica de archivos, y
  solo 3 funciones: la del plugin + `core_webservice_get_site_info` + `core_course_get_courses_by_field`.

## Medidas de seguridad (15-oct-2026)
1. **Interruptor general apagado al instalar** (`local_techcareagenda/enabled`): instalar el plugin no cambia nada en Moodle
   hasta que el administrador lo activa. Apagarlo corta la publicación al instante.
2. **Categorías permitidas** (opcional): IDs separados por coma; el curso debe estar en una de ellas o en una subcategoría.
3. **Capacidad propia `local/techcareagenda:publish`** que **ningún rol trae por defecto**; además se exige
   `moodle/course:manageactivities` en el curso. Nunca la portada del sitio.
4. **La imagen se valida por su contenido** (solo PNG/JPG reales; SVG, HTML o texto renombrado se rechazan), máx. 10 MB,
   8000 px por lado y 25 megapíxeles, y se **vuelve a generar con GD**: lo guardado es una imagen nueva, sin metadatos ni
   código escondido (probado: un PNG con `<?php …` pegado se guarda limpio).
5. **El nombre del archivo lo pone el plugin** (`agenda_AAAAMMDD_HHMMSS.png`); el texto alternativo se limpia y se escapa.
6. Todo en **una transacción** y cada publicación queda en **Informes → Registros** (evento *Agenda publicada desde TechCare*).
7. Proveedor de privacidad (no guarda datos personales). Desinstalarlo no deja nada (las etiquetas creadas quedan como actividades normales).

## Instalación segura en el Moodle real
1. El administrador del servidor copia la carpeta `techcareagenda` (del ZIP) en `<moodle>/local/` — o, si la carpeta `local`
   tiene permiso de escritura, *Administración del sitio → Plugins → Instalar plugins* con el ZIP — y completa la actualización.
2. Crear un usuario **técnico** (p. ej. `techcare`), **no administrador**, con contraseña fuerte.
3. Crear un rol "TechCare publicador" (contexto Sistema o Categoría) con: `local/techcareagenda:publish`,
   `moodle/course:manageactivities`, `moodle/course:view`, `webservice/rest:use`; asignárselo solo a ese usuario.
4. Activar Servicios Web + protocolo REST; en *Servicios externos → TechCare Agendas → Usuarios autorizados* agregar solo a `techcare`
   (opcional: limitar por IP del servidor de TechCare y poner fecha de vencimiento al token).
5. Crear el token de `techcare` para ese servicio y pegarlo en TechCare (se guarda cifrado).
6. *Plugins locales → TechCare · Agendas*: activar y, si se quiere, limitar las categorías. Probar primero con un curso oculto.

Probado el 15-oct-2026 en el Moodle de PRUEBAS (4.3.8, http://192.168.10.6:452, curso TEST id 2): imagen válida, texto renombrado,
PNG con PHP, SVG, nombre con ruta, alt con HTML, 9000 px, portada, base64 roto, función fuera del servicio, categoría no permitida
e interruptor apagado.
