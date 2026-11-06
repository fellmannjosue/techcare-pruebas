/* <--- hecho por claude code (06-nov-2026): TC-PRY-0005 Convocatoria a reforzamiento: marcar clases, nota opcional, docente de grado; todo se guarda solo */
(function () {
  var RZ = document.getElementById('rz-cfg').dataset;
  function csrf() { var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ''; }
  function post(url, body) {
    body.parcial = RZ.parcial; body.anio = RZ.anio;
    return fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().catch(function () { return { ok: false, error: 'Error del servidor (' + r.status + ').' }; }); })
      .catch(function () { return { ok: false, error: 'Sin conexión.' }; });
  }
  function aviso(txt) { alert(txt); }   // los errores son raros (máximo 8, sesión caducada)

  /* pestañas */
  var tabs = document.querySelectorAll('#rz-tabs .nav-link');
  function tab(t) {
    tabs.forEach(function (a) { a.classList.toggle('active', a.dataset.tab === t); });
    document.querySelectorAll('[data-pane]').forEach(function (p) { p.hidden = p.dataset.pane !== t; });
    var h = document.getElementById('rz-f-tab'); if (h) h.value = t;
  }
  tabs.forEach(function (a) { a.addEventListener('click', function (e) { e.preventDefault(); tab(a.dataset.tab); }); });
  tab(RZ.tab || 'grado');

  /* filtros: parcial y grado van a campos ocultos */
  var fp = document.getElementById('rz-periodo'), fg = document.getElementById('rz-grado');
  function filtros() {
    var p = (fp.value || '').split('|'), g = (fg.value || '').split('|');
    document.getElementById('rz-f-parcial').value = p[0] || ''; document.getElementById('rz-f-anio').value = p[1] || '';
    document.getElementById('rz-f-g').value = g[0] || ''; document.getElementById('rz-f-s').value = g[1] || '';
  }
  [fp, fg].forEach(function (x) { if (x) x.addEventListener('change', function () { filtros(); if (x === fg && fg.value) { document.getElementById('rz-f-tab').value = 'grado'; } x.form.submit(); }); });
  filtros();

  /* tabla por grado */
  function contar(tr) {
    var n = tr.querySelectorAll('.rz-mk:checked').length, b = tr.querySelector('.rz-cnt'), max = +RZ.max;
    if (b) { b.textContent = n + '/' + max; b.className = 'badge rz-cnt ' + (n >= max ? 'bg-orange-lt text-orange' : 'bg-blue-lt text-blue'); }
  }
  document.addEventListener('change', function (e) {
    var mk = e.target.closest('.rz-mk');
    if (mk) {
      var tr = mk.closest('tr'), nota = mk.parentNode.querySelector('.rz-nota'), on = mk.checked;
      if (on && tr.querySelectorAll('.rz-mk:checked').length > +RZ.max) { mk.checked = false; aviso('Máximo ' + RZ.max + ' asignaturas por alumno.'); return; }
      mk.disabled = true;
      post(RZ.marcar, { g: RZ.g, s: RZ.s, alumno_id: tr.dataset.alumno, asignatura: mk.dataset.asig, accion: on ? 'on' : 'off' }).then(function (r) {
        mk.disabled = false;
        if (!r.ok) { mk.checked = !on; aviso(r.error || 'No se pudo guardar.'); }
        else { nota.hidden = !mk.checked; if (!mk.checked) nota.value = ''; else nota.focus(); }
        contar(tr);
      });
      return;
    }
    var nt = e.target.closest('.rz-nota');
    if (nt) {
      var v = nt.value.trim();
      if (v !== '' && (!/^\d+$/.test(v) || +v > 100)) { nt.classList.add('is-invalid'); return; }
      nt.classList.remove('is-invalid');
      post(RZ.marcar, { g: RZ.g, s: RZ.s, alumno_id: nt.closest('tr').dataset.alumno, asignatura: nt.dataset.asig, accion: 'nota', nota: v }).then(function (r) {
        if (!r.ok) { nt.classList.add('is-invalid'); aviso(r.error || 'No se pudo guardar la nota.'); }
        else { nt.classList.add('is-valid'); setTimeout(function () { nt.classList.remove('is-valid'); }, 900); }
      });
      return;
    }
    var dg = e.target.closest('.rz-docente');
    if (dg) {
      post(RZ.docente, { g: dg.dataset.g, s: dg.dataset.s, docente: dg.value }).then(function (r) {
        if (!r.ok) { aviso(r.error || 'No se pudo guardar el docente.'); return; }
        document.querySelectorAll('.rz-docente[data-g="' + dg.dataset.g + '"][data-s="' + dg.dataset.s + '"]').forEach(function (o) { o.value = dg.value; });
        dg.classList.add('is-valid'); setTimeout(function () { dg.classList.remove('is-valid'); }, 900);
      });
    }
  });
})();
