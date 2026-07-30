/* permiso_marcas.js — <--- hecho por claude code: tabs "No marcó entrada" y "No marcó salida".

   Los dos tabs se llenan con UNA sola llamada (el endpoint devuelve ambas listas),
   así que el filtro de fechas de cualquiera de los dos recarga los dos.
   Aparecen TODOS los empleados, tengan o no incidencias. */
(function () {
  var P = window._PAGE || {};
  if (!P.urlMarcasFaltantes) return;

  var TABS = [
    { campo: 'sin_entrada', cont: 'pt-sinentrada-cont', badge: 'pt-sinentrada-badge',
      btn: 'pt-sinentrada-btn', pane: 'pt-sinentrada',
      color: 'orange', vacio: 'Nadie dejó de marcar la entrada en este rango.' },
    { campo: 'sin_salida',  cont: 'pt-sinsalida-cont',  badge: 'pt-sinsalida-badge',
      btn: 'pt-sinsalida-btn',  pane: 'pt-sinsalida',
      color: 'azure',  vacio: 'Nadie dejó de marcar la salida en este rango.' }
  ];

  var cargado = false;

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmtFecha(iso) {
    var p = iso.split('-');
    return p[2] + '/' + p[1];    // dd/mm
  }

  function pintarTab(cfg, data) {
    var cont = document.getElementById(cfg.cont);
    if (!cont) return;

    if (!data.ok) {
      cont.innerHTML = '<div class="alert alert-warning mb-0">' +
        esc(data.error || 'No se pudo cargar.') + '</div>';
      return;
    }

    var conIncidencia = data.empleados.filter(function (e) { return e[cfg.campo].length; });
    var totalDias = conIncidencia.reduce(function (a, e) { return a + e[cfg.campo].length; }, 0);

    var badge = document.getElementById(cfg.badge);
    if (badge) {
      badge.textContent = totalDias;
      badge.classList.toggle('d-none', totalDias === 0);
    }

    var aviso = '';
    if (cfg.campo === 'sin_salida' && data.hoy_excluido_salida) {
      aviso = '<div class="alert alert-info py-2 small mb-2">' +
        '<i class="ti ti-info-circle me-1"></i>El día de hoy no se cuenta aquí: la jornada ' +
        'todavía no termina y aún pueden marcar la salida.</div>';
    }

    // <--- hecho por claude code: solo salen los que SÍ tienen el problema;
    // las filas en 0 no aportaban nada y alargaban la lista a 69.
    if (!conIncidencia.length) {
      cont.innerHTML = aviso + '<div class="text-center text-muted py-5">' +
        '<i class="ti ti-checks" style="font-size:2rem"></i>' +
        '<div class="mt-2">' + cfg.vacio + '</div>' +
        '<div class="small">' + esc(data.desde) + ' a ' + esc(data.hasta) + '</div></div>';
      return;
    }

    var html = aviso +
      '<div class="text-muted small mb-2">' + conIncidencia.length + ' empleado(s) · ' +
      totalDias + ' día(s) · ' + esc(data.desde) + ' a ' + esc(data.hasta) + '</div>' +
      '<div class="table-responsive"><table class="table table-vcenter card-table">' +
      '<thead><tr><th style="width:70px">Código</th><th>Empleado</th>' +
      '<th class="text-center" style="width:90px">Veces</th>' +
      '<th>Días (con la hora marcada)</th></tr></thead><tbody>';

    conIncidencia.forEach(function (e) {
      var dias = e[cfg.campo];
      var chips = dias.map(function (d) {
        // <--- hecho por claude code: se muestra la hora real y la esperada, que es
        // lo que explica por qué el día está marcado.
        var tit = 'Marcó ' + d.hora + ' · su horario dice ' + (d.esperada || '?') +
                  ' · ' + (d.marcas || 1) + ' marca(s) ese día';
        return '<span class="badge bg-' + cfg.color + '-lt text-' + cfg.color +
               ' me-1 mb-1" title="' + esc(tit) + '">' +
               fmtFecha(d.fecha) + ' · ' + esc(d.hora) +
               (d.esperada ? ' <span class="opacity-75">(→ ' + esc(d.esperada) + ')</span>' : '') +
               '</span>';
      }).join('');
      html += '<tr>' +
        '<td class="text-muted">' + esc(e.emp_code) + '</td>' +
        '<td><div class="fw-medium">' + esc(e.nombre) + '</div>' +
          (e.cargo ? '<div class="text-muted small">' + esc(e.cargo) + '</div>' : '') + '</td>' +
        '<td class="text-center"><span class="badge bg-' + cfg.color + '">' + dias.length + '</span></td>' +
        '<td>' + chips + '</td>' +
        '</tr>';
    });
    html += '</tbody></table></div>';
    cont.innerHTML = html;
  }

  // Los dos filtros (uno por tab) se mantienen sincronizados.
  function sincronizar(desde, hasta) {
    document.querySelectorAll('.mf-filtro .mf-desde').forEach(function (i) { i.value = desde; });
    document.querySelectorAll('.mf-filtro .mf-hasta').forEach(function (i) { i.value = hasta; });
  }

  function rangoActual() {
    var d = document.querySelector('.mf-filtro .mf-desde');
    var h = document.querySelector('.mf-filtro .mf-hasta');
    return { desde: d ? d.value : '', hasta: h ? h.value : '' };
  }

  function cargar() {
    var r = rangoActual();
    sincronizar(r.desde, r.hasta);
    TABS.forEach(function (cfg) {
      var cont = document.getElementById(cfg.cont);
      if (cont) cont.innerHTML = '<p class="text-muted text-center py-4 mb-0">' +
        '<span class="spinner-border spinner-border-sm me-2"></span>Cargando…</p>';
    });
    fetch(P.urlMarcasFaltantes + '?desde=' + encodeURIComponent(r.desde) +
          '&hasta=' + encodeURIComponent(r.hasta))
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data.ok) sincronizar(data.desde, data.hasta);
        TABS.forEach(function (cfg) { pintarTab(cfg, data); });
      })
      .catch(function () {
        TABS.forEach(function (cfg) {
          var cont = document.getElementById(cfg.cont);
          if (cont) cont.innerHTML = '<div class="alert alert-danger mb-0">Error de conexión.</div>';
        });
      });
  }

  document.querySelectorAll('.mf-filtro .mf-aplicar').forEach(function (b) {
    b.addEventListener('click', function () { cargado = true; cargar(); });
  });

  // Carga diferida: solo la primera vez que se abre alguno de los dos tabs.
  TABS.forEach(function (cfg) {
    var btn = document.getElementById(cfg.btn);
    if (btn) btn.addEventListener('shown.bs.tab', function () {
      if (!cargado) { cargado = true; cargar(); }
    });
  });
})();
