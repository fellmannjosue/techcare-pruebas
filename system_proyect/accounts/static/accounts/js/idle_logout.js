/* <--- hecho por claude code: config por data-* (#idle-config). Antes tenía
   {% url %} DENTRO del .js (Django no lo procesa) y faltaba toda la lógica. */
(function(){
  var d = document.getElementById('idle-config');
  window.TC_LOGOUT_URL   = d ? d.dataset.logoutUrl : '/accounts/logout/?inactive=1';
  window.TC_IDLE_MINUTES = d ? parseFloat(d.dataset.idleMin) : 240;
})();

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
    var ring = document.getElementById('tcIdleRing');
    var C = 276.46;                       // circunferencia (r=44)
    ov.style.display = 'flex';
    if (num) num.textContent = cd;
    if (ring) {                           // anillo circular: lleno -> vacío en 30s
      ring.style.transition = 'none'; ring.style.strokeDashoffset = '0';
      requestAnimationFrame(function () {
        ring.style.transition = 'stroke-dashoffset ' + COUNT + 's linear';
        ring.style.strokeDashoffset = C;
      });
    }
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
