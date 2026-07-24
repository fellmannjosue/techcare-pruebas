/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #index-config (un .js no lo procesa Django). */
const CFG_NOTAS_PARCIAL_INDEX = (function(){
  var d = document.getElementById("index-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
  };
})();

window._PAGE = Object.assign(window._PAGE || {}, {
  csrf:       CFG_NOTAS_PARCIAL_INDEX.v0,
  urlSave:    CFG_NOTAS_PARCIAL_INDEX.v1,
});
