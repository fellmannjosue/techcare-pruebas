/* mu_conexion.js — <--- hecho por claude code (15-oct-2026): conexiones de Moodle guardadas.
   Cuenta regresiva del vencimiento de cada token y ventana "Token nuevo" (se abre sola si el token de la conexión
   activa vence pronto, ya venció o Moodle lo rechazó). Un solo global: MU_CONEXION. */
(function () {
  'use strict';
  var cfg = document.getElementById('mu-con-config'), modalEl = document.getElementById('muModalToken');
  if (!cfg || !modalEl) return;
  var avisoDias = parseInt(cfg.dataset.avisoDias || '15', 10);
  var vence = null, timer = null;

  function partes(ms) {
    var s = Math.floor(Math.abs(ms) / 1000);
    return { d: Math.floor(s / 86400), h: Math.floor(s % 86400 / 3600), m: Math.floor(s % 3600 / 60), s: s % 60 };
  }
  function dos(n) { return n < 10 ? '0' + n : String(n); }
  function texto(ms) {
    var p = partes(ms);
    if (ms <= 0) return 'venció hace ' + (p.d ? p.d + ' d ' : '') + p.h + ' h';
    return p.d ? 'faltan ' + p.d + ' d ' + p.h + ' h' : 'faltan ' + p.h + ' h ' + dos(p.m) + ' min';
  }

  /* Cuentas en las tarjetas de conexión */
  function tarjetas() {
    document.querySelectorAll('.mu-cuenta[data-vence]').forEach(function (el) {
      var ms = new Date(el.dataset.vence) - new Date();
      el.textContent = texto(ms);
    });
  }

  /* Reloj grande de la ventana */
  function reloj() {
    var caja = document.getElementById('mt-reloj');
    if (!vence) { caja.className = 'mu-reloj mu-reloj--sin'; document.getElementById('mt-reloj-tit').textContent = 'El token actual no tiene fecha de vencimiento registrada';
      ['d', 'h', 'm', 's'].forEach(function (k) { document.getElementById('mt-' + k).textContent = '–'; });
      document.getElementById('mt-reloj-pie').textContent = 'Anota la fecha «Válido hasta» del token nuevo para que el sistema te avise antes.'; return; }
    var ms = vence - new Date(), p = partes(ms);
    document.getElementById('mt-d').textContent = p.d;
    document.getElementById('mt-h').textContent = dos(p.h);
    document.getElementById('mt-m').textContent = dos(p.m);
    document.getElementById('mt-s').textContent = dos(p.s);
    var vencido = ms <= 0, pronto = !vencido && p.d < avisoDias;
    caja.className = 'mu-reloj' + (vencido ? ' mu-reloj--vencido' : pronto ? ' mu-reloj--pronto' : '');
    document.getElementById('mt-reloj-tit').textContent = vencido ? 'El token actual VENCIÓ hace' : 'El token actual vence en';
    document.getElementById('mt-reloj-pie').textContent = vencido
      ? 'Mientras no pongas el nuevo, TechCare no puede publicar en este Moodle.'
      : pronto ? 'Crea el token nuevo en Moodle (Servidor → Servicios web → Gestionar fichas) y pégalo aquí antes de que llegue a cero.'
               : 'Todavía está vigente; puedes reemplazarlo cuando quieras.';
  }

  function abrir(btn) {
    document.getElementById('mt-pk').value = btn.dataset.pk;
    document.getElementById('mt-nombre').textContent = btn.dataset.nombre;
    vence = btn.dataset.vence ? new Date(btn.dataset.vence) : null;
    document.getElementById('mt-vence').value = '';
    reloj(); clearInterval(timer); timer = setInterval(reloj, 1000);
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }
  modalEl.addEventListener('hidden.bs.modal', function () { clearInterval(timer); });
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.mu-btn-token');
    if (b) abrir(b);
  });

  tarjetas(); setInterval(tarjetas, 30000);
  if (cfg.dataset.abrir) {
    var b = document.querySelector('.mu-btn-token[data-pk="' + cfg.dataset.abrir + '"]');
    if (b) setTimeout(function () { abrir(b); }, 300);
  }
  window.MU_CONEXION = { abrir: abrir };
})();
