/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #formulario_bloqueado-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("formulario_bloqueado-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
  };
})();

(function(){
  // Vuelve atrás sin quedar atrapado en esta misma página
  document.getElementById('btn-volver').addEventListener('click', function(){
    var ref = document.referrer || '';
    if (ref && ref.indexOf(location.pathname) === -1 && history.length > 1) history.back();
    else location.href = CFG.v0;
  });
})();
