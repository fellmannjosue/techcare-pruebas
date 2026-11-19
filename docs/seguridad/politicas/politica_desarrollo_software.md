# Política de desarrollo de software — TechCare

> Recoge las convenciones técnicas que ya se aplican en el proyecto (ver `AGENTS.md`) y les suma requisitos de seguridad.

**Referencias:** ISO 27001:2022 8.25 (ciclo de vida de desarrollo seguro), 8.26 (requisitos de seguridad de las aplicaciones), 8.28 (codificación segura), 8.29 (pruebas de seguridad en desarrollo y aceptación), 8.31 (separación de entornos), 8.8 (vulnerabilidades técnicas) · COBIT 2019 BAI03, BAI06, BAI07.

## 1. Ciclo de vida

| Etapa | Requisito |
|---|---|
| Solicitud | Todo desarrollo nace de un requerimiento en **Gestión de Desarrollo** con su solicitante y su prioridad |
| Diseño | Se identifica **qué datos toca** (¿menores, médicos, credenciales?) y **quién debe poder verlos**. Si el módulo es nuevo: registrarlo en `core/programas.py`, en `core/admin_nav.py` y en el panel |
| Construcción | Codificación segura (§2) en una rama, nunca en producción |
| Pruebas | §3 |
| Despliegue | [Política de cambios](politica_cambios.md) |
| Mantenimiento | Revisión mensual de dependencias (§4) |

## 2. Codificación segura (reglas obligatorias)

**Autorización y sesión**
1. Toda vista exige sesión (el middleware global lo hace). Una vista pública solo con `@login_not_required` explícito y justificado en un comentario.
2. Toda vista valida **en el servidor** el grupo y el **área del objeto**. Los objetos pedidos por id se filtran por dueño o área (`get_object_or_404(Modelo, pk=pk)` sin chequeo **no** basta).
3. Las vistas que cambian datos aceptan solo **POST** con CSRF. Nada de borrar por GET.
4. Roles por nombre exacto de grupo; `is_staff` no es un rol.

**Entradas y consultas**
1. SQL **siempre parametrizado** (`%s`). Los nombres de tabla o columna variables solo pueden salir de listas cerradas.
2. Los ids se validan con `str.isdecimal()` antes de convertirlos.

**Salidas, XSS y JavaScript**
1. Plantillas con autoescape. `|safe` y `mark_safe` solo con datos que **no** vienen del usuario; si no, `format_html`.
2. En JavaScript, el texto del usuario se pinta con `textContent` o con escape. Nunca `innerHTML` con datos sin escapar.
3. JSON en `data-*` va **sin** `|safe`; para blobs grandes, `|json_script`. Nunca `|escapejs` en atributos.
4. Nada de JS ni CSS dentro del HTML: van en `static/<app>/js|css`, con un identificador global propio por archivo.

**Archivos**
1. Subidas con lista blanca de tipos, verificación real (Pillow `verify`, cabecera `%PDF`), tamaño máximo y **nombre generado** (uuid).
2. Lo subido se sirve **por una vista con permiso**, con `nosniff`, y nunca como página (html/svg en línea).
3. Toda carpeta nueva de `media/` nace cerrada en Apache.

**Secretos y datos**
1. Los secretos solo van en el `.env`. Nada de credenciales en el código, en `AGENTS.md`, en commits ni en la memoria de herramientas.
2. Las pruebas usan datos **sintéticos**. Prohibido probar con POST reales contra producción.
3. Los registros nunca guardan contraseñas, tokens ni contenido médico (`core/seguridad_eventos.py` lo aplica para la bitácora de seguridad).
4. Los eventos sensibles nuevos (borrados de expedientes, cambios de permisos, exportes masivos) se registran con `core.seguridad_eventos.evento()`.

**Integraciones**
1. HTTPS obligatorio hacia servicios externos.
2. Tokens con el alcance mínimo.
3. Timeouts en toda llamada saliente.

## 3. Pruebas

1. **Mínimo para todo cambio:** `manage.py check`, `node --check` de los JS tocados y la suite de pruebas:
   ```bash
   DJANGO_SECRET_KEY=solo-pruebas ../venv/bin/python manage.py test --settings=system_proyect.settings_test
   ```
2. Todo cambio de permisos agrega o actualiza pruebas en `core/tests_seguridad.py` (o en el `tests.py` del módulo). Casos mínimos: sin sesión, sin permiso, objeto de otra área o de otro usuario, y caso permitido.
3. Una regresión de seguridad corregida debe tener su prueba, para que no vuelva.
4. Las pantallas se prueban en el entorno de pruebas antes de pasar a producción.

## 4. Dependencias

1. `pip_audit -r system_proyect/requirements.txt` cada mes y antes de cada release.
2. Los parches menores se aplican en la siguiente ventana. Las versiones mayores se prueban primero en el entorno de pruebas.
3. Las librerías JS por CDN se fijan a una versión exacta.
4. No versionar `package-lock.json` de prototipos que no se despliegan.

## 5. Uso de asistentes de IA en el desarrollo

1. El código generado por IA pasa por la **misma revisión y las mismas pruebas**.
2. La IA no debe recibir credenciales. Si las necesita para operar, deben estar en un mecanismo acotado (por ejemplo, `sudoers` limitado), no en su memoria.
3. La IA trabaja en ramas o en copias aparte y no hace commit ni push a producción sin orden explícita del responsable (regla vigente).
