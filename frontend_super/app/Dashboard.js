'use client';
// <--- hecho por claude code: dashboard del portal (stat cards + gráficas + widgets).
import { Card, StatCard, Icon, Badge, Sparkline, Bars, Skeleton, EmptyState } from './ui';

const ESTADO_BADGE = {
  normal:    <Badge color="green">Normal</Badge>,
  lectura:   <Badge color="amber">Solo lectura</Badge>,
  bloqueado: <Badge color="red">Bloqueado</Badge>,
};

export default function Dashboard({ data, loading, error }) {
  const c = data?.conteos || {};
  const sys = data?.sistema || {};
  const totalLoginsMes = (data?.serie_logins || []).reduce((a, b) => a + b.valor, 0);

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="tc-text text-2xl font-bold tracking-tight">Panel de control</h1>
          <p className="tc-muted text-sm mt-1">Resumen general del sistema · {data?.usuario?.nombre || ''}</p>
        </div>
        {!loading && (sys.mantenimiento_activo
          ? <Badge color="red"><Icon name="ti-alert-triangle" /> Mantenimiento activo</Badge>
          : <Badge color="green"><Icon name="ti-circle-check" /> Sistema operativo</Badge>)}
      </div>

      {error && (
        <Card className="p-4 flex items-center gap-3" style={{ borderColor: '#f43f5e55' }}>
          <Icon name="ti-alert-circle" className="text-rose-500 text-xl" />
          <div className="tc-text text-sm">{error}</div>
        </Card>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard loading={loading} delay={0}   icon="ti-users"        label="Usuarios"    value={c.usuarios}   hint={`${c.activos} activos`} accent="#6366f1" />
        <StatCard loading={loading} delay={40}  icon="ti-user-shield"  label="Staff"       value={c.staff}      hint="acceso interno"        accent="#0ea5e9" />
        <StatCard loading={loading} delay={80}  icon="ti-crown"        label="Superusers"  value={c.superusers} hint="control total"         accent="#f59e0b" />
        <StatCard loading={loading} delay={120} icon="ti-tags"         label="Roles"       value={c.roles}      hint="grupos"                accent="#8b5cf6" />
        <StatCard loading={loading} delay={160} icon="ti-login-2"      label="Logins hoy"  value={c.logins_hoy} hint={`${c.logins_total} total`} accent="#10b981" />
        <StatCard loading={loading} delay={200} icon="ti-server-bolt"  label="Módulos"     value={sys.modulos?.length ?? 0} hint={sys.con_restricciones ? 'con restricciones' : 'todos normales'} accent="#ef4444" />
      </div>

      {/* Gráficas */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card className="p-5 xl:col-span-2 tc-anim">
          <div className="flex items-center justify-between mb-1">
            <div>
              <div className="tc-text font-semibold">Actividad de accesos</div>
              <div className="tc-muted text-xs">Logins por día · últimos 30 días</div>
            </div>
            <Badge color="indigo"><Icon name="ti-trending-up" /> {totalLoginsMes} en el mes</Badge>
          </div>
          {loading ? <Skeleton className="h-16 mt-3" /> : <Sparkline data={data?.serie_logins} color="#6366f1" height={72} />}
          <div className="flex justify-between tc-muted text-[.65rem] mt-1">
            <span>{data?.serie_logins?.[0]?.label}</span>
            <span>{data?.serie_logins?.[data.serie_logins.length - 1]?.label}</span>
          </div>
        </Card>

        <Card className="p-5 tc-anim">
          <div className="tc-text font-semibold mb-.5">Usuarios más activos</div>
          <div className="tc-muted text-xs mb-3">Por número de accesos (30 días)</div>
          {loading ? <div className="space-y-2">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-3" />)}</div>
            : (data?.top_usuarios?.length ? <Bars data={data.top_usuarios} color="#8b5cf6" />
              : <EmptyState icon="ti-users" title="Sin datos" />)}
        </Card>
      </div>

      {/* Widgets inferiores */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Estado de módulos */}
        <Card className="p-5 tc-anim">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="ti-adjustments-alt" className="tc-muted" />
            <div className="tc-text font-semibold">Estado de módulos</div>
          </div>
          <div className="space-y-2">
            {loading ? [...Array(5)].map((_, i) => <Skeleton key={i} className="h-8" />)
              : (sys.modulos || []).map(m => (
                <div key={m.key} className="flex items-center justify-between rounded-lg px-3 py-2" style={{ background: 'var(--surface-2)' }}>
                  <span className="tc-text text-sm flex items-center gap-2"><Icon name={m.icon || 'ti-point'} className="tc-muted" />{m.label}</span>
                  {ESTADO_BADGE[m.estado] || <Badge>{m.estado}</Badge>}
                </div>
              ))}
          </div>
        </Card>

        {/* Pendientes */}
        <Card className="p-5 tc-anim">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="ti-clipboard-list" className="tc-muted" />
            <div className="tc-text font-semibold">Pendientes</div>
          </div>
          {loading ? <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12" />)}</div> : (
            <div className="space-y-2">
              <Pendiente icon="ti-ticket" color="#0ea5e9" label="Tickets abiertos" value={data?.pendientes?.tickets} />
              <Pendiente icon="ti-chalkboard" color="#10b981" label="Reportes nuevos BL" value={data?.pendientes?.reportes_bl} />
              <Pendiente icon="ti-school" color="#f59e0b" label="Reportes nuevos Colegio" value={data?.pendientes?.reportes_col} />
            </div>
          )}
        </Card>

        {/* Accesos recientes */}
        <Card className="p-5 tc-anim">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="ti-history" className="tc-muted" />
            <div className="tc-text font-semibold">Accesos recientes</div>
          </div>
          <div className="space-y-1 max-h-72 overflow-y-auto pr-1">
            {loading ? [...Array(6)].map((_, i) => <Skeleton key={i} className="h-10" />)
              : (data?.accesos_recientes?.length ? data.accesos_recientes.map((a, i) => (
                <div key={i} className="flex items-center gap-3 py-1.5">
                  <div className="grid place-items-center rounded-full h-8 w-8 text-white text-xs font-semibold shrink-0"
                       style={{ background: 'linear-gradient(135deg,#64748b,#94a3b8)' }}>{(a.usuario || '?').slice(0, 1).toUpperCase()}</div>
                  <div className="min-w-0 flex-1">
                    <div className="tc-text text-sm font-medium truncate">{a.usuario}</div>
                    <div className="tc-muted text-xs truncate">{a.ip}</div>
                  </div>
                  <div className="tc-muted text-xs whitespace-nowrap">{a.fecha}</div>
                </div>
              )) : <EmptyState icon="ti-history" title="Sin accesos" />)}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Pendiente({ icon, color, label, value }) {
  return (
    <div className="flex items-center gap-3 rounded-lg px-3 py-2.5" style={{ background: 'var(--surface-2)' }}>
      <div className="grid place-items-center rounded-lg shrink-0" style={{ width: 36, height: 36, background: `${color}1a`, color }}>
        <Icon name={icon} />
      </div>
      <div className="tc-text text-sm flex-1">{label}</div>
      <div className="tc-text text-lg font-bold tabular-nums">{value ?? 0}</div>
    </div>
  );
}
