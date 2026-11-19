/* <--- hecho por claude code (06-nov-2026): Reporte Informativo (diseño B: tarjeta del alumno) y Reporte Conductual
   (diseño C: semáforo + vista previa). Solo presentación: el formulario envía los mismos campos de siempre. */
(function () {
  if (!window.jQuery) return;
  var $ = window.jQuery;
  var COLS = ['#2563eb', '#7c3aed', '#0ca678', '#f76707', '#d6336c', '#0d9488', '#4263eb'];
  var EST = { enviado: 'Enviado', revisado: 'Revisado', aprobado: 'Aprobado', revisando: 'Enviado' };
  function esc(x) { return String(x == null ? '' : x).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function txtSel(id) { var o = $('#' + id).find('option:selected'); return o.val() ? o.text().trim() : ''; }
  function comentario() {
    var ed = document.querySelector('.tc-rico-ed');
    var t = ed ? ed.innerText : ($('#id_comentario').val() || '');
    return (t || '').trim();
  }
  function iniciales(n) { return String(n || '?').split(/[\s,]+/).filter(Boolean).slice(0, 2).map(function (p) { return p[0]; }).join('').toUpperCase(); }
  function fechaTxt() { var v = $('#id_fecha').val(); if (!v) return '—'; var p = v.split('-'); return p[2] + '/' + p[1] + '/' + p[0]; }
  // doble clic = un solo envío
  $('#formReporteInformativo, #formReporteConductual').on('submit', function () {
    var $f = $(this); if ($f.data('enviado')) return false; $f.data('enviado', true);
    $f.find('button[type="submit"]').prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span>Guardando…');
  });

  /* ── Informativo · tarjeta del alumno ── */
  if ($('#formReporteInformativo').length) {
    var REC = {}; try { REC = JSON.parse(document.getElementById('fr-recientes').textContent) || {}; } catch (e) {}
    function pintarAlumno() {
      var id = $('#id_alumno').val(), nom = txtSel('id_alumno');
      $('#fr-alum-card').prop('hidden', !id); $('#fr-alum-vacio').prop('hidden', !!id);
      if (id) { $('#fr-alum-nom').text(nom); $('#fr-av').text(iniciales(nom)).css('background', COLS[(parseInt(id, 10) || 0) % COLS.length]); }
      var r = id ? (REC[id] || []) : [];
      $('#fr-rec').prop('hidden', !id);
      $('#fr-rec-lista').html(r.length ? r.map(function (x) {
        return '<div class="fr-rec__it"><span class="fr-t fr-t--' + x.t + '">' + (x.t === 'con' ? 'Conductual' : 'Informativo') + '</span><span class="fr-rec__f">' + esc(x.f) + '</span><span class="fr-rec__m">' + esc(x.m) + '</span><span class="fr-e fr-e--' + esc(x.e) + '">' + (EST[x.e] || esc(x.e)) + '</span></div>';
      }).join('') : '<div class="text-secondary small">Sin reportes en los últimos meses.</div>');
      estado();
    }
    function estado() {
      var falta = [];
      if (!$('#id_alumno').val()) falta.push('alumno'); if (!$('#id_materia_docente').val()) falta.push('materia'); if (!comentario()) falta.push('comentario');
      $('#fr-estado').toggleClass('ok', !falta.length).html(falta.length ? '<i class="ti ti-circle-dashed"></i> Falta: ' + falta.join(', ') : '<i class="ti ti-circle-check"></i> Listo para guardar');
    }
    $('#id_alumno').on('select2:select select2:clear change', pintarAlumno);
    $('#id_materia_docente').on('select2:select change', estado);
    document.addEventListener('input', estado);
    setTimeout(pintarAlumno, 0);
  }

  /* ── Conductual · semáforo + vista previa ── */
  if ($('#formReporteConductual').length) {
    var SEV = { muygrave: 'Muy grave', grave: 'Grave', leve: 'Leve' };
    function activo(s) { return $('#chk_' + s).prop('checked'); }
    function pintarSev() {
      var alguna = false;
      Object.keys(SEV).forEach(function (s) {
        var on = activo(s); alguna = alguna || on;
        $('.fc-luz[data-sev="' + s + '"]').toggleClass('on', on).attr('aria-pressed', on ? 'true' : 'false');
        $('.fc-inc[data-sev="' + s + '"]').prop('hidden', !on);
      });
      $('#fc-sev-vacio').prop('hidden', alguna);
      previa();
    }
    function previa() {
      $('#pv-fecha').text(fechaTxt());
      $('#pv-alumno').text(txtSel('id_alumno') || 'Sin alumno');
      var g = $('#grado-display').val(); $('#pv-grado').text(g ? ' · ' + g : '');
      $('#pv-materia').text(txtSel('id_materia_docente') || 'Sin materia');
      var h = '';
      Object.keys(SEV).forEach(function (s) {
        if (!activo(s)) return;
        var incs = $('.fc-inc-chk[data-sev="' + s + '"]:checked').map(function () { return $(this).next('span').text().trim(); }).get();
        h += '<div class="fc-pv-sev fc-pv-sev--' + s + '"><b>' + SEV[s] + '</b>' + (incs.length ? '<ul>' + incs.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' : '<div class="text-secondary small">Sin incisos marcados</div>') + '</div>';
      });
      $('#pv-sev').html(h || '<span class="text-secondary">Sin gravedad elegida</span>');
      var c = comentario(); $('#pv-com').html(c ? esc(c) : '<span class="text-secondary">Sin comentario</span>');
    }
    $(document).on('click', '.fc-luz', function () {
      var s = this.dataset.sev, $c = $('#chk_' + s), on = !$c.prop('checked');
      $c.prop('checked', on);
      if (!on) $('.fc-inc-chk[data-sev="' + s + '"]').prop('checked', false);   // apagar la luz limpia sus incisos
      pintarSev();
    });
    $(document).on('change', '.fc-inc-chk', previa);
    $('#id_alumno, #id_materia_docente').on('select2:select select2:clear change', function () { setTimeout(previa, 0); });
    $('#id_fecha').on('change', previa);
    document.addEventListener('input', previa);
    // no se puede guardar una gravedad encendida sin incisos
    $('#formReporteConductual').on('submit', function (e) {
      var mal = Object.keys(SEV).filter(function (s) { return activo(s) && !$('.fc-inc-chk[data-sev="' + s + '"]:checked').length; });
      if (mal.length) {
        e.preventDefault(); e.stopImmediatePropagation();
        $(this).data('enviado', false).find('button[type="submit"]').prop('disabled', false).html('<i class="ti ti-device-floppy me-1"></i> Guardar Reporte');
        $('#fc-sev-vacio').prop('hidden', false).html('<i class="ti ti-alert-triangle"></i> Marca al menos un inciso en: ' + mal.map(function (s) { return SEV[s]; }).join(', ') + '.');
        return false;
      }
    });
    setTimeout(pintarSev, 0);
  }
})();
