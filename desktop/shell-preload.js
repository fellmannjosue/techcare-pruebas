// Puente seguro entre la barra nativa (shell.html) y el proceso principal.
// contextIsolation activo: el HTML del shell solo ve lo que se expone aquí.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('shellApi', {
  // Navegación
  atras:     () => ipcRenderer.send('nav:atras'),
  adelante:  () => ipcRenderer.send('nav:adelante'),
  recargar:  () => ipcRenderer.send('nav:recargar'),
  inicio:    () => ipcRenderer.send('nav:inicio'),
  reintentar:() => ipcRenderer.send('nav:reintentar'),
  novedades: () => ipcRenderer.send('tc:abrir-novedades'),

  // Controles de ventana
  minimizar: () => ipcRenderer.send('win:min'),
  maximizar: () => ipcRenderer.send('win:max'),
  cerrar:    () => ipcRenderer.send('win:close'),

  // Eventos del proceso principal
  onNav:   (cb) => ipcRenderer.on('nav:estado',    (_e, d) => cb(d)),   // {atras, adelante}
  onVista: (cb) => ipcRenderer.on('vista',         (_e, d) => cb(d)),   // {modo:'cargando'|'sitio'|'offline', code?}
  onCarga: (cb) => ipcRenderer.on('carga',         (_e, d) => cb(d)),   // {cargando:bool}
  onWin:   (cb) => ipcRenderer.on('win:estado',    (_e, d) => cb(d)),   // {maximized}
  onUpd:   (cb) => ipcRenderer.on('tc:upd-estado', (_e, d) => cb(d))    // {fase, version, ...}
});
