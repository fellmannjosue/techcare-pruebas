// TechCare Pruebas — proceso principal de Electron.
// Es un envoltorio nativo: abre el sitio web de TechCare (pruebas) en una ventana de escritorio.
// No toca la base de datos ni necesita API: todo lo maneja el backend, igual que el navegador.
const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron');
const path = require('path');
const { autoUpdater } = require('electron-updater');

// URL de TechCare PRUEBAS (cámbiala aquí si el servidor cambia de IP/puerto).
const APP_URL = 'http://192.168.10.6:451/';

let mainWindow = null;
let updaterWindow = null;

// Estado actual de la actualización; se reenvía a la ventana cuando termina de cargar.
// fase: 'disponible' | 'descargando' | 'listo' | 'error'
let estadoUpd = null;

function crearVentana() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'TechCare Pruebas',
    icon: path.join(__dirname, 'build', 'icon.png'),
    autoHideMenuBar: true,            // sin barra de menú visible
    backgroundColor: '#2563eb',
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  Menu.setApplicationMenu(null);      // app limpia, sin menú de Electron
  mainWindow.once('ready-to-show', () => mainWindow.show());
  cargarSitio();

  // En la app .exe NO se muestra el footer del sitio (copyright + versión + Novedades):
  // eso es solo para la web. Se oculta inyectando CSS en cada página que carga.
  const CSS_SIN_FOOTER = 'footer.tc-footer{display:none !important;}';
  mainWindow.webContents.on('dom-ready', () => {
    mainWindow.webContents.insertCSS(CSS_SIN_FOOTER).catch(() => {});
  });

  // Enlaces a OTROS sitios (http/https externos) se abren en el navegador del sistema;
  // la navegación dentro de TechCare se queda en la app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(APP_URL)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  // Seguridad: la ventana SOLO puede navegar dentro de TechCare. Cualquier intento de
  // ir a otro sitio (redirección/phishing) se bloquea y, si es un enlace, se abre en el navegador.
  const esInterno = (url) => url.startsWith(APP_URL) || url.startsWith('file://');
  mainWindow.webContents.on('will-navigate', (e, url) => {
    if (!esInterno(url)) { e.preventDefault(); shell.openExternal(url); }
  });
  mainWindow.webContents.on('will-redirect', (e, url) => {
    if (!esInterno(url)) { e.preventDefault(); shell.openExternal(url); }
  });

  // Seguridad: negar por defecto los permisos del sistema (cámara, micrófono, ubicación, etc.).
  mainWindow.webContents.session.setPermissionRequestHandler((_wc, _permission, cb) => cb(false));

  // Si no logra conectar con el servidor, muestra una página de "sin conexión" con reintento.
  mainWindow.webContents.on('did-fail-load', (_e, code) => {
    if (code === -3) return;          // abortos normales de carga
    mainWindow.loadFile(path.join(__dirname, 'offline.html')).catch(() => {});
  });
}

function cargarSitio() {
  mainWindow.loadURL(APP_URL).catch(() => {
    mainWindow.loadFile(path.join(__dirname, 'offline.html')).catch(() => {});
  });
}

// ── Ventana de actualización (estilo Docker Desktop) ──────────────────────────
// Aparece SOLA cuando hay una actualización, aunque no se haya hecho login
// (es una ventana nativa de Electron, independiente del sitio web).
function crearVentanaActualizador() {
  if (updaterWindow && !updaterWindow.isDestroyed()) { updaterWindow.focus(); return; }
  updaterWindow = new BrowserWindow({
    width: 480,
    height: 340,
    resizable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    title: 'Actualización de TechCare',
    icon: path.join(__dirname, 'build', 'icon.png'),
    parent: mainWindow || undefined,
    autoHideMenuBar: true,
    backgroundColor: '#0b1220',
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'updater-preload.js')
    }
  });
  updaterWindow.loadFile(path.join(__dirname, 'updater.html')).catch(() => {});
  updaterWindow.once('ready-to-show', () => updaterWindow.show());
  // Cuando el HTML termina de cargar, mándale el último estado conocido.
  updaterWindow.webContents.on('did-finish-load', () => {
    if (estadoUpd) enviarAlActualizador(estadoUpd);
  });
  updaterWindow.on('closed', () => { updaterWindow = null; });
}

function enviarAlActualizador(datos) {
  estadoUpd = datos;
  if (updaterWindow && !updaterWindow.isDestroyed()) {
    updaterWindow.webContents.send('upd:estado', datos);
  }
}

function configurarActualizaciones() {
  // En desarrollo (no empaquetado) el updater lanza error; no lo activamos.
  if (!app.isPackaged) return;

  autoUpdater.autoDownload = true;              // descarga sola, como Docker/VSCode
  autoUpdater.autoInstallOnAppQuit = true;      // si cierran sin instalar, se aplica al salir

  autoUpdater.on('update-available', (info) => {
    crearVentanaActualizador();
    enviarAlActualizador({ fase: 'descargando', version: info.version, percent: 0 });
  });
  autoUpdater.on('download-progress', (p) => {
    enviarAlActualizador({ fase: 'descargando', version: (estadoUpd && estadoUpd.version) || '', percent: Math.round(p.percent || 0) });
  });
  autoUpdater.on('update-downloaded', (info) => {
    crearVentanaActualizador();
    enviarAlActualizador({ fase: 'listo', version: info.version, percent: 100 });
  });
  autoUpdater.on('error', (err) => {
    // Un error del updater (servidor caído, sin red) NO debe molestar al usuario:
    // solo se refleja si la ventana ya estaba abierta.
    if (updaterWindow && !updaterWindow.isDestroyed()) {
      enviarAlActualizador({ fase: 'error', mensaje: String(err && err.message ? err.message : err) });
    }
  });

  autoUpdater.checkForUpdates().catch(() => {});
}

// Acciones desde la ventana de actualización.
ipcMain.on('upd:instalar', () => {
  try { autoUpdater.quitAndInstall(); } catch (e) { /* no-op */ }
});
ipcMain.on('upd:despues', () => {
  if (updaterWindow && !updaterWindow.isDestroyed()) updaterWindow.close();
});

app.whenReady().then(() => {
  crearVentana();
  configurarActualizaciones();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) crearVentana();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
