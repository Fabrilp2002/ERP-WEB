'use client'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { lotesApi, type LoteResumen, type LoteVencimiento } from '@/lib/api'
import { AlertCircle, Boxes, Calendar, PackagePlus, Search } from 'lucide-react'
import clsx from 'clsx'
import Decimal from 'decimal.js'

function money(v: number | string) {
  return 'G. ' + new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}
function fmtFecha(s?: string | null) {
  if (!s) return '—'
  try { return new Date(s).toLocaleDateString('es-PY') } catch { return s }
}

export default function LotesPage() {
  const [busqueda, setBusqueda] = useState('')
  const [soloConVenc, setSoloConVenc] = useState(false)

  const { data: lotes = [], isLoading } = useQuery<LoteResumen[]>({
    queryKey: ['inventario', 'lotes', soloConVenc],
    queryFn: () => lotesApi.listar({ solo_con_vencimiento: soloConVenc, limit: 500 }).then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  const { data: vencimientos = [] } = useQuery<LoteVencimiento[]>({
    queryKey: ['inventario', 'vencimientos'],
    queryFn: () => lotesApi.vencimientos().then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  const lotesFiltrados = useMemo(() => {
    if (!busqueda.trim()) return lotes
    const q = busqueda.toLowerCase()
    return lotes.filter(l =>
      (l.inventario_descripcion || '').toLowerCase().includes(q) ||
      (l.inventario_codigo || '').toLowerCase().includes(q) ||
      l.numero_lote.toLowerCase().includes(q) ||
      (l.proveedor_nombre || '').toLowerCase().includes(q),
    )
  }, [lotes, busqueda])

  const valorTotal = useMemo(
    () => lotes.reduce(
      (s, l) => s.plus(new Decimal(l.cantidad).times(l.costo_unitario)),
      new Decimal(0),
    ),
    [lotes],
  )

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Encabezado */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted">Inventario</p>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <Boxes size={22} /> Lotes y vencimientos
          </h1>
          <p className="text-xs text-muted mt-1">
            Trazabilidad de stock con costo promedio ponderado (CPP).
          </p>
        </div>
      </header>

      {/* KPIs */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="card">
          <p className="text-xs uppercase text-muted">Lotes activos</p>
          <p className="text-2xl font-bold font-mono">{lotes.length}</p>
        </div>
        <div className="card">
          <p className="text-xs uppercase text-muted">Valor en stock</p>
          <p className="text-2xl font-bold font-mono text-emerald-700">{money(valorTotal.toString())}</p>
        </div>
        <div className={clsx(
          'card',
          vencimientos.some(v => v.vencido) ? 'border-rose-300 bg-rose-50' :
            vencimientos.length > 0 ? 'border-amber-300 bg-amber-50' : '',
        )}>
          <p className="text-xs uppercase text-muted flex items-center gap-1">
            <AlertCircle size={12} /> Próximos vencimientos
          </p>
          <p className="text-2xl font-bold font-mono">
            {vencimientos.length}
          </p>
          {vencimientos.some(v => v.vencido) && (
            <p className="text-xs text-rose-700 font-medium">
              {vencimientos.filter(v => v.vencido).length} ya vencidos
            </p>
          )}
        </div>
      </section>

      {/* Lista de vencimientos críticos */}
      {vencimientos.length > 0 && (
        <section className="card !p-0 overflow-hidden">
          <header className="px-4 py-3 border-b border-border bg-amber-50 flex items-center gap-2">
            <Calendar size={16} className="text-amber-700" />
            <h2 className="font-semibold text-amber-900">Vencen pronto / vencidos</h2>
          </header>
          <ul className="divide-y divide-border">
            {vencimientos.slice(0, 8).map(v => (
              <li key={v.lote_id} className="px-4 py-2.5 flex items-center gap-3 text-sm">
                <div className={clsx(
                  'flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center font-bold text-xs',
                  v.vencido ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700',
                )}>
                  {v.vencido ? '!' : v.dias_restantes}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{v.inventario_descripcion}</p>
                  <p className="text-xs text-muted">
                    Lote {v.numero_lote} · {v.cantidad} {v.unidad_medida ?? ''} · Vence {fmtFecha(v.fecha_vencimiento)}
                  </p>
                </div>
                <p className="text-right font-mono text-sm">{money(v.valor_lote)}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Buscador + filtros */}
      <section className="card flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={busqueda}
            onChange={e => setBusqueda(e.target.value)}
            placeholder="Buscar por producto, código, lote o proveedor…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
          <input
            type="checkbox"
            checked={soloConVenc}
            onChange={e => setSoloConVenc(e.target.checked)}
            className="rounded border-slate-300"
          />
          Sólo lotes con vencimiento
        </label>
      </section>

      {/* Tabla de lotes */}
      <section className="card !p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface border-b border-border">
              <tr>
                <th className="text-left px-4 py-2.5 font-semibold">Producto</th>
                <th className="text-left px-4 py-2.5 font-semibold">N° Lote</th>
                <th className="text-right px-4 py-2.5 font-semibold">Cantidad</th>
                <th className="text-right px-4 py-2.5 font-semibold">Costo unit.</th>
                <th className="text-right px-4 py-2.5 font-semibold">Valor</th>
                <th className="text-left px-4 py-2.5 font-semibold">Ingreso</th>
                <th className="text-left px-4 py-2.5 font-semibold">Vencimiento</th>
                <th className="text-left px-4 py-2.5 font-semibold">Proveedor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                <tr><td colSpan={8} className="text-center text-muted py-8">Cargando…</td></tr>
              ) : lotesFiltrados.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center text-muted py-10">
                    <PackagePlus size={28} className="mx-auto mb-2 text-slate-300" />
                    {busqueda ? 'Sin resultados para esa búsqueda.' : 'Todavía no hay lotes con stock.'}
                  </td>
                </tr>
              ) : (
                lotesFiltrados.map(l => {
                  const valor = new Decimal(l.cantidad).times(l.costo_unitario).toString()
                  const hoy = new Date(); hoy.setHours(0,0,0,0)
                  const venc = l.fecha_vencimiento ? new Date(l.fecha_vencimiento) : null
                  const diasRest = venc ? Math.ceil((venc.getTime() - hoy.getTime()) / (1000*60*60*24)) : null
                  const tonoVenc = diasRest === null ? 'text-muted'
                    : diasRest < 0 ? 'text-rose-700 font-semibold'
                    : diasRest <= 30 ? 'text-amber-700 font-medium'
                    : 'text-slate-700'
                  return (
                    <tr key={l.id} className="hover:bg-surface">
                      <td className="px-4 py-2.5">
                        <p className="font-medium text-slate-900">{l.inventario_descripcion}</p>
                        {l.inventario_codigo && (
                          <p className="text-[11px] text-muted font-mono">{l.inventario_codigo}</p>
                        )}
                      </td>
                      <td className="px-4 py-2.5 font-mono text-xs">{l.numero_lote}</td>
                      <td className="px-4 py-2.5 text-right font-mono">
                        {l.cantidad} <span className="text-xs text-muted">{l.unidad_medida ?? ''}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs">{money(l.costo_unitario)}</td>
                      <td className="px-4 py-2.5 text-right font-mono font-semibold">{money(valor)}</td>
                      <td className="px-4 py-2.5 text-muted">{fmtFecha(l.fecha_ingreso)}</td>
                      <td className={clsx('px-4 py-2.5', tonoVenc)}>
                        {fmtFecha(l.fecha_vencimiento)}
                        {diasRest !== null && (
                          <span className="block text-[11px]">
                            {diasRest < 0 ? `Vencido hace ${-diasRest}d` : `En ${diasRest}d`}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-muted text-xs">{l.proveedor_nombre ?? '—'}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      <p className="text-[11px] text-muted text-center">
        Fase v7.1. La integración FEFO con ventas se activa en v7.2.
      </p>
    </div>
  )
}
