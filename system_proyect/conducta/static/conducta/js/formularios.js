/* <--- hecho por claude code: MD_POR_GRADO llega por la isla JSON del template */
(function(){ var el=document.getElementById('md-por-grado-data');
  if (el && !window.MD_POR_GRADO) { try { window.MD_POR_GRADO = JSON.parse(el.textContent); }
    catch(e){ window.MD_POR_GRADO = {}; } } })();

// ===========================
//   JS UNIFICADO CONDUCTA + INFORMATIVO + PROGRESS REPORT
// ===========================

$(function () {

  // ===================================================
  // ============  PROGRESS REPORT - JS DINÁMICO  ======
  // ===================================================
  // Materias según tipo de grado — <--- hecho por claude code: lista fija completa como Agendas
  const MATERIAS_PRIMARIA = [
    "Math", "Language", "Spelling", "Phonics", "Reading", "Science",
    "Español", "CCSS", "Penmanship", "Arte", "Biblia", "Computación", "Speaking", "P.E"
  ];
  const MATERIAS_COLEGIO = [
    "Math", "Language", "Spelling", "Reading", "Science", "Español", "CCSS", "Cívica",
    "Arte", "Biblia", "Computación", "Speaking", "P.E"
  ];

  // Devuelve si el grado es primaria
  function esPrimaria(grado) {
    if (!grado) return false;
    return grado.toLowerCase().includes('primariabl') || grado.toLowerCase().includes('preescolar');
  }

  // Genera la tabla de materias
  function generarFilasTablaMaterias(grado) {
    let materias = esPrimaria(grado) ? MATERIAS_PRIMARIA : MATERIAS_COLEGIO;
    let html = '';
    materias.forEach(mat => {
      if (mat !== "Asociadas") {
        html += `
          <tr>
            <td><strong>${mat}</strong></td>
            <td>
              <textarea name="asignacion_${mat}" class="form-control" rows="2" maxlength="80" autocomplete="off"></textarea>
            </td>
            <td>
              <textarea name="comentario_${mat}" class="form-control" rows="2" maxlength="80" autocomplete="off"></textarea>
            </td>
          </tr>
        `;
      } else {
        html += `
          <tr id="fila-asociadas">
            <td><strong>Asociadas</strong></td>
            <td>
              <textarea name="asignacion_Asociadas[]" class="form-control input-asociadas" rows="2" maxlength="80" autocomplete="off"></textarea>
            </td>
            <td class="d-flex align-items-center gap-2">
              <button type="button" class="btn btn-success btn-sm add-asociada me-2" title="Agregar otra fila">+</button>
              <textarea name="comentario_Asociadas[]" class="form-control input-asociadas flex-grow-1" rows="2" maxlength="80" autocomplete="off"></textarea>
            </td>
          </tr>
        `;
      }
    });
    $("#tabla-materias-body").html(html);
  }

  // ========== Inicializar Progress Report ==========
  if ($('#id_alumno').length && $('#tabla-materias').length) {
    // <--- hecho por claude code: evita el reporte DOBLE por doble-clic/doble-envío.
    $('#progressForm').on('submit', function () {
      var $f = $(this);
      if ($f.data('enviado')) { return false; }   // ya se envió una vez
      $f.data('enviado', true);
      $f.find('button[type="submit"]').prop('disabled', true)
        .html('<span class="spinner-border spinner-border-sm me-1"></span>Guardando…');
    });

    // --- ACTIVAR SELECT2 EN ALUMNO ---
    $('#id_alumno').select2({
      placeholder: "-- Selecciona un estudiante --",
      minimumResultsForSearch: 0,
      width: '100%',
      allowClear: true,
      dropdownParent: $('#id_alumno').parent()
    });

    // --- Inicializar la tabla y autollenar grado ---
    function setGradoProgress() {
      let grado = '';
      let select2Data = $('#id_alumno').select2('data');
      if (select2Data && select2Data[0] && select2Data[0].element) {
        grado = $(select2Data[0].element).data('grado') || '';
      } else {
        grado = $('#id_alumno').find('option:selected').data('grado') || '';
      }
      $('#grado-display').val(grado);
      $('#id_grado').val(grado);
      generarFilasTablaMaterias(grado);
    }
    setGradoProgress();
    $('#id_alumno').on('select2:select change', setGradoProgress);

    // --------- Lógica Asociadas (agregar/eliminar/Enter) -----------
    $('#tabla-materias').on('click', '.add-asociada', function () {
      let nuevaFila = `
        <tr class="asociada-extra">
          <td></td>
          <td><textarea name="asignacion_Asociadas[]" class="form-control input-asociadas" rows="2" maxlength="80" autocomplete="off"></textarea></td>
          <td class="d-flex align-items-center gap-2">
            <button type="button" class="btn btn-danger btn-sm remove-asociada me-2" title="Eliminar fila">&ndash;</button>
            <textarea name="comentario_Asociadas[]" class="form-control input-asociadas flex-grow-1" rows="2" maxlength="80" autocomplete="off"></textarea>
          </td>
        </tr>
      `;
      $('#fila-asociadas').after(nuevaFila);
    });

    $('#tabla-materias').on('click', '.remove-asociada', function () {
      $(this).closest('tr').remove();
    });

    $('#tabla-materias').on('keydown', '.input-asociadas', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        $('#fila-asociadas .add-asociada').trigger('click');
        setTimeout(function () {
          $('#fila-asociadas').next('.asociada-extra').find('input[type="text"]').first().focus();
        }, 100);
      }
    });
  }

  // ===================================================
  // === JS PARA CONDUCTUAL E INFORMATIVO (Select2, Incisos, Autollenado Grado)
  // ===================================================

  // Aplica Select2 a campos de alumno y materia/docente si existen
  $('#id_alumno, #id_materia_docente').each(function () {
    if ($(this).length) {
      $(this).select2({
        placeholder: "-- Selecciona --",
        minimumResultsForSearch: 0,
        width: '100%',
        allowClear: true,
        dropdownParent: $(this).parent()
      });
    }
  });

  // <--- hecho por claude code: filtrar Materia/Docente según el grupo del alumno seleccionado
  const MD_POR_GRADO = window.MD_POR_GRADO || {};
  function filtrarMateriaDocentePorGrado(grado) {
    const $md = $('#id_materia_docente');
    if (!$md.length) return;
    const ops = MD_POR_GRADO[grado];
    if (!ops || !ops.length) return;   // sin datos para ese grupo → deja la lista completa
    const prev = $md.val();
    let html = '<option value="">-- Selecciona una materia --</option>';
    ops.forEach(function (o) { html += '<option value="' + o.value + '">' + o.label + '</option>'; });
    $md.html(html);
    if (ops.some(function (o) { return o.value === prev; })) { $md.val(prev); }
    $md.trigger('change');   // refresca select2
  }

  // Lógica de autollenado de grado en Conductual/Informativo (si existe campo grado)
  function setGradoUniversal() {
    let grado = '';
    let select2Data = $('#id_alumno').select2('data');
    if (select2Data && select2Data[0] && select2Data[0].element) {
      grado = $(select2Data[0].element).data('grado') || '';
    } else {
      grado = $('#id_alumno').find('option:selected').data('grado') || '';
    }
    $('#grado-display').val(grado);
    $('#id_grado').val(grado);
    filtrarMateriaDocentePorGrado(grado);
  }
  // Se ejecuta si existen campos de grado en el formulario
  if ($('#id_grado').length && $('#grado-display').length) {
    $('#id_alumno').on('select2:select change', setGradoUniversal);
    setGradoUniversal();
  }

  // ============= Select2 para incisos conductuales (si existen) ===========
  if ($('#inciso_leve').length) {
    $('#inciso_leve, #inciso_grave, #inciso_muygrave').select2({
      width: '100%',
      dropdownParent: $('.form-container').length ? $('.form-container') : $('body'),
      templateResult: function (data) {
        if (!data.id) return data.text;
        return $('<span style="white-space: pre-line;">' + data.text + '</span>');
      },
      templateSelection: function (data) {
        if (!data.id) return data.text;
        return $('<span style="white-space: pre-line;">' + data.text + '</span>');
      }
    });

    // Lógica checkboxes: activa/desactiva select y textarea
    function activarInciso(checkboxId, selectId, textareaId) {
      $(checkboxId).on('change', function () {
        $(selectId).prop('disabled', !this.checked).trigger('change');
        if (!this.checked) {
          $(selectId).val('').trigger('change');
          if (textareaId) $(textareaId).val('');
        }
      });
    }
    activarInciso('#chk_leve', '#inciso_leve', '#txt_incisos_leve');
    activarInciso('#chk_grave', '#inciso_grave', '#txt_incisos_grave');
    activarInciso('#chk_muygrave', '#inciso_muygrave', '#txt_incisos_muygrave');

    if ($('#chk_leve').is(':checked')) $('#inciso_leve').prop('disabled', false);
    if ($('#chk_grave').is(':checked')) $('#inciso_grave').prop('disabled', false);
    if ($('#chk_muygrave').is(':checked')) $('#inciso_muygrave').prop('disabled', false);

    // Mostrar seleccionados en textarea
    function actualizarTextareaIncisos(selectorSelect, selectorTextarea) {
      var incisos = [];
      $(selectorSelect + ' option:selected').each(function () {
        incisos.push($(this).text());
      });
      $(selectorTextarea).val(incisos.length > 0 ? incisos.join('\n\n') : '');
    }
    $('#inciso_leve').on('change', function () { actualizarTextareaIncisos('#inciso_leve', '#txt_incisos_leve'); });
    $('#inciso_grave').on('change', function () { actualizarTextareaIncisos('#inciso_grave', '#txt_incisos_grave'); });
    $('#inciso_muygrave').on('change', function () { actualizarTextareaIncisos('#inciso_muygrave', '#txt_incisos_muygrave'); });

    // Inicializar textareas
    actualizarTextareaIncisos('#inciso_leve', '#txt_incisos_leve');
    actualizarTextareaIncisos('#inciso_grave', '#txt_incisos_grave');
    actualizarTextareaIncisos('#inciso_muygrave', '#txt_incisos_muygrave');
  }

  // ===============================
  // Limitar scroll de Select2 y auto-hide alerts
  // ===============================
  $(document).on('select2:open', function () {
    $('.select2-results__options').css('max-height', '300px');
  });

  setTimeout(function () {
    $('.alert-success').fadeOut('slow');
  }, 4000);

});
