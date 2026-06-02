// <--- hecho por claude code: generador lorem ipsum
(function () {

  const WORDS = [
    'lorem','ipsum','dolor','sit','amet','consectetur','adipiscing','elit',
    'sed','do','eiusmod','tempor','incididunt','ut','labore','et','dolore',
    'magna','aliqua','enim','ad','minim','veniam','quis','nostrud','exercitation',
    'ullamco','laboris','nisi','aliquip','ex','ea','commodo','consequat',
    'duis','aute','irure','in','reprehenderit','voluptate','velit','esse',
    'cillum','eu','fugiat','nulla','pariatur','excepteur','sint','occaecat',
    'cupidatat','non','proident','sunt','culpa','qui','officia','deserunt',
    'mollit','anim','id','est','laborum','pellentesque','habitant','morbi',
    'tristique','senectus','netus','malesuada','fames','turpis','egestas',
    'venenatis','cras','ornare','arcu','dui','vivamus','arcu','felis','bibendum',
    'vitae','tortor','condimentum','lacinia','quis','vel','eros','donec',
    'ac','odio','tempor','orci','dapibus','ultrices','in','iaculis','nunc',
    'accumsan','lacus','vel','facilisis','volutpat','gravida','cum','sociis',
    'natoque','penatibus','magnis','dis','parturient','montes','nascetur',
    'ridiculus','mus','mauris','vitae','ultricies','leo','integer','malesuada',
    'nunc','vel','risus','commodo','viverra','maecenas','accumsan','lacus',
    'vel','facilisis','volutpat','est','velit','egestas','dui','id','ornare',
    'quam','viverra','orci','sagittis','eu','volutpat','odio','facilisis',
    'pulvinar','elementum','integer','enim','neque','volutpat','ac','tincidunt',
    'vitae','semper','quis','lectus','nulla','at','volutpat','diam','ut',
    'venenatis','tellus','in','metus','vulputate','eu','scelerisque',
    'feugiat','nisl','pretium','fusce','id','velit','ut','tortor'
  ];

  const LOREM_CLASSICO = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.';

  function rand(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function palabraRandom() {
    return WORDS[Math.floor(Math.random() * WORDS.length)];
  }

  function oracion() {
    const n = rand(8, 18);
    const ws = [];
    for (let i = 0; i < n; i++) ws.push(palabraRandom());
    return capitalize(ws.join(' ')) + '.';
  }

  function parrafo() {
    const n = rand(4, 7);
    const ss = [];
    for (let i = 0; i < n; i++) ss.push(oracion());
    return ss.join(' ');
  }

  function generarTexto(cantidad, tipo, clasico) {
    if (tipo === 'palabras') {
      const ws = [];
      for (let i = 0; i < cantidad; i++) ws.push(palabraRandom());
      let text = capitalize(ws.join(' ')) + '.';
      if (clasico && cantidad >= 5) {
        const extra = ws.slice(2).join(' ');
        text = 'Lorem ipsum dolor sit amet ' + (extra ? extra + '.' : '.');
      }
      return text;
    }

    if (tipo === 'oraciones') {
      const ss = [];
      for (let i = 0; i < cantidad; i++) ss.push(oracion());
      if (clasico) ss[0] = LOREM_CLASSICO;
      return ss.join(' ');
    }

    // párrafos
    const ps = [];
    for (let i = 0; i < cantidad; i++) ps.push(parrafo());
    if (clasico) {
      const resto = ps[0].split(' ').slice(10).join(' ');
      ps[0] = LOREM_CLASSICO + (resto ? ' ' + capitalize(resto) : '');
    }
    return ps.join('\n\n');
  }

  function contarStats(texto, tipo) {
    const palabras = texto.trim().split(/\s+/).length;
    const caracteres = texto.length;
    if (tipo === 'parrafos') {
      const ps = texto.trim().split(/\n\n+/).length;
      return `${ps} párrafo${ps !== 1 ? 's' : ''} · ${palabras} palabras · ${caracteres} caracteres`;
    }
    if (tipo === 'oraciones') {
      const ss = (texto.match(/[.!?]/g) || []).length;
      return `${ss} oración${ss !== 1 ? 'es' : ''} · ${palabras} palabras · ${caracteres} caracteres`;
    }
    return `${palabras} palabra${palabras !== 1 ? 's' : ''} · ${caracteres} caracteres`;
  }

  const btnGen    = document.getElementById('lorem-generar');
  const btnCopiar = document.getElementById('lorem-copiar');
  const output    = document.getElementById('lorem-output');
  const resultado = document.getElementById('lorem-resultado');
  const contador  = document.getElementById('lorem-contador');

  if (!btnGen) return;

  function generar() {
    const cantidad = Math.min(100, Math.max(1, parseInt(document.getElementById('lorem-cantidad').value) || 5));
    const tipo     = document.getElementById('lorem-tipo').value;
    const clasico  = document.getElementById('lorem-clasico').checked;
    const texto    = generarTexto(cantidad, tipo, clasico);
    output.value   = texto;
    contador.textContent = contarStats(texto, tipo);
    resultado.classList.remove('d-none');
  }

  btnGen.addEventListener('click', generar);
  generar();

  btnCopiar.addEventListener('click', function () {
    navigator.clipboard.writeText(output.value).then(function () {
      const orig = btnCopiar.innerHTML;
      btnCopiar.innerHTML = '<i class="ti ti-check me-1"></i>Copiado';
      btnCopiar.classList.replace('btn-outline-secondary', 'btn-success');
      setTimeout(function () {
        btnCopiar.innerHTML = orig;
        btnCopiar.classList.replace('btn-success', 'btn-outline-secondary');
      }, 1800);
    });
  });

})();
