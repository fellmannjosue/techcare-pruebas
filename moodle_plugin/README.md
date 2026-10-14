# Plugin de Moodle "TechCare · Agendas" (`local_techcareagenda`)

Publica la imagen de la agenda semanal en la sección **General** de un curso de Moodle y la **reemplaza** cada semana
(una sola "Área de texto y medios" marcada con idnumber `techcare_agenda`).

- Función de servicio web: `local_techcareagenda_publicar(courseid, filename, filecontent[base64], alttext)` → `{cmid, creado, url}`.
- Servicio "TechCare Agendas" (`techcare_agendas`, restringido a usuarios autorizados) con esa función + `core_webservice_get_site_info`,
  `core_course_get_courses_by_field`, `core_course_search_courses`.
- Requiere en Moodle: Servicios Web activos + protocolo REST + token del usuario autorizado (capacidad `moodle/course:manageactivities` en el curso).
- Probado el 14-oct-2026 en el Moodle de PRUEBAS (4.3.8, http://192.168.10.6:452, curso TEST id 2): 1.ª publicación crea, la 2.ª reemplaza.
- Instalar: comprimir la carpeta `local_techcareagenda` renombrada a `techcareagenda` en un .zip → *Site administration → Plugins → Install plugins*.
