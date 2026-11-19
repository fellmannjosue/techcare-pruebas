$(document).ready(function () {

    // <--- hecho por claude code (seguridad 05-nov-2026): token CSRF para el borrado (ahora solo POST): del input del formulario "Agregar" de la página o de la cookie.
    function csrfToken() {
        var el = document.querySelector('[name=csrfmiddlewaretoken]');
        if (el && el.value) return el.value;
        var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : '';
    }

    // ================================
    // ABRIR MODAL EDITAR DATASHOW
    // ================================
    // <--- hecho por claude code (seguridad 05-nov-2026): la plantilla usa .editar-datashow / .eliminar-datashow y el modal #modalEditarDatashow (aquí se escuchaba .editar-btn / .eliminar-btn y #modalEditarDataShow: los botones no hacían nada).
    $(document).on("click", ".editar-datashow", function () {

        let id = $(this).data("id");

        $("#modal-datashow-body").html(`
            <div class="text-center py-5">
                <div class="spinner-border text-primary"></div>
                <p class="mt-2">Cargando datos...</p>
            </div>
        `);

        $("#modalEditarDatashow").modal("show");

        $.get(`/inventario/datashow/get/${id}/`, function (html) {
            $("#modal-datashow-body").html(html);
        }).fail(() => {
            Swal.fire("Error", "No se pudo cargar el formulario.", "error");
        });

    });


    // ================================
    // GUARDAR CAMBIOS
    // ================================
    $(document).on("submit", "#form-edit-datashow", function (e) {

        e.preventDefault();

        let id = $("#datashow-id").val();
        let formData = $(this).serialize();

        $.post(`/inventario/datashow/update/${id}/`, formData)
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
    // ELIMINAR DATASHOW
    // ================================
    $(document).on("click", ".eliminar-datashow", function () {

        let id = $(this).data("id");

        Swal.fire({
            title: "¿Eliminar DataShow?",
            text: "No podrás recuperar este registro.",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Eliminar",
            cancelButtonText: "Cancelar"
        }).then((res) => {

            if (res.isConfirmed) {
                $.post(`/inventario/datashow/delete/${id}/`, { csrfmiddlewaretoken: csrfToken() }, function (resp) {
                    if (resp.ok) {
                        Swal.fire("Eliminado", "Registro eliminado correctamente.", "success")
                            .then(() => location.reload());
                    }
                }).fail((xhr) => {
                    // 409 = tiene reservas de DataShow (no se puede borrar)
                    Swal.fire({ title: "Error", text: (xhr.responseJSON && xhr.responseJSON.error) || "No se pudo eliminar.", icon: "error" });
                });
            }

        });

    });

});
