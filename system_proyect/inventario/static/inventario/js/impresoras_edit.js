$(document).ready(function () {

    // <--- hecho por claude code (seguridad 05-nov-2026): token CSRF para el borrado (ahora solo POST; sin token el servidor ya lo rechazaba con 403): del formulario "Agregar" o de la cookie.
    function csrfToken() {
        var el = document.querySelector('[name=csrfmiddlewaretoken]');
        if (el && el.value) return el.value;
        var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : '';
    }

    // ABRIR MODAL
    $(document).on("click", ".editar-impresora", function () {
        let id = $(this).data("id");

        $("#modal-impresora-body").html(`
            <div class="text-center py-5">
                <div class="spinner-border text-primary"></div>
                <p class="mt-2">Cargando datos...</p>
            </div>
        `);

        $("#modalEditarImpresora").modal("show");

        $.get(`/inventario/impresora/get/${id}/`, function (html) {
            $("#modal-impresora-body").html(html);
        });
    });

    // GUARDAR CAMBIOS
    $(document).on("submit", "#form-edit-impresora", function (e) {
        e.preventDefault();

        let id = $("#impresora-id").val();
        let data = $(this).serialize();

        $.post(`/inventario/impresora/update/${id}/`, data, function (resp) {

            if (resp.ok) {
                Swal.fire("Actualizado", "Cambios guardados correctamente.", "success")
                    .then(() => location.reload());
            } else {
                Swal.fire("Error", "Corrige los campos marcados.", "error");
            }

        });

    });

    // ELIMINAR
    $(document).on("click", ".eliminar-impresora", function () {
        let id = $(this).data("id");

        Swal.fire({
            title: "¿Eliminar impresora?",
            text: "Esta acción no se puede deshacer.",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Eliminar",
            cancelButtonText: "Cancelar"
        }).then((r) => {

            if (r.isConfirmed) {
                $.post(`/inventario/impresora/delete/${id}/`, { csrfmiddlewaretoken: csrfToken() }, function () {

                    Swal.fire("Eliminada", "La impresora fue eliminada.", "success")
                        .then(() => location.reload());
                }).fail((xhr) => {
                    Swal.fire({ title: "Error", text: (xhr.responseJSON && xhr.responseJSON.error) || "No se pudo eliminar la impresora.", icon: "error" });
                });
            }

        });

    });

});
