# Política de control de acceso — TechCare

**Referencias:** ISO 27001:2022 5.15 (control de acceso), 5.18 (derechos de acceso), 8.2 (derechos de acceso privilegiado), 8.3 (restricción de acceso a la información) · COBIT 2019 DSS05, APO13.

## 1. Principios

1. **Necesidad de saber y mínimo privilegio.** Cada persona recibe solo los grupos que su función exige, y solo de **su área**: Bilingüe, Colegio/Bachillerato, CFP o Administración.
2. **El permiso se valida en el servidor.** Ocultar un menú, una tarjeta o un programa (Programas ocultos, Programas por aplicación) **no** es un control de seguridad. Toda vista nueva debe comprobar grupo y área en el servidor.
3. **Sesión obligatoria.** Toda pantalla exige sesión (`TechCareLoginRequiredMiddleware`). Una vista pública debe marcarse explícitamente con `@login_not_required`, justificada y aprobada.
4. **El área sale del usuario, nunca de la URL o del navegador.**
5. **`is_staff` no es un rol de negocio.** Los roles son grupos con nombre exacto. Está prohibido el patrón `name__icontains`.

## 2. Roles y dueños de la información

| Información | Dueño (aprueba accesos) | Grupos que acceden hoy |
|---|---|---|
| Atenciones médicas, medicamentos, directorio de padres | Enfermería **[persona por designar]** | `enfermeria`, coordinaciones (⚠ ver R18) |
| Reportes de conducta, evidencias, Progress | Coordinación BL / Coordinación Colegio | Maestros (lo suyo), coordinadores del área |
| Notas (mitad de parcial, ingreso) | Coordinaciones académicas | `maestros_notas_*`, `ingreso notas *`, coordinadores |
| Asistencia y compensatorio del personal | RR. HH. / Administración | Permisos del modelo `RelojPermiso` |
| Contabilidad, CFP | Administración / Contabilidad | `contabilidad_*`, `cfp*` |
| Red (IPs, contraseñas de equipos) | TI | `red`, `red_admin` |
| Donantes (Sponsors) | Dirección / Sponsors | Permisos de Django de `sponsors` |
| Usuarios, configuración, seguridad | TI | Superusuario (+ gestor delegado, limitado) |

## 3. Accesos privilegiados

- **Un solo superusuario** nominal, con contraseña robusta y 2FA (propuesta). Se prohíben cuentas genéricas compartidas de administración.
- "Iniciar sesión como" queda limitado al superusuario, siempre con bitácora y solo para soporte. Debe anotarse el motivo en el ticket relacionado.
- `/admin/` solo desde la red interna.
- El acceso al servidor (SSH, sudo) se limita a TI. La contraseña sudo **no** se guarda en archivos ni en herramientas de IA (ver R40).

## 4. Acceso de terceros y de herramientas de IA

- Proveedores, practicantes o herramientas automatizadas (incluidos los asistentes de IA de desarrollo) acceden **solo** a lo necesario y **nunca** a datos reales de menores o médicos cuando se puede usar la base de pruebas.
- Los tokens de integración (API de Red, Moodle, GitHub) tienen un responsable, un alcance mínimo y una revisión semestral.

## 5. Revisión

Ver el [proceso de creación de usuarios](../10_proceso_creacion_usuarios.md), §10.5: revisión trimestral de usuarios y grupos, y mensual de privilegiados.

## 6. Decisiones pendientes que esta política exige tomar

- **R18:** qué debe ver `coord_progress_bl`; hoy equivale a coordinación BL completa más Enfermería.
- **R19:** quién puede borrar o editar atenciones médicas.
- **R20:** si Progress Report debe ser visible para todos los maestros BL o solo para los del grado.
