// TechCare Pruebas — proceso principal de Electron.
// Es un envoltorio nativo: abre el sitio web de TechCare (pruebas) en una ventana de escritorio.
// No toca la base de datos ni necesita API: todo lo maneja el backend, igual que el navegador.
const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('path');

// URL de TechCare PRUEBAS (cámbiala aquí si el servidor cambia de IP/puerto).
const APP_URL = 'http://192.168.10.6:451/';

let mainWindow = null;

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

  // Enlaces a OTROS sitios (http/https externos) se abren en el navegador del sistema;
  // la navegación dentro de TechCare se queda en la app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(APP_URL)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

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

app.whenReady().then(() => {
  crearVentana();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) crearVentana();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
