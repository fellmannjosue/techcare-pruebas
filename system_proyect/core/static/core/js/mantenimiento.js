(function(){
  var endTimeStr = window._PAGE && window._PAGE.maintEndTime;
  if (!endTimeStr) return;

  const endTime = new Date(endTimeStr);
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
