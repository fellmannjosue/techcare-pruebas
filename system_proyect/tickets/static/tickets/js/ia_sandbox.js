/* <--- hecho por claude code: sandbox IA (pruebas) — pregunta a OpenAI vía el endpoint, sin tocar la BD */
(function () {
  const form = document.getElementById('form-ia');
  const chat = document.getElementById('chat');
  const input = document.getElementById('mensaje');
  const btn = document.getElementById('btn-enviar');
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;

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
      body: new URLSearchParams({ mensaje: msg }),
    })
      .then(r => r.json())
      .then(d => burbuja(d.ok ? d.respuesta : ('Error: ' + (d.error || 'desconocido')), d.ok ? 'ia' : 'error'))
      .catch(err => burbuja('Error de red: ' + err, 'error'))
      .finally(() => { btn.disabled = false; btn.textContent = 'Enviar'; input.focus(); });
  });
})();
