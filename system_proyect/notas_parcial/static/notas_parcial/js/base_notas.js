/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #base_notas-config (un .js no lo procesa Django). */
const CFG_BASE_NOTAS = (function(){
  var d = document.getElementById("base_notas-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
  };
})();

if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js',{scope:'/'}).catch(function(){});});}

window._PAGE = window._PAGE || {};
window._PAGE.anioActual = parseInt(CFG_BASE_NOTAS.v0);


/* ── Parciales permitidos ────────────────────────────────────────────────
   <--- hecho por claude code: al abrir un parcial nuevo solo hay que subir
   PARCIAL_MAX. Arriba de ese número sale el modal "no hemos llegado a ese
   parcial todavía"; abajo de PARCIAL_MIN sale el de "eso ya pasó".
   Julio 2026: se habilitó el 3º, así que el aviso queda solo para el 4º. */
var PARCIAL_MAX = 3;   // último parcial habilitado
var PARCIAL_MIN = 2;   // primer parcial que aún se puede consultar

(function(){
  var ANIO_ACTUAL = parseInt(CFG_BASE_NOTAS.v0);

  function animar(elId, pasos){
    var el = document.getElementById(elId);
    if(!el) return;
    var i = 0;
    el.textContent = pasos[0];
    el.style.opacity = '1'; el.style.transform = 'scale(1)';
    var tick = setInterval(function(){
      el.style.opacity = '0';
      el.style.transform = 'scale(0.7)';
      setTimeout(function(){
        i = Math.min(i + 1, pasos.length - 1);
        el.textContent = pasos[i];
        el.style.opacity = '1';
        el.style.transform = 'scale(1.15)';
        setTimeout(function(){ el.style.transform = 'scale(1)'; }, 180);
        if(i >= pasos.length - 1) clearInterval(tick);
      }, 250);
    }, 750);
  }

  function animarDos(id1, id2){
    [id1, id2].forEach(function(id, idx){
      var el = document.getElementById(id);
      if(!el) return;
      el.style.opacity = '1'; el.style.transform = 'scale(1)';
      setTimeout(function(){
        el.style.transform = 'scale(1.4)';
        setTimeout(function(){
          el.style.transform = 'scale(0.85)';
          setTimeout(function(){ el.style.transform = 'scale(1)'; }, 150);
        }, 200);
      }, idx * 120);
    });
  }

  function abrirModal(id){
    var el = document.getElementById(id);
    if(el && window.bootstrap) new bootstrap.Modal(el).show();
  }

  document.addEventListener('DOMContentLoaded', function(){
    var selParcial = document.querySelector('select[name="parcial"]');
    var inpAnio    = document.querySelector('input[name="anio"]');

    if(selParcial){
      selParcial.addEventListener('change', function(){
        var v = parseInt(selParcial.value);
        if(isNaN(v)) return;
        if(v > PARCIAL_MAX){
          animar('emoji-futuro', ['😕','😟','😤','😠']);
          abrirModal('modalParcialFuturo');
          selParcial.value = '';
        } else if(v < PARCIAL_MIN){
          animar('emoji-pasado', ['😅','🤒','😵','💀']);
          abrirModal('modalParcialPasado');
          selParcial.value = '';
        }
      });
    }

    if(inpAnio){
      inpAnio.addEventListener('change', function(){
        if(parseInt(inpAnio.value) < ANIO_ACTUAL){
          inpAnio.value = ANIO_ACTUAL;
          animarDos('emoji-anio-1', 'emoji-anio-2');
          abrirModal('modalAnioPasado');
        }
      });
    }
  });
})();
