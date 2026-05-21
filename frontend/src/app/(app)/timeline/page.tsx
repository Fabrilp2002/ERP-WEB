'use client'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { ArrowDownRight, ArrowUpRight, Calendar, Filter } from 'lucide-react'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import { comprobantesApi } from '@/lib/api'
import PeriodFilter, { computeRange, type PeriodRange } from '@/components/PeriodFilter'

/**
 * Timeline de operaciones — vista cronológica de comprobantes
 * agrupados por mes, con stats mensuales (ventas / compras / neto).
 * Pensado para entender de un vistazo qué pasó cada mes.
 */

type Comp = {
  id: string
  numero_comprobante: string
  fecha_emision: string
  monto_total: string
  tipo: 'venta' | 'compra' | string
  contraparte?: string
  cliente_id?: string | null
  proveedor_id?: string | null
  estado_validacion?: string
  estado_pago?: string
}

function fmt(v: string | number) {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

const MONTH_SHORT = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

const MONTH_EMOJI: Record<number, string> = {
  0: '❄️', 1: '☀️', 2: '🌿', 3: '🍂', 4: '🌬️', 5: '⛄',
  6: '🌨️', 7: '🌷', 8: '🌸', 9: '🌻', 10: '🍃', 11: '🎄',
}

export default function TimelinePage() {
  const [tipo, setTipo] = useState<'todos' | 'venta' | 'compra'>('todos')
  const [periodo, setPeriodo] = useState<PeriodRange>(computeRange('ult_12_meses'))

  const { data: comprobantes = [], isLoading } = useQuery<Comp[]>({
    queryKey: ['comprobantes-timeline', tipo, periodo.desde, periodo.hasta],
    queryFn: () => comprobantesApi.listar({
      ...(tipo !== 'todos' ? { tipo } : {}),
      ...(periodo.desde ? { fecha_desde: periodo.desde } : {}),
      ...(periodo.hasta ? { fecha_hasta: periodo.hasta } : {}),
      limit: 500,
    }).then(r => r.data),
  })

  // Agrupar por mes (YYYY-MM)
  const groups = useMemo(() => {
    const byMonth: Record<string, Comp[]> = {}
    for (const c of comprobantes) {
      if (!c.fecha_emision) continue
      const key = c.fecha_emision.slice(0, 7) // YYYY-MM
      if (!byMonth[key]) byMonth[key] = []
      byMonth[key].push(c)
    }
    // Sort by month desc
    const sortedKeys = Object.keys(byMonth).sort().reverse()
    return sortedKeys.map(key => {
      const [year, month] = key.split('-').map(Number)
      const items = byMonth[key].sort((a, b) => b.fecha_emision.localeCompare(a.fecha_emision))
      const ventas  = items.filter(i => i.tipo === 'venta').reduce((s, i) => s.plus(i.monto_total || 0), new Decimal(0))
      const compras = items.filter(i => i.tipo === 'compra').reduce((s, i) => s.plus(i.monto_total || 0), new Decimal(0))
      const neto = ventas.minus(compras)
      return {
        key, year, month, items,
        ventas: Number(ventas),
        compras: Number(compras),
        neto: Number(neto),
        emoji: MONTH_EMOJI[month - 1] ?? '📅',
      }
    })
  }, [comprobantes])

  const totalVentas  = groups.reduce((s, g) => s + g.ventas, 0)
  const totalCompras = groups.reduce((s, g) => s + g.compras, 0)

  return (
    <div className="p-6 md:p-8 space-y-5 pb-20">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Calendar size={24} className="text-indigo-500" />
            Timeline de operaciones
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Historia cronológica de tus compras y ventas, agrupada por mes ·{' '}
            <span className="font-semibold text-slate-700">{periodo.label}</span>
          </p>
        </div>
        <PeriodFilter value={periodo.value} onChange={setPeriodo} />
      </div>

      {/* Stats globales */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-emerald-500 p-4">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Ventas (facturado)</div>
          <div className="text-xl font-bold text-emerald-600 mt-1">Gs. {fmt(totalVentas)}</div>
          <div className="text-[11px] text-slate-500 mt-1">
            {groups.reduce((s,g)=>s+g.items.filter(i=>i.tipo==='venta').length,0)} facturas · IVA incluido
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-rose-500 p-4">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Compras (facturado)</div>
          <div className="text-xl font-bold text-rose-600 mt-1">Gs. {fmt(totalCompras)}</div>
          <div className="text-[11px] text-slate-500 mt-1">
            {groups.reduce((s,g)=>s+g.items.filter(i=>i.tipo==='compra').length,0)} facturas · IVA incluido
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-indigo-500 p-4">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Neto</div>
          <div className={clsx(
            'text-xl font-bold mt-1',
            totalVentas - totalCompras >= 0 ? 'text-indigo-600' : 'text-rose-600',
          )}>Gs. {fmt(totalVentas - totalCompras)}</div>
          <div className="text-[11px] text-slate-500 mt-1">ventas − compras (no es ganancia)</div>
        </div>
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={14} className="text-slate-400" />
        <FilterChip active={tipo==='todos'} onClick={() => setTipo('todos')} label="Todo" />
        <FilterChip active={tipo==='venta'} onClick={() => setTipo('venta')} label="Solo ventas" color="emerald" />
        <FilterChip active={tipo==='compra'} onClick={() => setTipo('compra')} label="Solo compras" color="rose" />
      </div>

      {/* Timeline */}
      {isLoading && (
        <div className="card text-center py-8 text-slate-500">Cargando timeline...</div>
      )}

      {!isLoading && groups.length === 0 && (
        <div className="card text-center py-12">
          <div className="text-3xl mb-2">📭</div>
          <p className="text-slate-500 text-sm">Sin operaciones registradas todavía</p>
          <Link href="/comprobantes" className="text-blue-600 hover:underline text-xs mt-2 inline-block">
            Cargar primera factura →
          </Link>
        </div>
      )}

      <div className="space-y-5">
        {groups.map(group => (
          <div key={group.key} className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            {/* Cabecera del mes */}
            <div className="bg-gradient-to-r from-indigo-50 via-purple-50 to-pink-50 px-5 py-4 border-b border-slate-100">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                <h3 className="font-bold text-base text-slate-900 flex items-center gap-2">
                  <span>{group.emoji}</span>
                  <span>{MONTH_NAMES[group.month - 1]} {group.year}</span>
                  <span className="text-xs text-slate-500 font-normal">· {group.items.length} operaciones</span>
                </h3>
                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1">
                    <ArrowUpRight size={11} className="text-emerald-600" />
                    <span className="text-slate-500">Ventas:</span>
                    <strong className="text-emerald-600">Gs. {fmt(group.ventas)}</strong>
                  </span>
                  <span className="flex items-center gap-1">
                    <ArrowDownRight size={11} className="text-rose-600" />
                    <span className="text-slate-500">Compras:</span>
                    <strong className="text-rose-600">Gs. {fmt(group.compras)}</strong>
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="text-slate-500">Neto:</span>
                    <strong className={group.neto >= 0 ? 'text-indigo-600' : 'text-rose-600'}>
                      Gs. {fmt(group.neto)}
                    </strong>
                  </span>
                </div>
              </div>
            </div>

            {/* Entries */}
            <div className="divide-y divide-slate-100">
              {group.items.map(c => {
                const date = new Date(c.fecha_emision + 'T00:00:00')
                const isVenta = c.tipo === 'venta'
                return (
                  <Link
                    key={c.id}
                    href={`/comprobantes?id=${c.id}`}
                    className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50 transition-colors"
                  >
                    {/* Fecha */}
                    <div className="text-center w-14 flex-shrink-0">
                      <div className="text-xl font-bold text-slate-900 leading-none">
                        {date.getDate()}
                      </div>
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">
                        {MONTH_SHORT[date.getMonth()]}
                      </div>
                    </div>

                    {/* Tipo */}
                    <span className={clsx(
                      'text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider flex-shrink-0',
                      isVenta ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700',
                    )}>
                      {isVenta ? 'Venta' : 'Compra'}
                    </span>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm text-slate-900 truncate">
                        {c.contraparte ?? 'Sin contraparte'}
                      </div>
                      <div className="text-xs text-slate-500 font-mono truncate">
                        {c.numero_comprobante}
                      </div>
                    </div>

                    {/* Monto */}
                    <div className={clsx(
                      'text-right flex-shrink-0 font-bold text-sm flex items-center gap-1',
                      isVenta ? 'text-emerald-600' : 'text-rose-600',
                    )}>
                      {isVenta ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                      Gs. {fmt(c.monto_total)}
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


function FilterChip({
  active, onClick, label, color = 'slate',
}: {
  active: boolean; onClick: () => void; label: string; color?: 'slate' | 'emerald' | 'rose'
}) {
  const c: Record<string, { on: string; off: string }> = {
    slate:   { on: 'bg-slate-900 text-white',     off: 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50' },
    emerald: { on: 'bg-emerald-500 text-white',   off: 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100' },
    rose:    { on: 'bg-rose-500 text-white',      off: 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100' },
  }
  return (
    <button
      onClick={onClick}
      className={clsx(
        'text-xs font-semibold px-3 py-1.5 rounded-full transition-colors',
        active ? c[color].on : c[color].off,
      )}
    >
      {label}
    </button>
  )
}
