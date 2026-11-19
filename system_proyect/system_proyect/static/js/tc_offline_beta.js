/* tc_offline_beta.js — <--- hecho por claude code (12-nov-2026): MODO SIN CONEXIÓN (beta), solo superusuario.
   Registra el service worker, muestra un indicador con las páginas guardadas y, si se cae la red,
   un aviso de que se está viendo la copia guardada (y no deja enviar formularios). Global: TC_OFFLINE_BETA. */
(function () {
  'use strict';
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('/sw.js').catch(function () {});

  var pill, aviso;
  function el(tag, cls, html) { var e = document.createElement(tag); e.className = cls; if (html) e.innerHTML = html; return e; }
  function preguntar(tipo) {
    return navigator.serviceWorker.ready.then(function (reg) {
      return new Promise(function (ok) {
        if (!reg.active) return ok(null);
        var ch = new MessageChannel();
        ch.port1.onmessage = function (m) { ok(m.data); };
        reg.active.postMessage({ tipo: tipo }, [ch.port2]);
        setTimeout(function () { ok(null); }, 3000);
      });
    });
  }
  function contar() {
    preguntar('tc-beta-estado').then(function (d) {
      if (!pill || !d) return;
      pill.querySelector('b').textContent = d.paginas;
    });
  }
  function pintar() {
    var off = !navigator.onLine;
    document.body.classList.toggle('tc-sin-red', off);
    if (pill) pill.classList.toggle('tc-ob-pill--off', off);
    if (pill) pill.querySelector('span').textContent = off ? 'Sin conexión' : 'Offline beta';
    if (aviso) aviso.hidden = !off;
  }
  function iniciar() {
    pill = el('button', 'tc-ob-pill', '<i class="ti ti-cloud-download"></i><span>Offline beta</span> · <b>…</b> páginas');
    pill.type = 'button';
    pill.title = 'Modo sin conexión (beta). Las páginas que abres se guardan en este navegador. Clic: opciones.';
    document.body.appendChild(pill);
    aviso = el('div', 'tc-ob-aviso', '<i class="ti ti-wifi-off"></i><div><b>Sin conexión · modo beta.</b> Estás viendo la última copia guardada de esta página. Lo que escribas no se guardará hasta que vuelva la red.</div>');
    aviso.hidden = true;
    document.body.appendChild(aviso);
    pill.addEventListener('click', function () {
      var txt = 'Modo sin conexión (beta)\n\nSe guardan en ESTE navegador las páginas que abres como superusuario. ' +
                'Si se cae la red, puedes volver a abrirlas (solo ver).\n\n¿Borrar ahora las copias guardadas?';
      var borrar = function () { preguntar('tc-beta-borrar').then(contar); };
      if (window.Swal) {
        Swal.fire({ title: 'Modo sin conexión (beta)', icon: 'info',
          html: 'Las páginas que abres como superusuario se guardan en <b>este navegador</b>. Si se cae la red puedes volver a abrirlas (solo ver).<br><br>Páginas guardadas: <b>' + pill.querySelector('b').textContent + '</b>',
          showCancelButton: true, confirmButtonText: 'Borrar copias', cancelButtonText: 'Cerrar', confirmButtonColor: '#d63939' })
          .then(function (r) { if (r.isConfirmed) borrar(); });
      } else if (confirm(txt)) borrar();
    });
    // Sin red no se envían formularios (se perdería lo escrito)
    document.addEventListener('submit', function (e) {
      if (navigator.onLine) return;
      var m = (e.target.getAttribute('method') || 'get').toLowerCase();
      if (m === 'get') return;
      e.preventDefault(); e.stopImmediatePropagation();
      if (window.Swal) Swal.fire({ icon: 'warning', title: 'Sin conexión', text: 'No se puede guardar sin red. Espera a que vuelva la conexión.' });
    }, true);
    window.addEventListener('online', function () { pintar(); contar(); });
    window.addEventListener('offline', pintar);
    pintar();
    navigator.serviceWorker.ready.then(function () { setTimeout(contar, 800); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar); else iniciar();
  window.TC_OFFLINE_BETA = true;
})();
