/* <--- hecho por claude code (06-nov-2026): utilidades compartidas de las planillas de Ingreso de Notas (diseños A).
   Promedios por fila y por columna que se recalculan en vivo y burbuja «guardado ✓». Un solo global: TC_PLANILLA. */
var TC_PLANILLA = (function () {
  function num(v) {
    v = String(v == null ? '' : v).trim().replace(',', '.');
    if (v === '' || isNaN(v)) return null;
    return parseFloat(v);
  }
  function prom(lista) {
    var n = lista.filter(function (x) { return x !== null; });
    if (!n.length) return null;
    return n.reduce(function (a, b) { return a + b; }, 0) / n.length;
  }
  function fmt(x) { return x === null ? '—' : (Math.round(x * 10) / 10).toString(); }
  // marca en rojo las casillas por debajo del mínimo
  function marcarBajas(cont, selector, minimo) {
    cont.querySelectorAll(selector).forEach(function (inp) {
      var v = num(inp.value);
      inp.classList.toggle('celda-baja', v !== null && v < minimo);
    });
  }
  // burbuja breve junto a la casilla guardada (o con el motivo, si el servidor la rechazó)
  function burbuja(inp, texto, esError) {
    var td = inp.closest('td'); if (!td) return;
    var vieja = td.querySelector('.tc-guardado'); if (vieja) vieja.remove();
    var b = document.createElement('span');
    b.className = 'tc-guardado' + (esError ? ' tc-guardado-error' : '');
    b.textContent = texto || 'guardado ✓';
    td.style.position = 'relative'; td.appendChild(b);
    setTimeout(function () { b.remove(); }, esError ? 4500 : 1300);
  }
  // <--- hecho por claude code (06-nov-2026): si el servidor rechaza, lo escrito NO se borra: queda en rojo con el motivo
  function rechazo(inp, msg) {
    inp.classList.remove('celda-guardando', 'celda-ok');
    inp.classList.add('celda-error');
    inp.title = 'No se guardó: ' + msg;
    if (inp.value.trim() === '') inp.value = inp.dataset.antes || '';   // borrar no se permite: vuelve lo que había
    burbuja(inp, 'no se guardó', true);
  }
  return { num: num, prom: prom, fmt: fmt, marcarBajas: marcarBajas, burbuja: burbuja, rechazo: rechazo };
})();

// <--- hecho por claude code (06-nov-2026): regla del usuario — solo ENTEROS: exámenes 1-100, tareas y hábitos 1-10.
// Se borra todo lo que no sea dígito mientras se escribe; fuera de rango queda en rojo (el servidor también lo rechaza).
(function () {
  var REGLAS = [
    { sel: '.celda-nota', min: 1, max: 100 },
    { sel: '.celda-tarea[data-campo="puntos"]', min: 1, max: 10 },
    { sel: '.celda-habito[data-campo="puntos"]', min: 1, max: 10 }
  ];
  function regla(el) { for (var i = 0; i < REGLAS.length; i++) if (el.matches && el.matches(REGLAS[i].sel)) return REGLAS[i]; return null; }
  document.addEventListener('input', function (e) {
    var r = regla(e.target); if (!r) return;
    var el = e.target, limpio = el.value.replace(/\D/g, '').slice(0, String(r.max).length);
    if (limpio !== el.value) el.value = limpio;
    var v = limpio === '' ? null : parseInt(limpio, 10), mal = v !== null && (v < r.min || v > r.max);
    el.classList.toggle('celda-error', mal);
    el.title = mal ? 'Solo números enteros de ' + r.min + ' a ' + r.max : '';
  }, true);
  document.addEventListener('focusin', function (e) {
    var r = regla(e.target); if (!r) return;
    e.target.setAttribute('inputmode', 'numeric'); e.target.setAttribute('maxlength', String(r.max).length);
  }, true);
})();
