/* <--- hecho por claude code (16-sep-2026): Lista de IPs actuales — autoguardado por fila.
   Cada fila = IP actual · categoría · VLAN implementada · equipo · ¿tiene usuario? · usuario.
   El nombre de usuario solo se muestra (y se guarda) cuando la casilla está marcada. */
(function () {
  var cfg = document.getElementById('ia-cfg'); if (!cfg) return;
  var URL_G = cfg.dataset.guardar, URL_B = cfg.dataset.borrar, CSRF = cfg.dataset.csrf;
  var EDITAR = cfg.dataset.editar === '1';
  // IPAM por VLAN, pedido al servidor una sola vez por VLAN (16-sep-2026): {vlan_pk: [{ip, nombre, estado}]}
  var IPAM = {}, IPAM_URL = cfg.dataset.ipamUrl, pendientes = {};
  function cargarVlan(vlan, cb) {
    if (IPAM[vlan]) { cb(); return; }
    if (pendientes[vlan]) { pendientes[vlan].push(cb); return; }
    pendientes[vlan] = [cb];
    fetch(IPAM_URL.replace('/0/', '/' + vlan + '/'), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (r) { IPAM[vlan] = (r && r.ok) ? r.ips : []; })
      .catch(function () { IPAM[vlan] = []; })
      .then(function () { var cbs = pendientes[vlan] || []; delete pendientes[vlan]; cbs.forEach(function (f) { f(); }); });
  }
  var ESTADO = { asignada: 'Asignada', reservada: 'Reservada', dhcp: 'DHCP', conflicto: 'Conflicto', pendiente: 'Pendiente', libre: 'libre' };

  // Llena el select de "IP asignada" con las IPs del IPAM de la VLAN elegida; si la VLAN no
  // tiene IPs en el IPAM, se deja el campo de texto. Marca la IP guardada como seleccionada.
  function armarIpNueva(tr, cb) {
    var vlan = tr.querySelector('.ia-vlan').value;
    var sel = tr.querySelector('.ia-ipnueva-sel'), inp = tr.querySelector('.ia-ipnueva');
    if (!vlan) { sel.hidden = true; inp.hidden = true; if (cb) cb(); return; }
    if (!IPAM[vlan]) {                     // todavía no se pidió: se muestra "cargando" y se reintenta
      sel.innerHTML = '<option value="">Cargando IPs de la VLAN…</option>'; sel.hidden = false; inp.hidden = true;
      cargarVlan(vlan, function () { armarIpNueva(tr, cb); });
      return;
    }
    var lista = IPAM[vlan];
    if (!lista.length) { sel.hidden = true; inp.hidden = false; return; }
    var actual = inp.value.trim();
    var html = '<option value="">— elegir IP del IPAM —</option>';
    var hay = false;
    lista.forEach(function (r) {
      var txt = r.ip + (r.nombre ? ' · ' + r.nombre : '') + ' (' + (ESTADO[r.estado] || r.estado) + ')';
      if (r.ip === actual) hay = true;
      html += '<option value="' + r.ip + '" data-nombre="' + (r.nombre || '').replace(/"/g, '&quot;') + '"' + (r.ip === actual ? ' selected' : '') + '>' + txt + '</option>';
    });
    if (actual && !hay) html += '<option value="' + actual + '" selected>' + actual + ' (no está en el IPAM)</option>';
    sel.innerHTML = html; sel.hidden = false; inp.hidden = true;
    if (cb) cb();
  }
  var tpl = document.getElementById('ia-tpl-fila');
  var IPV4 = /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/;

  function grupo(cat) { return document.querySelector('.ia-grupo[data-cat="' + cat + '"]'); }

  function datos(tr) {
    var tiene = tr.querySelector('.ia-tiene').checked;
    return {
      id: tr.dataset.id || null,
      ip: tr.querySelector('.ia-ip').value.trim(),
      categoria: tr.querySelector('.ia-cat').value,
      vlan: tr.querySelector('.ia-vlan').value || null,
      ip_nueva: tr.querySelector('.ia-vlan').value ? tr.querySelector('.ia-ipnueva').value.trim() : '',
      descripcion: tr.querySelector('.ia-desc').value.trim(),
      tiene_usuario: tiene,
      usuario: tiene ? tr.querySelector('.ia-usuario').value.trim() : '',
      password: (tiene && tr.querySelector('.ia-pass')) ? tr.querySelector('.ia-pass').value : ''
    };
  }

  function msg(tr, texto, ok) {
    var m = tr.querySelector('.ia-msg');
    m.className = 'ia-msg small me-1 ' + (ok ? 'text-green' : 'text-danger');
    m.textContent = texto;
    if (ok) setTimeout(function () { if (m.textContent === texto) m.textContent = ''; }, 2000);
  }

  function contar() {
    var total = 0;
    document.querySelectorAll('.ia-grupo').forEach(function (g) {
      var n = g.querySelectorAll('.ia-fila').length;
      g.querySelector('.ia-count').textContent = n;
      g.hidden = n === 0;
      total += n;
    });
    document.getElementById('ia-total').textContent = total;
    document.getElementById('ia-con-usuario').textContent = document.querySelectorAll('.ia-fila .ia-tiene:checked').length;
    var vacio = document.getElementById('ia-vacio'); if (vacio) vacio.hidden = total > 0;
  }

  // Al cambiar de categoría la fila se pasa a su grupo.
  function mover(tr, cat) {
    var g = grupo(cat);
    if (!g || g.contains(tr)) return;
    g.querySelector('tbody').appendChild(tr);
    g.hidden = false;
  }

  var timers = new WeakMap();
  function programar(tr) {
    clearTimeout(timers.get(tr));
    timers.set(tr, setTimeout(function () { guardar(tr); }, 600));
  }

  function guardar(tr) {
    if (!EDITAR) return;
    var d = datos(tr);
    if (!IPV4.test(d.ip)) { if (d.ip) msg(tr, 'IP inválida', false); return; }
    if (d.ip_nueva && !IPV4.test(d.ip_nueva)) { msg(tr, 'IP asignada inválida', false); return; }
    fetch(URL_G, { method: 'POST', credentials: 'same-origin',
                   headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
                   body: JSON.stringify(d) })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (!r.ok) { msg(tr, r.error || 'No se pudo guardar', false); return; }
        tr.dataset.id = r.id;
        // VLAN en producción: el servidor asignó la IP solo → se refleja en la fila (16-sep-2026)
        var inpN = tr.querySelector('.ia-ipnueva');
        if (r.fila && r.fila.ip_nueva && inpN.value.trim() !== r.fila.ip_nueva) {
          inpN.value = r.fila.ip_nueva;
          armarIpNueva(tr);
        }
        msg(tr, r.auto ? 'IP asignada: ' + r.fila.ip_nueva : 'Guardado', true);
        mover(tr, d.categoria);
        contar();
      })
      .catch(function () { msg(tr, 'Sin conexión', false); });
  }

  function agregar(cat) {
    var g = grupo(cat); if (!g) return;
    var tr = tpl.content.firstElementChild.cloneNode(true);
    tr.querySelector('.ia-cat').value = cat;
    g.querySelector('tbody').appendChild(tr);
    g.hidden = false;
    contar();
    tr.querySelector('.ia-ip').focus();
  }

  document.addEventListener('input', function (e) {
    var tr = e.target.closest('.ia-fila'); if (!tr) return;
    if (e.target.classList.contains('ia-tiene')) {
      var u = tr.querySelector('.ia-usuario'), pw = tr.querySelector('.ia-pass-wrap');
      u.hidden = !e.target.checked;          // sin usuario no se muestra nada
      if (pw) pw.hidden = !e.target.checked;
      if (e.target.checked) u.focus();
      contar();
    }
    programar(tr);
  });
  document.addEventListener('change', function (e) {
    var tr = e.target.closest('.ia-fila'); if (!tr) return;
    // Al elegir VLAN aparece el campo "IP asignada" (16-sep-2026); sin VLAN se oculta y se limpia
    if (e.target.classList.contains('ia-vlan')) {
      var inp = tr.querySelector('.ia-ipnueva');
      if (!e.target.value) inp.value = '';
      else { var sub = e.target.selectedOptions[0].dataset.subred || ''; inp.placeholder = sub ? 'IP en ' + sub : 'IP asignada en la VLAN'; }
      var enProduccion = e.target.value && (e.target.selectedOptions[0].dataset.estado === 'produccion');
      if (enProduccion && !inp.value.trim()) {       // en producción la IP viene sola del servidor
        msg(tr, 'Asignando IP…', true);
        return;                                       // el 'change' ya programó el guardado
      }
      armarIpNueva(tr, function () {
        var sel = tr.querySelector('.ia-ipnueva-sel');
        if (!sel.hidden) { sel.focus(); return; }   // se guarda al elegir la IP
        if (!inp.hidden && !inp.value) inp.focus();
      });
    }
    // Al elegir la IP del IPAM: se copia al campo real y, si la fila no tiene nombre, se toma el del IPAM
    if (e.target.classList.contains('ia-ipnueva-sel')) {
      var inpN = tr.querySelector('.ia-ipnueva'); inpN.value = e.target.value;
      var opt = e.target.selectedOptions[0], desc = tr.querySelector('.ia-desc');
      if (opt && opt.dataset.nombre && !desc.value.trim()) desc.value = opt.dataset.nombre;
    }
    if (e.target.tagName === 'SELECT' || e.target.type === 'checkbox') programar(tr);
  });

  // Ojo: mostrar/ocultar la contraseña (16-sep-2026)
  document.addEventListener('click', function (e) {
    var v = e.target.closest('.ia-ver'); if (!v) return;
    var inp = v.parentNode.querySelector('.ia-pass');
    inp.type = inp.type === 'password' ? 'text' : 'password';
    v.querySelector('i').className = inp.type === 'password' ? 'ti ti-eye' : 'ti ti-eye-off';
  });

  document.addEventListener('click', function (e) {
    var b = e.target.closest('.ia-borrar'); if (!b) return;
    var tr = b.closest('.ia-fila'), id = tr.dataset.id;
    if (!id) { tr.remove(); contar(); return; }
    if (!confirm('¿Quitar la IP ' + tr.querySelector('.ia-ip').value + ' de la lista?')) return;
    fetch(URL_B.replace('/0/', '/' + id + '/'), { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': CSRF } })
      .then(function (r) { return r.json(); })
      .then(function (r) { if (!r.ok) { msg(tr, r.error || 'No se pudo quitar', false); return; } tr.remove(); contar(); })
      .catch(function () { msg(tr, 'Sin conexión', false); });
  });

  document.querySelectorAll('.ia-fila').forEach(function (tr) { armarIpNueva(tr); });   // filas ya guardadas

  var btn = document.getElementById('ia-agregar');
  if (btn) btn.addEventListener('click', function () { agregar(document.getElementById('ia-nueva-cat').value); });

  // Filtro rápido (no toca el servidor)
  var filtro = document.getElementById('ia-filtro');
  filtro.addEventListener('input', function () {
    var q = filtro.value.trim().toLowerCase();
    document.querySelectorAll('.ia-fila').forEach(function (tr) {
      var sel = tr.querySelector('.ia-vlan');
      var txt = [tr.querySelector('.ia-ip').value, tr.querySelector('.ia-ipnueva').value, tr.querySelector('.ia-desc').value,
                 tr.querySelector('.ia-usuario').value,
                 sel.selectedOptions[0] ? sel.selectedOptions[0].textContent : ''].join(' ').toLowerCase();
      tr.hidden = !!q && txt.indexOf(q) < 0;
    });
    document.querySelectorAll('.ia-grupo').forEach(function (g) {
      g.hidden = g.querySelectorAll('.ia-fila:not([hidden])').length === 0;
    });
    if (!q) contar();
  });
})();
