'use client';
// <--- hecho por claude code: alta/edición en panel lateral, sin cambiar de página.
import { useEffect, useState } from 'react';
import { api } from '../lib/api';

const CAMPOS = {
  servidores: [
    { n: 'nombre', t: 'Nombre', req: true },
    { n: 'ubicacion', t: 'Ubicación' },
    { n: 'ip', t: 'IP' },
    { n: 'observaciones', t: 'Observaciones', area: true },
  ],
  nvrs: [
    { n: 'nombre', t: 'Nombre', req: true },
    { n: 'modelo', t: 'Modelo' },
    { n: 'serie', t: 'Serie' },
    { n: 'ip', t: 'IP' },
    { n: 'canales', t: 'Canales', num: true },
    { n: 'observaciones', t: 'Observaciones', area: true },
  ],
  gabinetes: [
    { n: 'nombre', t: 'Gabinete', req: true },
    { n: 'ubicacion', t: 'Ubicación' },
    { n: 'observaciones', t: 'Observaciones', area: true },
  ],
  camaras: [
    { n: 'modelo', t: 'Modelo', req: true },
    { n: 'serie', t: 'Serie' },
    { n: 'ubicacion', t: 'Ubicación' },
    { n: 'estado', t: 'Estado' },
    { n: 'version_actualizada', t: 'Versión' },
    { n: 'observaciones', t: 'Observaciones', area: true },
  ],
  componentes: [
    { n: 'detalle', t: 'Detalle', req: true },
    { n: 'sub_detalle', t: 'Sub detalle' },
  ],
  mantenimientos: [
    { n: 'modelo', t: 'Modelo' },
    { n: 'serie', t: 'Serie' },
    { n: 'ubicacion', t: 'Ubicación' },
    { n: 'date', t: 'Fecha', req: true, tipo: 'date' },
    { n: 'status', t: 'Estado', opciones: ['Pendiente', 'En Proceso', 'Completado'] },
    { n: 'tipo_falla', t: 'Tipo de falla', ref: 'tipos-falla', etiqueta: 'nombre' },
    { n: 'solucion', t: 'Solución aplicada', area: true },
    { n: 'responsable_nombre', t: 'Responsable' },
    { n: 'tecnico_nombre', t: 'Técnico' },
    { n: 'observaciones', t: 'Observaciones', area: true },
  ],
};
const TITULOS = { servidores: 'Servidor', nvrs: 'NVR', gabinetes: 'Gabinete', camaras: 'Cámara',
                  componentes: 'Componente', mantenimientos: 'Ficha de mantenimiento' };

export default function PanelLateral({ seleccion, onCerrar, onGuardado }) {
  const { tipo, item, padre } = seleccion;
  const campos = CAMPOS[tipo] || [];
  const esNuevo = !item?.id;
  const [valores, setValores] = useState({});
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');
  const [refs, setRefs] = useState({});   // opciones traídas de la API (ej. tipos de falla)

  useEffect(() => {
    const v = {};
    campos.forEach((c) => { v[c.n] = item?.[c.n] ?? ''; });
    setValores(v);
    setError('');
    // carga las listas de referencia que necesite este formulario
    campos.filter((c) => c.ref).forEach((c) => {
      api.listar(c.ref).then((d) => setRefs((r) => ({ ...r, [c.n]: d }))).catch(() => {});
    });
  }, [seleccion]);   // eslint-disable-line

  const faltantes = campos.filter((c) => c.req && !String(valores[c.n] || '').trim());

  async function guardar() {
    if (faltantes.length) { setError(`Falta: ${faltantes.map((c) => c.t).join(', ')}`); return; }
    setGuardando(true); setError('');
    try {
      const limpio = {};
      campos.forEach((c) => {
        const v = valores[c.n];
        limpio[c.n] = c.num ? (v === '' ? null : Number(v)) : (v ?? '');
      });
      // <--- hecho por claude code: al crear desde el árbol, se enlaza al padre
      if (padre) limpio[padre.campo] = padre.id;
      if (esNuevo) await api.crear(tipo, limpio);
      else await api.actualizar(tipo, item.id, limpio);
      onGuardado();
    } catch (e) { setError(e.message); }
    finally { setGuardando(false); }
  }

  async function eliminar() {
    if (!confirm(`¿Eliminar este ${TITULOS[tipo].toLowerCase()}? No se puede deshacer.`)) return;
    setGuardando(true);
    try { await api.eliminar(tipo, item.id); onGuardado(); }
    catch (e) { setError(e.message); setGuardando(false); }
  }

  return (
    <div className="fixed inset-0 z-20 flex justify-end">
      <div className="absolute inset-0 bg-slate-900/30" onClick={onCerrar} />
      <aside className="relative bg-white w-full max-w-md h-full shadow-2xl flex flex-col">
        <header className="px-5 py-4 border-b border-slate-200 flex items-center">
          <div>
            <h2 className="font-semibold">
              {esNuevo ? `Nuevo ${TITULOS[tipo]}` : `Editar ${TITULOS[tipo]}`}
            </h2>
            {item?.codigo && <p className="text-xs text-slate-400 font-mono mt-0.5">{item.codigo}</p>}
            {padre && <p className="text-xs text-slate-500 mt-0.5">en <strong>{padre.nombre}</strong></p>}
          </div>
          <button onClick={onCerrar} className="ml-auto text-slate-400 hover:text-slate-600 text-xl leading-none">×</button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 px-3 py-2 text-sm">{error}</div>
          )}
          {campos.map((c) => (
            <label key={c.n} className="block">
              <span className="block text-sm font-medium mb-1">
                {c.t} {c.req && <span className="text-red-500">*</span>}
              </span>
              {c.opciones ? (
                <select value={valores[c.n] || ''}
                  onChange={(e) => setValores({ ...valores, [c.n]: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white
                             focus:outline-none focus:ring-2 focus:ring-marca-500/30 focus:border-marca-500">
                  {c.opciones.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : c.ref ? (
                <select value={valores[c.n] || ''}
                  onChange={(e) => setValores({ ...valores, [c.n]: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm bg-white
                             focus:outline-none focus:ring-2 focus:ring-marca-500/30 focus:border-marca-500">
                  <option value="">— Sin especificar —</option>
                  {(refs[c.n] || []).map((o) => (
                    <option key={o.id} value={o.id}>{o[c.etiqueta] || o.nombre}</option>
                  ))}
                </select>
              ) : c.area ? (
                <textarea rows={3} value={valores[c.n] || ''}
                  onChange={(e) => setValores({ ...valores, [c.n]: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm
                             focus:outline-none focus:ring-2 focus:ring-marca-500/30 focus:border-marca-500" />
              ) : (
                <input type={c.tipo || (c.num ? 'number' : 'text')} value={valores[c.n] ?? ''}
                  onChange={(e) => setValores({ ...valores, [c.n]: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm
                             focus:outline-none focus:ring-2 focus:ring-marca-500/30 focus:border-marca-500" />
              )}
            </label>
          ))}
        </div>

        <footer className="px-5 py-4 border-t border-slate-200 flex gap-2">
          <button onClick={guardar} disabled={guardando}
            className="rounded-lg bg-marca-600 text-white px-4 py-2 text-sm font-medium
                       hover:bg-marca-700 disabled:opacity-50">
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
          <button onClick={onCerrar} className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50">
            Cancelar
          </button>
          {!esNuevo && (
            <button onClick={eliminar} disabled={guardando}
              className="ml-auto rounded-lg border border-red-300 text-red-600 px-4 py-2 text-sm hover:bg-red-50">
              Eliminar
            </button>
          )}
        </footer>
      </aside>
    </div>
  );
}
