document.addEventListener("DOMContentLoaded", function () {
  // ---------- Lógica para mostrar/ocultar "Cargo" según área ----------
  const areaField = document.getElementById("id_area");
  const divCargo = document.getElementById("divCargo");
  function mostrarCargo() {
    if (!areaField) return;
    const area = areaField.value;
    if (area === "bilingue" || area === "colegio") {
      divCargo.style.display = "";
    } else {
      divCargo.style.display = "none";
      if (document.getElementById("id_cargo")) {
        document.getElementById("id_cargo").selectedIndex = 0;
      }
    }
  }
  if (areaField) {
    mostrarCargo();
    areaField.addEventListener("change", mostrarCargo);
  }

  // ---------- Modal de búsqueda de correos institucionales ----------
  const btnBuscarCorreo = document.getElementById("btnBuscarCorreo");
  const modal = new bootstrap.Modal(
    document.getElementById("modalBuscarCorreo")
  );
  const listaCorreos = document.getElementById("listaCorreos");
  const inputBuscarCorreo = document.getElementById("inputBuscarCorreo");
  const emailInput = document.getElementById("id_email");

  // <--- hecho por claude code: la lista viene del servidor (lista blanca), ya no fija
  let correosDisponibles = [];
  fetch("/accounts/register/correos-disponibles/", {credentials: "same-origin"})
    .then(function (r) { return r.json(); })
    .then(function (d) { correosDisponibles = d.correos || []; })
    .catch(function () { correosDisponibles = []; });

  function filtrarCorreos() {
    const filtro = inputBuscarCorreo.value.toLowerCase();
    listaCorreos.innerHTML = "";
    let encontrados = 0;
    correosDisponibles.forEach((correo) => {
      if (correo.toLowerCase().includes(filtro)) {
        const li = document.createElement("li");
        li.classList.add("list-group-item");
        li.textContent = correo;
        li.onclick = function () {
          emailInput.value = correo;
          modal.hide();
        };
        listaCorreos.appendChild(li);
        encontrados++;
      }
    });
    if (encontrados === 0) {
      const li = document.createElement("li");
      li.classList.add("list-group-item", "disabled");
      li.textContent = "No se encontraron correos";
      listaCorreos.appendChild(li);
    }
  }

  if (btnBuscarCorreo) {
    btnBuscarCorreo.addEventListener("click", function () {
      inputBuscarCorreo.value = "";
      filtrarCorreos();
      modal.show();
    });
  }

  if (inputBuscarCorreo) {
    inputBuscarCorreo.addEventListener("input", filtrarCorreos);
  }
});
