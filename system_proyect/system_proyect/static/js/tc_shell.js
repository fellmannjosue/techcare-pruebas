/* tc_shell.js — <--- hecho por claude code (30-sep-2026)
   Shell "Horizon Split": (1) marca el enlace activo del panel y abre su grupo,
   (2) construye el riel de íconos a partir de los grupos de primer nivel del sidebar,
   (3) tooltip del riel, (4) buscador del panel. Sin dependencias. */
(function () {
  'use strict';
  var side = document.querySelector('.navbar-vertical');
  var rail = document.getElementById('tc-rail-nav');
  var path = location.pathname;

  function hrefPath(h) { try { return new URL(h, location.origin).pathname; } catch (e) { return ''; } }

  /* 1. Enlace activo: el href con el prefijo más largo que coincida con la ruta actual */
  var best = null, bestLen = 0;
  if (side) {
    Array.prototype.forEach.call(side.querySelectorAll('a.nav-link[href]'), function (a) {
      var h = a.getAttribute('href') || '';
      if (!h || h.charAt(0) === '#') return;
      var p = hrefPath(h);
      if (!p || p === '/') return;
      if (path === p || path.indexOf(p) === 0) { if (p.length > bestLen) { best = a; bestLen = p.length; } }
    });
    if (best) {
      best.classList.add('active');
      var el = best.parentElement;
      while (el && el !== side) {
        if (el.classList.contains('collapse') && !el.classList.contains('navbar-collapse') && !el.classList.contains('show')) {
          el.classList.add('show');
          var tg = side.querySelector('[href="#' + el.id + '"],[data-bs-target="#' + el.id + '"]');
          if (tg) { tg.classList.remove('collapsed'); tg.setAttribute('aria-expanded', 'true'); }
        }
        el = el.parentElement;
      }
    }
  }

  /* 1b. <--- hecho por claude code (12-oct-2026): ACORDEÓN (pedido del usuario, sidebar de ylagos con todo abierto):
     los grupos empiezan cerrados, se abren al hacer clic y abrir uno cierra los demás; solo queda abierto el de la página actual. */
  if (side && side.getAttribute('data-acordeon') === '1') {   // todos menos el superusuario (pedido del usuario)
    var esTop = function (c) {
      var p = c.parentElement;
      while (p && p !== side) { if (p.classList.contains('collapse') && !p.classList.contains('navbar-collapse')) return false; p = p.parentElement; }
      return true;
    };
    var tops = Array.prototype.filter.call(side.querySelectorAll('.collapse:not(.navbar-collapse)'), esTop);
    var toggler = function (c) { return side.querySelector('[href="#' + c.id + '"],[data-bs-target="#' + c.id + '"]'); };
    tops.forEach(function (c) {
      if (c.classList.contains('show') && !(best && c.contains(best))) {
        c.classList.remove('show');
        var t = toggler(c); if (t) { t.classList.add('collapsed'); t.setAttribute('aria-expanded', 'false'); }
      }
    });
    side.addEventListener('show.bs.collapse', function (e) {
      if (tops.indexOf(e.target) < 0 || side.classList.contains('tc-filtering')) return;
      tops.forEach(function (o) {
        if (o !== e.target && o.classList.contains('show')) {
          if (window.bootstrap && bootstrap.Collapse) bootstrap.Collapse.getOrCreateInstance(o, { toggle: false }).hide();
          else { o.classList.remove('show'); var t = toggler(o); if (t) t.classList.add('collapsed'); }
        }
      });
    });
  }

  /* 2. Riel: un ícono por grupo de primer nivel del sidebar (+ accesos extra del superusuario) */
  if (rail && side) {
    var frag = document.createDocumentFragment();
    var seen = {};
    function add(title, iconCls, href, on) {
      var key = hrefPath(href);
      if (seen[key]) return; seen[key] = 1;
      var a = document.createElement('a');
      a.href = href; a.className = 'tc-rail-item' + (on ? ' on' : '');
      a.setAttribute('data-tip', title);
      a.innerHTML = '<i class="' + iconCls + '"></i>';
      frag.appendChild(a);
    }
    var top = side.querySelector('.navbar-nav');
    if (top) {
      Array.prototype.forEach.call(top.children, function (li) {
        if (!li.classList.contains('nav-item') || li.classList.contains('d-none')) return;
        var link = null;
        for (var i = 0; i < li.children.length; i++) { if (li.children[i].matches('a.nav-link')) { link = li.children[i]; break; } }
        if (!link) return;
        var icon = link.querySelector('.nav-link-icon i');
        var titleEl = link.querySelector('.nav-link-title');
        var title = (titleEl || link).textContent.replace(/\s+/g, ' ').trim();
        var href = link.getAttribute('href') || '#';
        if (href.charAt(0) === '#') {
          var first = li.querySelector('.collapse a.nav-link[href]:not([href^="#"])');
          href = first ? first.getAttribute('href') : '#';
        }
        if (href === '#') return;
        var cls = icon ? icon.className.replace(/\btext-[\w-]+/g, '').trim() : 'ti ti-circle';
        var on = (best && li.contains(best)) || hrefPath(href) === path;
        add(title, cls, href, on);
      });
    }
    var extra = rail.getAttribute('data-extra');
    if (extra) {
      try {
        JSON.parse(extra).forEach(function (x) {
          if (!x.h) return;
          var p = hrefPath(x.h);
          add(x.t, 'ti ' + x.i, x.h, !!p && p !== '/' && path.indexOf(p) === 0 && !best);
        });
      } catch (e) {}
    }
    rail.appendChild(frag);
  }

  /* 3. Tooltip del riel */
  var tip = document.createElement('div');
  tip.className = 'tc-rail-tip';
  document.body.appendChild(tip);
  document.addEventListener('mouseover', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('#tc-rail [data-tip]') : null;
    if (!a) { tip.classList.remove('show'); return; }
    var r = a.getBoundingClientRect();
    tip.textContent = a.getAttribute('data-tip');
    tip.style.top = (r.top + r.height / 2) + 'px';
    tip.style.left = (r.right + 10) + 'px';
    tip.classList.add('show');
  });

  /* 4. Buscador del panel */
  var q = document.getElementById('tc-side-q');
  if (q && side) {
    var items = side.querySelectorAll('.nav-item');
    q.addEventListener('input', function () {
      var v = q.value.trim().toLowerCase();
      side.classList.toggle('tc-filtering', !!v);
      Array.prototype.forEach.call(items, function (li) {
        li.classList.toggle('tc-hide', !!v && li.textContent.toLowerCase().indexOf(v) < 0);
      });
    });
  }
})();
