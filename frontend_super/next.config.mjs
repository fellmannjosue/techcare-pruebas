/** Build ESTÁTICO: HTML/JS/CSS que sirve Apache. Sin proceso Node en producción.
 *  <--- hecho por claude code: portal nuevo del superusuario. */
const nextConfig = {
  output: 'export',
  distDir: 'out',
  // Los assets los sirve Apache desde /static/portal_super/app
  assetPrefix: '/static/portal_super/app',
  images: { unoptimized: true },
  trailingSlash: false,
};
export default nextConfig;
