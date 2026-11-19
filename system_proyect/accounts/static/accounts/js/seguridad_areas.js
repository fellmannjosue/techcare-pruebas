/* <--- hecho por claude code (17-nov-2026): Seguridad · clasificar la lista blanca de correos por área (filtro + cambio de área) */
(function () {
  var cfgSeg = document.getElementById('seg-config');
  var filtro = document.getElementById('areas-filtro');
  var tbody = document.getElementById('tabla-correos');
  if (!cfgSeg || !filtro || !tbody) return;
  var areaActiva = '';

  // Toggle general: habilita/deshabilita todos los correos visibles (según el filtro de área)
  var todos = document.getElementById('c-todos');
  function visibles() { return Array.prototype.filter.call(tbody.querySelectorAll('tr[data-id]'), function (tr) { return !tr.hidden; }); }
  function estadoTodos() {
    if (!todos) return;
    var v = visibles();
    var act = v.filter(function (tr) { var b = tr.querySelector('.c-estado'); return b && b.textContent.trim() === 'Habilitado'; }).length;
    todos.checked = v.length > 0 && act === v.length;
    todos.indeterminate = act > 0 && act < v.length;
  }
  if (todos) todos.addEventListener('change', function () {
    var v = visibles();
    if (!v.length) return;
    var activo = todos.checked;
    var fd = new FormData();
    v.forEach(function (tr) { fd.append('ids', tr.dataset.id); });
    fd.append('activo', activo ? '1' : '0');
    fetch(cfgSeg.dataset.cmasivo, { method: 'POST', headers: { 'X-CSRFToken': cfgSeg.dataset.csrf }, body: fd })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (!r.ok) { estadoTodos(); return; }
        v.forEach(function (tr) {
          var b = tr.querySelector('.c-estado');
          if (!b) return;
          b.textContent = activo ? 'Habilitado' : 'Deshabilitado';
          b.className = 'badge c-estado ' + (activo ? 'bg-green-lt text-green' : 'bg-secondary-lt text-secondary');
        });
        estadoTodos();
      })
      .catch(estadoTodos);
  });
  // los botones de cada fila cambian el estado: refrescar el toggle general después
  tbody.addEventListener('click', function (e) { if (e.target.closest('.c-toggle, .c-del')) setTimeout(estadoTodos, 600); });

  function aplicarFiltro() {
    tbody.querySelectorAll('tr[data-id]').forEach(function (tr) {
      tr.hidden = !!areaActiva && tr.dataset.area !== areaActiva;
    });
    filtro.querySelectorAll('.a-filtro').forEach(function (b) {
      var on = b.dataset.area === areaActiva;
      b.classList.toggle('btn-primary', on);
      b.classList.toggle('btn-outline-secondary', !on);
    });
    estadoTodos();
  }

  function recontar() {
    var c = {};
    tbody.querySelectorAll('tr[data-id]').forEach(function (tr) { c[tr.dataset.area] = (c[tr.dataset.area] || 0) + 1; });
    filtro.querySelectorAll('.a-cnt').forEach(function (s) { s.textContent = c[s.dataset.area] || 0; });
  }

  filtro.addEventListener('click', function (e) {
    var b = e.target.closest('.a-filtro');
    if (!b) return;
    areaActiva = b.dataset.area;
    try { sessionStorage.setItem('seg_area', areaActiva); } catch (er) {}
    aplicarFiltro();
  });

  tbody.addEventListener('change', function (e) {
    var sel = e.target.closest('.c-area');
    if (!sel) return;
    var tr = sel.closest('tr');
    var fd = new FormData();
    fd.append('id', tr.dataset.id);
    fd.append('area', sel.value);
    fetch(cfgSeg.dataset.carea, { method: 'POST', headers: { 'X-CSRFToken': cfgSeg.dataset.csrf }, body: fd })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (!r.ok) { sel.classList.add('is-invalid'); return; }
        sel.classList.remove('is-invalid');
        tr.dataset.area = r.area;
        recontar();
        aplicarFiltro();
      })
      .catch(function () { sel.classList.add('is-invalid'); });
  });

  try { areaActiva = sessionStorage.getItem('seg_area') || ''; } catch (er) {}
  if (areaActiva && !filtro.querySelector('.a-filtro[data-area="' + areaActiva + '"]')) areaActiva = '';
  aplicarFiltro();
})();
