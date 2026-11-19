# 10. Proceso de creación, modificación y baja de usuarios — TechCare

> La sección **10.1 describe cómo funciona HOY**, verificado en el código el 09-nov-2026. Las secciones 10.2 a 10.5 son el **procedimiento a seguir**.

**Referencias:** ISO 27001:2022 5.16 (gestión de identidades), 5.18 (derechos de acceso), 8.2 (derechos de acceso privilegiado), 5.17 (información de autenticación) · COBIT 2019 DSS05, APO07.

## 10.1 Funcionamiento actual (verificado en el código)

**Quién puede crear cuentas**
- El **superusuario**.
- Un **gestor delegado**: usuario staff con la casilla "puede ver usuarios" en su perfil (`_can_manage`). El gestor delegado **solo** puede:
  - crear cuentas **sin** staff;
  - asignar o quitar estos grupos (`_GRUPOS_DELEGABLES`): `maestros_bilingue`, `maestros_colegio`, `maestros_notas_parcial_bl`, `maestros_notas_parcial_col`, `instructores`, `instructores_cfp`;
  - y no puede editar a superusuarios ni a cuentas staff, cambiar contraseñas ajenas, borrar usuarios ni crear grupos.
- La creación se puede **apagar** con el interruptor `REGISTRO_USUARIOS_ACTIVO`, en Configuración → Seguridad.

**Controles al crear**

| Control | Dónde |
|---|---|
| El correo debe ser `@ana-hn.org` y **estar en la lista blanca** de correos institucionales (`CorreoInstitucional`, gestionada en Configuración → Seguridad, con import/export). El superusuario puede saltarse la lista en `settings_usuario_crear` | `accounts/forms.py`, `accounts/views.py` |
| El usuario es el mismo correo; no puede repetir el usuario o correo de otra cuenta | Ídem |
| Contraseña validada con los 4 validadores de Django (ver la [política de contraseñas](politicas/politica_contrasenas.md)) | Ídem |
| Grupo según área y cargo: docente BL → `maestros_bilingue`; docente Colegio → `maestros_colegio`; instructor CFP → `instructores`; coordinador BL → `coordinador_bilingue` + staff; coordinador Colegio → `coordinador_colegio` + staff; Administración → `administracion` + staff | `_grupo_de_registro` |
| Un usuario **no staff** solo puede iniciar sesión si alguno de sus grupos está en `_GRUPO_A_ROL`; si no, el login dice "Credenciales inválidas" | `accounts/views.py` |
| Desde el 09-nov-2026 (rama) cada alta, cambio de privilegio, de grupo o de contraseña y cada baja queda en `logs/seguridad.log` | `core/seguridad_eventos.py` |

**Debilidades actuales:**
- La contraseña inicial **viaja en el correo de bienvenida** y no se obliga a cambiarla en el primer acceso (R10).
- No hay **solicitud ni aprobación** registrada de quién pidió la cuenta y quién la autorizó.
- No hay **revisión periódica** de accesos ni proceso de baja ligado a RR. HH.

## 10.2 Proceso propuesto de ALTA

| Paso | Quién | Qué | Registro |
|---|---|---|---|
| 1 | Jefatura del área (Coordinación, Dirección o Administración) | Solicita la cuenta: nombre, correo institucional, área, cargo, módulos que necesita y fecha de inicio | Ticket en TechCare, categoría "Acceso" **[a crear]** |
| 2 | Responsable de accesos **[por designar]** | Verifica que la persona está activa en RR. HH. y que el correo existe en la lista blanca | Comentario en el ticket |
| 3 | Dueño de la información del módulo | **Aprueba** los accesos sensibles: Enfermería, Conducta (coordinación), Notas (ingreso), Reloj, Contabilidad, Red, Sponsors | Comentario en el ticket |
| 4 | Gestor (superusuario o delegado) | Crea la cuenta con **el mínimo de grupos** necesario. Staff solo si el rol lo exige | Automático: `seguridad.log` + historial |
| 5 | Sistema | **Propuesta técnica (R10):** en lugar de enviar la contraseña, enviar un enlace de "crear contraseña" de un solo uso (24 h) | Correo |
| 6 | Usuario | Crea su contraseña, la mantiene en secreto y recibe la [inducción](09_plan_capacitacion.md) | — |

## 10.3 MODIFICACIÓN de accesos

- Cambio de cargo o de área: nueva solicitud por ticket. **Se quitan los grupos que ya no corresponden el mismo día** (no se acumulan).
- Acceso temporal (suplencia, auditoría): con **fecha de fin** anotada en el ticket; el responsable lo retira al vencer.
- Privilegios elevados (staff, `red_admin`, `contabilidad_*`, `coordinador_*`, `enfermeria`): solo con aprobación de Dirección o del dueño de la información.

## 10.4 BAJA

| Evento | Plazo | Acción |
|---|---|---|
| Fin de contrato o salida | **El mismo día** (RR. HH. avisa) | Desactivar la cuenta (`is_active = False`). **No borrarla**, para conservar el historial y la autoría de reportes y notas. Quitar los grupos. Quitar el correo de la lista blanca |
| Licencia prolongada (> 30 días) | Al inicio | Desactivar temporalmente |
| Cuenta sin uso por 90 días | Revisión trimestral | Confirmar con el área y desactivar si no se necesita |

## 10.5 Revisión periódica de accesos

- **Trimestral:** el responsable de accesos exporta usuarios activos y grupos (Configuración → Usuarios) y cada jefatura confirma su gente. Las diferencias se corrigen y se anotan en un ticket.
- **Mensual:** revisar los superusuarios (debe haber **1**), los staff y los grupos sensibles, y la bitácora de suplantaciones.
- **Cuentas de servicio** (tokens de la API de Red, conexión de Moodle): inventario con responsable y fecha de revisión.
