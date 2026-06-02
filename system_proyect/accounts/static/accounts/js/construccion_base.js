// <--- hecho por claude code: lógica página En Construcción

// ── Código flotante en el fondo ───────────────────────────────────────────
const snippets = [
  'const data = []', 'def __init__(self):', 'return response', 'if (x > 0) {',
  'SELECT * FROM', 'import django', 'class Model:', 'await fetch(url)',
  'git commit -m', 'npm install', '<div class=', 'border-radius:',
  'for i in range:', 'console.log()', 'def save(self):', '// TODO:',
  'border: 1px', '@login_required', 'render(request,', '.objects.all()',
];
const bg = document.getElementById('code-bg');
for (let i = 0; i < 18; i++) {
  const el = document.createElement('span');
  el.className = 'code-line';
  el.textContent = snippets[i % snippets.length];
  el.style.left = (Math.random() * 95) + '%';
  el.style.animationDuration = (12 + Math.random() * 18) + 's';
  el.style.animationDelay = (Math.random() * 15) + 's';
  el.style.fontSize = (11 + Math.random() * 5) + 'px';
  bg.appendChild(el);
}

// ── Porcentaje dinámico ────────────────────────────────────────────────────
let pct = 15;
const lbl = document.getElementById('pct-label');
setInterval(() => {
  if (pct < 80) pct += (Math.random() * .3);
  lbl.textContent = Math.round(pct) + '%';
}, 400);

// ── Features chips ─────────────────────────────────────────────────────────
const wrap = document.getElementById('features-wrap');
const featuresRaw = wrap.dataset.features;
const features = featuresRaw ? JSON.parse(featuresRaw) : [];
features.forEach((f, i) => {
  const chip = document.createElement('span');
  chip.className = 'feature-chip';
  chip.style.animationDelay = (i * .1) + 's';
  chip.innerHTML = `<i class="ti ${f.icon}"></i> ${f.label}`;
  wrap.appendChild(chip);
});
