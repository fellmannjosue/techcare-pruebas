// Genera build/icon.ico (que necesita Windows) a partir de build/icon.png (el logo de ANA).
// Se corre en el build (también en la GitHub Action), así no hace falta ImageMagick.
const fs = require('fs');
const path = require('path');
const pngToIco = require('png-to-ico');

const src = path.join(__dirname, '..', 'build', 'icon.png');
const out = path.join(__dirname, '..', 'build', 'icon.ico');

pngToIco(src)
  .then((buf) => { fs.writeFileSync(out, buf); console.log('✔ icon.ico generado'); })
  .catch((err) => { console.error('✖ error generando icon.ico:', err); process.exit(1); });
