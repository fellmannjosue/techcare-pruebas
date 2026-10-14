/* contable_asiento.js — <--- hecho por claude code (23-sep-2026): líneas dinámicas de la partida contable.
   Carga las cuentas de detalle por JSON, autocompleta por código/nombre (datalist), calcula totales y
   diferencia en vivo y bloquea "Contabilizar" si no cuadra. Sin librerías. */
(function () {
  'use strict';
  const cfg = document.getElementById('asiento-cfg');
  const tbody = document.querySelector('#tabla-lineas tbody');
  const tpl = document.getElementById('tpl-linea');
  const dl = document.getElementById('dl-cuentas');
  if (!cfg || !tbody || !tpl) return;
  let cuentas = [];            // [{id, codigo, nombre, tipo}]
  const porTexto = new Map();  // "codigo · nombre" -> cuenta

  function fmt(n) { return n.toLocaleString('es-HN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  function buscarCuenta(txt) {
    txt = (txt || '').trim().toLowerCase();
    if (!txt) return null;
    if (porTexto.has(txt)) return porTexto.get(txt);
    const cod = txt.split(' ')[0];
    return cuentas.find(c => c.codigo.toLowerCase() === cod) || cuentas.find(c => c.codigo.toLowerCase() === txt)
        || cuentas.find(c => c.nombre.toLowerCase() === txt) || null;
  }

  function resolver(tr) {
    const inp = tr.querySelector('.l-cuenta'), hid = tr.querySelector('.l-cuenta-id'), lbl = tr.querySelector('.l-cuenta-nombre');
    const c = buscarCuenta(inp.value);
    if (c) { hid.value = c.id; lbl.textContent = c.nombre + ' · ' + c.tipo; lbl.classList.remove('text-danger'); tr.classList.remove('l-error'); }
    else { hid.value = ''; lbl.textContent = inp.value ? 'Cuenta no encontrada' : ''; lbl.classList.toggle('text-danger', !!inp.value); tr.classList.toggle('l-error', !!inp.value); }
  }

  function totales() {
    let d = 0, h = 0, n = 0;
    tbody.querySelectorAll('tr').forEach(tr => {
      const vd = parseFloat(tr.querySelector('.l-debe').value) || 0, vh = parseFloat(tr.querySelector('.l-haber').value) || 0;
      if (vd || vh) n++;
      d += vd; h += vh;
    });
    d = Math.round(d * 100) / 100; h = Math.round(h * 100) / 100;
    const dif = Math.round((d - h) * 100) / 100;
    document.getElementById('tot-debe').textContent = fmt(d);
    document.getElementById('tot-haber').textContent = fmt(h);
    const elDif = document.getElementById('tot-dif'); elDif.textContent = fmt(Math.abs(dif));
    elDif.classList.toggle('text-danger', dif !== 0); elDif.classList.toggle('text-success', dif === 0 && d > 0);
    const badge = document.getElementById('estado-cuadre'), btn = document.getElementById('btn-contabilizar');
    const ok = dif === 0 && d > 0 && n >= 2;
    badge.className = 'badge ' + (n === 0 ? 'bg-secondary-lt text-secondary' : ok ? 'bg-green-lt text-green' : 'bg-red-lt text-red');
    badge.textContent = n === 0 ? 'Sin líneas' : ok ? 'Partida cuadrada' : (dif !== 0 ? 'No cuadra: diferencia L ' + fmt(Math.abs(dif)) : 'Faltan líneas');
    btn.disabled = !ok;
  }

  function addLinea(data) {
    const tr = tpl.content.firstElementChild.cloneNode(true);
    tbody.appendChild(tr);
    if (data) {
      tr.querySelector('.l-cuenta').value = data.codigo ? data.codigo + ' · ' + data.nombre : '';
      tr.querySelector('.l-cuenta-id').value = data.cuenta_id || '';
      tr.querySelector('.l-cuenta-nombre').textContent = data.nombre || '';
      tr.querySelector('.l-centro').value = data.centro || '';
      tr.querySelector('.l-desc').value = data.desc || '';
      tr.querySelector('.l-debe').value = data.debe || 0;
      tr.querySelector('.l-haber').value = data.haber || 0;
    }
    const inp = tr.querySelector('.l-cuenta');
    inp.addEventListener('change', () => resolver(tr));
    inp.addEventListener('blur', () => resolver(tr));
    // Debe y Haber son excluyentes: al escribir en uno se limpia el otro
    tr.querySelector('.l-debe').addEventListener('input', e => { if (parseFloat(e.target.value) > 0) tr.querySelector('.l-haber').value = 0; totales(); });
    tr.querySelector('.l-haber').addEventListener('input', e => { if (parseFloat(e.target.value) > 0) tr.querySelector('.l-debe').value = 0; totales(); });
    tr.querySelector('.l-quitar').addEventListener('click', () => { tr.remove(); if (!tbody.children.length) addLinea(); totales(); });
    // Enter en el Haber de la última línea agrega otra (captura rápida)
    tr.querySelector('.l-haber').addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); if (tr === tbody.lastElementChild) addLinea(); tr.nextElementSibling?.querySelector('.l-cuenta').focus(); }
    });
    return tr;
  }

  fetch(cfg.dataset.urlCuentas, { credentials: 'same-origin' }).then(r => r.json()).then(j => {
    cuentas = j.cuentas || [];
    cuentas.forEach(c => { porTexto.set((c.codigo + ' · ' + c.nombre).toLowerCase(), c);
      const o = document.createElement('option'); o.value = c.codigo + ' · ' + c.nombre; dl.appendChild(o); });
    tbody.querySelectorAll('tr').forEach(resolver);
  });

  let ini = [];
  try { ini = JSON.parse(document.getElementById('lineas-ini').textContent) || []; } catch (e) { ini = []; }
  if (ini.length) ini.forEach(addLinea); else { addLinea(); addLinea(); }
  totales();
  document.getElementById('btn-add-linea').addEventListener('click', () => { addLinea().querySelector('.l-cuenta').focus(); });
  // Antes de enviar: quitar líneas vacías para no molestar al servidor
  document.getElementById('form-asiento').addEventListener('submit', () => {
    tbody.querySelectorAll('tr').forEach(tr => {
      const vd = parseFloat(tr.querySelector('.l-debe').value) || 0, vh = parseFloat(tr.querySelector('.l-haber').value) || 0;
      if (!vd && !vh && !tr.querySelector('.l-cuenta-id').value) tr.remove();
    });
  });
})();
