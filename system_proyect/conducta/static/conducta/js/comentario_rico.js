// conducta/js/comentario_rico.js
// <--- hecho por claude code (03-nov-2026): editor de comentario con formato (negrita + 2 tamaños)
// y botones de IA (corregir / mejorar / formal / acortar). Un solo identificador global.
(function () {
  'use strict';

  var REDACTAR_URL = '/asistente/redactar/';
  var ACCIONES = [
    { id: 'corregir', txt: 'Corregir', icon: 'ti-spell-check', title: 'Corregir ortografía y gramática' },
    { id: 'mejorar',  txt: 'Mejorar',  icon: 'ti-wand',        title: 'Mejorar la redacción' },
    { id: 'formal',   txt: 'Formal',   icon: 'ti-briefcase',   title: 'Tono más formal' },
    { id: 'acortar',  txt: 'Acortar',  icon: 'ti-arrows-minimize', title: 'Versión más breve' }
  ];

  function esc(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Serializa el contenteditable al subconjunto canónico: <b>, <span class="tc-fs-lg|tc-fs-sm">, <br>
  function serialize(node, state) {
    var out = '';
    for (var i = 0; i < node.childNodes.length; i++) {
      var ch = node.childNodes[i];
      if (ch.nodeType === 3) {                     // texto
        out += wrap(esc(ch.nodeValue), state);
      } else if (ch.nodeType === 1) {              // elemento
        var tag = ch.tagName.toLowerCase();
        if (tag === 'br') { out += '<br>'; continue; }
        var s = { bold: state.bold, size: state.size };
        if (tag === 'b' || tag === 'strong') s.bold = true;
        var fw = ch.style && ch.style.fontWeight;
        if (fw === 'bold' || parseInt(fw, 10) >= 600) s.bold = true;
        if (ch.classList) {
          if (ch.classList.contains('tc-fs-lg')) s.size = 'lg';
          else if (ch.classList.contains('tc-fs-sm')) s.size = 'sm';
        }
        if (tag === 'font') {
          var z = parseInt(ch.getAttribute('size'), 10);
          if (z >= 5) s.size = 'lg'; else if (z && z <= 2) s.size = 'sm';
        }
        var fs = ch.style && ch.style.fontSize;
        if (fs) { var px = parseFloat(fs); if (px >= 18) s.size = 'lg'; else if (px && px <= 12) s.size = 'sm'; }
        var bloque = (tag === 'div' || tag === 'p');
        out += serialize(ch, s);
        if (bloque && i < node.childNodes.length - 1) out += '<br>';
      }
    }
    return out;
  }
  function wrap(text, state) {
    if (!text) return '';
    var t = text;
    if (state.size === 'lg') t = '<span class="tc-fs-lg">' + t + '</span>';
    else if (state.size === 'sm') t = '<span class="tc-fs-sm">' + t + '</span>';
    if (state.bold) t = '<b>' + t + '</b>';
    return t;
  }

  function csrfDe(form) {
    var i = form && form.querySelector('[name=csrfmiddlewaretoken]');
    return i ? i.value : '';
  }

  function construir(textarea) {
    if (textarea.dataset.ricoListo) return;
    textarea.dataset.ricoListo = '1';
    var form = textarea.form;

    var cont = document.createElement('div');
    cont.className = 'tc-rico';

    // Barra de herramientas
    var bar = document.createElement('div');
    bar.className = 'tc-rico-bar';
    bar.innerHTML =
      '<div class="tc-rico-fmt btn-group btn-group-sm" role="group">' +
      '  <button type="button" class="btn" data-cmd="bold" title="Negrita"><b>N</b></button>' +
      '  <button type="button" class="btn" data-cmd="lg" title="Más grande">A<sup>+</sup></button>' +
      '  <button type="button" class="btn" data-cmd="sm" title="Más pequeño">A<sup>-</sup></button>' +
      '</div>' +
      '<span class="tc-rico-ia-lbl"><i class="ti ti-sparkles"></i> IA:</span>' +
      '<div class="tc-rico-ia btn-group btn-group-sm" role="group"></div>' +
      '<span class="tc-rico-estado"></span>';
    var iaWrap = bar.querySelector('.tc-rico-ia');
    ACCIONES.forEach(function (a) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'btn btn-ia'; b.dataset.ia = a.id; b.title = a.title;
      b.innerHTML = '<i class="ti ' + a.icon + '"></i> ' + a.txt;
      iaWrap.appendChild(b);
    });

    // Área editable
    var ed = document.createElement('div');
    ed.className = 'tc-rico-ed form-control';
    ed.contentEditable = 'true';
    ed.setAttribute('role', 'textbox');
    ed.setAttribute('aria-label', 'Comentario');
    if (textarea.getAttribute('placeholder')) ed.dataset.ph = textarea.getAttribute('placeholder');
    ed.innerHTML = (textarea.value || '').trim();   // el valor ya viene saneado del servidor

    textarea.style.display = 'none';
    textarea.parentNode.insertBefore(cont, textarea);
    cont.appendChild(bar); cont.appendChild(ed); cont.appendChild(textarea);

    function sync() { textarea.value = serialize(ed, { bold: false, size: '' }); }
    ed.addEventListener('input', sync);
    ed.addEventListener('blur', sync);
    if (form) form.addEventListener('submit', sync);

    // Pegar como texto plano (evita pegar HTML externo)
    ed.addEventListener('paste', function (e) {
      e.preventDefault();
      var t = (e.clipboardData || window.clipboardData).getData('text/plain');
      document.execCommand('insertText', false, t);
    });

    // Formato
    bar.querySelectorAll('.tc-rico-fmt [data-cmd]').forEach(function (btn) {
      btn.addEventListener('mousedown', function (e) { e.preventDefault(); });
      btn.addEventListener('click', function () {
        ed.focus();
        var cmd = btn.dataset.cmd;
        if (cmd === 'bold') document.execCommand('bold');
        else if (cmd === 'lg') document.execCommand('fontSize', false, '5');
        else if (cmd === 'sm') document.execCommand('fontSize', false, '2');
        sync();
      });
    });

    // IA
    var estado = bar.querySelector('.tc-rico-estado');
    function setBusy(on) {
      cont.classList.toggle('tc-rico-busy', on);
      bar.querySelectorAll('button').forEach(function (b) { b.disabled = on; });
      estado.textContent = on ? 'Procesando…' : '';
    }
    iaWrap.querySelectorAll('[data-ia]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var texto = (ed.innerText || '').trim();
        if (!texto) { estado.textContent = 'Escribe algo primero.'; return; }
        setBusy(true);
        fetch(textarea.dataset.redactarUrl || REDACTAR_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfDe(form) },
          body: JSON.stringify({ accion: btn.dataset.ia, texto: texto })
        }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
          .then(function (res) {
            setBusy(false);
            if (res.ok && res.j && res.j.ok) {
              ed.textContent = res.j.texto;   // texto plano (se pierde el formato previo a propósito)
              sync();
              estado.textContent = 'Listo ✓';
              setTimeout(function () { estado.textContent = ''; }, 2500);
            } else {
              estado.textContent = (res.j && res.j.error) || 'No se pudo. Intenta de nuevo.';
            }
          }).catch(function () { setBusy(false); estado.textContent = 'Error de conexión.'; });
      });
    });

    sync();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('textarea[data-rico]').forEach(construir);
  });
})();
