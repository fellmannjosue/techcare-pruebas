# 9. Plan de capacitación del personal — TechCare

> Las fechas y los facilitadores los define la institución.

**Referencias:** ISO 27001:2022 6.3 (concienciación, educación y formación en seguridad de la información) · COBIT 2019 APO07 (Managed Human Resources).

## 1. Objetivo

Que cada persona use TechCare **de forma correcta y segura** según su rol, sepa proteger los datos de menores, médicos y del personal, y sepa qué hacer ante un incidente.

## 2. Públicos y módulos

| Módulo | Público | Duración sugerida | Contenido |
|---|---|---|---|
| **A. Inducción a TechCare (todos)** | Todo usuario nuevo y repaso anual | 45 min | Cómo entrar (web, .exe, APK); contraseña segura y frase de contraseña; "Recordar mis datos" solo en equipo propio; cierre de sesión en equipos compartidos; qué es información **restringida**; cómo pedir soporte (tickets, urgencia y SLA); cómo reportar un incidente |
| **B. Seguridad de la información y datos de menores** | Todo el personal con acceso a datos de alumnos | 60 min | Clasificación de la información; no compartir exportes ni fotos por canales personales; enlaces públicos de reportes; phishing (TI nunca pide la contraseña); uso responsable de la IA ("redactar con IA": sin nombres completos ni datos médicos); casos reales anonimizados |
| **C1. Maestros** | Maestros BL, Colegio, CFP | 60–90 min por rol | Reportes conductuales e informativos, Progress Report (borrador → enviar), evidencias; Notas mitad de parcial y fechas de cierre; Ingreso de Notas (rangos, tareas en orden, asistencias); agendas; salidas al baño |
| **C2. Coordinaciones** | Coordinadores BL y Colegio | 90 min | Dashboard por estados (Enviado → Revisado → Aprobado), firmas, ZIP; cierre de parcial y revocar permisos; maestro guía; ruteo BL y permisos por coordinador; período escolar; **responsabilidad sobre los accesos de su gente** (revisión trimestral) |
| **C3. Enfermería** | Enfermería | 60 min | Atenciones, envío de la ficha a los correos registrados, directorio; confidencialidad médica; qué no borrar (bitácora) |
| **C4. Administración y RR. HH.** | Reloj, compensatorio, contabilidad, CFP, Sponsors | 60–90 min por módulo | Uso del módulo; exportes y su resguardo |
| **C5. Soporte técnico** | Técnicos | 90 min | Tickets y SLA (horas laborales, pausas), Servicio Técnico (registrar, fichas, laboratorios), inventario, préstamos y firmas |
| **D. Administración técnica (TI)** | Administrador y **segunda persona de respaldo** | 4–6 h en 2 sesiones | Despliegue (guía 04), verificación del reinicio de Apache, `collectstatic`, logs (`seguridad.log`, `errores.log`), respaldo y **restauración práctica** (05), incidentes (06), altas y bajas de usuarios (10), lista blanca, programas ocultos y mantenimiento, rotación de credenciales |
| **E. Desarrollo seguro** | Quien desarrolle o modifique TechCare (incluida la supervisión de herramientas de IA) | 2–3 h | [Política de desarrollo](politicas/politica_desarrollo_software.md): autorización en el servidor, IDOR, XSS, SQL parametrizado, archivos; pruebas con `settings_test.py`; [política de cambios](politicas/politica_cambios.md) |

## 3. Calendario

| Momento | Actividad |
|---|---|
| Al dar de alta una cuenta | Módulo A (puede ser un video corto con checklist) + el módulo C de su rol |
| Inicio del año escolar | Módulos A y B para todo el personal; C1/C2 para docentes y coordinaciones (cambios de versión) |
| Antes de cada cierre de parcial | Repaso de 15 min de Notas e Ingreso de Notas (C1/C2) |
| Cada release general (2.º segmento de versión) | Nota de novedades (ventana "Novedades" del sistema) + sesión corta si cambia un flujo |
| Semestral | Módulo D: ensayo de restauración con la segunda persona |
| Anual | Simulacro de phishing o de incidente (opcional) |

## 4. Materiales

- Guías por rol en esta carpeta (se publican en **TechCare → Configuración → Documentación**).
- La ventana de **Novedades** de TechCare (changelog por versión).
- El **Asistente IA** de TechCare como apoyo de uso (no reemplaza la capacitación ni debe recibir datos sensibles).
- **[Por crear]:** videos cortos por módulo y checklist imprimible de la inducción.

## 5. Registro y evaluación

| Registro | Detalle |
|---|---|
| Asistencia | Lista por sesión: nombre, rol, módulo y fecha. Archivada por RR. HH. |
| Evaluación | Cuestionario corto de 5 preguntas al cierre de los módulos A y B; meta ≥ 80 % de aciertos |
| Indicadores | % del personal con A+B al día (meta 100 % de cuentas activas); % de cuentas nuevas con inducción antes de 7 días; tickets por "no sé cómo…" por módulo (debe bajar tras la capacitación) |
| Condición propuesta | Los accesos a información **restringida** (enfermería, coordinación, notas) se otorgan tras completar el módulo B |
