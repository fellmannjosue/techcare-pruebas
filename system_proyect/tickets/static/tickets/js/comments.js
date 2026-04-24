document.addEventListener("DOMContentLoaded", function () {
  const statusForm    = document.getElementById("form-status-ticket");
  const statusSelect  = document.getElementById("chat-status-select");
  const commentsInput = document.getElementById("ticket-comments");
  const badgeStatus   = document.getElementById("badge-status");
  const chatDiv       = document.getElementById("chat-mensajes");

  const form =
    document.getElementById("formComentario") ||
    document.getElementById("formComentarioTech") ||
    document.getElementById("formComentarioUsuario");

  const match    = window.location.pathname.match(/(\d+)/);
  const ticketId = match ? match[0] : null;
  if (!ticketId) return;

  let editandoEstado = false;

  if (statusSelect) {
    statusSelect.addEventListener("focus",  () => { editandoEstado = true; });
    statusSelect.addEventListener("change", () => { editandoEstado = true; });
    statusSelect.addEventListener("blur",   () => { setTimeout(() => { editandoEstado = false; }, 500); });
  }
  if (commentsInput) {
    commentsInput.addEventListener("focus", () => { editandoEstado = true; });
    commentsInput.addEventListener("input", () => { editandoEstado = true; });
    commentsInput.addEventListener("blur",  () => { setTimeout(() => { editandoEstado = false; }, 500); });
  }

  function scrollChatToBottom() {
    if (chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight;
  }

  function disableFormNormal() {
    if (!form) return;
    const textarea = form.querySelector("textarea");
    const boton    = form.querySelector('button[type="submit"]');
    if (textarea) textarea.disabled = true;
    if (boton)    { boton.disabled = true; boton.innerText = "Ticket cerrado"; }
  }

  // ------ Cargar mensajes ------
  function cargarMensajes() {
    fetch(`/tickets/ticket_comments/ajax/${ticketId}/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(r => r.json())
      .then(res => {
        if (chatDiv) { chatDiv.innerHTML = res.html; scrollChatToBottom(); }
      })
      .catch(err => console.error("Error al cargar mensajes:", err));
  }

  // ------ Obtener estado ------
  function getTicketStatus() {
    fetch(`/tickets/ticket_status_get_ajax/${ticketId}/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(r => r.json())
      .then(res => {
        if (!editandoEstado && statusSelect && res.status) statusSelect.value = res.status;

        if (badgeStatus && res.status) {
          badgeStatus.innerText = res.status;
          let color = "bg-secondary";
          if (res.status === "Pendiente")  color = "bg-warning text-dark";
          if (res.status === "En Proceso") color = "bg-info text-dark";
          if (res.status === "Resuelto")   color = "bg-success";
          badgeStatus.className = `badge ${color}`;
        }

        if (!editandoEstado && commentsInput && typeof res.comments !== "undefined") {
          commentsInput.value = res.comments || "";
        }

        if (res.status === "Resuelto") disableFormNormal();
      })
      .catch(err => console.error("Error al obtener estado:", err));
  }

  // ------ Actualizar estado ------
  if (statusForm) {
    statusForm.addEventListener("submit", function (e) {
      e.preventDefault();
      editandoEstado = true;

      const csrf     = statusForm.querySelector("[name=csrfmiddlewaretoken]");
      const status   = statusSelect  ? statusSelect.value   : "";
      const comments = commentsInput ? commentsInput.value  : "";

      fetch(`/tickets/ticket_status_update_ajax/${ticketId}/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrf ? csrf.value : "",
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({ status, comments }),
      })
        .then(r => r.json())
        .then(res => {
          editandoEstado = false;
          if (res.ok) {
            getTicketStatus();
            Swal.fire({ icon: "success", title: "Estado actualizado",
              text: "El estado del ticket se actualizó correctamente.",
              timer: 1800, showConfirmButton: false });
          } else {
            Swal.fire("Error", "No se pudo actualizar el estado.", "error");
          }
        })
        .catch(() => {
          editandoEstado = false;
          Swal.fire("Error", "Falló la actualización del estado.", "error");
        });
    });
  }

  // ------ Enviar comentario (AJAX) ------
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      const csrf     = form.querySelector("[name=csrfmiddlewaretoken]");
      const textarea = form.querySelector("textarea") || form.querySelector("input[name=mensaje]");
      const btn      = form.querySelector('button[type="submit"]');
      const mensaje  = textarea ? textarea.value.trim() : "";
      if (!mensaje) return;
      if (btn && btn.disabled) return;

      if (btn) btn.disabled = true;

      fetch(`/tickets/ticket_send_comment_ajax/${ticketId}/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrf ? csrf.value : "",
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({ mensaje }),
      })
        .then(r => r.json())
        .then(res => {
          if (res.ok) {
            if (textarea) textarea.value = "";
            cargarMensajes();
          }
        })
        .catch(() => {})
        .finally(() => {
          if (btn) btn.disabled = false;
        });
    });
  }

  // ------ Autosync cada 2s ------
  setInterval(cargarMensajes, 2000);

  cargarMensajes();
  getTicketStatus();
});
