# TechCare Pruebas — App de escritorio (Windows)

Envoltorio **Electron** que abre TechCare de **pruebas** (`http://192.168.10.6:451/`) en una
ventana nativa. No es PWA, no toca la base de datos ni usa API: solo muestra el sitio, igual
que el navegador. Funciona en PCs **dentro de la red de ANA**.

## Shell nativo (no se ve como el navegador)
La ventana **no usa el marco del sistema** (`frame:false`). La dibuja un shell propio:

- `shell.html` + `shell-preload.js` — **barra superior nativa**: marca ANA, pastilla *Pruebas*,
  navegación **Atrás / Adelante / Inicio / Recargar**, botón **Novedades** (con punto de aviso) y
  controles de ventana **min / max / cerrar**. También pinta el **splash** de carga y la pantalla
  **sin conexión** (con reintento automático).
- El sitio de TechCare va embebido **debajo** de la barra en una `WebContentsView` (`main.js`), así
  la barra nunca recarga ni parpadea al navegar.
- Atajos: **Alt+← / Alt+→** (navegar), **F5 / Ctrl+R** (recargar), **Ctrl + / Ctrl − / Ctrl 0** (zoom).
- Recuerda **tamaño, posición y zoom** de la ventana entre sesiones (`userData/ventana.json`).

> Al cambiar algo del shell (`shell.html`, `main.js`, etc.) hay que **recompilar** (Run workflow),
> porque el shell va dentro del `.exe`. El contenido del sitio NO: ese se actualiza con el redeploy
> de la web (el .exe solo abre la URL).

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

## Actualizaciones automáticas (estilo Docker Desktop)
La app se actualiza sola con **electron-updater** (solo el instalador **NSIS**; el MSI/portable no).
Al abrir, si hay una versión nueva, sale una **ventana de actualización** (aparece aunque no se
haya hecho login), descarga sola y ofrece *Reiniciar e instalar*. Si el usuario elige *Después*,
se instala al cerrar la app.

**Buscar a mano:** ícono de TechCare en la **bandeja del sistema** (junto al reloj) →
*Buscar actualizaciones…*. Abre la ventana y muestra el resultado: *Buscando…* →
*Ya tienes la última versión* / *Descargando…* / *Reiniciar e instalar*. (Requiere que el feed
tenga `latest.yml`; si no, dirá que no pudo buscar.)

- **Feed de actualizaciones (servidor Ubuntu):** `http://192.168.10.6:453/`
  Lo sirve el servicio systemd `techcare-updates` (directorio `/home/admin2/techcare-updates/`,
  puerto 453, ya abierto en el firewall para la LAN). Comandos:
  `sudo systemctl status|restart techcare-updates`.
- **Publicar una versión nueva:**
  1. Sube la versión en `package.json` → `"version"` (debe ser **mayor** que la instalada).
  2. Corre el workflow de Actions; descarga el artefacto (trae `*.exe`, `latest.yml` y `*.blockmap`).
  3. En el servidor: `~/techcare-updates/publicar.sh <carpeta-descargada>`
     (copia el `.exe`, el `.blockmap` y `latest.yml` al feed). Las apps instaladas lo detectan al abrir.

> El `.msi` que se reparte por **GPO** no se auto-actualiza; para esas PCs, TI vuelve a empujar el MSI.

## Cambiar la URL / versión
- URL del servidor: `main.js` (constante `APP_URL`) y el texto de `shell.html` (splash).
- URL del feed de updates: `package.json` → `build.publish[0].url`.
- Versión: `package.json` → `"version"`.

## Compilar localmente (opcional, solo en Windows/Mac/Linux con Node)
```bash
cd desktop
npm install
npm start        # probar la app
npm run build    # genera el instalador en desktop/dist/ (Windows)
```
