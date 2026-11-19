# Auditoría de vulnerabilidades de dependencias — 26-ago-2026

> Respuesta al aviso de GitHub: *"110 vulnerabilities on default branch (4 critical, 45 high,
> 46 moderate, 15 low)"*. Auditoría **local, de solo lectura** (nada actualizado todavía).
> Herramientas: `pip-audit 2.10.1` sobre `requirements.txt` · `npm audit` sobre los dos lockfiles Node.

## 1. De dónde salen las 110 alertas
Dependabot escanea **3 manifiestos** trackeados en el repo:

| Manifiesto | Qué es | ¿Se usa en producción? |
|---|---|---|
| `system_proyect/requirements.txt` | Dependencias **Python** del sistema real (Django) | **SÍ** (es TechCare) |
| `frontend/package-lock.json` | App **Next.js 15 / React 19** "camaras-app" (prototipo) | **NO** — sin `dist/`, Apache no la sirve, Django no la referencia |
| `frontend_super/package-lock.json` | App **Next.js 15 / React 19** "portal-super-app" (prototipo del portal) | **NO** — ídem (solo un texto en `app_pendiente.html`) |

Los **conteos de GitHub (110) incluyen duplicados y transitivas** de los dos lockfiles Node (cada uno
con 94 paquetes) más los avisos Python. El resultado local consolidado es mucho más manejable:

## 2. Resultado Python (`requirements.txt`) — LO QUE IMPORTA (producción)
**8 paquetes con vulnerabilidades**, todas con versión de corrección disponible salvo una:

| Paquete | Instalado | Avisos | Corrige en | Riesgo real para TechCare |
|---|---|---|---|---|
| **Django** | 6.0.5 | 9 (PYSEC-2026-197…201, 2090…2092, 3717) | **6.0.8** | **ALTO** — framework central, expuesto a Internet |
| **Pillow** | 12.2.0 | 20 (procesamiento de imágenes) | **12.3.0** | **ALTO** — se suben fotos (tickets, cámaras, planos de red) |
| **PyJWT** | 2.12.1 | 8 | **2.13.0** | MEDIO — usado por `simplejwt` (API de cámaras) |
| **sqlparse** | 0.5.5 | 4 | **0.6.0** | MEDIO — dependencia de Django (parseo SQL en admin/debug) |
| **cryptography** | 49.0.0 | 1 | **50.0.0** | MEDIO |
| **idna** | 3.13 | 1 | **3.15** | BAJO |
| **tablib** | 3.9.0 | 1 | **3.10.0** | BAJO — usado por `django-import-export` |
| **weasyprint** | 68.1 | 1 (PYSEC-2026-3412) | **sin fix publicado** | BAJO — genera PDFs solo desde HTML propio, no de usuarios |

## 3. Resultado Node (`frontend/` y `frontend_super/`) — NO en producción
Idéntico en ambos: **1 crítica + 3 altas** (`next`, `postcss`, `nanoid`, `sharp`), todas con fix.
Como **no se despliegan**, **no exponen a TechCare**; solo "ensucian" el tablero de Dependabot.

## 4. Plan recomendado (por prioridad)

### A. Python — actualizar en producción (con respaldo y pruebas)
Cambios en `requirements.txt` → `pip install -r` en el venv → `manage.py check` + pruebas + humo →
reinicio Apache (verificar por `ps lstart`). Hacerlo en **ventana de bajo uso** y con **backup previo**
(el "actualiza todo" ya lo incluye).
1. `Django 6.0.5 → 6.0.8` *(parche de la misma serie 6.0: bajo riesgo de ruptura, mismo API)*.
2. `Pillow 12.2.0 → 12.3.0`.
3. `PyJWT 2.12.1 → 2.13.0`, `sqlparse 0.5.5 → 0.6.0`, `cryptography 49 → 50`, `idna 3.13 → 3.15`, `tablib 3.9 → 3.10`.
4. `weasyprint`: no hay fix; **aceptar el riesgo** (input controlado) y re-evaluar en el próximo ciclo.

### B. Node — decidir el destino de los prototipos (sin riesgo para producción)
Opciones (decisión del líder):
- **(Recomendada) Retirar `frontend/` y `frontend_super/` del repo** si ya no se van a continuar
  (el portal se rehízo en Django/Tabler; `frontend_super` quedó obsoleto). Se conservan en backup.
  Elimina de golpe la mayoría de las 110 alertas.
- O, si se van a retomar: `npm audit fix` / actualizar `next` a la versión parcheada en cada carpeta.

### C. Higiene de Dependabot
- Añadir `.github/dependabot.yml` para que proponga PRs automáticos de actualización (pip + npm) y
  no se acumulen alertas.
- `.gitignore` solo excluye `frontend/node_modules/`; añadir `frontend_super/node_modules/` (hoy no
  hay `node_modules` trackeado, pero conviene blindarlo).

## 5. Qué NO se hizo (a propósito)
No se actualizó ninguna librería ni se tocó producción: esto es un **informe**. La actualización
Python (plan A) se ejecuta cuando el líder la autorice, dentro de un "actualiza todo" con backup.
