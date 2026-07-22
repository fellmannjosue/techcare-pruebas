/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #index-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("index-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
    v3: d.v3,
    j3: j(d.v3),
    v4: d.v4,
    j4: j(d.v4),
    v5: d.v5,
    j5: j(d.v5),
    v6: d.v6,
    j6: j(d.v6),
    v7: d.v7,
    j7: j(d.v7),
    v8: d.v8,
    j8: j(d.v8),
    v9: d.v9,
    j9: j(d.v9),
    v10: d.v10,
    j10: j(d.v10),
    v11: d.v11,
    j11: j(d.v11),
    v12: d.v12,
    j12: j(d.v12),
  };
})();

window._SB = {
  urlGuardar:        CFG.v0,
  urlNotifCount:     CFG.v1,
  urlNotifList:      CFG.v2,
  urlNotifLeerTodas: CFG.v3,
  urlHistorialBase:  CFG.v4,
  urlRegresoBase:    "/salidas-bano/{pk}/regreso/",
  urlEliminarBase:   "/salidas-bano/{pk}/eliminar/",
  urlNotifLeerBase:  "/salidas-bano/notif/{pk}/leer/",
  area:              CFG.v5,
  periodoId:         CFG.v6,
  csrfToken:         CFG.v7,
  fechaHoy:          CFG.v8,
  esCoord:           CFG.j9,
  alumnosPorGrado:   CFG.j10,
  salidasHoy:        CFG.j11,
  clasesPorGrado:    CFG.j12,
};
