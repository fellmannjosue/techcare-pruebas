/* tc_camara.js — <--- hecho por claude code (28-sep-2026): "Tomar foto" en todo input de imágenes.
   En teléfonos/tablets (puntero táctil) agrega, junto a cada <input type="file" accept="image/*">,
   un botón "Tomar foto" que abre la CÁMARA (input gemelo con capture="environment") y otro
   "Galería" que abre el selector normal. Las fotos tomadas se copian al input original y se
   dispara su evento change, así el JS de cada pantalla (vista previa, subida AJAX, submit) sigue
   funcionando sin cambios. Sin jQuery. */
(function () {
  'use strict';
  var TACTIL = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  if (!TACTIL) return;
  if (typeof DataTransfer === 'undefined') return;

  function esImagen(inp) {
    var acc = (inp.getAttribute('accept') || '').toLowerCase();
    return acc.indexOf('image') !== -1 && !inp.hasAttribute('capture') && !inp.dataset.tcCamara;
  }

  function copiar(desde, hacia) {
    var dt = new DataTransfer();
    var i;
    if (hacia.multiple) {                               // conservar lo ya elegido y sumar la foto nueva
      for (i = 0; i < hacia.files.length; i++) dt.items.add(hacia.files[i]);
    }
    for (i = 0; i < desde.files.length; i++) dt.items.add(desde.files[i]);
    try { hacia.files = dt.files; } catch (e) { return; }
    hacia.dispatchEvent(new Event('change', { bubbles: true }));
    desde.value = '';
  }

  function montar(inp) {
    inp.dataset.tcCamara = '1';
    var cam = document.createElement('input');
    cam.type = 'file'; cam.accept = 'image/*'; cam.setAttribute('capture', 'environment');
    cam.className = 'd-none'; cam.tabIndex = -1;
    if (inp.multiple) cam.multiple = true;
    cam.addEventListener('change', function () { if (cam.files.length) copiar(cam, inp); });

    var wrap = document.createElement('div');
    wrap.className = 'tc-camara-btns d-flex flex-wrap gap-2 mt-2';
    var b1 = document.createElement('button');
    b1.type = 'button'; b1.className = 'btn btn-sm btn-primary';
    b1.innerHTML = '<i class="ti ti-camera me-1"></i>Tomar foto';
    var b2 = document.createElement('button');
    b2.type = 'button'; b2.className = 'btn btn-sm btn-outline-secondary';
    b2.innerHTML = '<i class="ti ti-photo me-1"></i>Galería';
    b1.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); cam.click(); });
    b2.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); inp.click(); });
    wrap.appendChild(b1); wrap.appendChild(b2); wrap.appendChild(cam);

    // Dónde ponerlo: después de la zona de arrastre/etiqueta que contiene al input, o junto al input
    var padre = inp.parentElement;
    var ancla = (padre && (padre.tagName === 'LABEL' || /drop/i.test(padre.id || '') || /drop/i.test(padre.className || ''))) ? padre : inp;
    if (ancla.parentNode) ancla.parentNode.insertBefore(wrap, ancla.nextSibling);
  }

  function run() {
    document.querySelectorAll('input[type="file"]').forEach(function (inp) { if (esImagen(inp)) montar(inp); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
  if (window.MutationObserver) {
    var t = null;
    new MutationObserver(function () { if (t) return; t = setTimeout(function () { t = null; run(); }, 200); })
      .observe(document.documentElement, { childList: true, subtree: true });
  }
})();
