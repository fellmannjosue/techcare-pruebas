/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #grafica-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("grafica-config").dataset;
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
  };
})();

window.GRAFICA_CONTEXT = {
  presentes: CFG.j3,
  ausentes:  CFG.j4,
  fecha_inicio: CFG.v0,
  fecha_fin:    CFG.v1,
  detalleURL:   CFG.v2
};
