# Política de gestión de cambios — TechCare

**Referencias:** ISO 27001:2022 8.32 (gestión de cambios), 8.31 (separación de entornos de desarrollo, prueba y producción), 8.9 (gestión de la configuración) · COBIT 2019 BAI06 (Managed IT Changes), BAI07, BAI10.

## 1. Situación actual (verificada)

- La carpeta que sirve Apache **es** la copia de trabajo de git, en la rama `main`. Lo que hay en disco se publica al reiniciar, aunque no tenga commit.
- El flujo habitual es commit directo a `main`. La versión y las novedades se generan desde `git log` (`gen_changelog`).
- Existe un entorno de **pruebas** (`techcare-pruebas`, Coolify, base `sponsors2_pruebas`), pero no todo cambio pasa por él.
- Las **migraciones no están en git**.
- Antes de esta revisión no había pruebas automatizadas, salvo `red`.

## 2. Tipos de cambio

| Tipo | Ejemplos | Aprobación |
|---|---|---|
| **Estándar** (bajo riesgo, repetible) | Texto, estilos, una columna en una tabla | Responsable técnico |
| **Normal** | Funcionalidad nueva, cambio de permisos, migración de BD, dependencia nueva | Responsable técnico + **dueño del módulo** (por ticket o requerimiento) |
| **Mayor** (≥ 50 archivos o versión del 2.º segmento) | Releases generales | Además, aviso a los usuarios (novedades) |
| **Emergencia** | Contención de un incidente de seguridad | Se aplica y se documenta **después**, dentro de las 24 h |
| **Infraestructura** | Apache, `.env`, cron, permisos, SQL Server | Responsable técnico, con respaldo previo y plan de reversión escrito |

## 3. Flujo propuesto

1. **Registrar** el cambio: requerimiento en Gestión de Desarrollo (`REQ-AAAA-XXXX`) o ticket.
2. **Desarrollar en una rama** (`feature/…`, `fix/…`, `seguridad/…`) o en una copia aparte (git worktree), **nunca** directamente en la carpeta de producción.
3. **Probar:** pruebas automáticas (`manage.py test --settings=system_proyect.settings_test`), `manage.py check`, `node --check` de los JS tocados y prueba funcional en el entorno de pruebas.
4. **Revisar:** otra persona lee el cambio (diff). Si no hay segunda persona, dejar constancia de la autorrevisión y de las pruebas en el requerimiento. ⚠ Falta segregación de funciones (G03).
5. **Aprobar** según el tipo (§2).
6. **Desplegar** en una ventana acordada:
   - respaldo previo (tar del código, y volcado si hay migración);
   - merge del commit aprobado;
   - `collectstatic` con sudo y subir el `?v=N`;
   - migraciones;
   - reinicio de Apache **verificado por la hora de arranque**.
7. **Verificar** en vivo y registrar el resultado en el requerimiento.
8. **Revertir** si falla, con el plan escrito en el paso 6. Ver la [guía de despliegue](../04_guia_configuracion_despliegue.md), §4.4.

## 4. Reglas permanentes

- Toda migración que mueva datos se prueba primero en la base de pruebas.
- **Propuesta (G02):** versionar las migraciones en git, para que el repositorio pueda reconstruir el esquema.
- Ningún cambio de producción se hace sin respaldo previo identificable por fecha.
- Los cambios hechos por herramientas de IA siguen **el mismo flujo** y la misma revisión que los de una persona.
- La documentación de operación (`AGENTS.md`, `README.md`) se actualiza en el mismo cambio. **Nunca** con credenciales.
