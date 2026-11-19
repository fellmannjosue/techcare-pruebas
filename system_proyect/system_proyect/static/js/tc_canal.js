/* <--- hecho por claude code (09-nov-2026): quita de la página los enlaces a programas que el CANAL
   (Web / .exe / APK) no tiene activados (core/canales.py). El servidor ya bloquea esas rutas; esto
   solo limpia menús, tarjetas y paneles. Sube por los contenedores mientras contengan ÚNICAMENTE ese
   enlace, para que no queden tarjetas vacías. */
(function () {
  var el = document.getElementById('tc-canal-mapa');
  if (!el) return;
  var m; try { m = JSON.parse(el.textContent); } catch (e) { return; }
  if (!m || !m.ocultos || !m.ocultos.length) return;
  var oc = {}; m.ocultos.forEach(function (k) { oc[k] = 1; });
  var STOP = 'body,main,header,nav,aside,.page,.wrapper,.page-body,.page-wrapper,.page-header,.container,.container-xl,.container-fluid,.row,.tc-topnav,.tc-dd,.tc-dd-subitems,.navbar-nav,.dropdown-menu,ul,ol,form,table,tbody,tr';

  function programa(path) {
    for (var i = 0; i < m.programas.length; i++) {
      var p = m.programas[i];
      if (p.x.some(function (e) { return path.indexOf(e) === 0; })) continue;
      if (p.p.some(function (x) { return path.indexOf(x) === 0; })) return p.k;
    }
    return null;
  }
  function esOculto(a) {
    var h = a.getAttribute('href');
    if (!h || h.charAt(0) === '#' || /^(mailto|tel|javascript):/i.test(h)) return false;
    var u; try { u = new URL(h, location.href); } catch (e) { return false; }
    if (u.origin !== location.origin) return false;
    var k = programa(u.pathname);
    return !!(k && oc[k]);
  }
  function ocultar(n) { n.setAttribute('data-tc-canal-oculto', '1'); n.style.setProperty('display', 'none', 'important'); }
  function visibles(c) {
    return [].filter.call(c.querySelectorAll('a[href]'), function (a) { return !a.closest('[data-tc-canal-oculto]'); }).length;
  }

  function limpiar() {
    [].forEach.call(document.querySelectorAll('a[href]'), function (a) {
      if (a.closest('[data-tc-canal-oculto]') || !esOculto(a)) return;
      var n = a;
      while (n.parentElement && !n.parentElement.matches(STOP) && n.parentElement.querySelectorAll('a[href]').length === 1) n = n.parentElement;
      ocultar(n);
    });
    // grupos que se quedaron sin ningún enlace visible
    ['.tc-dd-sub', '.tc-nav-item', '.nav-item', '.ps-mod', '.card'].forEach(function (sel) {
      [].forEach.call(document.querySelectorAll(sel), function (g) {
        if (g.closest('[data-tc-canal-oculto]')) return;
        if (g.querySelector('a[href]') && !visibles(g)) ocultar(g);
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', limpiar); else limpiar();
  window.addEventListener('load', limpiar);   // el menú superior se arma con JS (tc_shell.js)
})();
