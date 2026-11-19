# 6. Procedimiento de gestión de incidentes de seguridad — TechCare

**Referencias:** ISO 27001:2022 5.24 (planificación y preparación de la gestión de incidentes), 5.26 (respuesta a incidentes) · COBIT 2019 DSS02 (solicitudes de servicio e incidentes), DSS03 (problemas).

## 6.1 Qué es un incidente de seguridad

Ejemplos aplicables a TechCare:

- Acceso a datos de menores, médicos o del personal por alguien que no debía. Incluye un enlace reenviado o una cuenta prestada.
- Cuenta comprometida: contraseña filtrada, inicio de sesión que el usuario no reconoce, cambios de grupos o permisos no autorizados.
- Credenciales expuestas: `.env`, contraseñas en un correo, un chat, un repositorio o una captura de pantalla.
- Pérdida o robo de un equipo con sesión abierta o con respaldos.
- Archivo malicioso subido, cambios en el código o en el servidor que nadie hizo.
- Indisponibilidad grave: sistema caído, base de datos dañada, ransomware.
- Datos borrados o alterados (notas, atenciones médicas, reportes).

## 6.2 Roles (por designar)

| Rol | Función | Persona |
|---|---|---|
| Responsable de seguridad de TechCare | Coordina la respuesta y decide la contención | [Responsable por designar] |
| Administrador técnico | Ejecuta la contención y la restauración en el servidor | [Responsable por designar] |
| Dirección | Decide las comunicaciones a familias, personal o autoridades | [Responsable por designar] |
| Dueños de la información | Validan el alcance: Enfermería, Coordinaciones, Contabilidad, RR. HH. | [Por área] |

**Segregación:** quien causó o detectó el incidente no debe ser el único que lo investiga.

## 6.3 Cómo se reporta

- **Cualquier persona** reporta lo antes posible, **sin intentar investigar por su cuenta**.
- **Canal:** un ticket en TechCare de categoría Soporte, con urgencia **Urgente**, o comunicación directa con el responsable si el sistema no está disponible. **[Canal alterno por definir:** teléfono o correo de guardia**]**.
- **No** reenviar el dato expuesto ni capturas con datos personales dentro del reporte. Basta con describir qué pasó, cuándo y dónde.

## 6.4 Fases de la respuesta

| Fase | Qué hacer | Herramientas en TechCare |
|---|---|---|
| **1. Registrar** | Abrir un expediente del incidente: fecha y hora, quién reporta, descripción y sistemas afectados | Ticket o requerimiento de Gestión de Desarrollo |
| **2. Clasificar** | **Severidad:** Crítica = datos de menores o médicos expuestos, credenciales de BD, sistema caído; Alta; Media; Baja | Matriz de 02_matriz_riesgos.md como guía |
| **3. Contener** | Según el caso, ver la tabla siguiente | — |
| **4. Preservar evidencia** | **Antes** de limpiar, copiar los logs y el estado | `logs/seguridad.log`, `logs/errores.log`, logs de Apache (`/var/log/apache2/servicios_ana_*`), historial (`simple_history`), Registro de accesos, Suplantaciones, `EscrituraNota` |
| **5. Erradicar y recuperar** | Corregir la causa, restaurar desde un respaldo si hace falta (ver [05](05_respaldo_restauracion.md)) y verificar | — |
| **6. Comunicar** | Decisión de la Dirección: a quién, qué y cuándo. Revisar las obligaciones legales aplicables en Honduras sobre datos personales y de menores **[pendiente de asesoría legal]** | — |
| **7. Cerrar y aprender** | Informe breve: causa raíz, impacto, acciones, qué cambiar. Si la causa se repite, abrir un **problema** (COBIT DSS03) | Requerimiento en Gestión de Desarrollo |

**Contención por tipo de incidente:**

| Situación | Acción inmediata |
|---|---|
| Cuenta comprometida | Desactivar la cuenta (Configuración → Usuarios → inactivo). Cambiar su contraseña. Revisar sus grupos y lo que hizo (historial y `seguridad.log`) |
| Superusuario comprometido | Cambiar la contraseña. Revisar `seguridad.log` (privilegios, grupos, configuración) y la bitácora de suplantaciones. Encender `DOSFA_ACTIVO` |
| Credencial de BD o servidor expuesta | **Rotarla** (ver la guía §4.6), actualizar el `.env` y reiniciar Apache |
| Un módulo filtra datos | Configuración → Seguridad → **Programas ocultos** (bloquea el módulo para todos) o modo mantenimiento por formulario (`lectura` / `bloqueado`) |
| Todo el sistema comprometido | Modo mantenimiento general (constance `MAINTENANCE_MODE`) o detener Apache |
| Archivo malicioso en `/media/` | No abrirlo. Moverlo fuera de `/media/` a una carpeta sin acceso web, conservar una copia como evidencia y revisar los logs de Apache por accesos a esa ruta |

## 6.5 Tiempos objetivo

| Severidad | Primera respuesta | Contención |
|---|---|---|
| Crítica | 1 hora laboral | Mismo día |
| Alta | 4 horas laborales | 1 día hábil |
| Media | 1 día hábil | 1 semana |
| Baja | 1 semana | Próxima ventana de cambios |

## 6.6 Revisión periódica (monitoreo)

Propuesta: el responsable revisa cada **semana** `logs/seguridad.log` y busca:
- `usuario_privilegios`, `grupos_add` hacia grupos sensibles (`enfermeria`, `coordinador_*`, `red_admin`).
- `bloqueo_ip_login`, `bloqueo_cuenta_login`.
- `configuracion_cambiada`.
- `enfermeria_atencion_eliminada`.

Cualquier evento que nadie reconozca se trata como incidente.
