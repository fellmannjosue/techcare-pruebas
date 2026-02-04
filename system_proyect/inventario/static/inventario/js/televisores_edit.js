$(document).ready(function () {

    // ================================
    // ABRIR MODAL EDITAR TELEVISOR
    // ================================
    $(document).on("click", ".editar-btn", function () {

        let id = $(this).data("id");

        $("#modal-televisor-body").html(`
            <div class="text-center py-5">
                <div class="spinner-border text-primary"></div>
                <p class="mt-2">Cargando datos...</p>
            </div>
        `);

        $("#modalEditarTelevisor").modal("show");

        $.get(`/inventario/televisor/get/${id}/`, function (html) {
            $("#modal-televisor-body").html(html);
        }).fail(() => {
            Swal.fire("Error", "No se pudo cargar el formulario.", "error");
        });

    });


    // ================================
    // GUARDAR CAMBIOS
    // ================================
    $(document).on("submit", "#form-edit-televisor", function (e) {

        e.preventDefault();

        let id = $("#televisor-id").val();
        let formData = $(this).serialize();

        $.post(`/inventario/televisor/update/${id}/`, formData)
            .done((resp) => {
                if (resp.ok) {
                    Swal.fire("Actualizado", "Cambios guardados correctamente.", "success")
                        .then(() => location.reload());
                } else {
                    Swal.fire("Error", "Verifica los datos ingresados.", "error");
                }
            })
            .fail(() => Swal.fire("Error", "Error al guardar cambios.", "error"));

    });


    // ================================
    // ELIMINAR TELEVISOR
    // ================================
    $(document).on("click", ".eliminar-btn", function () {

        let id = $(this).data("id");

        Swal.fire({
            title: "¿Eliminar televisor?",
            text: "Esta acción no se puede deshacer.",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Eliminar",
            cancelButtonText: "Cancelar"
        }).then((res) => {

            if (res.isConfirmed) {
                $.post(`/inventario/televisor/delete/${id}/`, function (resp) {
                    if (resp.ok) {
                        Swal.fire("Eliminado", "Televisor eliminado correctamente.", "success")
                            .then(() => location.reload());
                    }
                }).fail(() => {
                    Swal.fire("Error", "No se pudo eliminar el registro.", "error");
                });
            }

        });

    });

});
