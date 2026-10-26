// <--- hecho por claude code (26-oct-2026): widget del asistente IA (solo app .exe)
// IIFE con nombres propios: no choca con otros .js del sistema.
(function () {
  'use strict';

  var cfg = document.getElementById('tc-asis-config');
  if (!cfg) return;                                  // no está el widget en esta página
  var URL_CHAT = cfg.dataset.url;
  var ES_SUPER = cfg.dataset.super === '1';

  var fab, panel, msgsEl, textarea, enviarBtn, typingEl;
  var historial = [];                                // [{role, content}]
  var enviando = false;

  function cookie(nombre) {
    var m = document.cookie.match('(^|;)\\s*' + nombre + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : '';
  }

  function escapar(t) {
    return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Render mínimo: bloques ```code```, `inline` y saltos de línea.
  function formatear(texto) {
    var partes = texto.split(/```/);
    var out = '';
    for (var i = 0; i < partes.length; i++) {
      if (i % 2 === 1) {
        var cuerpo = partes[i].replace(/^[a-zA-Z0-9_-]*\n/, '');  // quita el lenguaje de la 1ª línea
        out += '<pre><code>' + escapar(cuerpo) + '</code></pre>';
      } else {
        var txt = escapar(partes[i]).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\n/g, '<br>');
        out += txt;
      }
    }
    return out;
  }

  function pintar(role, texto, bruto) {
    var fila = document.createElement('div');
    fila.className = 'tc-asis-msg ' + (role === 'user' ? 'user' : 'bot');
    var burbuja = document.createElement('div');
    burbuja.className = 'burbuja';
    if (role === 'user') burbuja.textContent = texto;
    else burbuja.innerHTML = formatear(texto);
    fila.appendChild(burbuja);
    msgsEl.appendChild(fila);
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function mostrarTyping(si) {
    typingEl.style.display = si ? 'block' : 'none';
    if (si) msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  function enviar() {
    if (enviando) return;
    var texto = textarea.value.trim();
    if (!texto) return;
    textarea.value = '';
    textarea.style.height = 'auto';
    historial.push({ role: 'user', content: texto });
    pintar('user', texto);
    enviando = true;
    enviarBtn.disabled = true;
    mostrarTyping(true);

    fetch(URL_CHAT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cookie('csrftoken') },
      body: JSON.stringify({ mensajes: historial })
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        mostrarTyping(false);
        if (res.j && res.j.ok) {
          historial.push({ role: 'assistant', content: res.j.reply });
          pintar('bot', res.j.reply);
        } else {
          pintar('bot', (res.j && res.j.error) || 'No se pudo responder.');
        }
      }).catch(function () {
        mostrarTyping(false);
        pintar('bot', 'No hay conexión con el servidor.');
      }).then(function () {
        enviando = false;
        enviarBtn.disabled = false;
        textarea.focus();
      });
  }

  document.addEventListener('DOMContentLoaded', function () {
    fab = document.getElementById('tc-asis-fab');
    panel = document.getElementById('tc-asis-panel');
    msgsEl = document.getElementById('tc-asis-msgs');
    textarea = document.getElementById('tc-asis-input');
    enviarBtn = document.getElementById('tc-asis-enviar');
    typingEl = document.getElementById('tc-asis-typing');
    if (!fab || !panel) return;

    fab.addEventListener('click', function () {
      panel.classList.toggle('abierto');
      if (panel.classList.contains('abierto')) textarea.focus();
    });
    document.getElementById('tc-asis-cerrar').addEventListener('click', function () {
      panel.classList.remove('abierto');
    });

    enviarBtn.addEventListener('click', enviar);
    textarea.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); }
    });
    textarea.addEventListener('input', function () {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    });
  });
})();
