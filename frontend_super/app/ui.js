'use client';
// <--- hecho por claude code: componentes reutilizables del portal (Tailwind + tokens).

export function Icon({ name, className = '', style }) {
  return <i className={`ti ${name} ${className}`} style={style} />;
}

export function Card({ className = '', children, style }) {
  return <div className={`tc-card ${className}`} style={style}>{children}</div>;
}

// Tarjeta de estadística con acento de color y microanimación
export function StatCard({ icon, label, value, hint, accent = '#6366f1', delay = 0, loading }) {
  return (
    <Card className="tc-anim p-4 flex items-start gap-3" style={{ animationDelay: `${delay}ms` }}>
      <div className="grid place-items-center rounded-xl shrink-0"
           style={{ width: 44, height: 44, background: `${accent}1a`, color: accent }}>
        <Icon name={icon} className="text-xl" />
      </div>
      <div className="min-w-0">
        <div className="tc-muted text-[.7rem] font-semibold uppercase tracking-wide">{label}</div>
        {loading
          ? <div className="tc-skeleton h-7 w-16 mt-1" />
          : <div className="tc-text text-2xl font-bold leading-tight tabular-nums">{value}</div>}
        {hint && <div className="tc-muted text-xs mt-.5">{hint}</div>}
      </div>
    </Card>
  );
}

export function Badge({ children, color = 'slate' }) {
  const map = {
    slate: 'bg-slate-500/10 text-slate-500',
    green: 'bg-emerald-500/12 text-emerald-600 dark:text-emerald-400',
    red:   'bg-rose-500/12 text-rose-600 dark:text-rose-400',
    amber: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
    indigo:'bg-indigo-500/12 text-indigo-600 dark:text-indigo-400',
    blue:  'bg-sky-500/12 text-sky-600 dark:text-sky-400',
  };
  return <span className={`inline-flex items-center gap-1 px-2 py-.5 rounded-full text-xs font-semibold ${map[color] || map.slate}`}>{children}</span>;
}

export function Skeleton({ className = '' }) {
  return <div className={`tc-skeleton ${className}`} />;
}

export function EmptyState({ icon = 'ti-inbox', title, subtitle }) {
  return (
    <div className="text-center py-10 px-4">
      <div className="mx-auto grid place-items-center rounded-2xl mb-3"
           style={{ width: 56, height: 56, background: 'var(--surface-2)' }}>
        <Icon name={icon} className="text-2xl tc-muted" />
      </div>
      <div className="tc-text font-semibold">{title}</div>
      {subtitle && <div className="tc-muted text-sm mt-1">{subtitle}</div>}
    </div>
  );
}

// ── Gráficas SVG hechas a mano (sin dependencias) ──────────────────────────
export function Sparkline({ data = [], color = '#6366f1', height = 64 }) {
  const vals = data.map(d => d.valor);
  const max = Math.max(1, ...vals);
  const w = 100, h = 100;
  const pts = vals.map((v, i) => {
    const x = vals.length > 1 ? (i / (vals.length - 1)) * w : 0;
    const y = h - (v / max) * (h - 8) - 4;
    return [x, y];
  });
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const area = pts.length ? `${line} L${w},${h} L0,${h} Z` : '';
  const id = 'sg' + color.replace('#', '');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ width: '100%', height }}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity=".28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {area && <path d={area} fill={`url(#${id})`} />}
      {line && <path d={line} fill="none" stroke={color} strokeWidth="2"
                     vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />}
    </svg>
  );
}

export function Bars({ data = [], color = '#6366f1' }) {
  const max = Math.max(1, ...data.map(d => d.total));
  return (
    <div className="flex flex-col gap-2">
      {data.map((d, i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="tc-muted text-xs w-32 truncate text-right shrink-0">{d.username}</div>
          <div className="flex-1 h-2.5 rounded-full overflow-hidden" style={{ background: 'var(--surface-2)' }}>
            <div className="h-full rounded-full tc-anim" style={{ width: `${(d.total / max) * 100}%`, background: color, animationDelay: `${i * 40}ms` }} />
          </div>
          <div className="tc-text text-xs font-semibold tabular-nums w-8">{d.total}</div>
        </div>
      ))}
    </div>
  );
}
