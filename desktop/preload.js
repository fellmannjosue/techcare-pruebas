// Preload. Con contextIsolation activado y sin nodeIntegration, el sitio web NO tiene
// acceso a Node ni a Electron. Solo exponemos un puente mínimo y seguro para el
// botón "Novedades y actualización" dentro de la app.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('tcDesktop', {
  esApp: true,
  // Abre la ventana "Novedades y actualización".
  abrirNovedades: () => ipcRenderer.send('tc:abrir-novedades'),
  // Recibe el estado de la actualización para pintar el aviso en la cabecera.
  // datos: { fase: 'descargando'|'listo'|'actual'|..., version }
  onEstado: (cb) => ipcRenderer.on('tc:upd-estado', (_e, datos) => cb(datos))
});
