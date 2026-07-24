/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #inventario_computadoras-config (un .js no lo procesa Django). */
const CFG_INVENTARIO_COMPUTADORAS = (function(){
  var d = document.getElementById("inventario_computadoras-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
    v3: d.v3,
    j3: j(d.v3),
    v4: d.v4,
    j4: j(d.v4),
  };
})();

window._COMP_PAGE = {
  csrf: CFG_INVENTARIO_COMPUTADORAS.v0,
  nextIds: {
    'estandar':   CFG_INVENTARIO_COMPUTADORAS.v1,
    'lab_bl':     CFG_INVENTARIO_COMPUTADORAS.v2,
    'lab_col':    CFG_INVENTARIO_COMPUTADORAS.v3,
    'informatica':CFG_INVENTARIO_COMPUTADORAS.v4
  }
};


/* ─────────────────────────────────────────────────────────────────────
   <--- hecho por claude code: este bloque se había PERDIDO al sacar el JS
   del HTML (commit c8d65db): solo quedó la configuración de arriba y la
   página se quedó sin ninguna lógica. Recuperado de c8d65db~1.
   ───────────────────────────────────────────────────────────────────── */

$(function(){
  $('#computadoras-table').DataTable({
    pageLength: 10, scrollX: true, order: [[0,'desc']],
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
  });
});


$(document).ready(function () {

  // ABRIR MODAL EDITAR
  $(document).on("click", ".editar-computadora", function () {
    let id = $(this).data("id");
    $("#modal-computadora-body").html(
      '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-2">Cargando...</p></div>'
    );
    $("#modalEditarComputadora").modal("show");
    $.get(`/inventario/computadora/get/${id}/`, function (html) {
      $("#modal-computadora-body").html(html);
    }).fail(() => Swal.fire("Error", "No se pudo cargar el formulario.", "error"));
  });

  // GUARDAR EDICIÓN
  $(document).on("submit", "#form-edit-computadora", function (e) {
    e.preventDefault();
    let id = $("#computadora-id").val();
    $.post(`/inventario/computadora/update/${id}/`, $(this).serialize())
      .done((resp) => {
        if (resp.ok) {
          Swal.fire("Actualizado", "Los cambios fueron guardados.", "success").then(() => location.reload());
        } else {
          Swal.fire("Error", "Verifica los campos ingresados.", "error");
        }
      })
      .fail(() => Swal.fire("Error", "No se pudo guardar la información.", "error"));
  });

  // ELIMINAR
  $(document).on("click", ".eliminar-computadora", function () {
    let id = $(this).data("id");
    Swal.fire({
      title: "¿Eliminar computadora?",
      text: "Esta acción no se puede deshacer.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sí, eliminar",
      cancelButtonText: "Cancelar"
    }).then((res) => {
      if (res.isConfirmed) {
        $.post(`/inventario/computadora/delete/${id}/`, { csrfmiddlewaretoken: window._COMP_PAGE.csrf }, function (resp) {
          if (resp.ok) {
            Swal.fire("Eliminado", "Registro eliminado.", "success").then(() => location.reload());
          }
        }).fail(() => Swal.fire("Error", "No se pudo eliminar el registro.", "error"));
      }
    });
  });

});


// ── Verificación lab vs área/grado ──
const LAB_AREA = { lab_bl: 'Bilingue', lab_col: 'Colegio' };
const LAB_GRADO = { informatica: 'informatica' };
const LAB_LABELS = { lab_bl: 'Lab BL', lab_col: 'Lab COL', informatica: 'Informática', estandar: 'General' };

function checkLabPrefijo() {
  var lab   = $('input[name="id_prefix"]:checked').val() || 'estandar';
  var area  = $('#id_area').val();
  var grado = $('#id_grado').val();
  var alertEl  = $('#alerta-lab-prefijo');
  var textoEl  = $('#alerta-lab-prefijo-texto');

  if (!area && !grado) { alertEl.addClass('d-none'); return; }

  var msg = '';
  var labLabel = LAB_LABELS[lab] || lab;

  // Lab BL/COL vs área
  if (LAB_AREA[lab] && area && area !== LAB_AREA[lab]) {
    msg = '<strong>¡Alto!</strong> Seleccionaste el laboratorio <strong>' + labLabel +
          '</strong> pero el área es <strong>' + area +
          '</strong>. ¿Estás usando el prefijo de ID correcto?';
  }
  // Informática vs grado
  else if (lab === 'informatica' && grado && grado !== 'Informatica Avanzada CFP') {
    msg = '<strong>¡Alto!</strong> Seleccionaste <strong>Informática</strong> pero el grado es <strong>' +
          grado + '</strong>. ¿Estás usando el prefijo correcto?';
  }

  if (msg) { textoEl.html(msg); alertEl.removeClass('d-none'); }
  else alertEl.addClass('d-none');
}

// Disparar al cambiar área o grado (el lab ya lo llama el handler de arriba)
$('#id_area, #id_grado').on('change', checkLabPrefijo);

// Sub-tipo de Otros
function toggleGradoSubtipo() {
  var esOtros = $('#id_grado').val() === 'Otros';
  $('#campo-grado-subtipo').toggleClass('d-none', !esOtros);
  if (!esOtros) $('#id_grado_subtipo').val('');
}
$('#id_grado').on('change', toggleGradoSubtipo);
toggleGradoSubtipo();

$('#chk-serie').on('change', function(){
  var inp = $('#input-serie');
  if ($(this).is(':checked')) {
    inp.removeClass('bg-light text-muted').prop('readonly', false).val('').focus();
  } else {
    inp.addClass('bg-light text-muted').prop('readonly', true).val('—');
  }
});

// ── Auto-prefijo de serie según modelo ──
var SERIE_PREFIJOS_COMP = {
  'Ideacentre AIO 3 22ITL6':  'MP24ML',
  'Ideacentre AIO 3 24ARE05': 'MP1Z5',
  'IdeaCentre AIO 5 24IMB05': 'MJ0F7'
};
$('#id_modelo').on('change', function(){
  var prefijo = SERIE_PREFIJOS_COMP[$(this).val()];
  if (prefijo) {
    $('#chk-serie').prop('checked', true);
    var inp = $('#input-serie');
    inp.removeClass('bg-light text-muted').prop('readonly', false).val(prefijo.toUpperCase()).focus();
    var el = document.getElementById('input-serie');
    if (el) el.setSelectionRange(el.value.length, el.value.length);
  }
});

var ipPrefijosChk = {
  'estandar':   '192.168.10.',
  'lab_bl':     '192.168.12.',
  'lab_col':    '192.168.13.',
  'informatica':'192.168.19.',
};
$('#chk-ip').on('change', function(){
  var inp = $('#input-ip');
  if ($(this).is(':checked')) {
    var lab = $('input[name="id_prefix"]:checked').val() || 'estandar';
    var prefijo = ipPrefijosChk[lab] || '192.168.10.';
    inp.removeClass('bg-light text-muted').prop('readonly', false).val(prefijo).focus();
    var el = document.getElementById('input-ip');
    if (el) el.setSelectionRange(el.value.length, el.value.length);
  } else {
    inp.addClass('bg-light text-muted').prop('readonly', true).val('0.0.0.0');
  }
});

// Radio buttons de laboratorio → Asset ID + IP automática
var nextIds = {
  'estandar':   window._COMP_PAGE.nextIds.estandar,
  'lab_bl':     window._COMP_PAGE.nextIds.lab_bl,
  'lab_col':    window._COMP_PAGE.nextIds.lab_col,
  'informatica':window._COMP_PAGE.nextIds.informatica,
};
var ipPrefijos = {
  'estandar':   '192.168.10.',
  'lab_bl':     '192.168.12.',
  'lab_col':    '192.168.13.',
  'informatica':'192.168.19.',
};

function toggleEdificio() {
  var lab = $('input[name="id_prefix"]:checked').val() || 'estandar';
  $('#campo-edificio').toggleClass('d-none', lab !== 'estandar');
  if (lab !== 'estandar') $('#id_edificio').val('');
}
toggleEdificio();

$('input[name="id_prefix"]').on('change', function(){
  var val = this.value;
  $('#preview-asset-id').val(nextIds[val] || nextIds['estandar']);
  toggleEdificio();

  // Auto-rellenar prefijo de IP y habilitar campo
  var prefijo = ipPrefijos[val] || ipPrefijos['estandar'];
  $('#input-ip')
    .val(prefijo)
    .removeClass('bg-light text-muted')
    .prop('readonly', false);
  $('#chk-ip').prop('checked', true);
  // Colocar cursor al final
  var el = document.getElementById('input-ip');
  if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); }

  checkLabPrefijo();
});
