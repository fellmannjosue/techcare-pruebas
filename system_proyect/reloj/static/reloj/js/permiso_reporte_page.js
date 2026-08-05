/* <--- hecho por claude code (fix): las claves url_reloj_* del template
   son camelCase (urlRecesoSet, urlBonoOverride, urlTardeReglas...); el JS las leía en
   snake_case -> undefined -> POST a /reporte/undefined (404). Alineadas. */
/* permiso_reporte_page.js — <--- hecho por claude code: extraído del template.
   Los datos de Django llegan por la isla JSON #permiso-reporte-data. */
window._PAGE = JSON.parse(document.getElementById('permiso-reporte-data').textContent);

/* ═══ bloques movidos del template ═══ */
(function () {
  var CSRF    = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
  var modal   = new bootstrap.Modal(document.getElementById('modalHorarioEmpleado'));
  var _btn    = null;
  var mhEmp = null, mhMes = null;

  // ── Horas por día (maestros por hora) ──
  function mhRecalcTotal() {
    var s = 0;
    document.querySelectorAll('.mhd-input').forEach(function(i){ s += parseFloat(i.value) || 0; });
    s = Math.round(s * 100) / 100;
    document.getElementById('mht-total').textContent = s;
    return s;
  }
  document.querySelectorAll('.mhd-input').forEach(function(i){
    i.addEventListener('input', mhRecalcTotal);
  });
  async function mhLoad() {
    document.querySelectorAll('.mhd-input').forEach(function(i){ i.value = ''; });
    var d = await (await fetch(window._PAGE.urlMDGet + '?emp_code=' + encodeURIComponent(mhEmp))).json();
    if (d.ok) {
      document.querySelectorAll('.mhd-input').forEach(function(i){
        var v = d.dias[i.dataset.wd];
        i.value = (v && parseFloat(v) > 0) ? v : '';
      });
      mhRecalcTotal();
    }
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.btn-horas-diarias');
    if (!btn) return;
    _btn = btn;

    // Poblar modal con datos actuales
    document.getElementById('mhe-nombre').textContent = btn.dataset.nombre + ' — ' + btn.dataset.mes;
    document.getElementById('mhe-horas').value = btn.dataset.valor || '8.0';
    document.getElementById('mhe-comentario').value = btn.dataset.comentario || '';

    var diasActivos = (btn.dataset.dias || 'L,M,X,J,V').split(',').map(function(d){return d.trim();});
    document.querySelectorAll('.mhe-dia').forEach(function(chk){
      chk.checked = diasActivos.includes(chk.value);
    });

    // Tabla de horas: solo maestros por hora (ocultar "Horas diarias laboradas")
    var tabla = document.getElementById('mhe-horas-tabla');
    var hdl   = document.getElementById('mhe-hdl-section');
    var diasSec   = document.getElementById('mhe-dias-section');
    var comentSec = document.getElementById('mhe-coment-section');
    if (btn.dataset.maestroHora === '1') {
      mhEmp = btn.dataset.emp; mhMes = btn.dataset.mes;
      tabla.classList.remove('d-none');
      hdl.classList.add('d-none');
      diasSec.classList.add('d-none');
      comentSec.classList.add('d-none');
      document.getElementById('mht-err').classList.add('d-none');
      mhLoad();
    } else {
      tabla.classList.add('d-none');
      hdl.classList.remove('d-none');
      diasSec.classList.remove('d-none');
      comentSec.classList.remove('d-none');
    }
    modal.show();
  });

  document.getElementById('mhe-guardar').addEventListener('click', function () {
    if (!_btn) return;
    var esMaestro = _btn.dataset.maestroHora === '1';

    // ── Maestros por hora: guardar las horas por día ──
    if (esMaestro) {
      var horasMap = {};
      document.querySelectorAll('.mhd-input').forEach(function(i){
        var v = parseFloat(i.value); horasMap[i.dataset.wd] = isNaN(v) ? 0 : v;
      });
      var btnG = document.getElementById('mhe-guardar'); btnG.disabled = true;
      fetch(window._PAGE.urlMDSet, {
        method: 'POST', headers: {'Content-Type':'application/json','X-CSRFToken':CSRF},
        body: JSON.stringify({ emp_code: _btn.dataset.emp, horas: horasMap, mes: mhMes })
      }).then(function(r){return r.json();}).then(function(d){
        if (d.ok) {
          var slug = _btn.dataset.emp.toLowerCase().replace(/[^a-z0-9]/g, '-');
          var badge = document.querySelector('.hdl-badge-' + slug);
          if (badge) badge.textContent = d.total + ' h/sem';
          var mes = document.querySelector('.mhmes-' + slug);
          if (mes && d.total_mes != null) mes.textContent = d.total_mes + ' h';
          modal.hide();
        } else { alert('Error: ' + (d.error || 'desconocido')); }
      }).finally(function(){ btnG.disabled = false; });
      return;
    }

    var horas = parseFloat(document.getElementById('mhe-horas').value);
    if (isNaN(horas) || horas <= 0) {
      document.getElementById('mhe-horas').classList.add('is-invalid');
      return;
    }
    document.getElementById('mhe-horas').classList.remove('is-invalid');

    var diasSel = [];
    document.querySelectorAll('.mhe-dia:checked').forEach(function(c){ diasSel.push(c.value); });
    var comentario = document.getElementById('mhe-comentario').value.trim();

    var fd = new FormData();
    fd.append('emp_code',            _btn.dataset.emp);
    fd.append('mes',                 _btn.dataset.mes);
    fd.append('valor',               horas);
    fd.append('dias',                diasSel.join(','));
    fd.append('comentario',          comentario);
    fd.append('csrfmiddlewaretoken', CSRF);

    document.getElementById('mhe-guardar').disabled = true;
    fetch(window._PAGE.urlSetHorasDias, { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          _btn.dataset.valor      = d.valor;
          _btn.dataset.dias       = d.dias;
          _btn.dataset.comentario = comentario;
          if (!esMaestro) {  // los maestros muestran el total h/mes, no h/d
            var slug  = _btn.dataset.emp.toLowerCase().replace(/[^a-z0-9]/g, '-');
            var badge = document.querySelector('.hdl-badge-' + slug);
            if (badge) badge.textContent = d.valor + ' h/d';
          }
          modal.hide();
        } else {
          alert('Error: ' + (d.error || 'desconocido'));
        }
      })
      .finally(function(){ document.getElementById('mhe-guardar').disabled = false; });
  });
})();


if (window._PAGE.esSuperusuario) {

(function () {
  var btn  = document.getElementById('btn-toggle-hdl');
  var CSRF = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
  if (!btn) return;
  btn.addEventListener('click', function () {
    btn.disabled = true;
    fetch(window._PAGE.urlToggleHdl, { method: 'POST', headers: {'X-CSRFToken': CSRF} })
      .then(function(r){ return r.json(); })
      .then(function(){ location.reload(); })
      .finally(function(){ btn.disabled = false; });
  });
})();

}


/* ───────────────────────────── */

(function () {
  var raEmp = null, raFecha = null, modal = null, selM2 = null, selM3 = null, marcasDia = [];
  function pintar(contId, sel, cual) {
    var cont = document.getElementById(contId);
    cont.innerHTML = '';
    marcasDia.forEach(function (m) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'btn btn-sm font-monospace ' + (m === sel ? 'btn-primary' : 'btn-outline-secondary');
      b.textContent = m;
      b.addEventListener('click', function () {
        if (cual === 'm2') selM2 = m; else selM3 = m;
        refrescar();
      });
      cont.appendChild(b);
    });
  }
  function refrescar() { pintar('ra-marcas-m2', selM2, 'm2'); pintar('ra-marcas-m3', selM3, 'm3'); }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.btn-receso-ajuste');
    if (!b) return;
    raEmp = b.dataset.emp; raFecha = b.dataset.fecha;
    marcasDia = (b.dataset.marcas || '').split(',').filter(Boolean);
    selM2 = b.dataset.m2 || null; selM3 = b.dataset.m3 || null;
    document.getElementById('ra-titulo').textContent = b.dataset.nombre + ' · ' + b.dataset.fechaD;
    document.getElementById('ra-err').classList.add('d-none');
    refrescar();
    if (!modal) modal = new bootstrap.Modal(document.getElementById('modalRecesoAjuste'));
    modal.show();
  });
  async function enviar(m2, m3, btn) {
    var err = document.getElementById('ra-err');
    btn.disabled = true;
    try {
      var r = await fetch(window._PAGE.urlRecesoSet, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': (document.cookie.match(/csrftoken=([^;]+)/)||[])[1] || '' },
        body: JSON.stringify({ emp_code: raEmp, fecha: raFecha, m2: m2, m3: m3 })
      });
      var d = await r.json();
      if (d.ok) {
        var p = new URLSearchParams(window.location.search);
        p.set('ptab', 'receso');
        window.location.search = p.toString();
      } else { err.textContent = d.error || 'Error'; err.classList.remove('d-none'); btn.disabled = false; }
    } catch (e2) { err.textContent = 'Error de red'; err.classList.remove('d-none'); btn.disabled = false; }
  }
  document.getElementById('ra-guardar').addEventListener('click', function () {
    var err = document.getElementById('ra-err');
    if (!selM2 || !selM3) { err.textContent = 'Selecciona la marca de salida y la de regreso.'; err.classList.remove('d-none'); return; }
    enviar(selM2, selM3, this);
  });
  document.getElementById('ra-restaurar').addEventListener('click', function () { enviar('', '', this); });
})();

/* ───────────────────────────── */

(function () {
  var t = new URLSearchParams(window.location.search).get('ptab');
  var map = { receso: 'pt-receso-btn', bono: 'pt-bono-btn' };
  if (map[t]) { var b = document.getElementById(map[t]); if (b && window.bootstrap) new bootstrap.Tab(b).show(); }
})();

/* ───────────────────────────── */

(function () {
  var CSRF = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  function post(url, body) {
    return fetch(url, { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF, 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify(body || {}) }).then(function (r) { return r.json(); });
  }

  // Override del bono (superuser)
  document.querySelectorAll('.bono-override').forEach(function (sel) {
    sel.addEventListener('change', function () {
      post(window._PAGE.urlBonoOverride, {
        emp_code: this.dataset.emp, nombre: this.dataset.nombre, mes: this.dataset.mes, valor: this.value
      }).then(function (d) {
        if (d.ok) { var p = new URLSearchParams(location.search); p.set('ptab', 'bono'); location.search = p.toString(); }
        else alert(d.error || 'Error');
      });
    });
  });

  
if (window._PAGE.esSuperusuario) {

  // Modal reglas
  var addToggle = document.getElementById('btn-bono-add-toggle');
  if (addToggle) addToggle.addEventListener('click', function () {
    document.getElementById('bono-add-form').classList.toggle('d-none');
  });
  var addTipo = document.getElementById('bono-add-tipo');
  if (addTipo) addTipo.addEventListener('change', function () {
    document.getElementById('bono-add-permiso-wrap').classList.toggle('d-none', this.value !== 'permiso');
    document.getElementById('bono-add-hora-wrap').classList.toggle('d-none', this.value !== 'hora');
  });
  var addSave = document.getElementById('btn-bono-add-save');
  if (addSave) addSave.addEventListener('click', function () {
    var tipo = document.getElementById('bono-add-tipo').value;
    var body = { tipo: tipo };
    if (tipo === 'permiso') body.permiso_tipo = document.getElementById('bono-add-permiso').value;
    else { body.hora = document.getElementById('bono-add-hora').value; if (!body.hora) { alert('Indica la hora'); return; } }
    post(window._PAGE.urlBonoReglaAdd, body).then(function (d) {
      if (d.ok) location.reload(); else alert(d.error || 'Error');
    });
  });
  document.querySelectorAll('.btn-bono-extra-del').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!confirm('¿Eliminar esta regla?')) return;
      post('/reloj/permisos/bono/regla-extra/' + this.dataset.id + '/eliminar/', {}).then(function (d) {
        if (d.ok) location.reload(); else alert(d.error || 'Error');
      });
    });
  });
  var save = document.getElementById('btn-bono-reglas-save');
  if (save) save.addEventListener('click', function () {
    post(window._PAGE.urlBonoReglas, {
      regla_otro_pagado: document.getElementById('bregla_otro').checked,
      regla_enfermedad: document.getElementById('bregla_enf').checked,
      regla_hora_activa: document.getElementById('bregla_hora').checked,
      hora_limite: document.getElementById('bregla_hora_val').value,
      regla_vigilancia: document.getElementById('bregla_vig').checked,
      hora_vigilancia: document.getElementById('bregla_vig_val').value,
      hora_vigilancia_2: document.getElementById('bregla_vig2_val').value,
      // <--- hecho por claude code: regla de falta de marca
      regla_marca_faltante: !!(document.getElementById('bregla_marca') || {}).checked
    }).then(function (d) {
      if (d.ok) { var p = new URLSearchParams(location.search); p.set('ptab', 'bono'); location.search = p.toString(); }
      else alert(d.error || 'Error');
    });
  });
  
}

})();

/* ───────────────────────────── */

(function () {
  var dataEl = document.getElementById('rt-data');
  var body   = document.getElementById('rt-body');
  if (!body) return;
  var reglas = [];
  try { reglas = JSON.parse(dataEl.textContent || '[]'); } catch (e) {}
  if (!reglas.length) reglas = [{min:11, max:30, horas:0.5}, {min:31, max:60, horas:1.0}];
  body.innerHTML = reglas.map(function (r) {
    return '<tr>' +
      '<td><input type="number" class="form-control form-control-sm rt-min" value="' + r.min + '"></td>' +
      '<td><input type="number" class="form-control form-control-sm rt-max" value="' + (r.max == null ? '' : r.max) + '"></td>' +
      '<td><input type="number" step="0.25" class="form-control form-control-sm rt-h" value="' + r.horas + '"></td>' +
    '</tr>';
  }).join('');
  var btn = document.getElementById('rt-guardar');
  if (btn) btn.addEventListener('click', function () {
    var out = [];
    document.querySelectorAll('#rt-body tr').forEach(function (tr) {
      out.push({
        min:   tr.querySelector('.rt-min').value,
        max:   tr.querySelector('.rt-max').value,
        horas: tr.querySelector('.rt-h').value,
      });
    });
    btn.disabled = true;
    fetch(window._PAGE.urlTardeReglas, {
      method: 'POST',
      headers: { 'X-CSRFToken': window._PAGE.csrf, 'Content-Type': 'application/json' },
      body: JSON.stringify({ reglas: out }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      btn.disabled = false;
      if (d.ok) { location.reload(); } else { alert(d.error || 'Error'); }
    }).catch(function () { btn.disabled = false; alert('Error de red'); });
  });
})();
