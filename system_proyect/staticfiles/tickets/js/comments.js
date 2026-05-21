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

  const match    = window.location.pathname.match(/\/ticket\/(\d+)\//);
  const ticketId = match ? match[1] : null;
  if (!ticketId) return;

  let editandoEstado = false;
  let lastHtml       = null;
  let primeraVez     = true;

  // ── Textarea: auto-resize + Enter para enviar ──
  const ta = document.getElementById("chat-input-msg");
  if (ta) {
    ta.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 140) + "px";
    });
    ta.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        enviarMensaje();
      }
    });
  }

  // ── Estado: detectar si técnico está editando ──
  if (statusSelect) {
    statusSelect.addEventListener("focus",  () => { editandoEstado = true; });
    statusSelect.addEventListener("change", () => { editandoEstado = true; });
    statusSelect.addEventListener("blur",   () => { setTimeout(() => { editandoEstado = false; }, 600); });
  }
  if (commentsInput) {
    commentsInput.addEventListener("focus", () => { editandoEstado = true; });
    commentsInput.addEventListener("input", () => { editandoEstado = true; });
    commentsInput.addEventListener("blur",  () => { setTimeout(() => { editandoEstado = false; }, 600); });
  }

  function resetTextarea() {
    if (!ta) return;
    ta.value = "";
    ta.style.height = "auto";
    // Belt-and-suspenders: clear again after all key events finish processing
    setTimeout(() => { ta.value = ""; ta.style.height = "auto"; }, 0);
  }

  function scrollChatToBottom() {
    if (chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight;
  }

  function estabaAlFondo() {
    if (!chatDiv) return true;
    return chatDiv.scrollHeight - chatDiv.scrollTop <= chatDiv.clientHeight + 80;
  }

  function disableFormNormal() {
    if (!form) return;
    const textarea = form.querySelector("textarea");
    const boton    = form.querySelector('button[type="submit"]');
    if (textarea) textarea.disabled = true;
    if (boton) { boton.disabled = true; boton.textContent = "Ticket cerrado"; }
  }

  // ── Cargar mensajes ──
  function cargarMensajes() {
    fetch(`/tickets/ticket_comments/ajax/${ticketId}/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(r => r.json())
      .then(res => {
        if (!chatDiv) return;
        if (res.html === lastHtml && !primeraVez) return;

        const alFondo = primeraVez || estabaAlFondo();
        lastHtml = res.html;
        chatDiv.innerHTML = res.html;
        if (alFondo) scrollChatToBottom();
        primeraVez = false;
      })
      .catch(err => console.error("Error al cargar mensajes:", err));
  }

  // ── Obtener estado ──
  function getTicketStatus() {
    fetch(`/tickets/ticket_status_get_ajax/${ticketId}/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(r => r.json())
      .then(res => {
        if (!editandoEstado && statusSelect && res.status) statusSelect.value = res.status;

        if (badgeStatus && res.status) {
          badgeStatus.innerText = res.status;
          let cls = "badge";
          if (res.status === "Pendiente")       cls += " bg-warning-lt text-warning";
          else if (res.status === "En Proceso") cls += " bg-blue-lt text-blue";
          else if (res.status === "Resuelto")   cls += " bg-success-lt text-success";
          else                                   cls += " bg-secondary";
          badgeStatus.className = cls + " ms-2";
        }

        if (!editandoEstado && commentsInput && typeof res.comments !== "undefined") {
          commentsInput.value = res.comments || "";
        }

        if (res.status === "Resuelto") disableFormNormal();
      })
      .catch(err => console.error("Error al obtener estado:", err));
  }

  // ── Enviar mensaje ──
  function enviarMensaje() {
    if (!form) return;
    const csrf    = form.querySelector("[name=csrfmiddlewaretoken]");
    const btn     = form.querySelector('button[type="submit"]');
    const mensaje = ta ? ta.value.trim() : "";

    if (!mensaje) return;
    if (btn && btn.disabled) return;

    // Deshabilitar botón y limpiar textarea INMEDIATAMENTE
    if (btn) btn.disabled = true;
    resetTextarea();

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
          lastHtml = null;
          cargarMensajes();
        } else {
          // Restaurar si el servidor rechazó
          if (ta) ta.value = mensaje;
        }
      })
      .catch(() => {
        if (ta) ta.value = mensaje;
      })
      .finally(() => {
        if (btn) btn.disabled = false;
      });
  }

  // ── Botón Enviar / form submit ──
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      enviarMensaje();
    });
  }

  // ── Actualizar estado (solo técnico) ──
  if (statusForm) {
    statusForm.addEventListener("submit", function (e) {
      e.preventDefault();
      editandoEstado = true;

      const csrf     = statusForm.querySelector("[name=csrfmiddlewaretoken]");
      const status   = statusSelect  ? statusSelect.value  : "";
      const comments = commentsInput ? commentsInput.value : "";

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
            lastHtml = null;
            cargarMensajes();
            getTicketStatus();
            Swal.fire({
              icon: "success", title: "Estado actualizado",
              text: `El ticket ahora está en: ${status}`,
              timer: 2000, showConfirmButton: false,
            });
          } else {
            Swal.fire("Error", "No se pudo actualizar el estado.", "error");
          }
        })
        .catch(() => {
          editandoEstado = false;
          Swal.fire("Error", "Falló la actualización.", "error");
        });
    });
  }

  // ── Autosync ──
  setInterval(cargarMensajes, 3000);
  setInterval(getTicketStatus, 8000);
  cargarMensajes();
  getTicketStatus();
});
