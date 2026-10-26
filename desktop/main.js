// TechCare Pruebas — proceso principal de Electron.
// Es un envoltorio nativo: abre el sitio web de TechCare (pruebas) en una ventana de escritorio.
// No toca la base de datos ni necesita API: todo lo maneja el backend, igual que el navegador.
const { app, BrowserWindow, Menu, Tray, nativeImage, shell, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { autoUpdater } = require('electron-updater');

// URL de TechCare PRUEBAS (cámbiala aquí si el servidor cambia de IP/puerto).
const APP_URL = 'http://192.168.10.6:451/';

let mainWindow = null;
let updaterWindow = null;
let tray = null;

// Estado actual de la actualización; se reenvía a la ventana cuando termina de cargar.
// fase: 'buscando' | 'actual' | 'descargando' | 'listo' | 'error' | 'dev'
let estadoUpd = null;
// true = el usuario pidió buscar a mano (entonces SÍ mostramos "ya estás al día"/errores).
let chequeoManual = false;
// Últimas novedades (changelog) traídas de la web; se reenvían a la ventana al cargar.
let ultimasNovedades = null;
// Último estado de actualización que se le avisa a la WEB (para el botón de la cabecera).
let estadoUpdWeb = null;
// Archivo donde recordamos la última versión del sistema que el usuario ya vio.
const VISTO_PATH = path.join(app.getPath('userData'), 'novedades_visto.json');

function crearVentana() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'TechCare Pruebas',
    icon: path.join(__dirname, 'assets', 'icon.png'),
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
    // Reenvía el último estado de actualización al botón de la cabecera tras cada carga.
    if (estadoUpdWeb) mainWindow.webContents.send('tc:upd-estado', estadoUpdWeb);
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
    width: 540,
    height: 600,
    resizable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    title: 'Novedades y actualización · TechCare',
    icon: path.join(__dirname, 'assets', 'icon.png'),
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
  // Cuando el HTML termina de cargar, mándale el último estado y las novedades conocidas.
  updaterWindow.webContents.on('did-finish-load', () => {
    if (estadoUpd) enviarAlActualizador(estadoUpd);
    if (ultimasNovedades) enviarNovedades(ultimasNovedades);
  });
  updaterWindow.on('closed', () => { updaterWindow = null; });
}

function enviarAlActualizador(datos) {
  estadoUpd = datos;
  if (updaterWindow && !updaterWindow.isDestroyed()) {
    updaterWindow.webContents.send('upd:estado', datos);
  }
  avisarWeb(datos);                 // también al botón de la cabecera del sitio
}

// Avisa a la WEB (ventana principal) el estado de la actualización, para el botón de la cabecera.
function avisarWeb(datos) {
  estadoUpdWeb = datos;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('tc:upd-estado', datos);
  }
}

function enviarNovedades(datos) {
  ultimasNovedades = datos;
  if (updaterWindow && !updaterWindow.isDestroyed()) {
    updaterWindow.webContents.send('upd:novedades', datos);
  }
}

// Lee las novedades (changelog) desde la WEB (proceso principal → sin CORS/CSP).
// cb(infoVersion) opcional: recibe la versión del sistema cuando llega.
function obtenerNovedades(cb) {
  const url = APP_URL.replace(/\/+$/, '') + '/core/api/novedades/?limite=20';
  const req = http.get(url, { timeout: 8000 }, (res) => {
    let data = '';
    res.on('data', (c) => { data += c; });
    res.on('end', () => {
      try {
        const j = JSON.parse(data);
        enviarNovedades({ ok: true, version: j.version, entradas: j.entradas || [] });
        if (cb) cb(j.version);
      } catch (e) {
        enviarNovedades({ ok: false });
        if (cb) cb(null);
      }
    });
  });
  req.on('error', () => { enviarNovedades({ ok: false }); if (cb) cb(null); });
  req.on('timeout', () => { req.destroy(); enviarNovedades({ ok: false }); if (cb) cb(null); });
}

// Recuerda qué versión del sistema ya vio el usuario (para auto-mostrar solo lo nuevo).
function versionVista() {
  try { return JSON.parse(fs.readFileSync(VISTO_PATH, 'utf8')).version || ''; }
  catch (e) { return ''; }
}
function guardarVersionVista(v) {
  try { fs.writeFileSync(VISTO_PATH, JSON.stringify({ version: v })); } catch (e) { /* no-op */ }
}

// Abre la ventana de Novedades y actualización (desde la bandeja): siempre se ve.
function abrirNovedades() {
  crearVentanaActualizador();
  obtenerNovedades();
  buscarActualizaciones(true);
}

function configurarActualizaciones() {
  autoUpdater.autoDownload = true;              // descarga sola, como Docker/VSCode
  autoUpdater.autoInstallOnAppQuit = true;      // si cierran sin instalar, se aplica al salir

  // Hay una versión nueva → siempre se muestra (automático o manual).
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
  // Ya está al día → solo se muestra si el usuario lo pidió a mano.
  autoUpdater.on('update-not-available', () => {
    if (chequeoManual) {
      crearVentanaActualizador();
      enviarAlActualizador({ fase: 'actual', version: app.getVersion() });
    }
  });
  // Error (servidor caído, sin red): molesta solo si fue búsqueda manual o la ventana ya está abierta.
  autoUpdater.on('error', (err) => {
    if (chequeoManual || (updaterWindow && !updaterWindow.isDestroyed())) {
      crearVentanaActualizador();
      enviarAlActualizador({ fase: 'error', mensaje: String(err && err.message ? err.message : err) });
    }
  });
}

// Lanza la búsqueda de actualizaciones.
//   manual=false → chequeo silencioso al abrir (solo avisa si hay una nueva).
//   manual=true  → el usuario lo pidió: abre la ventana y muestra SIEMPRE el resultado.
function buscarActualizaciones(manual) {
  chequeoManual = !!manual;
  if (!app.isPackaged) {
    // En desarrollo (npm start) el updater no funciona; solo avisamos si fue manual.
    if (manual) {
      crearVentanaActualizador();
      enviarAlActualizador({ fase: 'dev' });
    }
    return;
  }
  if (manual) {
    crearVentanaActualizador();
    enviarAlActualizador({ fase: 'buscando' });
  }
  autoUpdater.checkForUpdates().catch((e) => {
    if (manual) {
      crearVentanaActualizador();
      enviarAlActualizador({ fase: 'error', mensaje: String(e && e.message ? e.message : e) });
    }
  });
}

// Ícono en la bandeja del sistema (junto al reloj) con "Buscar actualizaciones".
function crearBandeja() {
  try {
    const img = nativeImage.createFromPath(path.join(__dirname, 'assets', 'icon.png'));
    tray = new Tray(img.isEmpty() ? img : img.resize({ width: 16, height: 16 }));
    tray.setToolTip('TechCare Pruebas v' + app.getVersion());
    const menu = Menu.buildFromTemplate([
      { label: 'Abrir TechCare', click: () => { if (mainWindow) { mainWindow.show(); mainWindow.focus(); } } },
      { label: 'Novedades y actualización…', click: () => abrirNovedades() },
      { type: 'separator' },
      { label: 'TechCare Pruebas  ·  v' + app.getVersion(), enabled: false },
      { label: 'Salir', click: () => app.quit() }
    ]);
    tray.setContextMenu(menu);
    tray.on('click', () => { if (mainWindow) { mainWindow.show(); mainWindow.focus(); } });
  } catch (e) { /* si no hay bandeja disponible, no pasa nada */ }
}

// Acciones desde la ventana de actualización.
ipcMain.on('upd:instalar', () => {
  try { autoUpdater.quitAndInstall(); } catch (e) { /* no-op */ }
});
ipcMain.on('upd:despues', () => {
  if (updaterWindow && !updaterWindow.isDestroyed()) updaterWindow.close();
});
// Botón "Buscar de nuevo" dentro de la ventana.
ipcMain.on('upd:reintentar', () => buscarActualizaciones(true));
// Botón "Novedades y actualización" en la cabecera del sitio (dentro de la app).
ipcMain.on('tc:abrir-novedades', () => abrirNovedades());

app.whenReady().then(() => {
  crearVentana();
  crearBandeja();
  configurarActualizaciones();
  buscarActualizaciones(false);                 // chequeo silencioso de updates al abrir

  // Al abrir, trae las novedades; si el sistema cambió de versión desde la última
  // vez que el usuario las vio, muestra SOLA la ventana (como "Novedades" al actualizar).
  obtenerNovedades((versionSistema) => {
    if (versionSistema && versionSistema !== versionVista()) {
      crearVentanaActualizador();
      buscarActualizaciones(true);              // de paso revisa updates y lo muestra
      guardarVersionVista(versionSistema);
    }
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) crearVentana();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
