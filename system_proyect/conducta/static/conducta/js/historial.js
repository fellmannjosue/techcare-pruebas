document.addEventListener('DOMContentLoaded', function() {
    // MODAL DE DETALLE DE TICKET AL CLIC EN ID
    document.querySelectorAll('.link-ticket').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            let id = this.dataset.ticketId;
            let nombre = this.dataset.name;
            let email = this.dataset.email;
            let descripcion = this.dataset.description;
            let status = this.dataset.status;
            let fecha = this.dataset.fecha;
            let adjunto = this.dataset.adjunto;

            Swal.fire({
                title: `<span style="color:#1967d2; font-weight:bold;">${id}</span>`,
                html: `
                  <div style="text-align:left; font-size:16px;">
                    <b>Nombre:</b> ${nombre}<br>
                    <b>Correo:</b> ${email}<br>
                    <b>Fecha:</b> ${fecha}<br>
                    <b>Status:</b> <span class="badge bg-info text-dark">${status}</span><br>
                    <b>Adjunto:</b> ${
                      adjunto
                        ? `<a href="${adjunto}" target="_blank" class="btn btn-sm btn-outline-secondary">Ver archivo</a>`
                        : '<span class="text-muted">No</span>'
                    }<br>
                    <b>Descripción:</b><br>
                    <textarea class="form-control" rows="5" readonly style="resize:none;">${descripcion}</textarea>
                  </div>
                `,
                showCloseButton: true,
                showConfirmButton: false,
                width: 440,
                customClass: {
                    popup: 'swal2-border-radius'
                }
            });
        });
    });

    // MODAL DE BIENVENIDA/CONFIRMACIÓN AL CLIC EN "CHAT"
    document.querySelectorAll('.btn-chat').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            let ticketId = btn.dataset.ticketId;
            let area = btn.dataset.area; // <-- IMPORTANTE: usa data-area
            let nombre = btn.dataset.nombre || 'Usuario';

            Swal.fire({
                title: '¿Deseas iniciar el chat con soporte técnico?',
                html: `<b>${nombre}</b>, te estás comunicando con el soporte técnico.<br>Por favor, espera a ser atendido.`,
                icon: 'info',
                showCancelButton: true,
                confirmButtonText: 'Sí, iniciar chat',
                cancelButtonText: 'Cancelar'
            }).then((result) => {
                if (result.isConfirmed) {
                    // Redirige con el área correspondiente
                    window.location.href = `/tickets/ticket/${ticketId}/comentarios/?area=${area}`;
                } else {
                    Swal.fire({
                        title: 'Chat no iniciado',
                        text: 'Pronto soporte técnico se comunicará contigo. Este pendiente de su correo.',
                        icon: 'warning',
                        confirmButtonText: 'OK'
                    });
                }
            });
        });
    });

    // <--- hecho por claude code: buscador de alumno en Progress ("¿ya tiene reporte?")
    (function () {
        var input = document.getElementById('buscar-progress');
        if (!input) return;
        var info  = document.getElementById('buscar-progress-info');
        var clear = document.getElementById('buscar-progress-clear');
        var cont  = document.getElementById('accProgGrado');
        if (!cont) return;

        // quita acentos y pasa a minúsculas para comparar sin importar tildes
        function norm(s) {
            return (s || '').toString().toLowerCase()
                .normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
        }

        var items = Array.prototype.slice.call(cont.querySelectorAll('.accordion-item'));

        function filtrar() {
            var q = norm(input.value);
            var total = 0;
            items.forEach(function (item) {
                var filas = item.querySelectorAll('tbody tr[data-alumno]');
                var visibles = 0;
                filas.forEach(function (tr) {
                    var match = !q || norm(tr.getAttribute('data-alumno')).indexOf(q) !== -1;
                    tr.style.display = match ? '' : 'none';
                    if (match) visibles++;
                });
                total += visibles;
                // ocultar el grado completo si no tiene coincidencias
                item.style.display = (q && visibles === 0) ? 'none' : '';
                // al buscar, abrir los acordeones con coincidencias
                var col = item.querySelector('.accordion-collapse');
                if (col && window.bootstrap && bootstrap.Collapse) {
                    var inst = bootstrap.Collapse.getOrCreateInstance(col, { toggle: false });
                    if (q && visibles > 0) inst.show(); else if (q) inst.hide();
                }
            });

            if (!q) { info.className = 'small mt-2 d-none'; info.textContent = ''; return; }
            info.classList.remove('d-none');
            if (total > 0) {
                info.className = 'small mt-2 text-success';
                info.innerHTML = '<i class="ti ti-check me-1"></i>' + total +
                    ' progress report(s) encontrado(s) para «' + input.value.trim() + '».';
            } else {
                info.className = 'small mt-2 text-danger';
                info.innerHTML = '<i class="ti ti-alert-circle me-1"></i>No existe progress report para «' +
                    input.value.trim() + '». Aún puedes crearlo.';
            }
        }

        input.addEventListener('input', filtrar);
        if (clear) clear.addEventListener('click', function () { input.value = ''; filtrar(); input.focus(); });
    })();

    // <--- hecho por claude code: abrir la pestaña indicada en la URL (ej. #agendas),
    // para que "Volver a Historial de Reportes" desde Editar Agenda caiga en Agendas.
    var hash = window.location.hash;
    if (hash && hash.length > 1) {
        var trigger = document.querySelector('#reportTabs a[href="' + hash + '"]');
        if (trigger && window.bootstrap && bootstrap.Tab) {
            bootstrap.Tab.getOrCreateInstance(trigger).show();
        }
    }
});
