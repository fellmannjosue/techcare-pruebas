/* <--- hecho por claude code (06-nov-2026): Configuración → Variables del sistema. Los valores llegan uno a uno por POST tras confirmar la contraseña; nunca están en el HTML */
(function () {
  var CFG_ENV = document.getElementById('env-cfg'); if (!CFG_ENV) return;
  var D = CFG_ENV.dataset, ESCRIBE = D.escribible === '1';
  var hasta = Date.now() + (parseInt(D.restante, 10) || 0) * 1000, pendiente = null, timer = null;
  function $(id) { return document.getElementById(id); }
  function modal(id) { return bootstrap.Modal.getOrCreateInstance($(id)); }
  function post(url, datos) {
    var fd = new FormData(); Object.keys(datos).forEach(function (k) { if (datos[k] !== undefined && datos[k] !== null) fd.append(k, datos[k]); });
    return fetch(url, { method: 'POST', body: fd, headers: { 'X-CSRFToken': D.csrf }, credentials: 'same-origin' })
      .then(function (r) { return r.json().catch(function () { return { ok: false, msg: 'Respuesta inválida del servidor.' }; }); });
  }
  function abierto() { return Date.now() < hasta; }
  function ocultarTodo() {
    document.querySelectorAll('.env-fila .env-mask').forEach(function (m) { if (m.dataset.visto) { m.textContent = '••••••••'; m.classList.remove('is-visto'); delete m.dataset.visto; } });
  }
  function pintarCandado() {
    var s = Math.max(0, Math.round((hasta - Date.now()) / 1000));
    var box = $('env-lock'); box.classList.toggle('is-open', s > 0);
    $('env-lock-txt').textContent = s > 0 ? ('Desbloqueado · ' + Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2)) : 'Bloqueado';
    box.querySelector('.env-lock-estado i').className = 'ti ' + (s > 0 ? 'ti-lock-open' : 'ti-lock');
    $('env-btn-desbloquear').hidden = s > 0;
    if (s <= 0) { ocultarTodo(); clearInterval(timer); timer = null; }
  }
  function arrancar() { pintarCandado(); if (!timer && abierto()) timer = setInterval(pintarCandado, 1000); }
  // Pide la contraseña y luego ejecuta la acción que la necesitaba
  function conClave(fn) { if (abierto()) return fn(); pendiente = fn; $('env-clave').value = ''; $('env-clave-err').hidden = true; modal('envModalClave').show(); setTimeout(function () { $('env-clave').focus(); }, 300); }
  $('env-btn-desbloquear').addEventListener('click', function () { conClave(function () {}); });
  $('env-form-clave').addEventListener('submit', function (e) {
    e.preventDefault();
    post(D.desbloquear, { password: $('env-clave').value }).then(function (r) {
      $('env-clave').value = '';
      if (!r.ok) { $('env-clave-err').textContent = r.msg; $('env-clave-err').hidden = false; return; }
      hasta = Date.now() + r.restante * 1000; arrancar(); modal('envModalClave').hide();
      var fn = pendiente; pendiente = null; if (fn) fn();
    });
  });
  function siBloqueo(r, reintento) { if (r && r.bloqueado) { hasta = 0; pintarCandado(); conClave(reintento); return true; } return false; }

  // Ver valor
  function ver(fila, cb) {
    post(D.ver, { k: fila.dataset.k }).then(function (r) {
      if (siBloqueo(r, function () { ver(fila, cb); })) return;
      if (!r.ok) return;
      if (cb) return cb(r);
      var m = fila.querySelector('.env-mask'), v = r.archivo !== null && r.archivo !== undefined ? r.archivo : r.actual;
      m.textContent = (v === null || v === undefined) ? '(no definida)' : (v === '' ? '(vacía)' : v);
      if (r.archivo !== null && r.archivo !== undefined && r.actual !== r.archivo) m.textContent += '   ·  en uso ahora: ' + (r.actual === null ? '(no definida)' : r.actual);
      m.dataset.visto = '1'; m.classList.add('is-visto');
    });
  }
  // Editar / agregar
  var ED = { k: null, accion: null };
  function campoValor(bool, valor) {
    var w = $('env-ed-wrap');
    if (bool) {
      var ops = bool === 'mayus' ? ['True', 'False'] : ['true', 'false'];
      w.innerHTML = '<select class="form-select" id="env-ed-v">' + ops.map(function (o) { return '<option' + (o === valor ? ' selected' : '') + '>' + o + '</option>'; }).join('') + '</select>';
    } else { w.innerHTML = '<input type="text" class="form-control font-monospace" id="env-ed-v" autocomplete="off" spellcheck="false">'; $('env-ed-v').value = valor || ''; }
  }
  function abrirEditor(accion, fila) {
    ED.accion = accion; ED.k = fila ? fila.dataset.k : null;
    $('env-ed-tit').textContent = accion === 'agregar' ? 'Agregar variable' : 'Editar variable';
    $('env-ed-k').value = ED.k || ''; $('env-ed-k').readOnly = !!ED.k;
    $('env-ed-err').hidden = true;
    var ayuda = fila ? fila.querySelector('.env-ayuda') : null;
    $('env-ed-hint').textContent = (ayuda ? ayuda.textContent + ' · ' : '') + 'Se aplica al reiniciar el servidor.';
    var bool = fila ? fila.dataset.bool : '';
    if (accion === 'editar') ver(fila, function (r) { campoValor(bool, r.archivo !== null && r.archivo !== undefined ? r.archivo : r.actual); modal('envModalEditar').show(); });
    else { campoValor(bool, ''); modal('envModalEditar').show(); }
  }
  $('env-form-editar').addEventListener('submit', function (e) {
    e.preventDefault();
    var k = $('env-ed-k').value.trim().toUpperCase(), v = $('env-ed-v').value;
    post(D.guardar, { k: k, v: v, accion: ED.accion }).then(function (r) {
      if (siBloqueo(r, function () { $('env-form-editar').requestSubmit(); })) return;
      if (!r.ok) { $('env-ed-err').textContent = r.msg; $('env-ed-err').hidden = false; return; }
      location.reload();
    });
  });
  // Deshabilitar / habilitar con confirmación propia
  var CF = null;
  $('env-cf-ok').addEventListener('click', function () {
    if (!CF) return;
    post(D.guardar, { k: CF.k, accion: CF.accion }).then(function (r) {
      if (siBloqueo(r, function () { $('env-cf-ok').click(); })) return;
      if (!r.ok) { $('env-cf-err').textContent = r.msg; $('env-cf-err').hidden = false; return; }
      location.reload();
    });
  });

  document.addEventListener('click', function (e) {
    var b = e.target.closest('.js-ver, .js-editar, .js-accion, .js-agregar-k, #env-btn-agregar, .js-probar'); if (!b) return;
    var fila = b.closest('.env-fila');
    if (b.classList.contains('js-probar')) {
      var res = document.querySelector('.env-res[data-res="' + b.dataset.destino + '"]');
      b.disabled = true; res.hidden = false; res.className = 'env-res small'; res.textContent = 'Probando…';
      post(D.probar, { destino: b.dataset.destino }).then(function (r) { b.disabled = false; res.classList.add(r.ok ? 'ok' : 'mal'); res.textContent = (r.ok ? '✓ ' : '✗ ') + r.msg; });
      return;
    }
    if (b.classList.contains('js-ver')) {
      var m = fila.querySelector('.env-mask');
      if (m.dataset.visto) { m.textContent = '••••••••'; m.classList.remove('is-visto'); delete m.dataset.visto; return; }
      return conClave(function () { ver(fila); });
    }
    if (!ESCRIBE) return;
    if (b.classList.contains('js-editar')) return conClave(function () { abrirEditor('editar', fila); });
    if (b.classList.contains('js-agregar-k')) return conClave(function () { abrirEditor('agregar', fila); });
    if (b.id === 'env-btn-agregar') return conClave(function () { abrirEditor('agregar', null); });
    if (b.classList.contains('js-accion')) {
      return conClave(function () {
        CF = { k: fila.dataset.k, accion: b.dataset.accion };
        $('env-cf-txt').innerHTML = (CF.accion === 'deshabilitar' ? '¿Deshabilitar <code>' : '¿Habilitar <code>') + CF.k + '</code>?' +
          (CF.accion === 'deshabilitar' ? '<br><small class="text-secondary">La línea queda comentada en el archivo (se puede volver a habilitar). Al reiniciar, el sistema la tomará como no definida.</small>' : '');
        $('env-cf-err').hidden = true; modal('envModalConfirmar').show();
      });
    }
  });

  // Buscador + filtros
  var filtro = '';
  function filtrar() {
    var q = $('env-q').value.trim().toLowerCase();
    document.querySelectorAll('.env-grupo').forEach(function (g) {
      var vis = 0;
      g.querySelectorAll('.env-fila').forEach(function (f) {
        var ok = (!q || f.textContent.toLowerCase().indexOf(q) > -1) &&
          (!filtro || (filtro === 'sin_uso' ? f.dataset.sinuso === '1' : filtro === 'off' ? f.dataset.off === '1' : f.dataset.tipo === filtro));
        f.hidden = !ok; vis += ok ? 1 : 0;
      });
      g.hidden = !vis;
    });
  }
  $('env-q').addEventListener('input', filtrar);
  $('env-filtros').addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    filtro = b.dataset.f; [].forEach.call(this.children, function (x) { x.classList.toggle('on', x === b); }); filtrar();
  });
  arrancar();
})();
