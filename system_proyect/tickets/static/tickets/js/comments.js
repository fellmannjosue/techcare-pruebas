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
  let lastMsgCount   = 0;

  // Sonido al llegar un mensaje nuevo (reusa el audio global #notifSound)
  function reproducirSonidoChat() {
    var audio = document.getElementById("notifSound");
    if (!audio) return;
    try { audio.currentTime = 0; audio.volume = 0.6; audio.play().catch(function () {}); } catch (e) {}
  }

  // ── Adjuntos (copy-paste / subir / adjuntar) ──
  let pendingFile = null;
  const fileImg   = document.getElementById("chat-file-img");
  const fileDoc   = document.getElementById("chat-file-doc");
  const previewBox = document.getElementById("chat-attach-preview");

  function renderPreview() {
    if (!previewBox) return;
    if (!pendingFile) { previewBox.classList.add("d-none"); previewBox.innerHTML = ""; return; }
    previewBox.classList.remove("d-none");
    let media = '<i class="ti ti-file-text chat-attach-fileicon"></i>';
    if (pendingFile.type && pendingFile.type.startsWith("image/")) {
      media = `<img src="${URL.createObjectURL(pendingFile)}" class="chat-attach-thumb" alt="">`;
    }
    const kb = Math.max(1, Math.round(pendingFile.size / 1024));
    previewBox.innerHTML =
      `<div class="chat-attach-chip">${media}` +
      `<span class="chat-attach-fname">${pendingFile.name}</span>` +
      `<span class="chat-attach-size">${kb} KB</span>` +
      `<button type="button" class="btn-close ms-2" id="btn-attach-remove" aria-label="Quitar"></button></div>`;
    const rm = document.getElementById("btn-attach-remove");
    if (rm) rm.addEventListener("click", clearPending);
  }
  function clearPending() {
    pendingFile = null;
    if (fileImg) fileImg.value = "";
    if (fileDoc) fileDoc.value = "";
    renderPreview();
  }
  // Redimensiona/comprime imágenes en el navegador (auto-ajuste, más liviano).
  function resizeImage(file, maxDim, quality) {
    return new Promise(function (resolve) {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = function () {
        let w = img.naturalWidth, h = img.naturalHeight;
        if (w > maxDim || h > maxDim) {
          if (w >= h) { h = Math.round(h * maxDim / w); w = maxDim; }
          else { w = Math.round(w * maxDim / h); h = maxDim; }
        }
        const canvas = document.createElement("canvas");
        canvas.width = w; canvas.height = h;
        canvas.getContext("2d").drawImage(img, 0, 0, w, h);
        URL.revokeObjectURL(url);
        canvas.toBlob(function (blob) {
          if (!blob) { resolve(file); return; }
          const base = (file.name || "imagen").replace(/\.[^.]+$/, "");
          resolve(new File([blob], base + ".jpg", { type: "image/jpeg" }));
        }, "image/jpeg", quality);
      };
      img.onerror = function () { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    });
  }

  async function setFile(f) {
    if (!f) return;
    if (f.type && f.type.startsWith("image/")) {
      try { f = await resizeImage(f, 1280, 0.8); } catch (e) { /* usa original */ }
    }
    if (f.size > 15 * 1024 * 1024) { alert("El archivo supera el límite de 15 MB."); return; }
    pendingFile = f;
    renderPreview();
  }

  const btnImg   = document.getElementById("btn-attach-img");
  const btnDoc   = document.getElementById("btn-attach-doc");
  const btnPaste = document.getElementById("btn-attach-paste");
  if (btnImg && fileImg) btnImg.addEventListener("click", () => fileImg.click());
  if (btnDoc && fileDoc) btnDoc.addEventListener("click", () => fileDoc.click());
  if (fileImg) fileImg.addEventListener("change", function () { if (this.files[0]) setFile(this.files[0]); });
  if (fileDoc) fileDoc.addEventListener("change", function () { if (this.files[0]) setFile(this.files[0]); });
  if (btnPaste) btnPaste.addEventListener("click", async function () {
    try {
      const items = await navigator.clipboard.read();
      for (const it of items) {
        const t = it.types.find(x => x.startsWith("image/"));
        if (t) { const blob = await it.getType(t); setFile(new File([blob], "pegado.png", { type: blob.type })); return; }
      }
      alert("No hay ninguna imagen en el portapapeles.");
    } catch (e) {
      alert("Tu navegador no permite leer el portapapeles. Copia la imagen y pégala con Ctrl+V dentro del cuadro de texto.");
    }
  });

  // ── Textarea: auto-resize + Enter para enviar + pegar imagen ──
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
    ta.addEventListener("paste", function (e) {
      const items = e.clipboardData && e.clipboardData.items;
      if (!items) return;
      for (const it of items) {
        if (it.type && it.type.startsWith("image/")) {
          const blob = it.getAsFile();
          if (blob) { setFile(new File([blob], "pegado.png", { type: blob.type })); e.preventDefault(); }
          return;
        }
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
    ["btn-attach-img", "btn-attach-doc", "btn-attach-paste"].forEach(function (id) {
      const b = document.getElementById(id); if (b) b.disabled = true;
    });
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

        // Sonido si llegó un mensaje nuevo entrante (no el mío)
        const bubbles = chatDiv.querySelectorAll('.chat-bubble');
        const count = bubbles.length;
        if (!primeraVez && count > lastMsgCount) {
          const last = bubbles[bubbles.length - 1];
          if (last && !last.classList.contains('bubble-me')) reproducirSonidoChat();
        }
        lastMsgCount = count;

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
    const fileToSend = pendingFile;

    if (!mensaje && !fileToSend) return;
    if (btn && btn.disabled) return;

    // Deshabilitar botón y limpiar entrada INMEDIATAMENTE
    if (btn) btn.disabled = true;
    resetTextarea();
    clearPending();

    const fd = new FormData();
    fd.append("mensaje", mensaje);
    if (fileToSend) fd.append("archivo", fileToSend, fileToSend.name);

    fetch(`/tickets/ticket_send_comment_ajax/${ticketId}/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrf ? csrf.value : "",
        "X-Requested-With": "XMLHttpRequest",
        // No fijar Content-Type: el navegador define el boundary multipart.
      },
      body: fd,
    })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(res => {
        if (res.ok) {
          lastHtml = null;
          cargarMensajes();
        } else {
          // Restaurar si el servidor rechazó
          if (ta) ta.value = mensaje;
          if (fileToSend) { pendingFile = fileToSend; renderPreview(); }
          if (res.error) alert(res.error);
        }
      })
      .catch(() => {
        if (ta) ta.value = mensaje;
        if (fileToSend) { pendingFile = fileToSend; renderPreview(); }
        alert("No se pudo enviar. Intenta de nuevo o con un archivo más pequeño.");
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
