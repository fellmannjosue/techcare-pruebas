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
      pageLength: 25, order: [[2, 'desc']],
      columnDefs: [{ orderable: false, targets: [0, 1, 9] }],
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
    // <--- hecho por claude code (09-nov-2026): AUTOGUARDADO — la categoría se guarda sola al salir del campo o con Enter
    // (no letra por letra, para no llenar el catálogo de nombres a medio escribir). El botón queda como opción.
    var guardando = false, ultimo = '';
    var ok = document.getElementById('ig-cat-ok');
    function guardarCat(auto) {
      var nombre = inp.value.trim();
      if (auto === true && (nombre.length < 2 || nombre.toLowerCase() === ultimo)) return;
      if (!selA.value) { error('Elige primero el área.'); return; }
      if (nombre.length < 2) { error('Escribe el nombre de la categoría.'); inp.focus(); return; }
      if (guardando) return;
      guardando = true; ultimo = nombre.toLowerCase();
      if (ok) { ok.textContent = 'Guardando…'; ok.classList.remove('d-none'); }
      fetch(cfg.dataset.urlCat, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.dataset.csrf },
        body: JSON.stringify({ area: selA.value, nombre: nombre }) })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          guardando = false;
          if (!d.ok) { ultimo = ''; if (ok) ok.classList.add('d-none'); error(d.error || 'No se pudo agregar.'); return; }
          var o = selC.querySelector('option[value="' + d.id + '"]');
          if (!o) {
            o = document.createElement('option'); o.value = d.id; o.textContent = d.nombre; o.dataset.area = d.area;
            selC.appendChild(o);
            var f = document.getElementById('ig-f-cat');   // también al filtro
            if (f) { var o2 = o.cloneNode(true); f.appendChild(o2); }
          }
          selC.value = d.id; selC.dispatchEvent(new Event('change', { bubbles: true }));
          inp.value = ''; ultimo = ''; caja.classList.add('d-none'); error('');
          if (ok) { ok.textContent = '✓ Categoría «' + d.nombre + '» guardada y elegida'; setTimeout(function () { ok.classList.add('d-none'); }, 3500); }
        }).catch(function () { guardando = false; ultimo = ''; if (ok) ok.classList.add('d-none'); error('Error de conexión.'); });
    }
    document.getElementById('ig-cat-guardar').addEventListener('click', function () { guardarCat(false); });
    inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); guardarCat(false); } });
    inp.addEventListener('blur', function () { guardarCat(true); });
  }
  window.INV_GENERAL = true;
})();

/* <--- hecho por claude code (12-nov-2026): los checkboxes de TIPO son excluyentes (un artículo va en una sola pestaña) */
(function () {
  document.addEventListener('change', function (ev) {
    var c = ev.target;
    if (!c.classList || !c.classList.contains('ig-tipo-chk') || !c.checked) return;
    document.querySelectorAll('.ig-tipo-chk').forEach(function (o) { if (o !== c) o.checked = false; });
  });
})();

/* <--- hecho por claude code (12-nov-2026): selección múltiple → «Asignar tipo» a los marcados (cuenta también los de otras páginas) */
(function () {
  var form = document.getElementById('ig-lote');
  if (!form) return;
  function filas() {   // todas las filas, incluso las de otras páginas de DataTables
    if (window.jQuery && jQuery.fn.DataTable && jQuery.fn.DataTable.isDataTable('#ig-tabla')) return jQuery('#ig-tabla').DataTable().rows().nodes().toArray();
    return Array.prototype.slice.call(document.querySelectorAll('#ig-tabla tbody tr'));
  }
  function marcados() {
    return filas().map(function (tr) { return tr.querySelector('.ig-sel'); }).filter(function (c) { return c && c.checked; });
  }
  function pintar() {
    var m = marcados();
    document.getElementById('ig-lote-n').textContent = m.length;
    form.classList.toggle('d-none', !m.length);
    filas().forEach(function (tr) { var c = tr.querySelector('.ig-sel'); if (c) tr.classList.toggle('ig-fila-sel', c.checked); });
    var visibles = document.querySelectorAll('#ig-tabla tbody .ig-sel'), todos = document.getElementById('ig-sel-todos');
    if (todos) {
      var n = Array.prototype.filter.call(visibles, function (c) { return c.checked; }).length;
      todos.checked = visibles.length > 0 && n === visibles.length;
      todos.indeterminate = n > 0 && n < visibles.length;
    }
  }
  document.addEventListener('change', function (e) {
    if (e.target.id === 'ig-sel-todos') {
      document.querySelectorAll('#ig-tabla tbody .ig-sel').forEach(function (c) { c.checked = e.target.checked; });
      pintar();
    } else if (e.target.classList && e.target.classList.contains('ig-sel')) pintar();
  });
  if (window.jQuery) jQuery('#ig-tabla').on('draw.dt', pintar);
  document.getElementById('ig-lote-limpiar').addEventListener('click', function () {
    filas().forEach(function (tr) { var c = tr.querySelector('.ig-sel'); if (c) c.checked = false; });
    pintar();
  });
  form.addEventListener('submit', function () {
    var caja = document.getElementById('ig-lote-ids');
    caja.innerHTML = '';
    marcados().forEach(function (c) {
      var i = document.createElement('input'); i.type = 'hidden'; i.name = 'ids'; i.value = c.value; caja.appendChild(i);
    });
  });
})();
