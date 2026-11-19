$(document).ready(function () {

    // <--- hecho por claude code (seguridad 05-nov-2026): token CSRF para el borrado (ahora solo POST; sin token el servidor ya lo rechazaba con 403): del formulario "Agregar" o de la cookie.
    function csrfToken() {
        var el = document.querySelector('[name=csrfmiddlewaretoken]');
        if (el && el.value) return el.value;
        var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : '';
    }

    // <--- hecho por claude code (seguridad 05-nov-2026): las rutas son router/get/ y router/update/ (router/edit/ no existe: el modal se quedaba cargando).
    $(document).on("click", ".editar-router", function () {
        let id = $(this).data("id");

        $("#modal-router-body").html(`
            <div class="text-center py-5">
                <div class="spinner-border text-primary"></div>
                <p class="mt-2">Cargando datos...</p>
            </div>
        `);

        $("#modalEditarRouter").modal("show");

        $.get(`/inventario/router/get/${id}/`, function (html) {
            $("#modal-router-body").html(html);
        }).fail(() => Swal.fire("Error", "No se pudo cargar el formulario.", "error"));
    });

    $(document).on("submit", "#form-edit-router", function (e) {
        e.preventDefault();

        let id = $("#router-id").val();

        $.post(`/inventario/router/update/${id}/`, $(this).serialize(), function (resp) {
            resp.ok
                ? Swal.fire("Actualizado", "Router actualizado.", "success").then(() => location.reload())
                : Swal.fire("Error", "Revisa los datos ingresados.", "error");
        }).fail(() => Swal.fire("Error", "No se pudo guardar.", "error"));
    });

    $(document).on("click", ".eliminar-router", function () {
        let id = $(this).data("id");

        Swal.fire({
            title: "¿Eliminar router?",
            icon: "warning",
            showCancelButton: true
        }).then((r) => {
            if (r.isConfirmed) {
                $.post(`/inventario/router/delete/${id}/`, { csrfmiddlewaretoken: csrfToken() }, function () {
                    Swal.fire("Eliminado", "Registro eliminado.", "success")
                        .then(() => location.reload());
                }).fail((xhr) => {
                    Swal.fire({ title: "Error", text: (xhr.responseJSON && xhr.responseJSON.error) || "No se pudo eliminar el router.", icon: "error" });
                });
            }
        });
    });

});
