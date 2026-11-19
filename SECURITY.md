# Política de seguridad — TechCare

TechCare es el sistema institucional de la Asociación Nuevo Amanecer (ANA). Maneja información de alumnos (en su mayoría menores), médica, académica y del personal.

## Versiones con soporte

Solo la versión **desplegada en producción** (rama `main`, servicios.ana-hn.org:437) recibe correcciones de seguridad. El entorno de pruebas (`techcare-pruebas`) no guarda datos reales.

## Cómo reportar una vulnerabilidad o un incidente

- **Personal de ANA:** abrir un ticket en TechCare con urgencia **Urgente** (Soporte), o avisar directamente al administrador de TechCare si el sistema no está disponible.
- **No** incluya en el reporte contraseñas, datos de alumnos ni capturas con información personal. Basta con describir qué observó, dónde y cuándo.
- **No** intente comprobar la falla accediendo a datos ajenos.

Se confirma la recepción en un día hábil y se aplica el [procedimiento de incidentes](docs/seguridad/06_procedimiento_incidentes.md).

## Documentación de seguridad

Diagnóstico, matriz de riesgos, guías y borradores de políticas: [`docs/seguridad/`](docs/seguridad/README.md). También se pueden leer dentro de TechCare, en **Configuración → Documentación** (solo el superusuario).
