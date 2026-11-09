// TechCare Pruebas — proceso principal de Electron.
//
// A diferencia de la versión anterior (una sola BrowserWindow que cargaba el sitio y se
// veía idéntica al navegador), esta app tiene un SHELL NATIVO propio:
//   • Una ventana SIN marco del sistema (frameless).
//   • Una barra superior nativa (shell.html) con marca ANA, navegación atrás/adelante/
//     inicio/recargar, botón de Novedades y controles de ventana (min/max/cerrar).
//   • El sitio de TechCare va embebido DEBAJO de la barra en una WebContentsView, así la
//     barra nunca recarga ni parpadea al navegar.
//   • Splash de carga y pantalla "sin conexión" integrados al shell (no reemplazan la barra).
//
// Sigue siendo un envoltorio: no toca la base de datos ni usa API; solo muestra el sitio.
const {
  app, BaseWindow, WebContentsView, Menu, Tray, nativeImage, shell, ipcMain
} = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { autoUpdater } = require('electron-updater');

// URL de TechCare PRUEBAS (cámbiala aquí si el servidor cambia de IP/puerto).
const APP_URL = 'http://192.168.10.6:451/';
// Alto (px) de la barra superior nativa. Debe coincidir con --barra-h de shell.html.
const TOPBAR = 46;

let win = null;              // BaseWindow (ventana contenedora, sin marco)
let shellView = null;        // barra nativa + estados de carga/offline (shell.html)
let siteView = null;         // el sitio web de TechCare, embebido
let updaterWindow = null;
let tray = null;

// Estado de la ventana del sitio: 'cargando' | 'sitio' | 'offline'.
let vistaActual = 'cargando';
let huboFallo = false;

// Estado actual de la actualización; se reenvía a la ventana cuando termina de cargar.
// fase: 'buscando' | 'actual' | 'descargando' | 'listo' | 'error' | 'dev'
let estadoUpd = null;
let chequeoManual = false;          // true = el usuario pidió buscar a mano.
let ultimasNovedades = null;        // changelog traído de la web.
let estadoUpdWeb = null;            // último estado que se avisa a la web/shell (para los botones).

const VISTO_PATH = path.join(app.getPath('userData'), 'novedades_visto.json');
const VENTANA_PATH = path.join(app.getPath('userData'), 'ventana.json');

// ── Preferencias de ventana (tamaño/posición/zoom) ────────────────────────────
function leerPrefsVentana() {
  try { return JSON.parse(fs.readFileSync(VENTANA_PATH, 'utf8')) || {}; }
  catch (e) { return {}; }
}
function guardarPrefsVentana() {
  if (!win || win.isDestroyed()) return;
  try {
    const maxi = win.isMaximized();
    const datos = {
      bounds: maxi ? (leerPrefsVentana().bounds || win.getBounds()) : win.getBounds(),
      maximized: maxi,
      zoom: siteView ? siteView.webContents.getZoomFactor() : 1
    };
    fs.writeFileSync(VENTANA_PATH, JSON.stringify(datos));
  } catch (e) { /* no-op */ }
}

// ── Mensajería al shell y a la web ────────────────────────────────────────────
function aShell(canal, datos) {
  if (shellView && !shellView.webContents.isDestroyed()) {
    shellView.webContents.send(canal, datos);
  }
}
function aWeb(canal, datos) {
  if (siteView && !siteView.webContents.isDestroyed()) {
    siteView.webContents.send(canal, datos);
  }
}

// ── Ventana principal (shell nativo + sitio embebido) ─────────────────────────
function crearVentana() {
  const prefs = leerPrefsVentana();
  const b = prefs.bounds || {};
  win = new BaseWindow({
    width: b.width || 1280,
    height: b.height || 820,
    x: (typeof b.x === 'number') ? b.x : undefined,
    y: (typeof b.y === 'number') ? b.y : undefined,
    minWidth: 940,
    minHeight: 620,
    frame: false,                 // sin marco del sistema: el shell dibuja el suyo
    title: 'TechCare Pruebas',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    backgroundColor: '#0b1220',
    show: false
  });
  Menu.setApplicationMenu(null);

  // 1) Shell nativo (barra superior + estados). Cubre toda la ventana y queda al fondo.
  shellView = new WebContentsView({
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'shell-preload.js')
    }
  });
  shellView.setBackgroundColor('#0b1220');
  win.contentView.addChildView(shellView);
  shellView.webContents.loadFile(path.join(__dirname, 'shell.html')).catch(() => {});

  // 2) Sitio de TechCare, embebido encima de la zona de contenido (debajo de la barra).
  siteView = new WebContentsView({
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });
  siteView.setBackgroundColor('#ffffff');
  win.contentView.addChildView(siteView);
  siteView.setVisible(false);     // oculto hasta que el sitio cargue (se ve el splash)

  colocarVistas();
  win.on('resize', colocarVistas);
  win.on('maximize', () => { colocarVistas(); aShell('win:estado', { maximized: true }); });
  win.on('unmaximize', () => { colocarVistas(); aShell('win:estado', { maximized: false }); });

  cablearSitio();
  cargarSitio();

  // Mostrar la ventana cuando el shell ya pintó (evita el flash).
  shellView.webContents.once('did-finish-load', () => {
    win.show();
    aShell('vista', { modo: vistaActual });
    aShell('win:estado', { maximized: win.isMaximized() });
    if (estadoUpdWeb) aShell('tc:upd-estado', estadoUpdWeb);
  });

  if (prefs.maximized) win.maximize();

  win.on('close', guardarPrefsVentana);
  win.on('closed', () => { win = null; shellView = null; siteView = null; });
}

// Posiciona la barra (arriba) y el sitio (resto) según el tamaño de la ventana.
function colocarVistas() {
  if (!win || win.isDestroyed()) return;
  // Ventana sin marco: el tamaño de la ventana coincide con el del contenido.
  const cb = win.getBounds();
  const W = cb.width, H = cb.height;
  if (shellView) shellView.setBounds({ x: 0, y: 0, width: W, height: H });
  if (siteView) siteView.setBounds({ x: 0, y: TOPBAR, width: W, height: Math.max(0, H - TOPBAR) });
}

// Cambia el estado visible (splash / sitio / offline) y muestra u oculta el sitio.
function fijarVista(modo, extra) {
  vistaActual = modo;
  if (siteView) siteView.setVisible(modo === 'sitio');
  aShell('vista', Object.assign({ modo: modo }, extra || {}));
}

function cablearSitio() {
  const wc = siteView.webContents;

  // Ocultar el footer del sitio (copyright/versión/Novedades): es solo para la web.
  wc.on('dom-ready', () => {
    wc.insertCSS('footer.tc-footer{display:none !important;}').catch(() => {});
    if (estadoUpdWeb) aWeb('tc:upd-estado', estadoUpdWeb);
  });

  // Enlaces externos → navegador del sistema; TechCare se queda dentro.
  wc.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(APP_URL)) { shell.openExternal(url); return { action: 'deny' }; }
    return { action: 'allow' };
  });
  const esInterno = (url) => url.startsWith(APP_URL) || url.startsWith('file://');
  wc.on('will-navigate', (e, url) => { if (!esInterno(url)) { e.preventDefault(); shell.openExternal(url); } });
  wc.on('will-redirect', (e, url) => { if (!esInterno(url)) { e.preventDefault(); shell.openExternal(url); } });

  // Negar por defecto permisos del sistema (cámara, micrófono, ubicación, etc.).
  wc.session.setPermissionRequestHandler((_wc, _permission, cb) => cb(false));

  // Estado de navegación (habilitar/deshabilitar Atrás/Adelante en la barra).
  const avisarNav = () => {
    let atras = false, adelante = false;
    try { atras = wc.navigationHistory.canGoBack(); adelante = wc.navigationHistory.canGoForward(); }
    catch (e) { try { atras = wc.canGoBack(); adelante = wc.canGoForward(); } catch (_) {} }
    aShell('nav:estado', { atras, adelante });
  };
  wc.on('did-navigate', avisarNav);
  wc.on('did-navigate-in-page', avisarNav);
  wc.on('did-frame-navigate', avisarNav);

  // Barra de progreso de carga en la barra superior.
  wc.on('did-start-loading', () => { huboFallo = false; aShell('carga', { cargando: true }); });
  wc.on('did-stop-loading', () => { aShell('carga', { cargando: false }); });

  // Carga OK del sitio → mostrarlo. Fallo → pantalla "sin conexión".
  wc.on('did-finish-load', () => {
    if (huboFallo) return;
    const u = wc.getURL() || '';
    if (u.startsWith(APP_URL)) { fijarVista('sitio'); aplicarZoomGuardado(); }
  });
  wc.on('did-fail-load', (_e, code, _desc, _url, isMainFrame) => {
    if (code === -3) return;              // abortos normales
    if (!isMainFrame) return;
    huboFallo = true;
    fijarVista('offline', { code });
  });

  // Atajos de teclado (navegación, recarga, zoom).
  wc.on('before-input-event', (e, input) => manejarAtajo(e, input));
  shellView.webContents.on('before-input-event', (e, input) => manejarAtajo(e, input));
}

function manejarAtajo(e, input) {
  if (input.type !== 'keyDown' || !siteView) return;
  const wc = siteView.webContents;
  const k = (input.key || '').toLowerCase();
  if (input.alt && k === 'arrowleft') { e.preventDefault(); irAtras(); }
  else if (input.alt && k === 'arrowright') { e.preventDefault(); irAdelante(); }
  else if ((input.control && k === 'r') || k === 'f5') { e.preventDefault(); wc.reload(); }
  else if (input.control && (k === '+' || k === '=')) { e.preventDefault(); ajustarZoom(+0.1); }
  else if (input.control && (k === '-' || k === '_')) { e.preventDefault(); ajustarZoom(-0.1); }
  else if (input.control && k === '0') { e.preventDefault(); fijarZoom(1); }
}

function cargarSitio() {
  huboFallo = false;
  fijarVista('cargando');
  siteView.webContents.loadURL(APP_URL).catch(() => { huboFallo = true; fijarVista('offline'); });
}

// ── Navegación (desde la barra o atajos) ──────────────────────────────────────
function irAtras() {
  const wc = siteView && siteView.webContents; if (!wc) return;
  try { if (wc.navigationHistory.canGoBack()) wc.navigationHistory.goBack(); }
  catch (e) { try { if (wc.canGoBack()) wc.goBack(); } catch (_) {} }
}
function irAdelante() {
  const wc = siteView && siteView.webContents; if (!wc) return;
  try { if (wc.navigationHistory.canGoForward()) wc.navigationHistory.goForward(); }
  catch (e) { try { if (wc.canGoForward()) wc.goForward(); } catch (_) {} }
}
function irInicio() { if (siteView) { huboFallo = false; fijarVista('cargando'); siteView.webContents.loadURL(APP_URL).catch(() => { huboFallo = true; fijarVista('offline'); }); } }

// ── Zoom ──────────────────────────────────────────────────────────────────────
function fijarZoom(z) {
  z = Math.min(2.2, Math.max(0.6, z));
  if (siteView) siteView.webContents.setZoomFactor(z);
}
function ajustarZoom(d) { if (siteView) fijarZoom(siteView.webContents.getZoomFactor() + d); }
function aplicarZoomGuardado() {
  const z = leerPrefsVentana().zoom;
  if (typeof z === 'number' && z > 0) fijarZoom(z);
}

// ── Ventana de Novedades y actualización ──────────────────────────────────────
function crearVentanaActualizador() {
  if (updaterWindow && !updaterWindow.isDestroyed()) { updaterWindow.focus(); return; }
  const { BrowserWindow } = require('electron');
  updaterWindow = new BrowserWindow({
    width: 560, height: 640,
    resizable: false, minimizable: false, maximizable: false, fullscreenable: false,
    title: 'Novedades y actualización · TechCare',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    parent: win || undefined,
    autoHideMenuBar: true, backgroundColor: '#0b1220', show: false,
    webPreferences: {
      contextIsolation: true, nodeIntegration: false,
      preload: path.join(__dirname, 'updater-preload.js')
    }
  });
  updaterWindow.loadFile(path.join(__dirname, 'updater.html')).catch(() => {});
  updaterWindow.once('ready-to-show', () => updaterWindow.show());
  updaterWindow.webContents.on('did-finish-load', () => {
    if (estadoUpd) enviarAlActualizador(estadoUpd);
    if (ultimasNovedades) enviarNovedades(ultimasNovedades);
  });
  updaterWindow.on('closed', () => { updaterWindow = null; });
}

function enviarAlActualizador(datos) {
  estadoUpd = datos;
  if (updaterWindow && !updaterWindow.isDestroyed()) updaterWindow.webContents.send('upd:estado', datos);
  avisarEstadoUpd(datos);
}

// Avisa el estado de la actualización a la web (botón de la cabecera) y al shell (punto de aviso).
function avisarEstadoUpd(datos) {
  estadoUpdWeb = datos;
  aWeb('tc:upd-estado', datos);
  aShell('tc:upd-estado', datos);
}

function enviarNovedades(datos) {
  ultimasNovedades = datos;
  if (updaterWindow && !updaterWindow.isDestroyed()) updaterWindow.webContents.send('upd:novedades', datos);
}

// Lee las novedades (changelog) desde la WEB (proceso principal → sin CORS/CSP).
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
      } catch (e) { enviarNovedades({ ok: false }); if (cb) cb(null); }
    });
  });
  req.on('error', () => { enviarNovedades({ ok: false }); if (cb) cb(null); });
  req.on('timeout', () => { req.destroy(); enviarNovedades({ ok: false }); if (cb) cb(null); });
}

function versionVista() {
  try { return JSON.parse(fs.readFileSync(VISTO_PATH, 'utf8')).version || ''; }
  catch (e) { return ''; }
}
function guardarVersionVista(v) {
  try { fs.writeFileSync(VISTO_PATH, JSON.stringify({ version: v })); } catch (e) { /* no-op */ }
}

function abrirNovedades() {
  crearVentanaActualizador();
  obtenerNovedades();
  buscarActualizaciones(true);
}

function configurarActualizaciones() {
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
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
  autoUpdater.on('update-not-available', () => {
    if (chequeoManual) { crearVentanaActualizador(); enviarAlActualizador({ fase: 'actual', version: app.getVersion() }); }
  });
  autoUpdater.on('error', (err) => {
    if (chequeoManual || (updaterWindow && !updaterWindow.isDestroyed())) {
      crearVentanaActualizador();
      enviarAlActualizador({ fase: 'error', mensaje: String(err && err.message ? err.message : err) });
    }
  });
}

function buscarActualizaciones(manual) {
  chequeoManual = !!manual;
  if (!app.isPackaged) {
    if (manual) { crearVentanaActualizador(); enviarAlActualizador({ fase: 'dev' }); }
    return;
  }
  if (manual) { crearVentanaActualizador(); enviarAlActualizador({ fase: 'buscando' }); }
  autoUpdater.checkForUpdates().catch((e) => {
    if (manual) { crearVentanaActualizador(); enviarAlActualizador({ fase: 'error', mensaje: String(e && e.message ? e.message : e) }); }
  });
}

function crearBandeja() {
  try {
    const img = nativeImage.createFromPath(path.join(__dirname, 'assets', 'icon.png'));
    tray = new Tray(img.isEmpty() ? img : img.resize({ width: 16, height: 16 }));
    tray.setToolTip('TechCare Pruebas v' + app.getVersion());
    const menu = Menu.buildFromTemplate([
      { label: 'Abrir TechCare', click: () => { if (win) { win.show(); win.focus(); } } },
      { label: 'Novedades y actualización…', click: () => abrirNovedades() },
      { type: 'separator' },
      { label: 'TechCare Pruebas  ·  v' + app.getVersion(), enabled: false },
      { label: 'Salir', click: () => app.quit() }
    ]);
    tray.setContextMenu(menu);
    tray.on('click', () => { if (win) { win.show(); win.focus(); } });
  } catch (e) { /* no-op */ }
}

// ── IPC desde el shell nativo ─────────────────────────────────────────────────
ipcMain.on('nav:atras', irAtras);
ipcMain.on('nav:adelante', irAdelante);
ipcMain.on('nav:recargar', () => { if (siteView) siteView.webContents.reload(); });
ipcMain.on('nav:inicio', irInicio);
ipcMain.on('nav:reintentar', () => cargarSitio());
ipcMain.on('win:min', () => { if (win) win.minimize(); });
ipcMain.on('win:max', () => { if (!win) return; win.isMaximized() ? win.unmaximize() : win.maximize(); });
ipcMain.on('win:close', () => { if (win) win.close(); });

// IPC de la ventana de actualización.
ipcMain.on('upd:instalar', () => { try { autoUpdater.quitAndInstall(); } catch (e) { /* no-op */ } });
ipcMain.on('upd:despues', () => { if (updaterWindow && !updaterWindow.isDestroyed()) updaterWindow.close(); });
ipcMain.on('upd:reintentar', () => buscarActualizaciones(true));
// Botón "Novedades" (en la barra nativa y en la cabecera del sitio).
ipcMain.on('tc:abrir-novedades', () => abrirNovedades());

// ── Arranque ──────────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  crearVentana();
  crearBandeja();
  configurarActualizaciones();
  buscarActualizaciones(false);

  obtenerNovedades((versionSistema) => {
    if (versionSistema && versionSistema !== versionVista()) {
      crearVentanaActualizador();
      buscarActualizaciones(true);
      guardarVersionVista(versionSistema);
    }
  });

  app.on('activate', () => { if (!win) crearVentana(); });
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
