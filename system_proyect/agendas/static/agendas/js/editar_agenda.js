/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #editar_agenda-config (un .js no lo procesa Django). */
const CFG_EDITAR_AGENDA = (function(){
  var d = document.getElementById("editar_agenda-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
  };
})();

window._PAGE = { agendaId: CFG_EDITAR_AGENDA.j2, csrf: CFG_EDITAR_AGENDA.v0, subirUrl: CFG_EDITAR_AGENDA.v1 };


/* <--- hecho por claude code: lógica recuperada; se había perdido al extraer el JS
   del HTML (solo quedó el puente de configuración de arriba). */

/* editar_agenda.js – agendas */
(function () {
  var PAGE     = window._PAGE || {};
  var AGENDA_ID = PAGE.agendaId || 0;
  var CSRF      = PAGE.csrf    || '';
  var SUBIR_URL = PAGE.subirUrl || '';

  var asoN = 0;

  function subirImg(input, agendaId, materia, zonaId) {
    var file = input.files[0];
    if (!file) return;
    var fd = new FormData();
    fd.append('agenda_id', agendaId);
    fd.append('imagen',    file);
    fd.append('materia',   materia);
    fd.append('csrfmiddlewaretoken', CSRF);
    fetch(SUBIR_URL, { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          var zona = document.getElementById('img-zona-' + zonaId);
          if (zona) {
            zona.innerHTML =
              '<img src="' + data.url + '" style="height:48px;width:100%;object-fit:cover;border-radius:4px;" class="d-block mb-1">' +
              '<button type="button" class="btn btn-xs btn-ghost-danger" onclick="eliminarImg(' + data.id + ', \'' + zonaId + '\')">' +
              '<i class="ti ti-trash"></i></button>';
          }
          document.querySelectorAll('.cam-zona-' + zonaId).forEach(function (el) {
            el.classList.add('d-none');
          });
        }
      });
  }

  function eliminarImg(imgId, zonaId) {
    if (!confirm('¿Eliminar imagen?')) return;
    fetch('/agendas/imagen/' + imgId + '/eliminar/', {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' }
    }).then(function (r) { return r.json(); }).then(function (data) {
      if (data.ok) {
        var zona = document.getElementById('img-zona-' + zonaId);
        if (zona) zona.innerHTML = '';
        document.querySelectorAll('.cam-zona-' + zonaId).forEach(function (el) {
          el.classList.remove('d-none');
        });
      }
    });
  }

  function addAsociada() {
    var sel = document.getElementById('asoSelect');
    var clase = sel ? sel.value : '';
    if (!clase) return;
    asoN++;
    var n   = asoN;
    var esc = clase.replace(/"/g, '&quot;');
    var opt = sel.querySelector('option[value="' + clase.replace(/"/g, '\\"') + '"]');
    var html =
      '<input type="hidden" name="nueva_aso_ids[]" value="' + n + '">' +
      '<div class="mb-2 p-2 rounded bg-yellow-lt border" id="nueva-aso-' + n + '">' +
        '<div class="d-flex align-items-center gap-2 mb-1">' +
          '<span class="fw-bold text-warning"><i class="ti ti-star me-1"></i>' + clase + '</span>' +
          '<input type="hidden" name="nueva_aso_nombre_' + n + '" value="' + esc + '">' +
          '<button type="button" class="btn btn-xs btn-ghost-danger ms-auto"' +
          ' data-aso-clase="' + esc + '" data-aso-n="' + n + '" onclick="window._asoRemove(this)">' +
          '<i class="ti ti-trash"></i></button>' +
        '</div>' +
        '<div class="table-responsive">' +
          '<table class="table table-sm table-bordered mb-0">' +
            '<thead class="table-secondary">' +
              '<tr><th>Lunes</th><th>Martes</th><th>Miércoles</th><th>Jueves</th><th>Viernes</th><th>Nota</th></tr>' +
            '</thead>' +
            '<tbody><tr>' +
              '<td><textarea name="nueva_aso_lunes_'     + n + '" class="form-control form-control-sm" rows="1"></textarea></td>' +
              '<td><textarea name="nueva_aso_martes_'    + n + '" class="form-control form-control-sm" rows="1"></textarea></td>' +
              '<td><textarea name="nueva_aso_miercoles_' + n + '" class="form-control form-control-sm" rows="1"></textarea></td>' +
              '<td><textarea name="nueva_aso_jueves_'    + n + '" class="form-control form-control-sm" rows="1"></textarea></td>' +
              '<td><textarea name="nueva_aso_viernes_'   + n + '" class="form-control form-control-sm" rows="1"></textarea></td>' +
              '<td><textarea name="nueva_aso_nota_'      + n + '" class="form-control form-control-sm" rows="1"></textarea></td>' +
            '</tr></tbody>' +
          '</table>' +
        '</div>' +
      '</div>';
    document.getElementById('nuevas-asociadas').insertAdjacentHTML('beforeend', html);
    if (opt) opt.remove();   // no permitir duplicar la clase
    sel.value = '';
  }

  // Eliminar fila nueva → devolver la clase al select
  function _asoRemove(btn) {
    var row = document.getElementById('nueva-aso-' + btn.dataset.asoN);
    if (row) row.remove();
    var sel = document.getElementById('asoSelect');
    if (sel) {
      var o = document.createElement('option');
      o.value = btn.dataset.asoClase; o.textContent = btn.dataset.asoClase;
      sel.appendChild(o);
    }
  }

  /* Expose functions called from inline onchange/onclick attributes in the template */
  window.subirImg    = subirImg;
  window.eliminarImg = eliminarImg;
  window.addAsociada = addAsociada;
  window._asoRemove  = _asoRemove;
})();
