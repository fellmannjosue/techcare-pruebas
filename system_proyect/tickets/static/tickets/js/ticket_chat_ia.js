/* <--- hecho por claude code: chat IA del ticket — el servidor guarda el historial en los
   comentarios del ticket, así que aquí solo se envía el mensaje. Si el usuario escala a
   técnico, el chat se cierra y se ofrece el chat humano. */
(function () {
  const form = document.getElementById('form-ia');
  const chat = document.getElementById('chat');
  const input = document.getElementById('mensaje');
  const btn = document.getElementById('btn-enviar');
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
  chat.scrollTop = chat.scrollHeight;

  function burbuja(texto, clase) {
    const d = document.createElement('div');
    d.className = 'msg ' + clase;
    d.textContent = texto;
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
  }

  function finalizar() {
    input.disabled = true; btn.disabled = true;
    input.placeholder = 'La IA finalizó — un técnico te atiende en este ticket';
    const a = document.createElement('a');
    a.href = form.dataset.tecnicoUrl; a.textContent = '💬 Continuar con el técnico';
    a.className = 'msg error';
    chat.appendChild(a); chat.scrollTop = chat.scrollHeight;
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
      .then(r => r.json().then(d => ({ st: r.status, d })))
      .then(({ st, d }) => {
        if (d.ok) {
          const m = d.mensaje_ia;
          burbuja(m.mensaje, m.tipo === 'sistema' ? 'error' : 'ia');
          if (m.ia_finalizada) finalizar();
        } else {
          burbuja(d.error || 'Error', 'error');
          if (st === 403 && (d.error || '').includes('bloqueada')) finalizar();
        }
      })
      .catch(err => burbuja('Error de red: ' + err, 'error'))
      .finally(() => { if (!input.disabled) { btn.disabled = false; btn.textContent = 'Enviar'; input.focus(); } else { btn.textContent = 'Enviar'; } });
  });
})();
