/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
window._MONITOR_PAGE = {
  labsUsados:      JSON.parse(document.getElementById('edit-labs-data').textContent),
  asignadosUsados: JSON.parse(document.getElementById('edit-asig-data').textContent)
};


/* ─────────────────────────────────────────────────────────────────────
   <--- hecho por claude code: este bloque se había PERDIDO al sacar el JS
   del HTML (commit c8d65db): solo quedó la configuración de arriba y la
   página se quedó sin ninguna lógica. Recuperado de c8d65db~1.
   ───────────────────────────────────────────────────────────────────── */

(function () {
    // Usar el form como raíz para evitar conflicto con IDs del formulario principal de la página
    var form = document.getElementById('form-edit-monitor');
    if (!form) return;

    var EDIT_LABS_USADOS      = new Set(JSON.parse(document.getElementById('edit-labs-data').textContent));
    var EDIT_ASIGNADOS_USADOS = new Set(JSON.parse(document.getElementById('edit-asig-data').textContent));

    var EDIT_PREFIX_LABELS = { ANAMONI: 'General', LABBLMONI: 'Lab BL', LABCOLMONI: 'Lab COL', CFPINFO: 'Lab Informática' };

    function getExpectedPrefix(assetId) {
        if (!assetId) return null;
        var id = assetId.toUpperCase();
        if (id.indexOf('LABCOL') !== -1) return 'LABCOLMONI';
        if (id.indexOf('LABBL')  !== -1) return 'LABBLMONI';
        if (id.indexOf('CFP')    !== -1) return 'CFPINFO';
        return 'ANAMONI';
    }

    function checkEditPrefijo(labAssetId) {
        var alertaEl = document.getElementById('edit-alerta-prefijo');
        var textoEl  = document.getElementById('edit-alerta-prefijo-texto');
        if (!alertaEl || !labAssetId) { if (alertaEl) alertaEl.classList.add('d-none'); return; }
        var checkedRadio = form.querySelector('input[name="edit_prefix_sel"]:checked');
        var selectedPrefix = checkedRadio ? checkedRadio.value : '';
        var expected = getExpectedPrefix(labAssetId);
        if (expected && selectedPrefix && selectedPrefix !== expected) {
            var expLabel = EDIT_PREFIX_LABELS[expected] || expected;
            var selLabel = EDIT_PREFIX_LABELS[selectedPrefix] || selectedPrefix;
            textoEl.innerHTML = '<strong>¡Alto!</strong> La computadora es de <strong>' + expLabel +
                '</strong> pero el ID Monitor usa el prefijo <strong>' + selLabel +
                '</strong>. ¿Estás seguro de la selección?';
            alertaEl.classList.remove('d-none');
        } else {
            alertaEl.classList.add('d-none');
        }
    }

    function checkEditDuplicado(valor, esLab) {
        var usado = esLab ? EDIT_LABS_USADOS.has(valor) : EDIT_ASIGNADOS_USADOS.has(valor);
        var el = document.getElementById('edit-alerta-duplicado');
        if (el) el.classList.toggle('d-none', !usado);
    }

    // ── Pre-seleccionar radio según asset_id actual ──
    var assetInput = form.querySelector('[name="asset_id"]');
    var currentId  = assetInput ? assetInput.value : '';
    var prefijos   = ['CFPINFO', 'LABCOLMONI', 'LABBLMONI', 'ANAMONI'];
    prefijos.forEach(function(p) {
        if (currentId.startsWith(p)) {
            var radio = document.getElementById('edit-prefix-' + p);
            if (radio) radio.checked = true;
        }
    });

    // ── Al cambiar radio: actualizar prefijo en el asset_id ──
    document.querySelectorAll('input[name="edit_prefix_sel"]').forEach(function(r) {
        r.addEventListener('change', function() {
            if (!assetInput) return;
            var match = assetInput.value.match(/(\d+)$/);
            var suffix = match ? match[1] : '001';
            assetInput.value = this.value + suffix;
            if (labSel && labSel.value) checkEditPrefijo(labSel.value);
        });
    });

    // ── Toggle campos según tipo ubicación ──
    var ubicacionSel = form.querySelector('[name="ubicacion_tipo"]');
    var labDiv       = document.getElementById('edit-campo-laboratorio');
    var asnDiv       = document.getElementById('edit-campo-asignado');
    var alertaDiv    = document.getElementById('edit-alerta-duplicado');
    var labSel       = document.getElementById('edit-sel-lab-comp');
    var asnSel       = document.getElementById('edit-sel-asig-comp');

    function toggleCamposEdit() {
        var val = ubicacionSel ? ubicacionSel.value : '';
        if (alertaDiv) alertaDiv.classList.add('d-none');

        if (val === 'laboratorio') {
            if (labDiv) labDiv.classList.remove('d-none');
            if (asnDiv) asnDiv.classList.add('d-none');
            if (labSel && labSel.value) checkEditDuplicado(labSel.value, true);
        } else if (val === 'persona') {
            if (labDiv) labDiv.classList.add('d-none');
            if (asnDiv) asnDiv.classList.remove('d-none');
            if (asnSel && asnSel.value) checkEditDuplicado(asnSel.value, false);
        } else {
            if (labDiv) labDiv.classList.add('d-none');
            if (asnDiv) asnDiv.classList.add('d-none');
        }
    }

    if (labSel) labSel.addEventListener('change', function(){
        if (this.value) {
            checkEditDuplicado(this.value, true);
            checkEditPrefijo(this.value);
        } else {
            if (alertaDiv) alertaDiv.classList.add('d-none');
            var ap = document.getElementById('edit-alerta-prefijo');
            if (ap) ap.classList.add('d-none');
        }
    });

    if (asnSel) asnSel.addEventListener('change', function(){
        if (this.value) checkEditDuplicado(this.value, false);
        else if (alertaDiv) alertaDiv.classList.add('d-none');
    });

    if (ubicacionSel) {
        ubicacionSel.addEventListener('change', toggleCamposEdit);
        toggleCamposEdit();
        // Verificar prefijo al abrir si ya hay laboratorio seleccionado
        if (ubicacionSel.value === 'laboratorio' && labSel && labSel.value) {
            checkEditPrefijo(labSel.value);
        }
    }
})();
