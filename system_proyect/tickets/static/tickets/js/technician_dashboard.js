/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #technician_dashboard-config (un .js no lo procesa Django). */
const CFG_TECHNICIAN_DASHBOARD = (function(){
  var d = document.getElementById("technician_dashboard-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
  };
})();

window._PAGE = {
  csrf: CFG_TECHNICIAN_DASHBOARD.v0,
};


/* ─────────────────────────────────────────────────────────────────────
   <--- hecho por claude code: este bloque se había PERDIDO al sacar el JS
   del HTML (commit c8d65db): solo quedó la configuración de arriba y la
   página se quedó sin ninguna lógica. Recuperado de c8d65db~1.
   ───────────────────────────────────────────────────────────────────── */

$(function(){
  $('#tickets-table').DataTable({
    pageLength: 25, order: [[0,'desc']],
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json' }
  });
});

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
      const isMe = c.tipo === 'tecnico';
      const cls  = tipoClass(c.tipo);
      return `
        <div class="${isMe ? 'chat-row-right' : ''}">
          <div class="chat-meta ${isMe ? 'right' : ''}">${escHtml(c.autor)} · ${escHtml(c.fecha)}</div>
          <div class="chat-bubble-modal ${cls}">${escHtml(c.mensaje).replace(/\n/g,'<br>')}</div>
        </div>`;
    }).join('');
  }

  document.addEventListener('click', function(e) {
    const row = e.target.closest('.ticket-row');
    if (!row || e.target.closest('a') || e.target.closest('button')) return;

    const ticketId = row.dataset.ticketId;
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
      document.getElementById('mNombre').textContent     = d.name;
      document.getElementById('mGrado').textContent      = d.grade;
      document.getElementById('mEmail').textContent      = d.email;
      document.getElementById('mFecha').textContent      = d.created_at;
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
})();

// ── Eliminar ticket ──────────────────────────────────────────────────────────
(function(){
  let idEliminar = null;
  document.querySelectorAll('.btn-eliminar-ticket').forEach(btn => {
    btn.addEventListener('click', function(){
      idEliminar = this.dataset.id;
      document.getElementById('modalEliminarTicketTxt').textContent =
        '¿Eliminar ' + this.dataset.tid + '?';
      new bootstrap.Modal(document.getElementById('modalEliminarTicket')).show();
    });
  });
  document.getElementById('btnConfirmarEliminarTicket')?.addEventListener('click', async function(){
    if(!idEliminar) return;
    const r = await fetch('/tickets/ticket_eliminar/' + idEliminar + '/', {
      method: 'POST',
      headers: {'X-CSRFToken': window._PAGE.csrf},
    });
    const d = await r.json();
    bootstrap.Modal.getInstance(document.getElementById('modalEliminarTicket')).hide();
    if(d.ok){
      document.querySelector(`tr[data-ticket-id="${idEliminar}"]`)?.remove();
    } else {
      alert('Error: ' + (d.error || 'No se pudo eliminar'));
    }
    idEliminar = null;
  });
})();


// <--- hecho por claude code: popovers de la columna Descripción (hover). Perezoso porque
// DataTables pagina y las filas ocultas no existen al cargar.
// <--- hecho por claude code (seguridad 05-nov-2026): la descripción es TEXTO del que envía el ticket (también anónimos): html:false (Bootstrap usa textContent) y se lee con getAttribute de data-desc, que no es data-bs-* (Bootstrap no la pasa por JSON.parse/decodeURIComponent). Sin data-bs-toggle: Tabler ya no lo auto-inicializa.
(function(){
  function abrirPopDesc(e){
    const el = e.target && e.target.closest && e.target.closest('.td-desc');
    if (!el || typeof bootstrap === 'undefined' || !bootstrap.Popover) return;
    if (!bootstrap.Popover.getInstance(el)) {
      bootstrap.Popover.getOrCreateInstance(el, {
        container: 'body', html: false, trigger: 'hover focus', placement: 'top',
        customClass: 'td-desc-pop',
        content: function(){ return el.getAttribute('data-desc') || ''; }
      }).show();
    }
  }
  document.addEventListener('mouseenter', abrirPopDesc, true);
  document.addEventListener('focusin', abrirPopDesc, true);
})();
