'use client';
// <--- hecho por claude code: controlador de la SPA del portal SuperUser.
import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import Shell from './Shell';
import Dashboard from './Dashboard';
import Usuarios from './Usuarios';

const TITULOS = { dashboard: 'Dashboard', usuarios: 'Usuarios y Roles' };

export default function Page() {
  const [nav, setNav] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [vista, setVista] = useState('dashboard');
  const [dark, setDark] = useState(false);

  // Tema (leído del layout no-flash; sincronizamos el estado)
  useEffect(() => {
    setDark(document.documentElement.classList.contains('dark'));
  }, []);

  function toggleDark() {
    setDark(d => {
      const nuevo = !d;
      document.documentElement.classList.toggle('dark', nuevo);
      try { localStorage.setItem('tc-theme', nuevo ? 'dark' : 'light'); } catch (e) {}
      return nuevo;
    });
  }

  // Carga inicial: navegación + resumen
  useEffect(() => {
    api.nav().then(d => setNav(d.grupos || [])).catch(() => {});
    api.resumen()
      .then(d => { setResumen(d); setError(''); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function volverClasica() {
    api.usarClasica().catch(() => {}).finally(() => { window.location.href = '/accounts/menu/'; });
  }

  return (
    <Shell
      nav={nav}
      vista={vista}
      onNavigate={setVista}
      dark={dark}
      onToggleDark={toggleDark}
      onClasica={volverClasica}
      usuario={resumen?.usuario}
      breadcrumb={TITULOS[vista]}
    >
      {vista === 'dashboard' && <Dashboard data={resumen} loading={loading} error={error} />}
      {vista === 'usuarios' && <Usuarios />}
    </Shell>
  );
}
