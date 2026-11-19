# Política de información sensible — TechCare

**Referencias:** ISO 27001:2022 5.12 (clasificación de la información), 5.34 (privacidad y protección de datos personales), 8.12 (prevención de fuga de datos), 5.19 (proveedores) · COBIT 2019 APO13, DSS05, DSS06.

## 1. Clasificación

| Nivel | Qué incluye en TechCare | Reglas mínimas |
|---|---|---|
| **Restringida** | Atenciones médicas y medicamentos; reportes y evidencias de conducta; notas y asistencia de alumnos; teléfonos y correos de padres; contraseñas de equipos de red; credenciales (`.env`) | Solo por pantallas con permiso. Sin copias locales salvo necesidad. Descargas sin caché (vigente en la rama). Nunca por canales personales (WhatsApp personal, correo personal) |
| **Interna** | Asistencia del personal, inventarios, tickets, contabilidad, donantes | Solo personal autorizado; no publicar |
| **Pública** | Avisos institucionales, logo | Sin restricción |

## 2. Reglas de manejo

1. **Exportes** (Excel, PDF, ZIP): solo cuando hace falta. Guardarlos en equipos institucionales y borrarlos cuando ya no se usen. **No** subirlos a nubes personales.
2. **Imágenes de menores:** las evidencias se suben solo al reporte correspondiente y se ven por la pantalla con permiso. **No** compartirlas por enlaces directos.
3. **Enlace público del reporte en PNG** (para compartir con familias): vale 60 días y no se puede revocar. **Propuesta:** reducirlo a 7–14 días (R21) y compartirlo solo con el tutor del alumno.
4. **Correo:** las fichas médicas solo se envían a los correos registrados del alumno, ya restringido en el sistema.
5. **Pantallas compartidas y proyectores:** no mostrar listas de alumnos con datos médicos o de conducta.
6. **Datos de prueba:** las pruebas de software usan **datos sintéticos** (`settings_test.py`) o la base de pruebas, **nunca** la de producción.
7. **Registros (logs):** nunca contienen contraseñas, tokens, códigos 2FA ni contenido médico. El código de la bitácora de seguridad descarta esas claves.

## 3. Inteligencia artificial y proveedores externos

- TechCare envía a la **API de Anthropic (Claude)** el texto que el usuario escribe en el asistente y en "redactar con IA" de Conducta. Este último puede contener información de **menores**.
- **Propuesta (R22):**
  - Limitar "redactar con IA" a los grupos de Conducta.
  - Mostrar un aviso: "no escriba nombres completos ni datos médicos".
  - Revisar las condiciones del proveedor sobre retención y uso de datos y registrar su aprobación en esta política.
- Otros proveedores con datos: Google (correo SMTP), Moodle (agendas publicadas) y GitHub (código, **no** datos). Deben quedar en un **inventario de proveedores** con su responsable.

## 4. Retención (propuesta, a validar con Dirección y asesoría legal)

| Información | Retención sugerida |
|---|---|
| Atenciones médicas | Mientras el alumno esté inscrito + **[N años por definir]** |
| Reportes de conducta y evidencias | Año escolar en curso + **[N años por definir]** |
| Bitácoras de seguridad (`seguridad.log`) | 1 año como mínimo |
| Respaldos | Ver el [procedimiento de respaldo](../05_respaldo_restauracion.md), §5.5 |

## 5. Incumplimientos

Toda fuga o sospecha de fuga se maneja con el [procedimiento de incidentes](../06_procedimiento_incidentes.md).
