/* <--- hecho por claude code: selects agregables (Área, Tipo) en el form de producto. */
(function () {
  'use strict';
  var csrfEl = document.querySelector('input[name=csrfmiddlewaretoken]');
  var csrf = csrfEl ? csrfEl.value : '';

  function wire(btn) {
    var id = btn.getAttribute('data-target');
    var url = btn.getAttribute('data-url');
    var grupo = btn.getAttribute('data-grupo') || '';
    var sel = document.getElementById(id);
    var box = document.querySelector('[data-addbox="' + id + '"]');
    if (!sel || !box) { return; }
    var input = box.querySelector('input');

    btn.addEventListener('click', function () { box.classList.remove('d-none'); input.value = ''; input.focus(); });
    box.querySelector('[data-addcancel]').addEventListener('click', function () { box.classList.add('d-none'); });

    function save() {
      var nombre = (input.value || '').trim();
      if (!nombre) { input.focus(); return; }
      fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest',
                   'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'grupo=' + encodeURIComponent(grupo) + '&nombre=' + encodeURIComponent(nombre)
      }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (!res.ok || !res.j.ok) { alert((res.j && res.j.error) || 'No se pudo agregar.'); return; }
          var v = String(res.j.value), existe = null, i;
          for (i = 0; i < sel.options.length; i++) {
            if (String(sel.options[i].value) === v) { existe = sel.options[i]; break; }
          }
          if (!existe) { existe = new Option(res.j.label, v); sel.add(existe); }
          sel.value = v;
          box.classList.add('d-none');
        }).catch(function () { alert('Error de red al agregar.'); });
    }

    box.querySelector('[data-addsave]').addEventListener('click', save);
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); save(); } });
  }

  var botones = document.querySelectorAll('.cc-add');
  for (var i = 0; i < botones.length; i++) { wire(botones[i]); }
})();
