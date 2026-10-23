# TechCare Pruebas — App de escritorio (Windows)

Envoltorio **Electron** que abre TechCare de **pruebas** (`http://192.168.10.6:451/`) en una
ventana nativa. No es PWA, no toca la base de datos ni usa API: solo muestra el sitio, igual
que el navegador. Funciona en PCs **dentro de la red de ANA**.

## Activar el workflow (una sola vez)
El YAML del CI está en `desktop/github-workflow.yml`. El token actual no tiene permiso para
crear workflows por push, así que **créalo desde la web** (una vez):
GitHub → repo `techcare-pruebas` → **Actions** → *New workflow* → *set up a workflow yourself* →
pega el contenido de `desktop/github-workflow.yml`, nómbralo `.github/workflows/desktop-build.yml` → **Commit**.

## Cómo se genera el instalador (sin compilar en Windows a mano)
El servidor es Linux y no compila Windows, así que lo hace **GitHub Actions**:

1. Entra a GitHub → repo `techcare-pruebas` → pestaña **Actions** → **Build Desktop (Windows)** → **Run workflow**.
   *(O se dispara solo al empujar un tag `desktop-v*`.)*
2. Cuando termine, descarga el artefacto **TechCare-Pruebas-Windows** (el `.exe` instalador).
   Si fue por tag, también queda en **Releases**.
3. Instálalo en la PC (Windows pedirá confirmar porque no está firmado: *Más información → Ejecutar de todos modos*).

## Cambiar la URL / versión
- URL del servidor: `main.js` (constante `APP_URL`) y `offline.html`.
- Versión: `package.json` → `"version"`.

## Compilar localmente (opcional, solo en Windows/Mac/Linux con Node)
```bash
cd desktop
npm install
npm start        # probar la app
npm run build    # genera el instalador en desktop/dist/ (Windows)
```
