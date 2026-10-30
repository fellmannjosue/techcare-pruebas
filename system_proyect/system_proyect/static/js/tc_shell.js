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

  /* 2. Menú horizontal: un ítem por grupo de primer nivel del sidebar.
        Grupo sin submenú → enlace directo. Grupo con submenú → desplegable. */
  if (topnav && side) {
    var top = side.querySelector('.navbar-nav');
    var frag = document.createDocumentFragment();

    function iconoDe(link) {
      var i = link.querySelector('.nav-link-icon i');
      return i ? i.className.replace(/\btext-[\w-]+/g, '').trim() : 'ti ti-circle';
    }
    function tituloDe(link) {
      var t = link.querySelector('.nav-link-title');
      return (t || link).textContent.replace(/\s+/g, ' ').trim();
    }

    if (top) {
      Array.prototype.forEach.call(top.children, function (li) {
        if (!li.classList.contains('nav-item') || li.classList.contains('d-none')) return;
        var link = null;
        for (var i = 0; i < li.children.length; i++) { if (li.children[i].matches && li.children[i].matches('a.nav-link')) { link = li.children[i]; break; } }
        if (!link) return;
        var title = tituloDe(link);
        var icls = iconoDe(link);
        var href = link.getAttribute('href') || '#';
        var sub = li.querySelectorAll('.collapse a.nav-link[href]:not([href^="#"])');
        var activo = !!(best && li.contains(best));

        var item = document.createElement('div');
        item.className = 'tc-nav-item' + (activo ? ' activo' : '');

        if (href.charAt(0) !== '#' && sub.length === 0) {
          // Enlace directo (p. ej. Panel Principal, Modo Mantenimiento)
          var a = document.createElement('a');
          a.className = 'tc-nav-link'; a.href = href;
          a.innerHTML = '<i class="' + icls + '"></i><span>' + title + '</span>';
          item.appendChild(a);
        } else {
          // Desplegable
          var btn = document.createElement('button');
          btn.type = 'button'; btn.className = 'tc-nav-link tc-nav-toggle';
          btn.innerHTML = '<i class="' + icls + '"></i><span>' + title + '</span><i class="ti ti-chevron-down tc-nav-car"></i>';
          var dd = document.createElement('div'); dd.className = 'tc-dd';
          Array.prototype.forEach.call(sub.length ? sub : [], function (s) {
            var si = s.querySelector('.nav-link-icon i');
            var sc = si ? si.className.replace(/\btext-[\w-]+/g, '').trim() : 'ti ti-point';
            var st = tituloDe(s);
            var sh = s.getAttribute('href');
            var da = document.createElement('a'); da.className = 'tc-dd-link'; da.href = sh;
            if (best && s === best) da.classList.add('on');
            da.innerHTML = '<i class="' + sc + '"></i><span>' + st + '</span>';
            dd.appendChild(da);
          });
          item.appendChild(btn); item.appendChild(dd);
        }
        frag.appendChild(item);
      });
    }
    topnav.appendChild(frag);

    /* Abrir/cerrar desplegables (clic); cerrar al hacer clic fuera o con Escape */
    topnav.addEventListener('click', function (e) {
      var tg = e.target.closest('.tc-nav-toggle');
      if (!tg) return;
      var it = tg.parentElement;
      var abierto = it.classList.contains('abierto');
      cerrarTodos();
      if (!abierto) { it.classList.add('abierto'); posicionar(it, tg); }
      e.stopPropagation();
    });
    /* En escritorio el desplegable va position:fixed; lo colocamos bajo su botón, sin salirse */
    function posicionar(it, tg) {
      if (window.innerWidth < 992) return;   // en móvil el CSS lo pone estático
      var dd = it.querySelector('.tc-dd'); if (!dd) return;
      var r = tg.getBoundingClientRect();
      dd.style.top = (r.bottom + 6) + 'px';
      var w = dd.offsetWidth || 258;
      dd.style.left = Math.max(8, Math.min(r.left, window.innerWidth - w - 10)) + 'px';
    }
    function cerrarTodos() {
      Array.prototype.forEach.call(topnav.querySelectorAll('.tc-nav-item.abierto'), function (x) { x.classList.remove('abierto'); });
    }
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
