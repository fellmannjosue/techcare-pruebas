document.addEventListener("DOMContentLoaded", function () {
  // ------ SELECTORES ------
  const statusForm = document.getElementById("form-status-ticket");
  const statusSelect = document.getElementById("chat-status-select");
  const commentsInput = document.getElementById("ticket-comments");
  const badgeStatus = document.getElementById("badge-status");
  const chatDiv = document.getElementById("chat-mensajes");

  // IA pendiente para más adelante
  // const formIA = document.getElementById("formComentarioIA");

  const form =
    document.getElementById("formComentario") ||
    document.getElementById("formComentarioTech") ||
    document.getElementById("formComentarioUsuario");

  // IA pendiente para más adelante
  // const btnContactarTecnico = document.getElementById("btn-contactar-tecnico");
  // const iaOpciones = document.getElementById("chat-ia-opciones");

  // ------ OBTIENE TICKET ID ------
  const match = window.location.pathname.match(/(\d+)/);
  const ticketId = match ? match[0] : null;

  if (!ticketId) return;

  // ------ SCROLL ------
  function scrollChatToBottom() {
    if (chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight;
  }

  // Renderiza mensaje del chat
  function renderBubble(data) {
    let icon = "";
    let autor = "";
    let clase = "";

    if (data.tipo === "usuario") {
      icon = '<i class="bi bi-person-circle"></i>';
      autor = `<span class="fw-semibold">${data.autor}</span>`;
      clase = "mine";
    } else if (data.tipo === "tecnico") {
      icon = '<i class="bi bi-tools"></i>';
      autor = `<span class="fw-semibold text-primary">Técnico</span>`;
      clase = "tecnico-bubble";
    }

    // IA pendiente para más adelante
    /*
    else if (data.tipo === "ia") {
      icon = '<i class="bi bi-robot"></i>';
      autor = `<span class="fw-semibold text-success">IA TechCare</span>`;
      clase = "ia-bubble";
    }
    */

    return `
        <div class="chat-bubble ${clase}">
            ${data.mensaje.replace(/\n/g, "<br>")}
            <div class="chat-meta">
                ${icon} ${autor}
                <span class="text-secondary">${data.fecha}</span>
            </div>
        </div>`;
  }

  // ------ Cargar mensajes chat ------
  function cargarMensajes() {
    fetch(`/tickets/ticket_comments/ajax/${ticketId}/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((resp) => resp.json())
      .then((res) => {
        if (chatDiv) {
          chatDiv.innerHTML = res.html;
          scrollChatToBottom();
        }
      })
      .catch((err) => {
        console.error("Error al cargar mensajes:", err);
      });
  }

  // ------ Obtener estado ------
  function getTicketStatus() {
    fetch(`/tickets/ticket_status_get_ajax/${ticketId}/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((resp) => resp.json())
      .then((res) => {
        if (statusSelect && res.status) statusSelect.value = res.status;

        if (badgeStatus && res.status) {
          badgeStatus.innerText = res.status;
          let color = "bg-secondary";
          if (res.status === "Pendiente") color = "bg-warning text-dark";
          if (res.status === "En Proceso") color = "bg-info text-dark";
          if (res.status === "Resuelto") color = "bg-success";
          badgeStatus.className = `badge ${color}`;
        }

        if (commentsInput && typeof res.comments !== "undefined") {
          commentsInput.value = res.comments || "";
        }

        if (res.status === "Resuelto") {
          disableFormNormal();

          // IA pendiente para más adelante
          // if (formIA) disableFormIA();
        }
      })
      .catch((err) => {
        console.error("Error al obtener estado:", err);
      });
  }

  /*
  // IA pendiente para más adelante
  function disableFormIA() {
    let textarea = formIA.querySelector("textarea");
    let boton = formIA.querySelector('button[type="submit"]');
    if (textarea) textarea.disabled = true;
    if (boton) {
      boton.disabled = true;
      boton.innerText = "Ticket cerrado";
    }
  }
  */

  function disableFormNormal() {
    if (!form) return;

    let textarea = form.querySelector("textarea");
    let boton = form.querySelector('button[type="submit"]');

    if (textarea) textarea.disabled = true;
    if (boton) {
      boton.disabled = true;
      boton.innerText = "Ticket cerrado";
    }
  }

  // ------ ACTUALIZAR ESTADO ------
  if (statusForm) {
    statusForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const csrf = statusForm.querySelector("[name=csrfmiddlewaretoken]");
      const status = statusSelect ? statusSelect.value : "";
      const comments = commentsInput ? commentsInput.value : "";

      fetch(`/tickets/ticket_status_update_ajax/${ticketId}/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrf ? csrf.value : "",
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          status: status,
          comments: comments,
        }),
      })
        .then((resp) => resp.json())
        .then((res) => {
          if (res.ok) {
            getTicketStatus();

            Swal.fire({
              icon: "success",
              title: "Estado actualizado",
              text: "El estado del ticket se actualizó correctamente.",
              timer: 1800,
              showConfirmButton: false,
            });
          } else {
            Swal.fire("Error", "No se pudo actualizar el estado.", "error");
          }
        })
        .catch(() => {
          Swal.fire("Error", "Falló la actualización del estado.", "error");
        });
    });
  }

  // ------ FORMULARIO NORMAL DE MENSAJE ------
  if (form) {
    form.addEventListener("submit", function () {
      setTimeout(() => {
        cargarMensajes();
      }, 500);
    });
  }

  // ------ AUTOSYNC ------
  setInterval(cargarMensajes, 2000);
  setInterval(getTicketStatus, 2000);

  cargarMensajes();
  getTicketStatus();

  /*
  // ============================================================
  // IA pendiente para más adelante
  // CHAT IA
  // ============================================================
  if (formIA) {
    formIA.addEventListener("submit", function (e) {
      e.preventDefault();
      const mensaje = formIA.querySelector("textarea").value.trim();
      if (!mensaje) return;

      fetch(`/tickets/ticket/${ticketId}/chat_ai/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": formIA.querySelector("[name=csrfmiddlewaretoken]").value,
        },
        body: new URLSearchParams({ mensaje: mensaje }),
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.ok) {
            chatDiv.innerHTML += renderBubble(data.mensaje_usuario);
            chatDiv.innerHTML += renderBubble(data.mensaje_ia);
            scrollChatToBottom();
            formIA.reset();
          } else {
            Swal.fire("Atención", data.error, "info");
          }
        })
        .catch(() => Swal.fire("Error", "Fallo en IA", "error"));
    });
  }

  // ============================================================
  // IA pendiente para más adelante
  // BOTÓN "NO ME AYUDÓ, CONTACTAR TÉCNICO"
  // ============================================================
  if (btnContactarTecnico) {
    btnContactarTecnico.addEventListener("click", function () {
      Swal.fire({
        icon: "warning",
        title: "¿Deseas contactar a un técnico?",
        text: "La IA dejará de responder y un técnico humano continuará con tu ticket.",
        showCancelButton: true,
        confirmButtonText: "Sí, contactar técnico",
        cancelButtonText: "Cancelar",
      }).then((result) => {
        if (!result.isConfirmed) return;

        fetch(`/tickets/ticket/${ticketId}/contactar_tecnico/`, {
          method: "POST",
          headers: {
            "X-CSRFToken":
              document.querySelector("[name=csrfmiddlewaretoken]").value,
          },
        })
          .then((resp) => resp.json())
          .then((res) => {
            if (res.ok) {
              if (formIA) {
                disableFormIA();
                formIA.style.display = "none";
              }
              if (iaOpciones) iaOpciones.style.display = "none";

              Swal.fire({
                icon: "success",
                title: "Un técnico fue notificado",
                text: "La IA ya no responderá más en este ticket.",
                confirmButtonText: "Entendido",
              });

              cargarMensajes();
              scrollChatToBottom();
            }
          });
      });
    });
  }
  */
});document.addEventListener("DOMContentLoaded", function () {
  // ------ SELECTORES ------
  const statusForm = document.getElementById("form-status-ticket");
  const statusSelect = document.getElementById("chat-status-select");
  const commentsInput = document.getElementById("ticket-comments");
  const badgeStatus = document.getElementById("badge-status");
  const chatDiv = document.getElementById("chat-mensajes");

  // IA pendiente para más adelante
  // const formIA = document.getElementById("formComentarioIA");

  const form =
    document.getElementById("formComentario") ||
    document.getElementById("formComentarioTech") ||
    document.getElementById("formComentarioUsuario");

  // IA pendiente para más adelante
  // const btnContactarTecnico = document.getElementById("btn-contactar-tecnico");
  // const iaOpciones = document.getElementById("chat-ia-opciones");

  // ------ OBTIENE TICKET ID ------
  const match = window.location.pathname.match(/(\d+)/);
  const ticketId = match ? match[0] : null;

  if (!ticketId) return;

  // ------ CONTROL DE EDICIÓN ------
  let editandoEstado = false;

  if (statusSelect) {
    statusSelect.addEventListener("focus", function () {
      editandoEstado = true;
    });

    statusSelect.addEventListener("change", function () {
      editandoEstado = true;
    });

    statusSelect.addEventListener("blur", function () {
      setTimeout(() => {
        editandoEstado = false;
      }, 500);
    });
  }

  if (commentsInput) {
    commentsInput.addEventListener("focus", function () {
      editandoEstado = true;
    });

    commentsInput.addEventListener("input", function () {
      editandoEstado = true;
    });

    commentsInput.addEventListener("blur", function () {
      setTimeout(() => {
        editandoEstado = false;
      }, 500);
    });
  }

  // ------ SCROLL ------
  function scrollChatToBottom() {
    if (chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight;
  }

  // Renderiza mensaje del chat
  function renderBubble(data) {
    let icon = "";
    let autor = "";
    let clase = "";

    if (data.tipo === "usuario") {
      icon = '<i class="bi bi-person-circle"></i>';
      autor = `<span class="fw-semibold">${data.autor}</span>`;
      clase = "mine";
    } else if (data.tipo === "tecnico") {
      icon = '<i class="bi bi-tools"></i>';
      autor = `<span class="fw-semibold text-primary">Técnico</span>`;
      clase = "tecnico-bubble";
    }

    // IA pendiente para más adelante
    /*
    else if (data.tipo === "ia") {
      icon = '<i class="bi bi-robot"></i>';
      autor = `<span class="fw-semibold text-success">IA TechCare</span>`;
      clase = "ia-bubble";
    }
    */

    return `
        <div class="chat-bubble ${clase}">
            ${data.mensaje.replace(/\n/g, "<br>")}
            <div class="chat-meta">
                ${icon} ${autor}
                <span class="text-secondary">${data.fecha}</span>
            </div>
        </div>`;
  }

  // ------ Cargar mensajes chat ------
  function cargarMensajes() {
    fetch(`/tickets/ticket_comments/ajax/${ticketId}/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((resp) => resp.json())
      .then((res) => {
        if (chatDiv) {
          chatDiv.innerHTML = res.html;
          scrollChatToBottom();
        }
      })
      .catch((err) => {
        console.error("Error al cargar mensajes:", err);
      });
  }

  // ------ Obtener estado ------
  function getTicketStatus() {
    fetch(`/tickets/ticket_status_get_ajax/${ticketId}/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then((resp) => resp.json())
      .then((res) => {
        if (!editandoEstado && statusSelect && res.status) {
          statusSelect.value = res.status;
        }

        if (badgeStatus && res.status) {
          badgeStatus.innerText = res.status;
          let color = "bg-secondary";
          if (res.status === "Pendiente") color = "bg-warning text-dark";
          if (res.status === "En Proceso") color = "bg-info text-dark";
          if (res.status === "Resuelto") color = "bg-success";
          badgeStatus.className = `badge ${color}`;
        }

        if (!editandoEstado && commentsInput && typeof res.comments !== "undefined") {
          commentsInput.value = res.comments || "";
        }

        if (res.status === "Resuelto") {
          disableFormNormal();

          // IA pendiente para más adelante
          // if (formIA) disableFormIA();
        }
      })
      .catch((err) => {
        console.error("Error al obtener estado:", err);
      });
  }

  /*
  // IA pendiente para más adelante
  function disableFormIA() {
    let textarea = formIA.querySelector("textarea");
    let boton = formIA.querySelector('button[type="submit"]');
    if (textarea) textarea.disabled = true;
    if (boton) {
      boton.disabled = true;
      boton.innerText = "Ticket cerrado";
    }
  }
  */

  function disableFormNormal() {
    if (!form) return;

    let textarea = form.querySelector("textarea");
    let boton = form.querySelector('button[type="submit"]');

    if (textarea) textarea.disabled = true;
    if (boton) {
      boton.disabled = true;
      boton.innerText = "Ticket cerrado";
    }
  }

  // ------ ACTUALIZAR ESTADO ------
  if (statusForm) {
    statusForm.addEventListener("submit", function (e) {
      e.preventDefault();

      editandoEstado = true;

      const csrf = statusForm.querySelector("[name=csrfmiddlewaretoken]");
      const status = statusSelect ? statusSelect.value : "";
      const comments = commentsInput ? commentsInput.value : "";

      fetch(`/tickets/ticket_status_update_ajax/${ticketId}/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrf ? csrf.value : "",
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          status: status,
          comments: comments,
        }),
      })
        .then((resp) => resp.json())
        .then((res) => {
          if (res.ok) {
            editandoEstado = false;
            getTicketStatus();

            Swal.fire({
              icon: "success",
              title: "Estado actualizado",
              text: "El estado del ticket se actualizó correctamente.",
              timer: 1800,
              showConfirmButton: false,
            });
          } else {
            editandoEstado = false;
            Swal.fire("Error", "No se pudo actualizar el estado.", "error");
          }
        })
        .catch(() => {
          editandoEstado = false;
          Swal.fire("Error", "Falló la actualización del estado.", "error");
        });
    });
  }

  // ------ FORMULARIO NORMAL DE MENSAJE ------
  if (form) {
    form.addEventListener("submit", function () {
      setTimeout(() => {
        cargarMensajes();
      }, 500);
    });
  }

  // ------ AUTOSYNC ------
  setInterval(cargarMensajes, 2000);
  setInterval(getTicketStatus, 2000);

  cargarMensajes();
  getTicketStatus();

  /*
  // ============================================================
  // IA pendiente para más adelante
  // CHAT IA
  // ============================================================
  if (formIA) {
    formIA.addEventListener("submit", function (e) {
      e.preventDefault();
      const mensaje = formIA.querySelector("textarea").value.trim();
      if (!mensaje) return;

      fetch(`/tickets/ticket/${ticketId}/chat_ai/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": formIA.querySelector("[name=csrfmiddlewaretoken]").value,
        },
        body: new URLSearchParams({ mensaje: mensaje }),
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.ok) {
            chatDiv.innerHTML += renderBubble(data.mensaje_usuario);
            chatDiv.innerHTML += renderBubble(data.mensaje_ia);
            scrollChatToBottom();
            formIA.reset();
          } else {
            Swal.fire("Atención", data.error, "info");
          }
        })
        .catch(() => Swal.fire("Error", "Fallo en IA", "error"));
    });
  }

  // ============================================================
  // IA pendiente para más adelante
  // BOTÓN "NO ME AYUDÓ, CONTACTAR TÉCNICO"
  // ============================================================
  if (btnContactarTecnico) {
    btnContactarTecnico.addEventListener("click", function () {
      Swal.fire({
        icon: "warning",
        title: "¿Deseas contactar a un técnico?",
        text: "La IA dejará de responder y un técnico humano continuará con tu ticket.",
        showCancelButton: true,
        confirmButtonText: "Sí, contactar técnico",
        cancelButtonText: "Cancelar",
      }).then((result) => {
        if (!result.isConfirmed) return;

        fetch(`/tickets/ticket/${ticketId}/contactar_tecnico/`, {
          method: "POST",
          headers: {
            "X-CSRFToken":
              document.querySelector("[name=csrfmiddlewaretoken]").value,
          },
        })
          .then((resp) => resp.json())
          .then((res) => {
            if (res.ok) {
              if (formIA) {
                disableFormIA();
                formIA.style.display = "none";
              }
              if (iaOpciones) iaOpciones.style.display = "none";

              Swal.fire({
                icon: "success",
                title: "Un técnico fue notificado",
                text: "La IA ya no responderá más en este ticket.",
                confirmButtonText: "Entendido",
              });

              cargarMensajes();
              scrollChatToBottom();
            }
          });
      });
    });
  }
  */
});