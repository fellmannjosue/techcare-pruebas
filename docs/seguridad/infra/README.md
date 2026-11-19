# Cambios de infraestructura preparados (NO aplicados)

Estos archivos los aplica TI en el servidor, en una ventana de mantenimiento y con respaldo previo. Ninguno se aplicó durante la revisión del 09-nov-2026.

| Archivo | Qué hace | Riesgos |
|---|---|---|
| [apache_media.conf](apache_media.conf) | Fase A: cierra `media/evidencias` y limita las peticiones a 30 MB. Fase B: `/media/` pasa a lista blanca | R01, R02, R16 |

**Orden:** primero desplegar el código de la rama `seguridad/iso27001-cobit` y después Apache. Ver la [guía de despliegue](../04_guia_configuracion_despliegue.md).
