/* inventario_general.js — <--- hecho por claude code (13-oct-2026): Inventario general.
   Tabla (DataTables), foto ampliada, comentario de la auditora y confirmación al eliminar. Un solo global: INV_GENERAL. */
(function () {
  'use strict';
  function modal(el, accion) {
    if (!el) return;
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(el)[accion]();
    else if (window.jQuery && jQuery.fn.modal) jQuery(el).modal(accion);
  }
  if (window.jQuery && jQuery.fn.DataTable && document.querySelectorAll('#ig-tabla tbody tr').length) {
    jQuery('#ig-tabla').DataTable({
      pageLength: 25, order: [[1, 'desc']],
      columnDefs: [{ orderable: false, targets: [0, 8] }],
      language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
    });
  }
  // Foto ampliada (delegado: DataTables vuelve a pintar las filas al paginar)
  document.addEventListener('click', function (e) {
    var img = e.target.closest('.ig-thumb');
    if (!img) return;
    document.getElementById('ig-foto-grande').src = img.dataset.full;
    document.getElementById('ig-foto-titulo').textContent = img.dataset.titulo || '';
    modal(document.getElementById('igModalFoto'), 'show');
  });
  // Comentario de la auditora
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.ig-comentar');
    if (!b) return;
    var f = document.getElementById('ig-form-comentario');
    f.setAttribute('action', b.dataset.url);
    document.getElementById('ig-com-cod').textContent = b.dataset.codigo;
    document.getElementById('ig-com-txt').value = b.dataset.texto || '';
    modal(document.getElementById('igModalComentario'), 'show');
  });
  // Confirmar antes de eliminar
  document.addEventListener('submit', function (e) {
    var f = e.target.closest('.ig-eliminar');
    if (!f || f.dataset.ok === '1') return;
    e.preventDefault();
    var txt = '¿Eliminar ' + f.dataset.codigo + '? No se puede deshacer.';
    if (window.Swal) {
      Swal.fire({ title: 'Eliminar artículo', text: txt, icon: 'warning', showCancelButton: true,
        confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar', confirmButtonColor: '#d63939' })
        .then(function (r) { if (r.isConfirmed) { f.dataset.ok = '1'; f.submit(); } });
    } else if (confirm(txt)) { f.dataset.ok = '1'; f.submit(); }
  });
  /* <--- hecho por claude code (13-oct-2026): la categoría depende del ÁREA (formulario y filtro) */
  function ligar(selArea, selCat, mantenerSinArea) {
    if (!selArea || !selCat) return;
    function aplicar(limpiar) {
      var a = selArea.value;
      Array.prototype.forEach.call(selCat.options, function (o) {
        if (!o.value) return;
        var ok = mantenerSinArea && !a ? true : o.dataset.area === a;
        o.hidden = !ok; o.disabled = !ok;
      });
      var cur = selCat.options[selCat.selectedIndex];
      if (limpiar && cur && cur.value && cur.disabled) selCat.value = '';
    }
    selArea.addEventListener('change', function () { aplicar(true); });
    aplicar(false);
  }
  ligar(document.getElementById('ig-area'), document.getElementById('ig-categoria'), false);
  ligar(document.getElementById('ig-f-area'), document.getElementById('ig-f-cat'), true);

  /* Agregar categoría al área elegida, sin salir del formulario */
  var cfg = document.getElementById('ig-config');
  var btnNueva = document.getElementById('ig-cat-nueva-btn');
  if (cfg && btnNueva) {
    var caja = document.getElementById('ig-cat-nueva'), inp = document.getElementById('ig-cat-nombre');
    var err = document.getElementById('ig-cat-err'), selA = document.getElementById('ig-area'), selC = document.getElementById('ig-categoria');
    function error(t) { err.textContent = t; err.classList.toggle('d-none', !t); }
    btnNueva.addEventListener('click', function () {
      caja.classList.toggle('d-none'); error('');
      if (!caja.classList.contains('d-none')) inp.focus();
    });
    function guardarCat() {
      if (!selA.value) { error('Elige primero el área.'); return; }
      var nombre = inp.value.trim();
      if (nombre.length < 2) { error('Escribe el nombre de la categoría.'); inp.focus(); return; }
      fetch(cfg.dataset.urlCat, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.dataset.csrf },
        body: JSON.stringify({ area: selA.value, nombre: nombre }) })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) { error(d.error || 'No se pudo agregar.'); return; }
          var o = selC.querySelector('option[value="' + d.id + '"]');
          if (!o) {
            o = document.createElement('option'); o.value = d.id; o.textContent = d.nombre; o.dataset.area = d.area;
            selC.appendChild(o);
            var f = document.getElementById('ig-f-cat');   // también al filtro
            if (f) { var o2 = o.cloneNode(true); f.appendChild(o2); }
          }
          selC.value = d.id; inp.value = ''; caja.classList.add('d-none'); error('');
        }).catch(function () { error('Error de conexión.'); });
    }
    document.getElementById('ig-cat-guardar').addEventListener('click', guardarCat);
    inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); guardarCat(); } });
  }
  window.INV_GENERAL = true;
})();
