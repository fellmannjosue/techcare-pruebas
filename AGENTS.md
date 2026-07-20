# AGENTS.md — Guía para agentes/IA en TechCare

Contexto operativo del proyecto para cualquier agente (Claude Code u otro). El
detalle funcional por módulo está en `README.md`; aquí va lo necesario para
**trabajar y desplegar** sin romper nada. **Este archivo NO contiene
credenciales** (contraseñas, tokens, claves). Nunca las agregues aquí ni a
ningún archivo versionado.

## Qué es
Sistema web Django para la **Asociación Nuevo Amanecer (ANA)**. Centraliza
tickets, asistencia (reloj), conducta, inventario, enfermería, agendas, notas
parciales, sponsors, mantenimiento, CFP y calculadoras.

- Producción: https://servicios.ana-hn.org:437 · Apache + mod_wsgi
- Stack: Django 6 · Python 3.13 (venv `venv313`) · MySQL (principal) + SQL Server (reloj y datos de alumnos)
- UI: Tabler UI (beta19) + Tabler Icons webfont · Admin: Unfold

## Layout del repo
- Código: `system_proyect/` (una app Django por dominio: `accounts`, `conducta`, `reloj`, `core`, …).
- Cada app tiene su **propia plantilla base** con `<html>` completo (no hay un base global único).
- Estáticos servidos por Apache desde `system_proyect/staticfiles/` (generada por `collectstatic`).
- `media/` está en `.gitignore` — **datos de alumnos/config no se versionan** (ej. `media/conducta/routing_bl.json`).

## Ejecutar / verificar (siempre desde `system_proyect/`)
```bash
cd /home/admin2/techcare_project/system_proyect
../venv313/bin/python manage.py check          # antes de dar por hecho cualquier cambio
../venv313/bin/python manage.py makemigrations && ../venv313/bin/python manage.py migrate
```
- **Test client:** pasar `SERVER_NAME='servicios.ana-hn.org'` (ALLOWED_HOSTS).
- Para módulos MySQL/SQL Server, correr contra la BD real (no hay fixtures).

## Desplegar (aplicar cambios en producción)
Cambios de **Python/settings/middleware** → reiniciar Apache. Cambios de
**templates** → normalmente basta el reinicio. Cambios de **JS/CSS** →
`collectstatic` + bump `?v=N` en el `<script>/<link>` + reiniciar.

```bash
../venv313/bin/python manage.py collectstatic --noinput   # requiere sudo (archivos de www-data)
sudo systemctl restart apache2
```
La contraseña sudo del servidor **no** está aquí; el operador la conoce (o está
en la memoria privada del agente, nunca en el repo). Apache corre como
**`www-data`**: puede **leer** el repo pero **no** escribir archivos de admin2
ni ejecutar `git` en este repo. Scripts que deban escribir archivos de www-data
(ej. `media/conducta/routing_bl.json`) se corren con `sudo -u www-data`.

## Convenciones
- **Comentarios de autoría en templates:** `{# <--- hecho por claude code: ... #}` (una línea; nunca `<!--{# ... #}-->`).
- Variables Django→JS: preferir `data-*` en un `<div hidden>` o `|json_script`; evitar `<script>` con literales Django salvo casos heredados.
- Badges Tabler: `bg-blue-lt text-blue`, `bg-orange-lt text-orange`, `bg-green-lt text-green`, etc.
- Roles = **grupos de Django por nombre** (revisados en `core/context_processors.py`, `accounts/panel_roles.py`). Casi ninguno usa permisos de Django (excepción: `inventario`). Los permisos del Reloj vienen del modelo `reloj.RelojPermiso`.

## Versionado y novedades
- Versión y changelog en `core/changelog.json`; lo lee `core/version.py`, lo expone `version_context`, y `templates/_version_footer.html` pinta el pie + el modal.
- `manage.py gen_changelog` genera entradas desde `git log` y sube el build; lo dispara `.git/hooks/post-commit`. Marcador de rango en `.git/changelog_base` (local, sobrevive a `--amend`).
- `PerfilUsuario.version_vista` recuerda qué versión vio cada usuario.

## Ruteo de reportes Bilingüe (área activa reciente)
- Pantalla única `conducta/routing_bl.html` (`routing_bl_config`); config en `media/conducta/routing_bl.json` (no BD, no versionado).
- Decisión de coordinador: `_coord_bl(materia, docente, grado)` → override único fuerza → materia manda (C3/C4) → grupo/grado (C1 grados 1-3, C2 grados 4-9) → override múltiple restringe por grado. Un docente puede reportar a **varios** coordinadores (override = unión de sus cargas).
- Nombres/correos de coordinadores: C1 cvarela · C2 druiz · C3 ialcerro · C4 jmartinez.
- Permisos por coordinador (`coord_permisos`): `none` / `lectura` / `edit`; los endpoints de guardar usan `_puede_editar_ruteo`.

## Gotchas
- **Nunca** borrar/pisar `media/conducta/routing_bl.json` en pruebas: contiene la config real (alumnos, grupos, catálogo). Escribir solo vía la app o `sudo -u www-data`.
- `git` en este repo se hace **directo a `main`** (flujo del proyecto). Rama principal = `main`.
- Al terminar código: `manage.py check` verde y, si corresponde, reiniciar Apache.
