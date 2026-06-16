/* <--- hecho por claude code: cierre de sesión por inactividad (4h) con alerta + countdown */
(function () {
  if (window.__tcIdleInit) return;
  window.__tcIdleInit = true;

  var P = new URLSearchParams(location.search);
  // Minutos de inactividad (4h por defecto). ?idlemin=N para pruebas rápidas.
  var mins = parseFloat(P.get('idlemin')) || window.TC_IDLE_MINUTES || 240;
  var IDLE_MS = mins * 60000;
  var COUNT = 30;                         // segundos del countdown
  var LOGOUT_URL = window.TC_LOGOUT_URL || '/accounts/logout/';
  var KEY = 'tc_last_activity';

  var warned = false, cd = 0, cdIv = null;

  function nowMs() { return Date.now(); }
  function mark() { try { localStorage.setItem(KEY, String(nowMs())); } catch (e) {} }
  function last() { var v = 0; try { v = parseInt(localStorage.getItem(KEY) || '0', 10); } catch (e) {} return v || nowMs(); }

  // Movimiento real del usuario (los polls de fondo NO disparan estos eventos)
  ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click', 'wheel'].forEach(function (ev) {
    window.addEventListener(ev, onActivity, { passive: true, capture: true });
  });
  function onActivity() {
    if (warned) cancelWarn();
    else mark();
  }

  mark();
  setInterval(check, 1000);
  function check() {
    if (warned) return;
    if (nowMs() - last() >= IDLE_MS) showWarn();
  }

  function showWarn() {
    var ov = document.getElementById('tcIdleWarn');
    if (!ov) { doLogout(); return; }
    warned = true; cd = COUNT;
    var num = document.getElementById('tcIdleNum');
    var bar = document.getElementById('tcIdleBar');
    ov.style.display = 'flex';
    if (num) num.textContent = cd;
    if (bar) { bar.style.transition = 'none'; bar.style.width = '100%';
      requestAnimationFrame(function () { bar.style.transition = 'width 30s linear'; bar.style.width = '0%'; }); }
    cdIv = setInterval(function () {
      // Si hubo actividad en otra pestaña, cancelar
      if (nowMs() - last() < IDLE_MS) { cancelWarn(); return; }
      cd--;
      if (num) num.textContent = cd;
      if (cd <= 0) { clearInterval(cdIv); cdIv = null; doLogout(); }
    }, 1000);
  }

  function cancelWarn() {
    warned = false;
    if (cdIv) { clearInterval(cdIv); cdIv = null; }
    var ov = document.getElementById('tcIdleWarn');
    if (ov) ov.style.display = 'none';
    mark();
  }

  function doLogout() { playCloseAnim(LOGOUT_URL); }

  // Animación de cierre + navegación al destino indicado
  var cerrando = false;
  function playCloseAnim(targetUrl) {
    if (cerrando) return;
    cerrando = true;
    var ov = document.getElementById('tcIdleWarn');
    if (ov) ov.style.display = 'none';
    var cl = document.getElementById('tcLogoutOverlay');
    if (cl) {
      cl.style.display = 'flex';
      requestAnimationFrame(function () {
        cl.classList.add('show');
        var bar = document.getElementById('tcLogoutBar');
        if (bar) bar.style.width = '100%';
      });
      setTimeout(function () { location.href = targetUrl; }, 1800);
    } else {
      location.href = targetUrl;
    }
  }

  // Botón "Seguir conectado" + interceptar enlaces de cierre de sesión para animarlos
  document.addEventListener('click', function (e) {
    if (e.target && e.target.id === 'tcIdleStay') { cancelWarn(); return; }
    var a = e.target.closest && e.target.closest('a[href]');
    if (a) {
      var href = a.getAttribute('href') || '';
      if (/\/(maestro_)?logout\/?/.test(href) || /logout/.test(href)) {
        e.preventDefault();
        playCloseAnim(a.href);
      }
    }
  }, true);
})();
