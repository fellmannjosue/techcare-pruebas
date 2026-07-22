/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #submit_ticket-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("submit_ticket-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
  };
})();

window._PAGE = {
  csrf:      CFG.v0,
  submitUrl: CFG.v1,
};
