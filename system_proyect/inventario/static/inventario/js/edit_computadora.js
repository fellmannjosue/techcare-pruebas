/* edit_computadora.js */
(function(){
  var form = document.getElementById('form-edit-computadora');
  if (!form) return;

  // Sub-tipo Otros
  var gradoSel     = form.querySelector('[name="grado"]');
  var subtipoDiv   = document.getElementById('edit-campo-grado-subtipo');
  var subtipoSel   = document.getElementById('edit-id-grado-subtipo');
  if (gradoSel) {
    gradoSel.addEventListener('change', function(){
      var esOtros = this.value === 'Otros';
      if (subtipoDiv) subtipoDiv.classList.toggle('d-none', !esOtros);
      if (!esOtros && subtipoSel) subtipoSel.value = '';
    });
  }

  var SERIE_PREFIJOS = {
    'Ideacentre AIO 3 22ITL6':  'MP24ML',
    'Ideacentre AIO 3 24ARE05': 'MP1Z5',
    'IdeaCentre AIO 5 24IMB05': 'MJ0F7'
  };
  var modeloSel = form.querySelector('[name="modelo"]');
  var serieInp  = form.querySelector('[name="serie"]');
  if (modeloSel && serieInp) {
    modeloSel.addEventListener('change', function(){
      var prefijo = SERIE_PREFIJOS[this.value];
      if (prefijo) {
        serieInp.value = prefijo.toUpperCase();
        serieInp.focus();
        serieInp.setSelectionRange(serieInp.value.length, serieInp.value.length);
      }
    });
  }
})();
