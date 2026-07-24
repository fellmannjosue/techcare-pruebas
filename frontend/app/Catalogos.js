'use client';
// <--- hecho por claude code: Componentes y Mantenimiento, que faltaban en la app.
import { useEffect, useState } from 'react';
import { api } from '../lib/api';

const ESTADOS = ['Pendiente', 'En Proceso', 'Completado'];
const COLOR_ESTADO = {
  'Pendiente':  'bg-amber-100 text-amber-700',
  'En Proceso': 'bg-blue-100 text-blue-700',
  'Completado': 'bg-emerald-100 text-emerald-700',
};

export function Componentes({ onEditar, recargarSenal }) {
  const [lista, setLista] = useState([]);
  const [carg, setCarg] = useState(true);
  useEffect(() => {
    api.listar('componentes').then((d) => { setLista(d); setCarg(false); }).catch(() => setCarg(false));
  }, [recargarSenal]);

  return (
    <div className="bg-white rounded-xl border border-slate-200">
      <div className="px-4 py-3 border-b border-slate-200 flex items-center">
        <h2 className="font-semibold text-sm">Catálogo de componentes</h2>
        <button onClick={() => onEditar({ tipo: 'componentes', item: {} })}
                className="ml-auto text-sm rounded-lg bg-marca-600 text-white px-3 py-1.5 font-medium hover:bg-marca-700">
          + Componente
        </button>
      </div>
      {carg && <p className="p-8 text-center text-slate-400 text-sm">Cargando…</p>}
      {!carg && !lista.length && (
        <p className="p-8 text-center text-slate-400 text-sm">Sin componentes en el catálogo.</p>
      )}
      {!carg && lista.map((c) => (
        <div key={c.id} className="flex items-center gap-3 px-4 py-2 border-b border-slate-100 hover:bg-slate-50">
          <span className="font-mono text-xs text-slate-400">{c.comp_id}</span>
          <span className="text-sm font-medium">{c.detalle}</span>
          {c.sub_detalle && <span className="text-xs text-slate-500">{c.sub_detalle}</span>}
          <button onClick={() => onEditar({ tipo: 'componentes', item: c })}
                  className="ml-auto text-xs text-marca-600 hover:text-marca-700 font-medium">Editar</button>
        </div>
      ))}
    </div>
  );
}

export function Mantenimiento({ onEditar, recargarSenal }) {
  const [lista, setLista] = useState([]);
  const [filtro, setFiltro] = useState('');
  const [carg, setCarg] = useState(true);

  useEffect(() => {
    setCarg(true);
    api.listar('mantenimientos', filtro ? `status=${encodeURIComponent(filtro)}` : '')
      .then((d) => { setLista(d); setCarg(false); }).catch(() => setCarg(false));
  }, [filtro, recargarSenal]);

  return (
    <div className="bg-white rounded-xl border border-slate-200">
      <div className="px-4 py-3 border-b border-slate-200 flex items-center flex-wrap gap-2">
        <h2 className="font-semibold text-sm">Fichas de mantenimiento</h2>
        <div className="flex gap-1 ml-3">
          {['', ...ESTADOS].map((e) => (
            <button key={e || 'todos'} onClick={() => setFiltro(e)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition
                ${filtro === e ? 'bg-marca-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
              {e || 'Todas'}
            </button>
          ))}
        </div>
        <button onClick={() => onEditar({ tipo: 'mantenimientos', item: {} })}
                className="ml-auto text-sm rounded-lg bg-marca-600 text-white px-3 py-1.5 font-medium hover:bg-marca-700">
          + Ficha
        </button>
      </div>
      {carg && <p className="p-8 text-center text-slate-400 text-sm">Cargando…</p>}
      {!carg && !lista.length && (
        <p className="p-8 text-center text-slate-400 text-sm">
          {filtro ? `Sin fichas en estado "${filtro}".` : 'Todavía no hay fichas de mantenimiento.'}
        </p>
      )}
      {!carg && lista.map((m) => (
        <div key={m.id} className="flex items-center gap-3 px-4 py-2.5 border-b border-slate-100 hover:bg-slate-50">
          <span className="font-mono text-xs text-slate-400 shrink-0">{m.record_id}</span>
          <div className="min-w-0">
            <div className="text-sm font-medium truncate">{m.modelo || 'Sin modelo'}</div>
            <div className="text-xs text-slate-500 truncate">
              {[m.ubicacion, m.tipo_falla_nombre].filter(Boolean).join(' · ') || '—'}
            </div>
          </div>
          <span className="text-xs text-slate-500 ml-auto shrink-0">{m.date}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${COLOR_ESTADO[m.status] || 'bg-slate-100'}`}>
            {m.status}
          </span>
          <button onClick={() => onEditar({ tipo: 'mantenimientos', item: m })}
                  className="text-xs text-marca-600 hover:text-marca-700 font-medium shrink-0">Editar</button>
        </div>
      ))}
    </div>
  );
}
