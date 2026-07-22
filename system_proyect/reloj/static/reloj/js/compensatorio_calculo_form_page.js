/* compensatorio_calculo_form_page.js — <--- hecho por claude code: extraído del template.
   Los datos de Django llegan por la isla JSON #compensatorio_calculo_form-data. */
window._PAGE = JSON.parse(document.getElementById('compensatorio_calculo_form-data').textContent);

// empMap se arma desde los pares (evita comas finales inválidas en JSON)
window._PAGE.empMap = {};
(window._PAGE.empPairs || []).forEach(function(p){ if (p[0]) window._PAGE.empMap[p[0]] = p[1]; });


