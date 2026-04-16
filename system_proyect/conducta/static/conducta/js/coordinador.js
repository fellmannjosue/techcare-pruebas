// static/conducta/js/coordinador.js

$(function() {
    // Inicializar DataTable en la tabla principal
    if ($('#tabla-coordinador').length) {
        $('#tabla-coordinador').DataTable({
            "order": [[2, "desc"]],
            "language": {
                "url": "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json"
            }
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
        $('#modalTresFaltas').modal('show');
    });

    // <--- hecho por claude code: abrir modal de evidencia con Bootstrap 5 API.
    // $().modal('show') es Bootstrap 4 — en Bootstrap 5 se usa new bootstrap.Modal().
    // Esto era la causa de que el botón 📷 no hacía nada.
    $(document).on('click', '.btn-evidencia', function() {
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
