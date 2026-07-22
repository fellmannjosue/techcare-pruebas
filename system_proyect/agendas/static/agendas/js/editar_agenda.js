/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #editar_agenda-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("editar_agenda-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
  };
})();

window._PAGE = { agendaId: CFG.j2, csrf: CFG.v0, subirUrl: CFG.v1 };
