/* enfermeria/js/atencion_form.js */
/* <--- hecho por claude code (seguridad 05-nov-2026): el correo es un select con los correos REGISTRADOS del alumno (data-emails de cada opción) y "Eliminar" hace POST con CSRF a data-url (antes GET ?delete=<id>); todo va dentro del ready de jQuery, sin identificadores globales. */
$(function () {
  'use strict';

  var $alumno   = $('#student-select');
  var selCorreo = document.getElementById('email-padre');
  var aviso     = document.getElementById('email-aviso');

  $alumno.select2({ placeholder: '-- Selecciona un alumno --', width: '100%' });

  function correosDe(opt) {
    return String((opt && opt.getAttribute('data-emails')) || '').split(/\s+/).filter(Boolean);
  }

  // Llena el select de correo con los correos registrados del alumno elegido.
  // proponer = true deja elegido el primero (al elegir alumno); false deja "No enviar" (al abrir para editar).
  function llenarCorreos(opt, proponer) {
    if (!selCorreo) return;
    var hayAlumno = !!(opt && opt.value);
    var correos   = hayAlumno ? correosDe(opt) : [];
    while (selCorreo.options.length) selCorreo.remove(0);
    var vacio = !hayAlumno ? '— Elige primero al alumno —'
              : (correos.length ? 'No enviar por correo' : 'Sin correo registrado (no se enviará)');
    selCorreo.add(new Option(vacio, ''));
    correos.forEach(function (c) { selCorreo.add(new Option(c, c)); });
    selCorreo.value = (proponer && correos.length) ? correos[0] : '';
    if (aviso) {
      var sinCorreo = hayAlumno && !correos.length;
      aviso.textContent = sinCorreo
        ? 'Este alumno no tiene correo registrado en el sistema académico: la ficha se guardará sin enviarse.'
        : '';
      aviso.style.color = sinCorreo ? '#c2410c' : '';
    }
  }

  $alumno.on('change', function () {
    var opt   = this.options[this.selectedIndex];
    var grado = (opt && opt.value) ? (opt.getAttribute('data-grado') || '') : '';
    $('#grade-display').val(grado);
    $('#student_grade').val(grado);
    llenarCorreos(opt, true);
  });

  // Al abrir una atención para editar el alumno ya viene elegido: se cargan sus correos sin proponer el envío.
  var sel0 = $alumno.get(0);
  if (sel0 && sel0.selectedIndex > 0) llenarCorreos(sel0.options[sel0.selectedIndex], false);

  $('#atenciones-table').DataTable({
    order: [[2, 'desc']],
    pageLength: 15,
    lengthChange: false,
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
  });

  // Eliminar: confirmación + POST con el token CSRF del formulario de la página.
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest ? ev.target.closest('.btn-eliminar-atencion') : null;
    if (!btn) return;
    ev.preventDefault();
    var url   = btn.getAttribute('data-url');
    var token = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (!url || !token) return;
    Swal.fire({
      title: '¿Eliminar esta atención?', icon: 'warning',
      showCancelButton: true, confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar'
    }).then(function (result) {
      if (!result.isConfirmed) return;
      var f = document.createElement('form');
      f.method = 'post';
      f.action = url;
      var i = document.createElement('input');
      i.type = 'hidden';
      i.name = 'csrfmiddlewaretoken';
      i.value = token.value;
      f.appendChild(i);
      document.body.appendChild(f);
      f.submit();
    });
  });
});
