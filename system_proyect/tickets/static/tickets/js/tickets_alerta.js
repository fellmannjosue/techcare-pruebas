/* <--- hecho por claude code: alerta de tickets SIN ATENDER — suena + toast cada 10 min (tipo salidas al baño) */
(function () {
  var cfg = document.getElementById('tickets-alerta-cfg');
  if (!cfg) return;
  var URL = cfg.dataset.url;
  var SONIDO = cfg.dataset.sonido;
  var INTERVALO_ALERTA = 10 * 60 * 1000;   // re-avisar cada 10 minutos
  var POLL = 60 * 1000;                     // sondear cada 60 s
  var ultimaAlerta = 0;
  var audio = null, audioListo = false;

  function getAudio() {
    if (!audio && SONIDO) { audio = new Audio(SONIDO); audio.preload = 'auto'; }
    return audio;
  }
  // El navegador bloquea audio hasta el primer gesto del usuario → lo desbloqueamos.
  function desbloquear() {
    var a = getAudio();
    if (!a || audioListo) return;
    a.play().then(function () { a.pause(); a.currentTime = 0; audioListo = true; }).catch(function () {});
  }
  ['click', 'keydown', 'touchstart'].forEach(function (ev) {
    document.addEventListener(ev, desbloquear, { once: true });
  });

  function sonar() {
    var a = getAudio();
    if (!a) return;
    try { a.currentTime = 0; a.play().catch(function () {}); } catch (e) {}
  }

  function contenedor() {
    var cont = document.getElementById('tc-notif-global');
    if (!cont) {
      cont = document.createElement('div');
      cont.id = 'tc-notif-global';
      cont.className = 'toast-container position-fixed bottom-0 end-0 p-3';
      cont.style.zIndex = '9999';
      document.body.appendChild(cont);
    }
    return cont;
  }

  function toast(count) {
    var cont = contenedor();
    var el = document.createElement('div');
    el.className = 'toast show align-items-center text-bg-warning border-0 mb-2';
    el.setAttribute('role', 'alert');
    el.innerHTML =
      '<div class="d-flex"><div class="toast-body">' +
      '<i class="ti ti-bell-ringing me-1"></i><strong>' + count +
      '</strong> ticket(s) sin atender. Revísalos en el panel.</div>' +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
    cont.appendChild(el);
    el.querySelector('.btn-close').addEventListener('click', function () { el.remove(); });
    setTimeout(function () { el.remove(); }, 15000);
  }

  function chequear() {
    fetch(URL, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) return;
        var b = document.getElementById('tickets-sin-atender-badge');
        if (b) { if (d.count > 0) { b.textContent = d.count; b.style.display = ''; } else { b.style.display = 'none'; } }
        if (d.count > 0) {
          var ahora = Date.now();
          if (ahora - ultimaAlerta >= INTERVALO_ALERTA) {
            ultimaAlerta = ahora;
            sonar();
            toast(d.count);
          }
        } else {
          ultimaAlerta = 0;   // al vaciarse, la próxima vez avisa de inmediato
        }
      })
      .catch(function () {});
  }

  chequear();
  setInterval(chequear, POLL);
})();
