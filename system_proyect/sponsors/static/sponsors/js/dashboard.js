/* dashboard.js – sponsors module */

function redirectWithAlert(url, section) {
  Swal.fire({
    title: "Redirigiendo...",
    text: "Cargando " + section,
    icon: "info",
    showConfirmButton: false,
    timer: 1200
  }).then(() => { window.location.href = url; });
}
