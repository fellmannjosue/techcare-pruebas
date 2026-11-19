# Política de contraseñas y autenticación — TechCare

> Lo marcado **(vigente en el sistema)** ya lo aplica el software hoy, o la rama del 09-nov-2026 si se indica. Lo demás es una propuesta.

**Referencias:** ISO 27001:2022 5.17 (información de autenticación), 8.5 (autenticación segura) · COBIT 2019 DSS05.

## 1. Alcance

Todas las cuentas de TechCare (web, app de escritorio y app móvil), las cuentas de servicio y las credenciales técnicas: bases de datos, servidor y API.

## 2. Requisitos de la contraseña

| Requisito | Estado |
|---|---|
| Mínimo **8** caracteres | **Vigente en el sistema** (`MinimumLengthValidator`, valor por defecto de Django) |
| No parecida al nombre, usuario o correo | **Vigente** (`UserAttributeSimilarityValidator`) |
| No estar en la lista de ~20 000 contraseñas comunes | **Vigente** (`CommonPasswordValidator`) |
| No ser solo números | **Vigente** (`NumericPasswordValidator`) |
| **Propuesta:** mínimo **12** caracteres para staff y superusuario. Se recomienda una **frase de contraseña** (varias palabras) en lugar de símbolos forzados | Pendiente: requiere `OPTIONS: {'min_length': 12}` |
| No reutilizar la contraseña del correo personal ni de otros servicios | Política (no verificable por el sistema) |

**No** se exige cambio periódico obligatorio: la práctica actual recomienda cambiarla **solo cuando hay sospecha de compromiso** o cuando lo pide el sistema. Si la Dirección prefiere vencimiento periódico, debe indicarlo al aprobar.

## 3. Protección contra adivinación

| Control | Estado |
|---|---|
| 3 fallos → espera de 1 minuto; 5 fallos en 15 min → **bloqueo** de la cuenta hasta que el superusuario la desbloquee (se pide por ticket) | **Vigente** (decisión del 05-nov-2026) |
| El superusuario recibe la espera de 1 minuto cada 3 fallos, nunca el bloqueo total | **Rama del 09-nov-2026** |
| Desde internet: 20 fallos por IP en 15 min → espera de 15 minutos | **Rama del 09-nov-2026** |
| Todo fallo, bloqueo y acceso queda en `logs/seguridad.log` | **Rama del 09-nov-2026** |

## 4. Recuperación y entrega de contraseñas

| Control | Estado |
|---|---|
| Recuperación por enlace al correo institucional; el enlace vence en **24 horas** y sirve una sola vez | **Rama del 09-nov-2026** (antes duraba 3 días) |
| Máximo 3 solicitudes por correo por hora; la pantalla no revela si el correo existe | **Rama del 09-nov-2026** |
| **Propuesta:** la cuenta nueva recibe un **enlace para crear su contraseña**, no la contraseña por correo | Pendiente (R10) |
| El personal de TI **nunca pide** la contraseña de un usuario, ni por teléfono, correo, chat o en persona. Para revisar algo como el usuario, el superusuario usa "Iniciar sesión como", que queda registrado | Política |

## 5. Segundo factor (2FA)

- Existe un 2FA por correo con códigos de 6 dígitos, 10 minutos de validez y 5 intentos. Se pide cada 15 días al superusuario, cada 30 a staff y cada 60 al resto. **Hoy está apagado** (`DOSFA_ACTIVO`).
- **Propuesta:**
  - Encenderlo **para el superusuario y staff** una vez confirmado que el correo saliente funciona.
  - A mediano plazo, una aplicación de autenticación (TOTP) para el superusuario.

## 6. Sesiones

| Control | Estado |
|---|---|
| Cierre por **inactividad a los 240 minutos** (configurable) y tope de 7 días | **Vigente** |
| Cookies solo por HTTPS, inaccesibles a JavaScript | **Vigente** |
| "Recordar mis datos" guarda usuario y contraseña en el equipo por 1 mes (ofuscados, **no cifrados**) | **Vigente.** **Propuesta:** usarlo solo en equipos personales y nunca en equipos compartidos (laboratorios, sala de maestros) |

## 7. Responsabilidades del usuario

1. La contraseña es personal e intransferible. Prestar la cuenta es una falta.
2. No anotarla en papel visible, en archivos sin cifrar ni en chats.
3. Cerrar sesión al dejar un equipo compartido.
4. Si sospecha que alguien la conoce: cambiarla de inmediato y avisar por ticket (ver [incidentes](../06_procedimiento_incidentes.md)).

## 8. Credenciales técnicas (TI)

1. Viven solo en el `.env` del servidor (permisos `640`, grupo `www-data`) o en un **gestor de contraseñas institucional [por definir]**.
2. **Nunca** se escriben en el código, en git, en tickets, en documentación, en chats ni en la memoria de herramientas de IA.
3. Se **rotan** cuando: sale una persona que las conocía, aparecen en un lugar indebido, o una vez al año como mínimo.
4. **Excepción documentada:** `SECRET_KEY` no se rota hasta separar la clave de cifrado de Red y Moodle (ver la guía §4.6).
