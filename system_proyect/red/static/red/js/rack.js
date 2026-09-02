/* <--- hecho por claude code: elevación de rack. Numeración estándar (U1 abajo, U42 arriba),
   caras frente/atrás, arrastre por U y tipo bandeja. */
(function () {
  var cfg = document.getElementById('rack-cfg'); if (!cfg) return;
  var CSRF = cfg.dataset.csrf, U = parseInt(cfg.dataset.unidades, 10) || 42;
  var URL_ADD = cfg.dataset.add, URL_EDIT = cfg.dataset.edit, URL_MOVE = cfg.dataset.move, URL_DEL = cfg.dataset.del;
  var U_PX = 26;
  var body = document.getElementById('rack-body'), ruler = document.getElementById('rack-ruler');
  function J(v) { try { return JSON.parse(v || '[]'); } catch (e) { return []; } }
  function post(url, data) {
    return fetch(url, { method: 'POST', headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(data) })
      .then(function (r) { return r.json(); });
  }
  function esc(s) { var d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

  var ICON = {
    switch: 'ti-topology-star-3', patch: 'ti-layout-grid', servidor: 'ti-server-2',
    firewall: 'ti-shield-lock', router: 'ti-router', nvr: 'ti-device-cctv', mediaconv: 'ti-arrows-exchange',
    bandeja: 'ti-layout-rows', pdu: 'ti-plug', organizador: 'ti-line-dashed',
    kvm: 'ti-device-desktop', ups: 'ti-battery-2', blank: 'ti-minus', otro: 'ti-box'
  };

  body.style.height = (U * U_PX) + 'px';
  // regla: arriba el número más alto (U), abajo el 1
  for (var n = U; n >= 1; n--) {
    var r = document.createElement('div'); r.className = 'ru'; r.style.height = U_PX + 'px'; r.textContent = n; ruler.appendChild(r);
  }
  // px desde arriba para un ítem cuyo U inferior es u_pos y ocupa u_alto
  function topDe(it) { return (U - (it.u_pos + it.u_alto - 1)) * U_PX; }

  var ALL = [];        // todos los ítems (ambas caras)
  var ITEMS = {};      // id -> {el,data} de la cara visible
  var cara = 'frente';

  function place(el, it) { el.style.top = topDe(it) + 'px'; el.style.height = (it.u_alto * U_PX) + 'px'; }
  function pinta(el, it) {
    el.className = 'ri ri-' + it.tipo; el.dataset.id = it.id;
    el.style.borderLeftColor = it.color || '#495057';
    place(el, it);
    var rango = 'U' + it.u_pos + (it.u_alto > 1 ? ('–' + (it.u_pos + it.u_alto - 1)) : '');
    el.innerHTML = '<i class="ti ' + (ICON[it.tipo] || 'ti-box') + '"></i>' +
      '<span class="ri-name">' + esc(it.nombre) + '</span><span class="ri-u">' + rango + '</span>';
  }
  function render(it) {
    var el = document.createElement('div'); pinta(el, it);
    body.appendChild(el); ITEMS[it.id] = { el: el, data: it }; hook(el); return el;
  }
  function repintarCara() {
    body.innerHTML = ''; ITEMS = {};
    ALL.filter(function (it) { return (it.cara || 'frente') === cara; }).forEach(render);
  }

  // ── Arrastre vertical (cambia la U inferior) ──
  function hook(el) {
    var dragging = false, moved = false, sy, top0;
    el.addEventListener('mousedown', function (e) {
      dragging = true; moved = false; sy = e.clientY; top0 = parseInt(el.style.top, 10) || 0; e.preventDefault();
    });
    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      if (Math.abs(e.clientY - sy) > 3) moved = true;
      var alto = parseInt(el.style.height, 10) / U_PX;
      var top = Math.min((U - alto) * U_PX, Math.max(0, top0 + (e.clientY - sy)));
      el.style.top = top + 'px';
    });
    document.addEventListener('mouseup', function () {
      if (!dragging) return; dragging = false;
      var d = ITEMS[el.dataset.id].data;
      if (moved) {
        var topU = U - Math.round(parseInt(el.style.top, 10) / U_PX);   // U del borde superior
        var upos = topU - d.u_alto + 1;
        upos = Math.min(U - d.u_alto + 1, Math.max(1, upos));
        d.u_pos = upos; place(el, d); pinta(el, d);
        post(URL_MOVE.replace('/0/', '/' + d.id + '/'), { u_pos: upos });
      } else {
        cargarEdicion(d);
      }
    });
  }

  // ── Caras (frente / atrás) ──
  var btnF = document.getElementById('cara-frente'), btnA = document.getElementById('cara-atras');
  function setCara(c) {
    cara = c;
    btnF.className = 'btn ' + (c === 'frente' ? 'btn-primary' : 'btn-outline-primary');
    btnA.className = 'btn ' + (c === 'atras' ? 'btn-primary' : 'btn-outline-primary');
    if (fCara) fCara.value = c;
    modoAgregar(); repintarCara();
  }
  btnF.addEventListener('click', function () { setCara('frente'); });
  btnA.addEventListener('click', function () { setCara('atras'); });

  // ── Formulario (agregar / editar) ──
  var fTitle = document.getElementById('ri-form-title');
  var fNom = document.getElementById('ri-nombre'), fTipo = document.getElementById('ri-tipo');
  var fCara = document.getElementById('ri-cara');
  var fUpos = document.getElementById('ri-upos'), fUalto = document.getElementById('ri-ualto');
  var fVinc = document.getElementById('ri-vinc'), fColor = document.getElementById('ri-color');
  var bAdd = document.getElementById('ri-add'), editBtns = document.getElementById('ri-editbtns');
  var bSave = document.getElementById('ri-save'), bDel = document.getElementById('ri-del'), bCancel = document.getElementById('ri-cancel');
  var editId = null;

  function splitVinc() {
    var v = fVinc.value;
    if (v.charAt(0) === 's') return { ref_kind: 'switch', ref_pk: v.slice(2) };
    if (v.charAt(0) === 'd') return { ref_kind: 'device', ref_pk: v.slice(2) };
    return { ref_kind: '', ref_pk: '' };
  }
  function payload() {
    var vc = splitVinc();
    return { nombre: fNom.value || 'Equipo', tipo: fTipo.value, cara: fCara.value,
      u_pos: fUpos.value || 1, u_alto: fUalto.value || 1, color: fColor.value, ref_kind: vc.ref_kind, ref_pk: vc.ref_pk };
  }
  function modoAgregar() {
    editId = null; fTitle.textContent = 'Agregar equipo';
    bAdd.style.display = ''; editBtns.style.setProperty('display', 'none', 'important');
    fNom.value = ''; fVinc.value = ''; if (fCara) fCara.value = cara;
  }
  function cargarEdicion(d) {
    editId = d.id; fTitle.textContent = 'Editar equipo';
    fNom.value = d.nombre || ''; fTipo.value = d.tipo || 'switch'; fCara.value = d.cara || 'frente';
    fUpos.value = d.u_pos; fUalto.value = d.u_alto; fColor.value = d.color || '#495057';
    fVinc.value = d.ref || '';
    bAdd.style.display = 'none'; editBtns.style.setProperty('display', 'flex', 'important');
  }

  bAdd.addEventListener('click', function () {
    post(URL_ADD, payload()).then(function (r) {
      if (!r.ok) return;
      ALL.push(r.it);
      if ((r.it.cara || 'frente') === cara) render(r.it);
      fNom.value = '';
    });
  });
  bSave.addEventListener('click', function () {
    if (!editId) return;
    post(URL_EDIT.replace('/0/', '/' + editId + '/'), payload()).then(function (r) {
      if (!r.ok) return;
      for (var i = 0; i < ALL.length; i++) if (ALL[i].id === r.it.id) ALL[i] = r.it;
      modoAgregar(); repintarCara();
    });
  });
  bDel.addEventListener('click', function () {
    if (!editId) return; if (!confirm('¿Eliminar este equipo del rack?')) return;
    var id = editId;
    post(URL_DEL.replace('/0/', '/' + id + '/'), {}).then(function () {
      ALL = ALL.filter(function (x) { return x.id !== id; });
      modoAgregar(); repintarCara();
    });
  });
  bCancel.addEventListener('click', modoAgregar);

  // ── Carga inicial ──
  ALL = J(cfg.dataset.items);
  setCara('frente');
})();
