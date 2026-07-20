/* TechCare — tema: toggle claro/oscuro + marcado del ítem de sidebar activo.
   hecho por claude code. */
(function () {
  'use strict';

  // ── Modo claro/oscuro ──────────────────────────────────────────────────
  var root = document.documentElement;
  var META = document.querySelector('meta[name="theme-color"]');

  function apply(theme) {
    root.setAttribute('data-bs-theme', theme);
    if (META) META.setAttribute('content', theme === 'dark' ? '#0e131b' : '#206bc4');
  }
  function current() {
    return root.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
  }
  // El script anti-FOUC del <head> ya fijó el tema inicial; aquí solo el toggle.
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('tc-theme-toggle');
    if (btn) {
      btn.addEventListener('click', function () {
        var next = current() === 'dark' ? 'light' : 'dark';
        apply(next);
        try { localStorage.setItem('tc-theme', next); } catch (e) {}
      });
    }

    // ── Sidebar: marcar activo por URL y expandir su grupo ────────────────
    try {
      var path = location.pathname.replace(/\/+$/, '');
      var links = document.querySelectorAll('.navbar-vertical .nav-link[href]');
      var best = null, bestLen = -1;
      links.forEach(function (a) {
        var href = a.getAttribute('href') || '';
        if (!href || href === '#' || href.charAt(0) === '#') return;
        var lp;
        try { lp = new URL(href, location.origin).pathname.replace(/\/+$/, ''); }
        catch (e) { return; }
        if (!lp) return;
        // coincidencia exacta o prefijo del path actual; el más largo gana
        if ((path === lp || path.indexOf(lp + '/') === 0) && lp.length > bestLen) {
          best = a; bestLen = lp.length;
        }
      });
      if (best) {
        best.classList.add('active');
        // Expandir el collapse padre (grupo) si lo hay
        var grp = best.closest('.collapse');
        if (grp) {
          grp.classList.add('show');
          var toggler = document.querySelector('[data-bs-target="#' + grp.id + '"], [href="#' + grp.id + '"]');
          if (toggler) toggler.classList.remove('collapsed');
        }
      }
    } catch (e) {}
  });
})();
