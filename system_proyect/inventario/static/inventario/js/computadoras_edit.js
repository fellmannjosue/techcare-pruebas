$(document).ready(function () {

    // ================================
    // ABRIR MODAL EDITAR COMPUTADORA
    // ================================
    $(document).on("click", ".editar-computadora", function () {
        let id = $(this).data("id");

        $("#modal-computadora-body").html(`
            <div class="text-center py-5">
                <div class="spinner-border text-primary"></div>
                <p class="mt-2">Cargando datos...</p>
            </div>
        `);

        $("#modalEditarComputadora").modal("show");

        $.get(`/inventario/computadora/get/${id}/`, function (html) {
            $("#modal-computadora-body").html(html);
        }).fail(() => {
            Swal.fire("Error", "No se pudo cargar el formulario.", "error");
        });
    });


    // ================================
    // GUARDAR EDICIÓN
    // ================================
    $(document).on("submit", "#form-edit-computadora", function (e) {
        e.preventDefault();

        let id = $("#computadora-id").val();
        let formData = $(this).serialize();

        $.post(`/inventario/computadora/update/${id}/`, formData)
            .done((resp) => {
                if (resp.ok) {
                    Swal.fire("Actualizado", "Los cambios fueron guardados.", "success")
                        .then(() => location.reload());
                } else {
                    Swal.fire("Error", "Verifica los campos ingresados.", "error");
                }
            })
            .fail(() => Swal.fire("Error", "No se pudo guardar la información.", "error"));
    });


    // ================================
    // ELIMINAR COMPUTADORA
    // ================================
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
                // <--- hecho por claude code (seguridad 05-nov-2026): el borrado ahora es solo POST con token CSRF (este archivo no lo carga ninguna plantilla: la página usa inventario_computadoras.js)
                var _tok = ($('[name=csrfmiddlewaretoken]').first().val()) || ((document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/) || [])[1] || '');
                $.post(`/inventario/computadora/delete/${id}/`, { csrfmiddlewaretoken: _tok }, function (resp) {
                    if (resp.ok) {
                        Swal.fire("Eliminado", "Registro eliminado correctamente.", "success")
                            .then(() => location.reload());
                    }
                }).fail(() => {
                    Swal.fire("Error", "No se pudo eliminar el registro.", "error");
                });
            }

        });

    });

});
