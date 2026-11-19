# Seguridad y gestión de TI de TechCare

**Revisión del 09-nov-2026**, en producción desde la versión **8.0.1**.

**Dónde leerlo:** dentro de TechCare, en **Configuración → Documentación** (solo el superusuario), o en la carpeta `docs/seguridad/` del repositorio.

> **Advertencia sobre el alcance.** Esta carpeta documenta mejoras **orientadas** por ISO/IEC 27001:2022 y COBIT 2019, adaptadas a TechCare. **No certifica nada.** Ni el sistema ni la Asociación Nuevo Amanecer (ANA) quedan "cumpliendo" ISO 27001 o COBIT por estos cambios.
>
> La certificación exige un sistema de gestión (SGSI) aprobado por la dirección, con alcance, análisis de riesgos, declaración de aplicabilidad, auditorías internas y revisión por la dirección. Eso **no** se resuelve con software.

## Contenido

| # | Documento | Tipo |
|---|---|---|
| 1 | [01_diagnostico.md](01_diagnostico.md) | Diagnóstico de seguridad y de gestión, con evidencia |
| 2 | [02_matriz_riesgos.md](02_matriz_riesgos.md) | Matriz de riesgos: evidencia, impacto, prioridad y tratamiento |
| 3 | [03_matriz_trazabilidad.md](03_matriz_trazabilidad.md) | Trazabilidad: hallazgo → referencia → mejora → evidencia → validación → estado |
| 4 | [04_guia_configuracion_despliegue.md](04_guia_configuracion_despliegue.md) | Configuración segura, despliegue y reversión de esta rama |
| 5 | [05_respaldo_restauracion.md](05_respaldo_restauracion.md) | Respaldo y restauración, separando lo **probado** de lo no probado |
| 6 | [06_procedimiento_incidentes.md](06_procedimiento_incidentes.md) | Procedimiento de incidentes de seguridad |
| 7 | [07_plan_seguridad.md](07_plan_seguridad.md) | Plan de seguridad de la información (aprobado) |
| 8 | [08_plan_continuidad_negocio.md](08_plan_continuidad_negocio.md) | Plan de continuidad del negocio (aprobado) |
| 9 | [09_plan_capacitacion.md](09_plan_capacitacion.md) | Plan de capacitación del personal (aprobado) |
| 10 | [10_proceso_creacion_usuarios.md](10_proceso_creacion_usuarios.md) | Proceso de creación, cambio y baja de usuarios (estado actual + propuesta) |
| 11 | [politicas/](politicas/) | Políticas aprobadas: acceso, información sensible, cambios, desarrollo de software y contraseñas |
| — | [infra/](infra/) | Cambios de Apache **preparados, no aplicados**, con su reversión |

## Sobre las referencias a ISO y COBIT

- **ISO/IEC 27001:2022.** Los números y títulos de los controles del Anexo A (5.x organizacionales, 8.x tecnológicos) se verificaron contra **fuentes secundarias públicas**, no contra el texto oficial, que es de pago. Por eso se cita solo **número y título**, nunca el texto del control. Antes de usarlos en una auditoría hay que confirmarlos contra la norma oficial y contra ISO/IEC 27002:2022, que la describe.
  - Fuentes consultadas: [ISMS.online](https://www.isms.online/iso-27001/annex-a/8-13-information-backup-2022/), [High Table](https://hightable.io/iso-27001-annex-a-controls-list/) y [Open Security Architecture](https://opensecurityarchitecture.org/frameworks/iso-27001-2022).
- **COBIT 2019.** Los objetivos (APO12, APO13, BAI06, BAI09, BAI10, DSS02, DSS03, DSS04, DSS05, MEA01) se verificaron contra fuentes secundarias, entre ellas un artículo de [ISACA](https://www.isaca.org/resources/news-and-trends/industry-news/2020/evaluating-business-service-continuity-and-availability-using-cobit-2019). Una fuente nombra APO13 como "Managed Security and Privacy"; aquí se usa "Managed Security", la denominación mayoritaria. Conviene confirmarlo con la publicación oficial de ISACA.

## Reglas de esta documentación

- No contiene contraseñas, tokens, IPs públicas de usuarios ni datos personales. Cuando se habla de un secreto se dice **dónde** está y **qué hacer**, nunca su valor.
- No inventa responsables. Donde falta una persona designada dice **[Responsable por designar]**.
