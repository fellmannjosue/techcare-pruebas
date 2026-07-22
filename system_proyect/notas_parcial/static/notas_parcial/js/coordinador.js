/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #coordinador-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("coordinador-config").dataset;
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
  };
})();

window._PAGE = Object.assign(window._PAGE || {}, {
  csrf:       CFG.v0,
  urlSave:    CFG.v1,
  urlAsig:    CFG.v2,
  urlLeer:    CFG.v3,
  urlEmail:   CFG.v4,
  area:       CFG.v5,
  parcial:    CFG.v6,
  anio:       CFG.v7,
  curso:      CFG.v8,
  grado:      CFG.v9,
  seccion:    CFG.v10,
  soloCarrusel: CFG.j11,
});
