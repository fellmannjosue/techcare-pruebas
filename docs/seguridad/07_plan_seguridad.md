# 7. Plan de seguridad de la información — TechCare

> Este plan **no** constituye un SGSI certificable. Es el primer paso hacia uno.

**Referencias:** ISO 27001:2022, cláusulas 4 a 10 (contexto, liderazgo, planificación, apoyo, operación, evaluación y mejora; descritas de forma general, sin citar su texto) y Anexo A · COBIT 2019 APO12 (Managed Risk), APO13 (Managed Security), DSS05 (Managed Security Services), MEA01.

## 1. Objetivo y alcance

- **Objetivo:** proteger la confidencialidad, integridad y disponibilidad de la información que TechCare gestiona sobre alumnos (en su mayoría **menores**), personal, donantes y operaciones de ANA.
- **Alcance propuesto:**
  - La aplicación TechCare: web, app de escritorio y APK.
  - Su servidor Ubuntu, Apache y la base MySQL `sponsors2`.
  - Sus integraciones: SQL Server académico y ZKBio de solo lectura, salvo Ingreso de Notas; SMTP; Moodle; IA; GitHub.
  - Los respaldos.
  - Las personas que la administran y la usan.
- **Fuera de alcance por ahora:** la red institucional, los servidores SQL Server (otra área) y los equipos de usuarios. Deben incorporarse en una segunda etapa.

## 2. Gobierno y roles (por designar)

| Rol | Responsabilidad | Persona |
|---|---|---|
| Patrocinador (Dirección) | Aprueba el plan y las políticas, asigna recursos y acepta riesgos residuales | [Responsable por designar] |
| Responsable de seguridad de la información | Mantiene el plan, la matriz de riesgos y las revisiones; coordina incidentes | [Responsable por designar] |
| Administrador técnico de TechCare | Opera el servidor, los despliegues, los respaldos y las cuentas | [Responsable por designar] |
| Responsable de accesos | Altas, bajas y revisiones de usuarios | [Responsable por designar] |
| Dueños de la información | Enfermería, Coordinaciones académicas, RR. HH., Contabilidad, Sponsors: aprueban accesos a su información | [Por área] |
| Usuarios | Cumplen las políticas y reportan incidentes | Todo el personal |

> **Riesgo de gestión (G03):** hoy una sola persona desarrolla, despliega, administra el servidor, crea usuarios y gestiona respaldos. Mientras no haya una segunda persona, al menos la **aprobación** de cambios mayores y de accesos sensibles debe quedar en otra persona (Dirección o el dueño de la información).

## 3. Gestión de riesgos

- La matriz vigente es [02_matriz_riesgos.md](02_matriz_riesgos.md). Se **revisa cada trimestre** y tras cada incidente o cambio mayor.
- **Criterio de aceptación:** los riesgos Críticos y Altos no pueden quedar aceptados sin firma de la Dirección. Los Medios los acepta el responsable de seguridad con fecha de revisión.

## 4. Plan de acción (priorizado)

| Plazo | Acción | Riesgo | Quién |
|---|---|---|---|
| **Inmediato (≤ 1 semana)** | Restablecer la copia externa de los respaldos (falla desde el 17-sep) | R33 | Administrador técnico |
| Inmediato | Desplegar la rama `seguridad/iso27001-cobit` y aplicar la fase A de Apache (evidencias de conducta) | R01, R03, R04, R06, R11, R17, R23 | Administrador técnico |
| Inmediato | Rotar las credenciales de MySQL, SQL Server académico y ZKBio, y la contraseña sudo; retirarla de la memoria del asistente de IA | R29, R40 | Administrador técnico + DBA de SQL Server |
| **Corto (≤ 1 mes)** | Respaldo **diario** de MySQL, cifrado, sin `.env` dentro | R30, R31 | Administrador técnico |
| Corto | Decidir el alcance de `coord_progress_bl`, quién borra atenciones médicas y la visibilidad de Progress | R18, R19, R20 | Dirección + Coordinaciones + Enfermería |
| Corto | Encender el 2FA para el superusuario y staff | R03 | Administrador técnico |
| Corto | Actualizar las dependencias menores; planificar Pillow 13 y WeasyPrint 70 en pruebas | R28 | Administrador técnico |
| Corto | Aplicar la fase B de Apache (`/media/` en lista blanca) | R02 | Administrador técnico |
| **Medio (≤ 3 meses)** | Primera prueba de restauración de la BD en una base aislada | R32 | Administrador técnico |
| Medio | Enlace de "crear contraseña" en las altas; reenvío de 2FA con límite; logout por POST; caducidad de la suplantación | R10, R12–R14 | Desarrollo |
| Medio | Versionar las migraciones; flujo por ramas con revisión | G01, G02 | Desarrollo |
| Medio | Política de uso de IA y avisos en "redactar con IA" | R22 | Dirección + Desarrollo |
| Medio | Capacitación de la [primera ronda](09_plan_capacitacion.md) | — | Responsable de seguridad |
| **Continuo** | Revisión semanal de `seguridad.log`; trimestral de accesos y riesgos; mensual de dependencias | — | Responsable de seguridad |

## 5. Controles técnicos vigentes

Ver el [diagnóstico](01_diagnostico.md), §1.3 y §1.5.

## 6. Indicadores (para soporte y gestión, COBIT MEA01)

| Indicador | Fuente | Meta propuesta |
|---|---|---|
| Días desde el último respaldo externo correcto | `sync_backups.log` | ≤ 1 |
| Días desde la última prueba de restauración de la BD | Registro de pruebas | ≤ 90 |
| Riesgos Críticos y Altos abiertos | Matriz de riesgos | Tendencia a 0 |
| Avisos de dependencias (Critical/High) | `pip_audit` mensual | 0 con más de 30 días |
| Cuentas activas sin revisión trimestral | Revisión de accesos | 0 |
| Cuentas activas de personas que ya no laboran | RR. HH. vs. usuarios | 0 |
| Incidentes de seguridad por trimestre (y tiempo de contención) | Registro de incidentes | Medir |
| Bloqueos de login por IP pública por semana | `seguridad.log` (`bloqueo_ip_login`) | Medir (señal de ataque) |
| Tickets de soporte: dentro del SLA, vencidos y sin atender | Módulo Tickets (SLA en horas laborales) | ≥ 90 % dentro del SLA |
| Errores 500 por semana | `logs/errores.log` | Tendencia a la baja |

## 7. Evaluación y mejora

- **Revisión anual** del plan por la Dirección, con los indicadores, los incidentes, los cambios de alcance y el estado de la matriz.
- **Auditoría interna**: una revisión técnica anual. Esta revisión del 09-nov-2026 sirve como línea base.
