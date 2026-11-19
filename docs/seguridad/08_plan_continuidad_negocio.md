# 8. Plan de continuidad del negocio — TechCare

> Los tiempos de recuperación (RTO) y la pérdida de datos tolerable (RPO) son **propuestas**: la Dirección y los dueños de los procesos deben confirmarlos.

**Referencias:** ISO 27001:2022 5.29 (la seguridad de la información durante una interrupción), 5.30 (preparación de las TIC para la continuidad), 8.13 (respaldo), 8.14 (redundancia) · COBIT 2019 DSS04 (Managed Continuity), BAI09 (activos), BAI10 (configuración).

## 1. Inventario de componentes y dependencias

| Componente | Función | Ubicación / responsable | Si falla… |
|---|---|---|---|
| Servidor Ubuntu (Apache + mod_wsgi) | Aloja TechCare y el feed de actualizaciones del .exe | Servidor institucional / TI | **Todo TechCare cae** |
| MySQL `sponsors2` | Base principal: usuarios, tickets, conducta, enfermería, reloj (cálculos), inventario, contabilidad… | Mismo servidor / TI | Todo TechCare cae |
| SQL Server académico (Test2 / AdmonANASQL) | Alumnos, notas, matrícula; Ingreso de Notas escribe aquí | Otra área / [DBA por confirmar] | Notas, Ingreso de Notas, directorios y listas de alumnos fallan. **Se apaga de noche (~21:00–06:00)** |
| SQL Server ZKBio | Marcas del reloj | Otra área | Reloj sin marcas nuevas |
| Correo SMTP (Gmail y cuentas institucionales) | Recuperación de contraseña, 2FA, avisos, fichas médicas | Google / TI | No llegan correos; con el 2FA encendido, nadie entra al vencer |
| Moodle | Publicación de agendas | Servidor `mail` / TI | Solo la publicación |
| API de Anthropic | Asistente IA | Proveedor externo | Solo el asistente |
| GitHub | Código y compilación de las apps | Proveedor externo | No se pueden publicar versiones nuevas de las apps |
| Feed :453 | Actualizaciones del .exe | Mismo servidor | Las apps no se actualizan, pero funcionan |
| Respaldos | Recuperación | `/home/admin2/backups` + copia externa (**fallando**) | Sin recuperación posible |
| DNS / certificado TLS | Acceso por `servicios.ana-hn.org:437` | TI | Navegadores y apps no conectan |

## 2. Procesos críticos y objetivos

| Proceso | Módulos | Impacto si se detiene | RTO propuesto | RPO propuesto |
|---|---|---|---|---|
| Atención de enfermería | Enfermería | Alto (salud de menores; la atención sigue en papel) | 4 h | 24 h |
| Reportes de conducta y comunicación con familias | Conducta | Medio | 1 día hábil | 24 h |
| Notas y cierre de parcial | Notas mitad de parcial, Ingreso de Notas | **Alto en semana de cierre**, bajo el resto del tiempo | 4 h en cierre, 1 día fuera de él | 24 h (las notas viven en SQL Server) |
| Asistencia del personal | Reloj | Medio (cálculo mensual) | 2 días | Las marcas viven en ZKBio |
| Soporte técnico | Tickets, Servicio Técnico | Medio | 1 día | 24 h |
| Contabilidad, CFP, Sponsors | — | Medio | 2 días | 24 h |
| Resto (agendas, datashow, mant. mecánico, red, calculadoras) | — | Bajo | 3 días | 7 días |

**Brecha actual:** el RPO real es de hasta **31 días** (respaldo mensual) y sin copia externa vigente. **No cumple** ninguno de los objetivos propuestos hasta que se implemente el respaldo diario y se repare la copia externa (ver [05](05_respaldo_restauracion.md)).

## 3. Escenarios y respuesta

| Escenario | Respuesta | Tiempo estimado (a validar en un ensayo) |
|---|---|---|
| **Apache caído o error de código** tras un despliegue | Ver `logs/errores.log` y los logs de Apache; revertir el despliegue (guía §4.4) y reiniciar, verificando la hora de arranque | 15–60 min |
| **SQL Server académico apagado** (noche, mantenimiento) | Normal fuera de horario. En horario: avisar a las áreas; las pantallas de notas fallan, el resto sigue | Depende de otra área |
| **Base MySQL dañada o borrado masivo** | Modo mantenimiento → restaurar el último volcado en una base aparte → verificar → cambiar (05 §5.4 B) → informar los datos perdidos desde el respaldo | 2–4 h + recaptura |
| **Servidor perdido** (disco, robo, ransomware) | Servidor nuevo con Ubuntu: Apache, mod_wsgi, Python 3.13, MySQL. Restaurar el código desde el tar (incluye las migraciones) y la BD desde el volcado. Reponer el `.env` desde su copia cifrada, el vhost y el certificado. Recrear el venv con `requirements.txt` y los crons | **1–3 días**, *solo si existe una copia externa vigente* |
| **Ransomware o compromiso** | Además: [procedimiento de incidentes](06_procedimiento_incidentes.md). No restaurar sobre el sistema comprometido; rotar **todas** las credenciales | + días |
| **Correo caído** | El 2FA debe tener plan B: apagarlo temporalmente con `DOSFA_ACTIVO` (decisión del responsable, registrada) | Minutos |
| **Persona clave no disponible** (el único administrador) | Este documento, la guía de despliegue y `AGENTS.md`. **Falta:** credenciales en custodia institucional (sobre sellado o gestor) y una segunda persona capacitada | — |

## 4. Medidas para cerrar las brechas

1. Restablecer la **copia externa** en un destino institucional siempre encendido, con alerta.
2. Volcado **diario** de MySQL y respaldo del vhost, el crontab y `/etc` relevante.
3. **Custodia de credenciales:** `.env` cifrado fuera del servidor, acceso de 2 personas.
4. **Segunda persona** capacitada en despliegue, reinicio y restauración (ver el [plan de capacitación](09_plan_capacitacion.md), módulo D).
5. **Procedimientos manuales alternos** por área durante una caída:
   - Enfermería: formato en papel de atención.
   - Conducta: reporte en papel que se digitaliza después.
   - Soporte: tickets por correo o teléfono.
6. **Ensayo anual:** restaurar el sistema completo en un servidor de prueba y medir el tiempo real.

## 5. Activación y comunicación

- **Quién declara la contingencia:** responsable de seguridad o administrador técnico **[por designar]**, informando a la Dirección.
- **Aviso a los usuarios:** modo mantenimiento con mensaje (TechCare lo trae), correo o grupos institucionales.
- **Fin de la contingencia:** cuando los procesos críticos funcionan y los datos están verificados. Se registra el informe de cierre.
