/* tc_shell.js — <--- hecho por claude code
   Shell TechCare. Desde el 30-oct-2026: MENÚ SUPERIOR HORIZONTAL.
   (1) marca el enlace activo, (2) construye el menú horizontal (#tc-topnav) con
   desplegables a partir del menú del sidebar (que queda oculto, solo como fuente),
   (3) botón hamburguesa en móvil, (4) buscador (si existe). Sin dependencias. */
(function () {
  'use strict';
  var side = document.querySelector('.navbar-vertical');
  var topnav = document.getElementById('tc-topnav');
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
    if (best) best.classList.add('active');
  }

  /* 2. Menú horizontal. Para el superusuario viene server-side POR CATEGORÍAS (partial
        _topnav_super.html); para los demás se construye aquí desde su sidebar. */
  if (topnav && side) {
    // Construir desde el sidebar SOLO si el menú llega vacío (no es el superusuario).
    if (!topnav.children.length) {
      var top = side.querySelector('.navbar-nav');
      var frag = document.createDocumentFragment();
      var iconoDe = function (link) {
        var i = link.querySelector('.nav-link-icon i');
        return i ? i.className.replace(/\btext-[\w-]+/g, '').trim() : 'ti ti-circle';
      };
      var tituloDe = function (link) {
        var t = link.querySelector('.nav-link-title');
        return (t || link).textContent.replace(/\s+/g, ' ').trim();
      };
      if (top) {
        /* <--- hecho por claude code (03-nov-2026): grupos marcados data-rol-combina se FUSIONAN
           en un solo menú con acordeón por área (p. ej. Maestro BL + Maestro Colegio → "Maestro BL/COL").
           Solo se fusiona cuando hay 2+ del mismo tipo; con 1 solo queda como un menú normal. */
        var COMBINA_TITULO = { maestro: 'Maestros COL/BL' };
        var COMBINA_ICONO  = { maestro: 'ti ti-school' };
        var ddLinkDe = function (s) {
          var si = s.querySelector('.nav-link-icon i');
          var sc = si ? si.className.replace(/\btext-[\w-]+/g, '').trim() : 'ti ti-point';
          var da = document.createElement('a'); da.className = 'tc-dd-link'; da.href = s.getAttribute('href');
          da.innerHTML = '<i class="' + sc + '"></i><span>' + tituloDe(s) + '</span>';
          return da;
        };
        var combinaCount = {}, combinaDD = {};
        Array.prototype.forEach.call(top.children, function (li) {
          var k = li.getAttribute && li.getAttribute('data-rol-combina');
          if (k && li.classList.contains('nav-item') && !li.classList.contains('d-none')) combinaCount[k] = (combinaCount[k] || 0) + 1;
        });

        Array.prototype.forEach.call(top.children, function (li) {
          if (!li.classList.contains('nav-item') || li.classList.contains('d-none')) return;
          var link = null;
          for (var i = 0; i < li.children.length; i++) { if (li.children[i].matches && li.children[i].matches('a.nav-link')) { link = li.children[i]; break; } }
          if (!link) return;
          var title = tituloDe(link);
          var icls = iconoDe(link);
          var href = link.getAttribute('href') || '#';
          var sub = li.querySelectorAll('.collapse a.nav-link[href]:not([href^="#"])');
          var combina = li.getAttribute('data-rol-combina');

          /* Grupo combinable con 2+ presentes → un solo menú con una sección acordeón por área */
          if (combina && combinaCount[combina] >= 2) {
            var area = li.getAttribute('data-rol-area') || title;
            var dd = combinaDD[combina];
            if (!dd) {
              var it = document.createElement('div'); it.className = 'tc-nav-item';
              var bt = document.createElement('button');
              bt.type = 'button'; bt.className = 'tc-nav-link tc-nav-toggle';
              bt.innerHTML = '<i class="' + (COMBINA_ICONO[combina] || icls) + '"></i><span>' + (COMBINA_TITULO[combina] || title) + '</span><i class="ti ti-chevron-down tc-nav-car"></i>';
              dd = document.createElement('div'); dd.className = 'tc-dd';
              it.appendChild(bt); it.appendChild(dd);
              frag.appendChild(it);
              combinaDD[combina] = dd;
            }
            var secc = document.createElement('div'); secc.className = 'tc-dd-sub';
            var stog = document.createElement('button'); stog.type = 'button'; stog.className = 'tc-dd-subtog';
            stog.innerHTML = '<i class="' + icls + '"></i><span>' + area + '</span><i class="ti ti-chevron-down tc-dd-subcar"></i>';
            var sit = document.createElement('div'); sit.className = 'tc-dd-subitems';
            Array.prototype.forEach.call(sub, function (s) { sit.appendChild(ddLinkDe(s)); });
            secc.appendChild(stog); secc.appendChild(sit);
            dd.appendChild(secc);
            return;
          }

          var item = document.createElement('div');
          item.className = 'tc-nav-item';
          if (href.charAt(0) !== '#' && sub.length === 0) {
            var a = document.createElement('a');
            a.className = 'tc-nav-link'; a.href = href;
            a.innerHTML = '<i class="' + icls + '"></i><span>' + title + '</span>';
            item.appendChild(a);
          } else {
            var btn = document.createElement('button');
            btn.type = 'button'; btn.className = 'tc-nav-link tc-nav-toggle';
            btn.innerHTML = '<i class="' + icls + '"></i><span>' + title + '</span><i class="ti ti-chevron-down tc-nav-car"></i>';
            var dd2 = document.createElement('div'); dd2.className = 'tc-dd';
            Array.prototype.forEach.call(sub, function (s) { dd2.appendChild(ddLinkDe(s)); });
            item.appendChild(btn); item.appendChild(dd2);
          }
          frag.appendChild(item);
        });
      }
      topnav.appendChild(frag);
    }

    /* Resaltar el enlace activo del menú superior (server-side o construido) */
    var bestT = null, bestTL = 0;
    Array.prototype.forEach.call(topnav.querySelectorAll('a.tc-dd-link[href], a.tc-nav-link[href]'), function (a) {
      var p = hrefPath(a.getAttribute('href') || ''); if (!p || p === '/') return;
      if (path === p || path.indexOf(p) === 0) { if (p.length > bestTL) { bestT = a; bestTL = p.length; } }
    });
    if (bestT) { bestT.classList.add('on'); var itA = bestT.closest('.tc-nav-item'); if (itA) itA.classList.add('activo'); }

    /* Abrir/cerrar desplegables; en escritorio van position:fixed bajo su botón */
    var cerrarTodos = function () {
      Array.prototype.forEach.call(topnav.querySelectorAll('.tc-nav-item.abierto'), function (x) { x.classList.remove('abierto'); });
    };
    var posicionar = function (it, tg) {
      if (window.innerWidth < 992) return;   // en móvil el CSS lo pone estático
      var dd = it.querySelector('.tc-dd'); if (!dd) return;
      var r = tg.getBoundingClientRect();
      dd.style.top = (r.bottom + 6) + 'px';
      var w = dd.offsetWidth || 258;
      dd.style.left = Math.max(8, Math.min(r.left, window.innerWidth - w - 10)) + 'px';
    };
    topnav.addEventListener('click', function (e) {
      // Sub-grupo (acordeón) dentro de un desplegable: no cierra el desplegable padre.
      var sub = e.target.closest('.tc-dd-subtog');
      if (sub) { e.stopPropagation(); sub.parentElement.classList.toggle('abierto'); return; }
      var tg = e.target.closest('.tc-nav-toggle');
      if (!tg) return;
      var it = tg.parentElement;
      var abierto = it.classList.contains('abierto');
      cerrarTodos();
      if (!abierto) { it.classList.add('abierto'); posicionar(it, tg); }
      e.stopPropagation();
    });
    document.addEventListener('click', function (e) { if (!e.target.closest('#tc-topnav')) cerrarTodos(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrarTodos(); });
  }

  /* 3. Hamburguesa (móvil): muestra/oculta el menú horizontal como panel */
  var burger = document.getElementById('tc-burger');
  if (burger && topnav) {
    burger.addEventListener('click', function (e) {
      e.stopPropagation();
      topnav.classList.toggle('abierto-movil');
      burger.classList.toggle('on');
    });
    topnav.addEventListener('click', function (e) {
      if (e.target.closest('.tc-dd-link, .tc-nav-link:not(.tc-nav-toggle)')) {
        topnav.classList.remove('abierto-movil'); burger.classList.remove('on');
      }
    });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('#tc-topnav') && !e.target.closest('#tc-burger')) {
        topnav.classList.remove('abierto-movil'); burger.classList.remove('on');
      }
    });
  }

  /* 4. Buscador del menú (si existe): filtra los ítems del menú horizontal */
  var q = document.getElementById('tc-side-q');
  if (q && topnav) {
    q.addEventListener('input', function () {
      var v = q.value.trim().toLowerCase();
      Array.prototype.forEach.call(topnav.querySelectorAll('.tc-nav-item'), function (it) {
        var txt = it.textContent.toLowerCase();
        it.style.display = (!v || txt.indexOf(v) >= 0) ? '' : 'none';
      });
    });
  }
})();
