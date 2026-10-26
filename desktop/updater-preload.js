// Puente seguro entre la ventana de actualización (updater.html) y el proceso principal.
// contextIsolation activo: el HTML solo ve lo que se expone aquí.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('upd', {
  // Recibe el estado de la actualización desde main.js.
  alCambiar: (cb) => {
    ipcRenderer.on('upd:estado', (_e, datos) => cb(datos));
  },
  // Recibe las novedades (changelog) desde main.js.
  alNovedades: (cb) => {
    ipcRenderer.on('upd:novedades', (_e, datos) => cb(datos));
  },
  // Reiniciar e instalar ahora.
  instalar: () => ipcRenderer.send('upd:instalar'),
  // Cerrar la ventana (la actualización se aplicará al salir del app).
  despues: () => ipcRenderer.send('upd:despues'),
  // Volver a buscar (botón en estados "al día"/"error").
  reintentar: () => ipcRenderer.send('upd:reintentar')
});
