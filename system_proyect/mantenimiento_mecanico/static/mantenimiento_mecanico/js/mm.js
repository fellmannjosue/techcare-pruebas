/* mm.js — <--- hecho por claude code (01-oct-2026): Mantenimiento Mecánico (página de un insumo).
   Config por data-* (#mm-config) + islas JSON (#mm-entregas, #mm-maquinaria). Un solo global: MM_PAGE (IIFE). */
(function () {
  'use strict';
  var cfg = document.getElementById('mm-config');
  if (!cfg) return;
  var CSRF = cfg.dataset.csrf, URL_MAQ = cfg.dataset.urlMaquinaria, URL_CREAR = cfg.dataset.urlCrear, URL_EDITAR = cfg.dataset.urlEditar;
  var SALDO = parseFloat(cfg.dataset.saldo || '0'), PIDE_KM = cfg.dataset.km === '1';
  function isla(id) {   // <--- siempre devuelve una lista (si llegara serializada dos veces, se vuelve a leer)
    try { var v = JSON.parse(document.getElementById(id).textContent); if (typeof v === 'string') v = JSON.parse(v); return Array.isArray(v) ? v : []; }
    catch (e) { return []; }
  }
  var ENTREGAS = {}; isla('mm-entregas').forEach(function (e) { ENTREGAS[e.id] = e; });

  var form = document.getElementById('mm-form-entrega');
  if (form) {   // <--- hecho por claude code (02-oct-2026): solo existe para quien puede editar (la auditoría no lo tiene)
  var modalEl = document.getElementById('mmModalEntrega');
  /* <--- hecho por claude code (01-oct-2026): la instancia se pide AL HACER CLIC. Antes se pedía al cargar el
     script y, como este corría antes que Bootstrap, quedaba null y "Nueva entrega" / "Editar" no abrían. */
  function mostrarModal() {
    if (window.bootstrap && bootstrap.Modal) { bootstrap.Modal.getOrCreateInstance(modalEl).show(); return; }
    if (window.jQuery && jQuery.fn.modal) { jQuery(modalEl).modal('show'); return; }
    alert('No se pudo abrir el formulario. Recarga la página (Ctrl+F5).');
  }
  var titulo = document.getElementById('mm-entrega-titulo');
  var selMaq = document.getElementById('mm-maq');
  var kmWrap = document.getElementById('mm-km-wrap');
  var inpGal = form.elements.namedItem('galones');
  var aviso = form.querySelector('.mm-aviso-saldo');
  if (aviso) aviso.querySelector('.mm-saldo-txt').textContent = SALDO.toFixed(2);

  function ajustarKm() {
    var opt = selMaq ? selMaq.options[selMaq.selectedIndex] : null;   // en diésel no hay maquinaria (se elige vehículo)
    var maqKm = !!(opt && opt.dataset.km === '1');
    var mostrar = PIDE_KM || maqKm;
    kmWrap.classList.toggle('d-none', !mostrar);
    F('kilometraje').required = PIDE_KM;
  }
  if (selMaq) selMaq.addEventListener('change', ajustarKm);
  // <--- hecho por claude code (12-oct-2026): diésel → vehículo; muestra su último km como referencia
  var selVeh = document.getElementById('mm-veh'), vehHint = document.getElementById('mm-veh-km');
  function vehKm() {
    if (!selVeh || !vehHint) return;
    var o = selVeh.options[selVeh.selectedIndex], km = o ? o.dataset.km : '';
    vehHint.textContent = km ? 'Último km registrado: ' + String(km).replace(/\B(?=(\d{3})+(?!\d))/g, '.') : '';
  }
  if (selVeh) selVeh.addEventListener('change', vehKm);

  function F(n) { return form.elements.namedItem(n); }   // campo del formulario por nombre (no depende de form.<nombre>)
  function abrir(e) {
    form.reset();
    if (e) {
      titulo.textContent = 'Editar entrega';
      form.setAttribute('action', URL_EDITAR.replace('/0/', '/' + e.id + '/'));
      F('fecha').value = e.fecha; F('hora').value = e.hora; F('galones').value = e.galones;
      if (F('maquinaria')) F('maquinaria').value = e.maquinaria || '';
      if (F('vehiculo')) F('vehiculo').value = e.vehiculo || ''; F('kilometraje').value = e.kilometraje || '';
      F('persona').value = e.persona || ''; F('observaciones').value = e.observaciones || '';
    } else {
      titulo.textContent = 'Nueva entrega';
      form.setAttribute('action', URL_CREAR);
      var ahora = new Date();
      F('hora').value = ('0' + ahora.getHours()).slice(-2) + ':' + ('0' + ahora.getMinutes()).slice(-2);
    }
    ajustarKm(); vehKm(); revisarSaldo();
    mostrarModal();
  }
  function revisarSaldo() {
    if (!aviso) return;
    var v = parseFloat(inpGal.value || '0');
    aviso.classList.toggle('d-none', !(v > SALDO));
  }
  inpGal.addEventListener('input', revisarSaldo);

  document.getElementById('mm-btn-nueva').addEventListener('click', function () { abrir(null); });
  document.querySelectorAll('.mm-editar').forEach(function (b) {
    b.addEventListener('click', function () { abrir(ENTREGAS[b.dataset.id]); });
  });

  /* Maquinaria agregable desde el propio formulario */
  var nuevaWrap = document.getElementById('mm-maq-nueva');
  if (selMaq) document.getElementById('mm-maq-nueva-btn').addEventListener('click', function () {
    nuevaWrap.classList.toggle('d-none');
    if (!nuevaWrap.classList.contains('d-none')) document.getElementById('mm-maq-nombre').focus();
  });
  if (selMaq) document.getElementById('mm-maq-guardar').addEventListener('click', function () {
    var nombre = document.getElementById('mm-maq-nombre').value.trim();
    if (nombre.length < 2) { document.getElementById('mm-maq-nombre').focus(); return; }
    fetch(URL_MAQ, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ nombre: nombre, tipo: document.getElementById('mm-maq-tipo').value, usa_kilometraje: PIDE_KM }) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) { alert(d.error || 'No se pudo agregar.'); return; }
        var existe = selMaq.querySelector('option[value="' + d.id + '"]');
        if (!existe) {
          var o = document.createElement('option'); o.value = d.id; o.textContent = d.nombre; o.dataset.km = d.usa_kilometraje ? '1' : '0';
          selMaq.appendChild(o);
        }
        selMaq.value = d.id; ajustarKm();
        document.getElementById('mm-maq-nombre').value = ''; nuevaWrap.classList.add('d-none');
      }).catch(function () { alert('Error de conexión.'); });
  });

  }

  /* <--- hecho por claude code (02-oct-2026): ELIMINAR se retiró del módulo (pedido del usuario): lo registrado no se borra, ni el superusuario. */

  /* <--- hecho por claude code (02-oct-2026): comentarios de auditoría (todos los que ven el módulo) */
  var comEl = document.getElementById('mmModalComentarios');
  var comForm = document.getElementById('mm-form-comentario');
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  document.querySelectorAll('.mm-comentarios').forEach(function (b) {
    b.addEventListener('click', function () {
      var e = ENTREGAS[b.dataset.id] || { comentarios: [] };
      document.getElementById('mm-com-cod').textContent = e.codigo || '';
      var lista = document.getElementById('mm-com-lista');
      lista.innerHTML = (e.comentarios || []).length
        ? e.comentarios.map(function (c) { return '<div class="mm-com"><div class="mm-com-meta">' + esc(c.autor) + ' · ' + esc(c.fecha) + '</div><div class="mm-com-txt">' + esc(c.texto) + '</div></div>'; }).join('')
        : '<div class="text-muted small">Sin comentarios todavía.</div>';
      comForm.setAttribute('action', b.dataset.url);
      comForm.elements.namedItem('texto').value = '';
      if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(comEl).show();
      else if (window.jQuery && jQuery.fn.modal) jQuery(comEl).modal('show');
    });
  });

  /* Reportes: arma el enlace con el rango elegido */
  function enlaces() {
    var d = document.getElementById('mm-rep-desde').value, h = document.getElementById('mm-rep-hasta').value;
    document.querySelectorAll('.mm-rep-link').forEach(function (a) { a.href = a.dataset.base + '?desde=' + d + '&hasta=' + h; });
  }
  ['mm-rep-desde', 'mm-rep-hasta'].forEach(function (id) { var el = document.getElementById(id); if (el) el.addEventListener('change', enlaces); });
  enlaces();

  /* DataTable de entregas */
  if (window.jQuery && jQuery.fn.DataTable) {
    var t = jQuery('#mm-tabla');
    if (t.find('tbody tr').length && t.find('tbody td[colspan]').length === 0) {
      t.DataTable({ pageLength: 25, order: [[1, 'desc']], columnDefs: [{ orderable: false, targets: -1 }],
        language: { search: 'Buscar:', lengthMenu: 'Mostrar _MENU_', info: 'Mostrando _START_ a _END_ de _TOTAL_', infoEmpty: 'Sin registros',
          infoFiltered: '(filtrado de _MAX_)', zeroRecords: 'Sin coincidencias', paginate: { first: '«', last: '»', next: '›', previous: '‹' } } });
    }
  }
  window.MM_PAGE = { abrir: (typeof abrir === 'function') ? abrir : null };
})();
