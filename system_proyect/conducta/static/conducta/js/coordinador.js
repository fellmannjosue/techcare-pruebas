// static/conducta/js/coordinador.js

$(function() {
    // Inicializar DataTables — orden por FECHA descendente (último registrado primero).
    // Columnas (todas): chk(0), #(1), Alumno(2), Tipo(3), Fecha(4), Grado(5), ...
    const lang = { "url": "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json" };

    // <--- hecho por claude code: ACORDEÓN por alumno (DataTables RowGroup) en Informativo/Conductual.
    // Conserva buscador, orden, selección múltiple, evidencias y editar. Cada alumno es un
    // encabezado plegable; se puede colapsar/expandir haciendo clic en él.
    var _grpColapsados = {};   // { tablaId: { nombreAlumno: true } }

    // <--- hecho por claude code: claves de orden (RowGroup lee texto plano; el orden va por render)
    var _GRADO_ORD = { primero:1, segundo:2, tercero:3, cuarto:4, quinto:5, sexto:6,
                       septimo:7, octavo:8, noveno:9, decimo:10 };
    function _fechaSort(d) { var p = ('' + d).split('/'); return p.length === 3 ? p[2] + p[1] + p[0] : ('' + d); }
    function _gradoSort(d) {
        var s = ('' + d).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        var m = s.match(/([a-z]+)\s*(\d+)?/);
        if (!m) return '99-99';
        var g = _GRADO_ORD[m[1]] || 90;
        return ('0' + g).slice(-2) + '-' + ('0' + (m[2] ? parseInt(m[2], 10) : 0)).slice(-2);
    }

    // groupCol: 4 = por FECHA (recientes primero) · 5 = por GRADO (1..9) · null = sin agrupar
    function _initTablaReportes(id, groupCol) {
        var $t = $('#' + id);
        if (!$t.length) return;
        var nCols = $t.find('thead th').length;
        var opts = {
            language: lang, pageLength: 100,
            columnDefs: [
                { targets: [-1, -2], orderable: false },
                { targets: 4, render: function (d, t) { return (t === 'sort' || t === 'type') ? _fechaSort(d) : d; } },
                { targets: 5, render: function (d, t) { return (t === 'sort' || t === 'type') ? _gradoSort(d) : d; } }
            ]
        };
        if (groupCol != null) {
            _grpColapsados[id] = {};
            var dir = (groupCol === 4) ? 'desc' : 'asc';        // fecha: recientes primero
            opts.orderFixed = { pre: [[groupCol, dir]] };        // grupo estable
            opts.order = (groupCol === 4) ? [[2, 'asc']] : [[4, 'desc']];  // dentro del grupo
            opts.rowGroup = {
                dataSrc: groupCol,
                startRender: function (rows, group) {
                    var colapsado = !!_grpColapsados[id][group];
                    rows.nodes().each(function (r) { r.style.display = colapsado ? 'none' : ''; });
                    var n = rows.count();
                    return $('<tr class="grupo-alumno' + (colapsado ? ' colapsado' : '') + '"/>')
                        .attr('data-group', group)
                        .append(
                            '<td colspan="' + nCols + '">' +
                            '<i class="ti ti-chevron-' + (colapsado ? 'right' : 'down') + ' ga-chev"></i>' +
                            '<span class="ga-nombre">' + group + '</span>' +
                            '<span class="badge bg-blue-lt text-blue ms-2">' + n + ' reporte' + (n === 1 ? '' : 's') + '</span>' +
                            '</td>'
                        );
                }
            };
        } else {
            opts.order = [[4, 'desc']];
        }
        var table = $t.DataTable(opts);
        if (groupCol != null) {
            $t.find('tbody').on('click', 'tr.grupo-alumno', function () {
                var g = $(this).data('group');
                _grpColapsados[id][g] = !_grpColapsados[id][g];
                table.draw(false);
            });
        }
        return table;
    }

    _initTablaReportes('tabla-academicos', 4);    // <--- Informativo/Académico → por FECHA
    _initTablaReportes('tabla-conductuales', 4);  // <--- Conductual → por FECHA
    _initTablaReportes('tabla-progress', 5);      // <--- Progress → por GRADO

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

    // <--- hecho por claude code: WhatsApp al padre/madre con mensaje EDITABLE + enlace al reporte.
    function _waActualizarLink() {
        var num = $('#wa-numero').val() || '';
        var txt = encodeURIComponent($('#wa-mensaje').val() || '');
        $('#wa-enviar').attr('href', num ? ('https://wa.me/' + num + '?text=' + txt) : '#');
    }
    $(document).on('input', '#wa-mensaje', _waActualizarLink);
    $(document).on('change', '#wa-numero', _waActualizarLink);

    $(document).on('click', '.btn-whatsapp', function (e) {
        e.stopPropagation();
        var b = $(this);
        var alumnoId = b.attr('data-alumno-id');
        var alumno   = b.attr('data-alumno')   || '';
        var grado    = b.attr('data-grado')    || '';
        var tipo     = b.attr('data-tipo-txt') || 'reporte';
        var fecha    = b.attr('data-fecha')    || '';
        var materia  = b.attr('data-materia')  || '';
        var reporteUrl = b.attr('data-reporte-url') || '';

        // Mensaje base editable — depende del reporte
        var msg = 'Saludos, le escribimos de la Asociación Nuevo Amanecer sobre ' + alumno;
        if (grado) msg += ' (' + grado + ')';
        msg += '. Referente al reporte ' + tipo + ' del ' + fecha;
        if (materia) msg += ' — ' + materia;
        msg += '. ';
        if (reporteUrl) msg += '\n\nVer reporte: ' + reporteUrl;

        $('#wa-alumno').text(alumno);
        $('#wa-mensaje').val(msg);
        $('#wa-numero').empty();
        $('#wa-loading').removeClass('d-none');
        $('#wa-body').addClass('d-none');
        $('#wa-sin-numero').addClass('d-none');
        $('#wa-enviar').attr('href', '#');
        new bootstrap.Modal(document.getElementById('modalWhatsApp')).show();

        $.get('/conducta/telefonos-alumno/' + encodeURIComponent(alumnoId) + '/', function (data) {
            $('#wa-loading').addClass('d-none');
            if (data && data.ok && data.numeros && data.numeros.length) {
                data.numeros.forEach(function (n) {
                    var etq = n.label ? (' — ' + n.label) : '';
                    $('#wa-numero').append('<option value="' + n.e164 + '">' + n.num + etq + '</option>');
                });
                $('#wa-body').removeClass('d-none');
                _waActualizarLink();
            } else {
                $('#wa-sin-numero').removeClass('d-none');
            }
        }).fail(function () {
            $('#wa-loading').addClass('d-none');
            $('#wa-sin-numero').removeClass('d-none')
                .html('<i class="ti ti-alert-triangle me-1"></i>No se pudo consultar el número. Intenta de nuevo.');
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
