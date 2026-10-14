/* cierre_notas.js — <--- hecho por claude code (12-oct-2026)
   Pantalla del coordinador: botones "Revocar permisos" y "Fecha de cierre" por grado-sección.
   Config por data-* (#cierre-notas-config) + islas JSON (#cierres-notas, #cierre-parcial-notas).
   El bloqueo real lo hace el servidor; aquí solo se pinta el estado y se llama al endpoint. */
(function () {
  'use strict';
  var cfg = document.getElementById('cierre-notas-config');
  if (!cfg) return;
  function isla(id) { try { return JSON.parse(document.getElementById(id).textContent) || {}; } catch (e) { return {}; } }
  var ESTADOS = isla('cierres-notas');
  var PARCIAL = isla('cierre-parcial-notas');
  var modalEl = document.getElementById('modalCierreNotas');
  var inpFecha = document.getElementById('cierre-fecha-inp');
  var chkTodo = document.getElementById('cierre-todo-parcial');
  var errEl = document.getElementById('cierre-err');
  var grupoActual = null;

  function etiqueta(g, s) { return (g || '') + (s ? ' ' + s : ''); }

  function pintar(ctrl) {
    var e = ESTADOS[ctrl.dataset.grado + '|' + ctrl.dataset.seccion] || {};
    var badge = ctrl.querySelector('.cierre-badge');
    var btnRev = ctrl.querySelector('.btn-cierre-revocar');
    var alcanceParcial = e.revocado_parcial || (!e.fecha_grupo && e.fecha_parcial);
    if (e.parcial_cerrado) {   // <--- hecho por claude code (12-oct-2026)
      badge.className = 'badge cierre-badge cerrado';
      badge.innerHTML = '<i class="ti ti-lock me-1"></i>Parcial cerrado';
    } else if (e.cerrado) {
      badge.className = 'badge cierre-badge cerrado';
      badge.innerHTML = '<i class="ti ti-lock me-1"></i>' + (e.motivo === 'revocado' ? 'Escritura revocada' : 'Cerrado desde ' + e.cierre_en) + (alcanceParcial ? ' · todo el parcial' : '');
    } else if (e.cierre_en) {
      badge.className = 'badge cierre-badge programa';
      badge.innerHTML = '<i class="ti ti-clock me-1"></i>Cierra ' + e.cierre_en + (alcanceParcial ? ' · todo el parcial' : '');
    } else {
      badge.className = 'badge cierre-badge abierto';
      badge.innerHTML = '<i class="ti ti-lock-open me-1"></i>Abierto';
    }
    var revocado = e.revocado_grupo || e.revocado_parcial;
    btnRev.className = 'btn btn-sm btn-cierre-revocar ' + (revocado ? 'btn-success' : 'btn-outline-danger');
    btnRev.querySelector('i').className = 'ti ' + (revocado ? 'ti-lock-open' : 'ti-lock') + ' me-1';
    btnRev.querySelector('.lbl').textContent = revocado ? (e.revocado_parcial ? 'Restaurar permisos (todo el parcial)' : 'Restaurar permisos') : 'Revocar permisos';
  }
  document.querySelectorAll('.cierre-ctrl').forEach(pintar);

  function enviar(payload) {
    payload.area = cfg.dataset.area; payload.parcial = cfg.dataset.parcial; payload.anio = cfg.dataset.anio;
    return fetch(cfg.dataset.url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.dataset.csrf },
      body: JSON.stringify(payload) }).then(function (r) { return r.json(); });
  }
  function aviso(titulo, texto, icono) {
    if (window.Swal) return Swal.fire({ title: titulo, text: texto, icon: icono || 'error' });
    alert(titulo + (texto ? '\n' + texto : '')); return Promise.resolve();
  }

  /* Revocar / restaurar */
  document.querySelectorAll('.btn-cierre-revocar').forEach(function (b) {
    b.addEventListener('click', function () {
      var ctrl = b.closest('.cierre-ctrl'), g = ctrl.dataset.grado, s = ctrl.dataset.seccion;
      var e = ESTADOS[g + '|' + s] || {};
      if (e.revocado_grupo || e.revocado_parcial) {
        var alc = e.revocado_parcial ? 'parcial' : 'grupo';
        enviar({ accion: 'restaurar', alcance: alc, grado: g, seccion: s }).then(function (d) {
          if (d.ok) location.reload(); else aviso('No se pudo restaurar', d.error);
        });
        return;
      }
      var ejecutar = function (todo) {
        enviar({ accion: 'revocar', alcance: todo ? 'parcial' : 'grupo', grado: g, seccion: s }).then(function (d) {
          if (d.ok) location.reload(); else aviso('No se pudo revocar', d.error);
        });
      };
      if (window.Swal) {
        Swal.fire({ title: 'Revocar permisos de escritura', icon: 'warning',
          html: 'Los maestros asignados a <b>' + etiqueta(g, s) + '</b> ya no podrán escribir ni marcar Finalizado.<br><small class="text-muted">Coordinación sí puede seguir editando. Se puede restaurar cuando quieras.</small>',
          input: 'checkbox', inputValue: 0, inputPlaceholder: 'Aplicar a todos los grados y secciones de este parcial',
          showCancelButton: true, confirmButtonText: 'Sí, revocar', cancelButtonText: 'Cancelar', confirmButtonColor: '#d63939'
        }).then(function (r) { if (r.isConfirmed) ejecutar(r.value === 1); });
      } else if (confirm('¿Revocar los permisos de escritura de ' + etiqueta(g, s) + '?')) ejecutar(false);
    });
  });

  /* Fecha de cierre */
  document.querySelectorAll('.btn-cierre-fecha').forEach(function (b) {
    b.addEventListener('click', function () {
      var ctrl = b.closest('.cierre-ctrl');
      grupoActual = { g: ctrl.dataset.grado, s: ctrl.dataset.seccion };
      var e = ESTADOS[grupoActual.g + '|' + grupoActual.s] || {};
      document.getElementById('cierre-grupo-lbl').textContent = etiqueta(grupoActual.g, grupoActual.s);
      chkTodo.checked = !e.fecha_grupo && !!e.fecha_parcial;
      inpFecha.value = e.fecha_grupo || e.fecha_parcial || '';
      errEl.classList.add('d-none');
      if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(modalEl).show();
      else if (window.jQuery && jQuery.fn.modal) jQuery(modalEl).modal('show');
    });
  });
  function guardarFecha(valor) {
    if (!grupoActual) return;
    enviar({ accion: 'fecha', alcance: chkTodo.checked ? 'parcial' : 'grupo', grado: grupoActual.g, seccion: grupoActual.s, cierre_en: valor })
      .then(function (d) {
        if (d.ok) location.reload();
        else { errEl.textContent = d.error || 'No se pudo guardar.'; errEl.classList.remove('d-none'); }
      });
  }
  document.getElementById('cierre-guardar').addEventListener('click', function () {
    if (!inpFecha.value) { errEl.textContent = 'Elige la fecha y la hora.'; errEl.classList.remove('d-none'); return; }
    guardarFecha(inpFecha.value);
  });
  document.getElementById('cierre-quitar').addEventListener('click', function () { guardarFecha(''); });

  /* <--- hecho por claude code (12-oct-2026): Cerrar / reabrir el parcial completo del área */
  function parcialAccion(accion) {
    enviar({ accion: accion, alcance: 'parcial' }).then(function (d) {
      if (d.ok) location.reload(); else aviso('No se pudo guardar', d.error);
    });
  }
  var btnCerrarP = document.getElementById('btn-cerrar-parcial');
  if (btnCerrarP) btnCerrarP.addEventListener('click', function () {
    var n = cfg.dataset.parcial;
    var txt = 'Los maestros ya no podrán escribir y el <b>Parcial ' + n + '</b> desaparecerá de su "Mis Reportes" en esta área.<br><small class="text-muted">Coordinación lo sigue viendo y se puede reabrir.</small>';
    if (window.Swal) {
      Swal.fire({ title: 'Cerrar Parcial ' + n, html: txt, icon: 'warning', showCancelButton: true,
        confirmButtonText: 'Sí, cerrar parcial', cancelButtonText: 'Cancelar', confirmButtonColor: '#d63939'
      }).then(function (r) { if (r.isConfirmed) parcialAccion('cerrar_parcial'); });
    } else if (confirm('¿Cerrar el Parcial ' + n + '?')) parcialAccion('cerrar_parcial');
  });
  var btnReabrirP = document.getElementById('btn-reabrir-parcial');
  if (btnReabrirP) btnReabrirP.addEventListener('click', function () { parcialAccion('reabrir_parcial'); });

  window.CIERRE_NOTAS = { estados: ESTADOS, parcial: PARCIAL };
})();
