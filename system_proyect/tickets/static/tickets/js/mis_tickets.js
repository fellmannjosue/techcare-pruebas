(function(){
  const statusClasses = {
    'Resuelto':   'bg-success-lt text-success',
    'En Proceso': 'bg-blue-lt text-blue',
    'Pendiente':  'bg-warning-lt text-warning',
  };

  // <--- hecho por claude code (seguridad 05-nov-2026): XSS — el chat lo escribe el usuario; se escapa antes de pintarlo con innerHTML
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[ch];
    });
  }

  function tipoClass(tipo) {
    if (tipo === 'tecnico') return 'bm-tecnico';
    if (tipo === 'sistema') return 'bm-sistema';
    return 'bm-usuario';
  }

  function renderChat(chat) {
    if (!chat.length) return '<div class="text-center text-muted small py-2">Sin mensajes aún.</div>';
    return chat.map(c => {
      const isMe = c.tipo === 'usuario';
      const cls  = tipoClass(c.tipo);
      if (c.tipo === 'sistema') {
        return `<div class="my-2"><span class="bm-sistema">${escHtml(c.mensaje)}</span></div>`;
      }
      return `
        <div class="${isMe ? 'chat-row-right' : ''}">
          <div class="chat-meta ${isMe ? 'right' : ''}">${escHtml(c.autor)} · ${escHtml(c.fecha)}</div>
          <div class="chat-bubble-modal ${cls}">${escHtml(c.mensaje).replace(/\n/g,'<br>')}</div>
        </div>`;
    }).join('');
  }

  document.querySelectorAll('.ticket-row').forEach(row => {
    row.addEventListener('click', function() {
      const ticketId = this.dataset.ticketId;
      document.getElementById('mChat').innerHTML = '<div class="text-center text-muted small py-3">Cargando…</div>';
      document.getElementById('modalTicketId').textContent = 'Cargando…';

      const modal = new bootstrap.Modal(document.getElementById('modalReporte'));
      modal.show();

      fetch(`/tickets/ticket/${ticketId}/reporte/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
      .then(r => r.json())
      .then(d => {
        document.getElementById('modalTicketId').textContent = 'Ticket ' + d.ticket_id;
        const sb = document.getElementById('modalStatus');
        sb.textContent = d.status;
        sb.className = 'badge mt-1 ' + (statusClasses[d.status] || 'bg-secondary');
        document.getElementById('mNombre').textContent      = d.name;
        document.getElementById('mGrado').textContent       = d.grade;
        document.getElementById('mEmail').textContent       = d.email;
        document.getElementById('mFecha').textContent       = d.created_at;
        document.getElementById('mDescripcion').textContent = d.description;
        if (d.attachment_url) {
          document.getElementById('mAdjunto').href = d.attachment_url;
          document.getElementById('adjuntoRow').style.display = '';
        } else {
          document.getElementById('adjuntoRow').style.display = 'none';
        }
        document.getElementById('mBtnChat').href = d.chat_url;
        document.getElementById('mChat').innerHTML = renderChat(d.chat);
        const cs = document.getElementById('mChat');
        cs.scrollTop = cs.scrollHeight;
      })
      .catch(() => {
        document.getElementById('mChat').innerHTML = '<div class="text-danger small">Error al cargar el reporte.</div>';
      });
    });
  });
})();

// Botón Volver: usa history.back() si hay historial, sino nav_home_url
(function(){
  var btn = document.getElementById('btn-volver-hist');
  if (btn && window.history.length > 1) {
    btn.addEventListener('click', function(e){
      e.preventDefault();
      history.back();
    });
  }
})();
