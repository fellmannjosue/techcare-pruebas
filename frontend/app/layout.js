import './globals.css';

export const metadata = {
  title: 'Inventario de Cámaras – TechCare',
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body className="antialiased text-slate-800">{children}</body>
    </html>
  );
}
