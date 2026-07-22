/* version_modal.js — <--- hecho por claude code: extraído del template.
   La URL y la bandera llegan por data-* en #tc-novedades-config. */
var CFGN = (function(){ var d=document.getElementById("tc-novedades-config").dataset;
  return { urlVisto: d.urlVisto, mostrar: d.mostrar === "1" }; })();

// <--- hecho por claude code: el footer va antes de los <script>, así que esperamos
// a que cargue Bootstrap antes de inicializar el modal.
(function(){
function tcInitNovedades(){
  var el = document.getElementById('tc-novedades-modal');
  if(!el || typeof bootstrap === 'undefined') return;
  var modal = new bootstrap.Modal(el);

  function marcarVisto(){
    var m = document.cookie.match(/csrftoken=([^;]+)/);
    fetch(CFGN.urlVisto, {
      method: 'POST',
      headers: {'X-CSRFToken': m ? m[1] : '', 'Content-Type': 'application/json'},
      body: '{}'
    }).catch(function(){});
  }

  // Se muestra solo una vez por versión; al cerrarlo queda marcado como visto.
  if (CFGN.mostrar) {

  el.addEventListener('hidden.bs.modal', marcarVisto, {once: true});
  modal.show();
  
  }

  var link = document.getElementById('tc-ver-novedades');
  if(link) link.addEventListener('click', function(e){ e.preventDefault(); modal.show(); });
}
if (document.readyState === 'complete') tcInitNovedades();
else window.addEventListener('load', tcInitNovedades);
})();
