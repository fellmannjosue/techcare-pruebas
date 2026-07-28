import './globals.css';

export const metadata = {
  title: 'Portal SuperUser – TechCare',
};

// <--- hecho por claude code: aplica el tema guardado ANTES de pintar (sin parpadeo),
// y carga los iconos Tabler (webfont) + la fuente Inter.
const noFlash = `(function(){try{var t=localStorage.getItem('tc-theme');
if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark');}}catch(e){}})();`;

export default function RootLayout({ children }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: noFlash }} />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
        <link href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.11.0/dist/tabler-icons.min.css" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}
