// static/conducta/js/coordinador.js

$(function() {
    // Inicializar DataTables — orden por FECHA descendente (último registrado primero).
    // Columnas (todas): chk(0), #(1), Alumno(2), Tipo(3), Fecha(4), Grado(5), ...
    const lang = { "url": "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json" };
    const noSort = { orderable: false };
    if ($('#tabla-academicos').length) {
        $('#tabla-academicos').DataTable({
            language: lang, order: [[4, 'desc']], pageLength: 100,
            columnDefs: [{ targets: [-1, -2], orderable: false }]
        });
    }
    if ($('#tabla-conductuales').length) {
        $('#tabla-conductuales').DataTable({
            language: lang, order: [[4, 'desc']], pageLength: 100,
            columnDefs: [{ targets: [-1, -2], orderable: false }]
        });
    }
    if ($('#tabla-progress').length) {
        $('#tabla-progress').DataTable({
            language: lang, order: [[4, 'desc']], pageLength: 100,
            columnDefs: [{ targets: [-1, -2], orderable: false }]
        });
    }

    // Acción para mostrar historial del alumno en modal
    // <--- hecho por claude code: usando Bootstrap 5 API (no jQuery .modal())
    $(document).on('click', '.btn-historial', function() {
        let alumno_id = $(this).data('alumno');
        $('#historial-content').html('<div class="text-center text-muted py-3">Cargando historial...</div>');
        const modalEl = document.getElementById('modalHistorial');
        new bootstrap.Modal(modalEl).show();
        $.get('/conducta/coordinador/historial/alumno/' + alumno_id + '/', function(data) {
            $('#historial-content').html(data);
        }).fail(function() {
            $('#historial-content').html('<div class="alert alert-danger">Error al cargar historial.</div>');
        });
    });

    // Mostrar el modal de advertencia si el usuario intenta descargar PDF sin 3 reportes
    $(document).on('click', '.btn-pdf-disabled', function(e) {
        e.preventDefault();
        new bootstrap.Modal(document.getElementById('modalTresFaltas')).show();
    });

    // <--- hecho por claude code: click en botón lápiz O en cualquier celda de la fila.
    // Usa jQuery delegation (compatible con DataTables) para abrir modal de edición inline.
    // Llama a window._abrirEditar que se define en dashboard_coordinador.js.
    $(document).on('click', '.btn-editar-inline', function(e) {
        e.stopPropagation();
        var pk   = $(this).data('pk');
        var tipo = $(this).data('tipo');
        var area = $(this).data('area') || 'bilingue';
        if (typeof window._abrirEditar === 'function') window._abrirEditar(pk, tipo, area);
    });
    $(document).on('click', '#tabla-academicos tbody tr, #tabla-conductuales tbody tr, #tabla-progress tbody tr', function(e) {
        if ($(e.target).closest('button, a, select, input, textarea, .ev-thumb-wrap').length) return;
        var $btn = $(this).find('.btn-editar-inline').first();
        if (!$btn.length) return;
        if (typeof window._abrirEditar === 'function') {
            window._abrirEditar($btn.data('pk'), $btn.data('tipo'), $btn.data('area') || 'bilingue');
        }
    });

    // <--- hecho por claude code: abrir modal de evidencia con Bootstrap 5 API.
    // $().modal('show') es Bootstrap 4 — en Bootstrap 5 se usa new bootstrap.Modal().
    // Bloquea la apertura si el reporte ya tiene 2 evidencias (máximo permitido).
    $(document).on('click', '.btn-evidencia', function() {
        const numEvidencias = parseInt($(this).data('num-evidencias')) || 0;
        if (numEvidencias >= 2) {
            alert('Este reporte ya tiene el máximo de 2 evidencias permitidas.');
            return;
        }
        const tipo = $(this).data('tipo');
        const id   = $(this).data('id');
        $('#ev-tipo').val(tipo);
        $('#ev-reporte-id').val(id);
        // Limpiar preview de imagen anterior
        $('#ev-preview').addClass('d-none').attr('src', '#');
        $('#ev-imagen').val('');
        const modalEl = document.getElementById('modalEvidencia');
        new bootstrap.Modal(modalEl).show();
    });

    // <--- hecho por claude code: preview en tiempo real de la imagen seleccionada.
    // Usa FileReader para mostrar la imagen antes de enviar el formulario.
    $(document).on('change', '#ev-imagen', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                $('#ev-preview').attr('src', e.target.result).removeClass('d-none');
            };
            reader.readAsDataURL(file);
        } else {
            $('#ev-preview').addClass('d-none').attr('src', '#');
        }
    });
});
