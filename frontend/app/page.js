'use client';
// <--- hecho por claude code: panel de Inventario de Cámaras.
// Todo el estado vive en React: el árbol, los filtros y el panel lateral se
// redibujan solos. No hay manipulación manual del DOM.
import { useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api';
import Arbol from './Arbol';
import PanelLateral from './PanelLateral';
import { Componentes, Mantenimiento } from './Catalogos';

const TARJETAS = [
  { k: 'servidores', t: 'Servidores', c: 'bg-blue-500',   i: 'M5 7h14M5 12h14M5 17h14' },
  { k: 'nvrs',       t: 'NVRs',       c: 'bg-indigo-500', i: 'M4 6h16v12H4z' },
  { k: 'gabinetes',  t: 'Gabinetes',  c: 'bg-teal-500',   i: 'M4 4h16v16H4z' },
  { k: 'camaras',    t: 'Cámaras',    c: 'bg-emerald-500',i: 'M15 10l4.5-2.5v9L15 14M4 6h11v12H4z' },
];

export default function Page() {
  const [datos, setDatos]   = useState(null);
  const [error, setError]   = useState('');
  const [busca, setBusca]   = useState('');
  const [sel, setSel]       = useState(null);   // {tipo, item}
  const [cargando, setCarg] = useState(true);
  const [vista, setVista] = useState('equipos');   // equipos | componentes | mantenimiento
  const [senal, setSenal] = useState(0);          // fuerza recarga de las listas

  async function recargar() {
    try { setCarg(true); setDatos(await api.resumen()); setError(''); }
    catch (e) { setError(e.message); }
    finally { setCarg(false); }
  }
  useEffect(() => { recargar(); }, []);

  // Filtro en vivo: recorre el árbol y deja solo lo que coincide
  const arbol = useMemo(() => {
    if (!datos) return [];
    const q = busca.trim().toLowerCase();
    if (!q) return datos.arbol;
    const coincide = (o) => JSON.stringify(o).toLowerCase().includes(q);
    return datos.arbol
      .map((s) => ({
        ...s,
        nvrs: s.nvrs
          .map((n) => ({
            ...n,
            gabinetes: n.gabinetes
              .map((g) => ({ ...g, camaras: g.camaras.filter((c) => coincide(c) || coincide(g)) }))
              .filter((g) => g.camaras.length || coincide(g)),
          }))
          .filter((n) => n.gabinetes.length || coincide(n)),
      }))
      .filter((s) => s.nvrs.length || coincide(s));
  }, [datos, busca]);

  const vacio = datos && datos.conteos.servidores === 0;

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <h1 className="text-lg font-semibold">Inventario de Cámaras</h1>
          <span className="text-xs px-2 py-0.5 rounded-full bg-marca-50 text-marca-700 font-medium">
            nuevo
          </span>
          <div className="ml-auto flex items-center gap-2">
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar servidor, NVR, gabinete o cámara…"
              className="w-72 max-w-[50vw] rounded-lg border border-slate-300 px-3 py-1.5 text-sm
                         focus:outline-none focus:ring-2 focus:ring-marca-500/30 focus:border-marca-500"
            />
            <a href="/inventario-camaras/"
               className="text-sm rounded-lg border border-slate-300 px-3 py-1.5 hover:bg-slate-50">
              Vista clásica
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-5">
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm">
            {error}
          </div>
        )}

        <section className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
          {TARJETAS.map((t) => (
            <div key={t.k} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
              <span className={`${t.c} text-white rounded-lg w-10 h-10 grid place-items-center shrink-0`}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
                  <path d={t.i} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <div>
                <div className="text-2xl font-bold leading-none">
                  {cargando ? '—' : datos.conteos[t.k]}
                </div>
                <div className="text-xs text-slate-500 mt-1">{t.t}</div>
              </div>
            </div>
          ))}
        </section>

        <nav className="flex gap-1 mb-4">
          {[['equipos', 'Equipos'], ['componentes', 'Componentes'], ['mantenimiento', 'Mantenimiento']].map(([k, t]) => (
            <button key={k} onClick={() => setVista(k)}
              className={`text-sm px-4 py-2 rounded-lg font-medium transition
                ${vista === k ? 'bg-white border border-slate-200 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
              {t}
              {k === 'mantenimiento' && datos?.conteos.mantenimientos > 0 && (
                <span className="ml-1.5 text-xs bg-slate-100 rounded-full px-1.5 py-0.5">
                  {datos.conteos.mantenimientos}
                </span>
              )}
            </button>
          ))}
        </nav>

        {vista === 'componentes' && <Componentes onEditar={setSel} recargarSenal={senal} />}
        {vista === 'mantenimiento' && <Mantenimiento onEditar={setSel} recargarSenal={senal} />}

        <div className={`bg-white rounded-xl border border-slate-200 ${vista === 'equipos' ? '' : 'hidden'}`}>
          <div className="px-4 py-3 border-b border-slate-200 flex items-center">
            <h2 className="font-semibold text-sm">Servidor → NVR → Gabinete → Cámara</h2>
            <div className="ml-auto flex items-center gap-3">
              <button onClick={() => setSel({ tipo: 'servidores', item: {} })}
                      className="text-sm rounded-lg bg-marca-600 text-white px-3 py-1.5 font-medium hover:bg-marca-700">
                + Servidor
              </button>
              <button onClick={recargar} className="text-sm text-marca-600 hover:text-marca-700 font-medium">
                Recargar
              </button>
            </div>
          </div>

          {cargando && <p className="p-8 text-center text-slate-400 text-sm">Cargando…</p>}

          {!cargando && vacio && (
            <div className="p-10 text-center">
              <p className="font-medium">Todavía no hay equipos registrados</p>
              <p className="text-sm text-slate-500 mt-1">
                Empieza agregando un servidor; luego sus NVRs, gabinetes y cámaras.
              </p>
              <button onClick={() => setSel({ tipo: 'servidores', item: {} })}
                      className="mt-4 rounded-lg bg-marca-600 text-white px-4 py-2 text-sm font-medium hover:bg-marca-700">
                Agregar servidor
              </button>
            </div>
          )}

          {!cargando && !vacio && (
            <Arbol datos={arbol} onSeleccionar={setSel} />
          )}
        </div>
      </main>

      {sel && (
        <PanelLateral
          seleccion={sel}
          onCerrar={() => setSel(null)}
          onGuardado={() => { setSel(null); recargar(); setSenal((n) => n + 1); }}
        />
      )}
    </div>
  );
}
