/* <--- hecho por claude code: sandbox IA (pruebas) — pregunta a OpenAI vía el endpoint, sin tocar la BD */
(function () {
  const form = document.getElementById('form-ia');
  const chat = document.getElementById('chat');
  const input = document.getElementById('mensaje');
  const btn = document.getElementById('btn-enviar');
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
  const historial = [];   // <--- hecho por claude code: memoria del chat (se envía al servidor)

  function burbuja(texto, clase) {
    const d = document.createElement('div');
    d.className = 'msg ' + clase;
    d.textContent = texto;
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const msg = input.value.trim();
    if (!msg) return;
    burbuja(msg, 'yo');
    input.value = ''; btn.disabled = true; btn.textContent = 'Pensando…';
    fetch(form.dataset.url, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf },
      body: new URLSearchParams({ mensaje: msg, historial: JSON.stringify(historial) }),
    })
      .then(r => r.json())
      .then(d => {
        burbuja(d.ok ? d.respuesta : ('Error: ' + (d.error || 'desconocido')), d.ok ? 'ia' : 'error');
        if (d.ok) {
          historial.push({ role: 'user', content: msg });
          historial.push({ role: 'assistant', content: d.respuesta });
        }
        // <--- hecho por claude code: se creó un ticket real → el chat termina aquí
        if (d.escalado) {
          input.disabled = true; btn.disabled = true;
          input.placeholder = 'Chat finalizado — ticket ' + d.ticket_id + ' creado';
        }
      })
      .catch(err => burbuja('Error de red: ' + err, 'error'))
      .finally(() => { if (!input.disabled) { btn.disabled = false; btn.textContent = 'Enviar'; input.focus(); } else { btn.textContent = 'Enviar'; } });
  });
})();
