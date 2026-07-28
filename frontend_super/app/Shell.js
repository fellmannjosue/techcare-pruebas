'use client';
// <--- hecho por claude code: layout empresarial (sidebar + topbar) del portal.
import { useState } from 'react';
import { Icon } from './ui';

function NavItem({ it, active, collapsed, onNavigate }) {
  const base = `group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors`;
  const inner = (
    <>
      <Icon name={it.icon} className="text-lg shrink-0" style={{ width: 20 }} />
      <span className={`truncate transition-all ${collapsed ? 'opacity-0 w-0' : 'opacity-100'}`}>{it.label}</span>
      {collapsed && (
        <span className="pointer-events-none absolute left-full ml-3 whitespace-nowrap rounded-md px-2 py-1 text-xs
                         opacity-0 group-hover:opacity-100 transition-opacity z-50"
              style={{ background: '#0b1020', color: '#e6eaf3', boxShadow: '0 6px 20px rgba(0,0,0,.4)' }}>
          {it.label}
        </span>
      )}
    </>
  );
  const cls = active
    ? `${base} text-white`
    : `${base}`;
  const style = active
    ? { background: 'linear-gradient(135deg,#4f46e5,#6366f1)', boxShadow: '0 6px 16px -6px rgba(79,70,229,.6)' }
    : { color: 'var(--sidebar-fg)' };
  if (it.spa) {
    return (
      <button type="button" onClick={() => onNavigate(it.spa)} className={cls} style={style}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,.06)'; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}>
        {inner}
        {active && <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-1 rounded-r bg-white/90" />}
      </button>
    );
  }
  return (
    <a href={it.href} className={cls} style={style}
       onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,.06)'; }}
       onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}>
      {inner}
      {!collapsed && <Icon name="ti-external-link" className="ml-auto text-xs opacity-40" />}
    </a>
  );
}

export default function Shell({ nav, vista, onNavigate, dark, onToggleDark, onClasica,
                                usuario, breadcrumb, children }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const W = collapsed ? 76 : 264;

  const Sidebar = (
    <aside className="flex flex-col h-full text-sm" style={{ width: W, background: 'var(--sidebar-bg)', transition: 'width .22s cubic-bezier(.4,0,.2,1)' }}>
      {/* Marca */}
      <div className="flex items-center gap-2 h-16 px-4 shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,.06)' }}>
        <div className="grid place-items-center rounded-lg shrink-0" style={{ width: 34, height: 34, background: 'linear-gradient(135deg,#4f46e5,#6366f1)' }}>
          <Icon name="ti-shield-bolt" className="text-white text-lg" />
        </div>
        {!collapsed && <div className="leading-tight">
          <div className="font-bold text-white">TechCare</div>
          <div className="text-[.65rem]" style={{ color: 'var(--sidebar-fg-muted)' }}>Portal SuperUser</div>
        </div>}
      </div>

      {/* Navegación */}
      <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
        {nav.map(g => (
          <div key={g.key}>
            {g.titulo && !collapsed && (
              <div className="px-3 mb-1 text-[.62rem] font-semibold uppercase tracking-wider" style={{ color: 'var(--sidebar-fg-muted)' }}>{g.titulo}</div>
            )}
            {g.titulo && collapsed && <div className="mx-3 my-2 h-px" style={{ background: 'rgba(255,255,255,.06)' }} />}
            <div className="space-y-.5">
              {g.items.map(it => (
                <NavItem key={it.label} it={it} collapsed={collapsed}
                         active={it.spa && it.spa === vista}
                         onNavigate={(v) => { onNavigate(v); setMobileOpen(false); }} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Pie: usuario + volver a clásica */}
      <div className="p-3 shrink-0" style={{ borderTop: '1px solid rgba(255,255,255,.06)' }}>
        <button onClick={onClasica}
                className="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                style={{ color: 'var(--sidebar-fg-muted)' }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,.06)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
          <Icon name="ti-arrow-back-up" className="text-lg shrink-0" style={{ width: 20 }} />
          {!collapsed && <span>Interfaz clásica</span>}
        </button>
      </div>
    </aside>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar escritorio */}
      <div className="hidden lg:block shrink-0">{Sidebar}</div>

      {/* Drawer móvil/tablet */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0">{Sidebar}</div>
        </div>
      )}

      {/* Columna principal */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="h-16 shrink-0 flex items-center gap-3 px-4 tc-surface" style={{ borderBottom: '1px solid var(--border)' }}>
          <button className="hidden lg:grid place-items-center rounded-lg h-9 w-9 tc-muted hover:tc-text transition"
                  style={{ background: 'var(--surface-2)' }} onClick={() => setCollapsed(c => !c)} title="Colapsar menú">
            <Icon name={collapsed ? 'ti-layout-sidebar-left-expand' : 'ti-layout-sidebar-left-collapse'} className="text-lg" />
          </button>
          <button className="lg:hidden grid place-items-center rounded-lg h-9 w-9 tc-muted"
                  style={{ background: 'var(--surface-2)' }} onClick={() => setMobileOpen(true)}>
            <Icon name="ti-menu-2" className="text-lg" />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-sm min-w-0">
            <span className="tc-muted">Portal</span>
            <Icon name="ti-chevron-right" className="tc-muted text-xs" />
            <span className="tc-text font-semibold truncate">{breadcrumb}</span>
          </div>

          {/* Buscador */}
          <div className="ml-auto hidden md:flex items-center gap-2 rounded-lg px-3 h-9 w-64"
               style={{ background: 'var(--surface-2)' }}>
            <Icon name="ti-search" className="tc-muted text-sm" />
            <input placeholder="Buscar…" className="bg-transparent outline-none text-sm w-full tc-text" />
            <kbd className="tc-muted text-[.62rem] px-1.5 rounded border tc-border">⌘K</kbd>
          </div>

          {/* Tema */}
          <button onClick={onToggleDark} title="Cambiar tema"
                  className="grid place-items-center rounded-lg h-9 w-9 tc-muted hover:tc-text transition"
                  style={{ background: 'var(--surface-2)' }}>
            <Icon name={dark ? 'ti-sun' : 'ti-moon'} className="text-lg" />
          </button>

          {/* Avatar */}
          <div className="flex items-center gap-2 pl-1">
            <div className="grid place-items-center rounded-full h-9 w-9 text-white font-semibold text-sm shrink-0"
                 style={{ background: 'linear-gradient(135deg,#4f46e5,#6366f1)' }}>
              {(usuario?.nombre || 'S').slice(0, 1).toUpperCase()}
            </div>
            <div className="hidden xl:block leading-tight">
              <div className="tc-text text-sm font-semibold truncate max-w-[10rem]">{usuario?.nombre || 'SuperUser'}</div>
              <div className="tc-muted text-xs truncate max-w-[10rem]">{usuario?.email || ''}</div>
            </div>
          </div>
        </header>

        {/* Contenido */}
        <main className="flex-1 overflow-y-auto tc-bg">
          <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
