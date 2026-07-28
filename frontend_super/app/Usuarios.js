'use client';
// <--- hecho por claude code: módulo Usuarios y Roles (lectura en Fase 1;
// el "nivel" se deriva de is_superuser/is_staff — multi-admin solo-UI).
import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Card, Icon, Badge, Skeleton, EmptyState } from './ui';

const NIVEL = {
  superuser: { label: 'SuperUser', color: 'amber', icon: 'ti-crown' },
  staff:     { label: 'Staff', color: 'blue', icon: 'ti-user-shield' },
  usuario:   { label: 'Usuario', color: 'slate', icon: 'ti-user' },
};

export default function Usuarios() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [nivel, setNivel] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let vivo = true;
    setLoading(true);
    const t = setTimeout(() => {
      api.usuarios(q, nivel)
        .then(d => { if (vivo) { setData(d); setError(''); } })
        .catch(e => { if (vivo) setError(e.message); })
        .finally(() => { if (vivo) setLoading(false); });
    }, q ? 250 : 0);
    return () => { vivo = false; clearTimeout(t); };
  }, [q, nivel]);

  const filtros = [
    { k: '', label: 'Todos' },
    { k: 'superuser', label: 'SuperUsers' },
    { k: 'staff', label: 'Staff' },
    { k: 'usuario', label: 'Usuarios' },
    { k: 'inactivo', label: 'Inactivos' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="tc-text text-2xl font-bold tracking-tight">Usuarios y Roles</h1>
          <p className="tc-muted text-sm mt-1">{data ? `${data.total} usuarios` : 'Gestión de accesos'} · niveles según permisos actuales</p>
        </div>
        <a href="/accounts/settings/usuarios/" className="inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-semibold text-white"
           style={{ background: 'linear-gradient(135deg,#4f46e5,#6366f1)' }}>
          <Icon name="ti-settings" /> Gestión avanzada
        </a>
      </div>

      {/* Barra: buscador + filtros */}
      <Card className="p-3 flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 rounded-lg px-3 h-9 flex-1 min-w-[200px]" style={{ background: 'var(--surface-2)' }}>
          <Icon name="ti-search" className="tc-muted text-sm" />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Buscar por nombre, usuario o correo…"
                 className="bg-transparent outline-none text-sm w-full tc-text" />
          {q && <button onClick={() => setQ('')} className="tc-muted"><Icon name="ti-x" /></button>}
        </div>
        <div className="flex items-center gap-1 rounded-lg p-1" style={{ background: 'var(--surface-2)' }}>
          {filtros.map(f => (
            <button key={f.k} onClick={() => setNivel(f.k)}
                    className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${nivel === f.k ? 'text-white' : 'tc-muted'}`}
                    style={nivel === f.k ? { background: 'linear-gradient(135deg,#4f46e5,#6366f1)' } : {}}>
              {f.label}
            </button>
          ))}
        </div>
      </Card>

      {error && (
        <Card className="p-4 flex items-center gap-3" style={{ borderColor: '#f43f5e55' }}>
          <Icon name="ti-alert-circle" className="text-rose-500 text-xl" /><div className="tc-text text-sm">{error}</div>
        </Card>
      )}

      {/* Tabla */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left" style={{ background: 'var(--surface-2)' }}>
                <th className="px-4 py-3 tc-muted font-semibold text-xs uppercase tracking-wide">Usuario</th>
                <th className="px-4 py-3 tc-muted font-semibold text-xs uppercase tracking-wide">Nivel</th>
                <th className="px-4 py-3 tc-muted font-semibold text-xs uppercase tracking-wide">Roles</th>
                <th className="px-4 py-3 tc-muted font-semibold text-xs uppercase tracking-wide">Estado</th>
                <th className="px-4 py-3 tc-muted font-semibold text-xs uppercase tracking-wide">Último acceso</th>
              </tr>
            </thead>
            <tbody>
              {loading ? [...Array(8)].map((_, i) => (
                <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                  <td className="px-4 py-3" colSpan={5}><Skeleton className="h-8" /></td>
                </tr>
              )) : (data?.usuarios?.length ? data.usuarios.map(u => {
                const n = NIVEL[u.nivel] || NIVEL.usuario;
                return (
                  <tr key={u.id} className="transition-colors" style={{ borderTop: '1px solid var(--border)' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="grid place-items-center rounded-full h-9 w-9 text-white text-xs font-semibold shrink-0"
                             style={{ background: u.activo ? 'linear-gradient(135deg,#4f46e5,#6366f1)' : 'linear-gradient(135deg,#94a3b8,#cbd5e1)' }}>
                          {(u.nombre || '?').slice(0, 1).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="tc-text font-medium truncate">{u.nombre}</div>
                          <div className="tc-muted text-xs truncate">{u.email || u.username}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3"><Badge color={n.color}><Icon name={n.icon} /> {n.label}</Badge></td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {u.roles.length ? u.roles.slice(0, 3).map(r => (
                          <span key={r} className="text-xs px-2 py-.5 rounded-md tc-muted" style={{ background: 'var(--surface-2)' }}>{r}</span>
                        )) : <span className="tc-muted text-xs">—</span>}
                        {u.roles.length > 3 && <span className="text-xs tc-muted">+{u.roles.length - 3}</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3">{u.activo ? <Badge color="green">Activo</Badge> : <Badge color="red">Suspendido</Badge>}</td>
                    <td className="px-4 py-3 tc-muted text-xs whitespace-nowrap">{u.ultimo_acceso}</td>
                  </tr>
                );
              }) : (
                <tr><td colSpan={5}><EmptyState icon="ti-users" title="Sin resultados" subtitle="Prueba con otro término o filtro." /></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <p className="tc-muted text-xs flex items-center gap-1.5">
        <Icon name="ti-info-circle" /> En esta fase el listado es de solo lectura. Crear/editar/suspender se hará desde aquí en la siguiente entrega (o desde <a className="underline" href="/accounts/settings/usuarios/">Gestión avanzada</a>).
      </p>
    </div>
  );
}
