/** Build ESTÁTICO: genera HTML/JS/CSS que sirve Apache.
 *  No hay proceso Node en producción.  <--- hecho por claude code */
const nextConfig = {
  output: 'export',
  distDir: 'out',
  // Los assets los sirve Apache desde /static/
  assetPrefix: '/static/inventario_camaras/app',
  images: { unoptimized: true },
  trailingSlash: false,
};
export default nextConfig;
