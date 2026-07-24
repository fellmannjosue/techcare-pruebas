'use client';
// <--- hecho por claude code: árbol jerárquico plegable. Antes eran 5 pantallas
// separadas sin relación visible entre servidor, NVR, gabinete y cámara.
import { useState } from 'react';

function Chevron({ abierto }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
         className={`w-4 h-4 transition-transform ${abierto ? 'rotate-90' : ''}`}>
      <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Fila({ nivel, abierto, onToggle, color, codigo, nombre, extra, hijos, onEditar, onAgregar, etiquetaHijo }) {
  return (
    <div>
      <div className="flex items-center gap-2 px-4 py-2 hover:bg-slate-50 border-b border-slate-100"
           style={{ paddingLeft: 16 + nivel * 22 }}>
        {hijos > 0 ? (
          <button onClick={onToggle} className="text-slate-400 hover:text-slate-600 shrink-0">
            <Chevron abierto={abierto} />
          </button>
        ) : <span className="w-4 shrink-0" />}
        <span className={`${color} w-2 h-2 rounded-full shrink-0`} />
        <span className="font-mono text-xs text-slate-400 shrink-0">{codigo}</span>
        <span className="font-medium text-sm truncate">{nombre}</span>
        {extra && <span className="text-xs text-slate-500 truncate">{extra}</span>}
        {hijos > 0 && (
          <span className="text-xs bg-slate-100 text-slate-600 rounded-full px-2 py-0.5 shrink-0">
            {hijos}
          </span>
        )}
        <div className="ml-auto flex items-center gap-3 shrink-0">
          {onAgregar && (
            <button onClick={onAgregar}
                    className="text-xs text-emerald-600 hover:text-emerald-700 font-medium">
              + {etiquetaHijo}
            </button>
          )}
          <button onClick={onEditar}
                  className="text-xs text-marca-600 hover:text-marca-700 font-medium">
            Editar
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Arbol({ datos, onSeleccionar }) {
  const [abiertos, setAbiertos] = useState({});
  const alternar = (k) => setAbiertos((a) => ({ ...a, [k]: !a[k] }));

  if (!datos.length) {
    return <p className="p-8 text-center text-slate-400 text-sm">Sin resultados para esa búsqueda.</p>;
  }

  return (
    <div>
      {datos.map((s) => {
        const ks = `s${s.id}`;
        return (
          <div key={ks}>
            <Fila nivel={0} abierto={abiertos[ks]} onToggle={() => alternar(ks)}
                  color="bg-blue-500" codigo={s.codigo} nombre={s.nombre}
                  extra={s.ubicacion} hijos={s.nvrs.length}
                  etiquetaHijo="NVR"
                  onAgregar={() => onSeleccionar({ tipo: 'nvrs', item: {}, padre: { campo: 'servidor', id: s.id, nombre: s.nombre } })}
                  onEditar={() => onSeleccionar({ tipo: 'servidores', item: s })} />
            {abiertos[ks] && s.nvrs.map((n) => {
              const kn = `n${n.id}`;
              return (
                <div key={kn}>
                  <Fila nivel={1} abierto={abiertos[kn]} onToggle={() => alternar(kn)}
                        color="bg-indigo-500" codigo={n.codigo} nombre={n.nombre}
                        extra={n.ip} hijos={n.gabinetes.length}
                        etiquetaHijo="Gabinete"
                        onAgregar={() => onSeleccionar({ tipo: 'gabinetes', item: {}, padre: { campo: 'nvr', id: n.id, nombre: n.nombre } })}
                        onEditar={() => onSeleccionar({ tipo: 'nvrs', item: n })} />
                  {abiertos[kn] && n.gabinetes.map((g) => {
                    const kg = `g${g.id}`;
                    return (
                      <div key={kg}>
                        <Fila nivel={2} abierto={abiertos[kg]} onToggle={() => alternar(kg)}
                              color="bg-teal-500" codigo={g.codigo} nombre={g.nombre}
                              hijos={g.camaras.length}
                              etiquetaHijo="Cámara"
                              onAgregar={() => onSeleccionar({ tipo: 'camaras', item: {}, padre: { campo: 'gabinete', id: g.id, nombre: g.nombre } })}
                              onEditar={() => onSeleccionar({ tipo: 'gabinetes', item: g })} />
                        {abiertos[kg] && g.camaras.map((c) => (
                          <Fila key={`c${c.id}`} nivel={3} color="bg-emerald-500"
                                codigo={c.codigo} nombre={c.modelo}
                                extra={[c.ubicacion, c.estado].filter(Boolean).join(' · ')}
                                hijos={0}
                                onEditar={() => onSeleccionar({ tipo: 'camaras', item: c })} />
                        ))}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
