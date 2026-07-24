/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #mantenimiento-config (un .js no lo procesa Django). */
const CFG_CORE_MANTENIMIENTO = (function(){
  var d = document.getElementById("mantenimiento-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
  };
})();

window._PAGE = {
  maintEndTime: CFG_CORE_MANTENIMIENTO.v0
};


/* ─────────────────────────────────────────────────────────────────────
   <--- hecho por claude code: este bloque se había PERDIDO al sacar el JS
   del HTML (commit c8d65db): solo quedó la configuración de arriba y la
   página se quedó sin ninguna lógica. Recuperado de c8d65db~1.
   ───────────────────────────────────────────────────────────────────── */

(function(){
  const endTime = new Date(window._PAGE.maintEndTime);
  const hEl = document.getElementById('cd-h');
  const mEl = document.getElementById('cd-m');
  const sEl = document.getElementById('cd-s');
  const lblEl = document.getElementById('cd-date-lbl');

  const opts = { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' };
  lblEl.textContent = 'Fecha estimada: ' + endTime.toLocaleString('es', opts);

  function pad(n){ return String(n).padStart(2,'0'); }

  function tick(){
    const diff = endTime - Date.now();
    if(diff <= 0){
      hEl.textContent = '00'; mEl.textContent = '00'; sEl.textContent = '00';
      return;
    }
    const totalSec = Math.floor(diff / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    hEl.textContent = pad(h);
    mEl.textContent = pad(m);
    sEl.textContent = pad(s);
  }
  tick();
  setInterval(tick, 1000);
})();
