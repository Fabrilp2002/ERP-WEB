'use client'

import Decimal from 'decimal.js'
import { Users, AlertTriangle } from 'lucide-react'

/**
 * Análisis de concentración de clientes — mide qué tan dependiente
 * está Esplendida de sus clientes más grandes.
 *
 * Regla de oro de finanzas: si un solo cliente concentra más del 30%
 * de las ventas o saldos, hay riesgo de continuidad del negocio si
 * ese cliente se pierde. Este componente lo visualiza.
 */

type SaldoCliente = {
  cliente_id: string
  cliente: string
  saldo_pendiente: string
  total_facturado?: string
}

type Props = {
  clientes: SaldoCliente[]
}

function fmt(v: string | number | Decimal): string {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function fmtM(v: number): string {
  if (v >= 100_000_000) return (v / 1_000_000).toFixed(0) + 'M'
  if (v >= 10_000_000)  return (v / 1_000_000).toFixed(1) + 'M'
  return (v / 1_000_000).toFixed(2) + 'M'
}

export default function ClientConcentration({ clientes }: Props) {
  // Filtrar solo clientes con saldo y ordenar
  const ordenados = clientes
    .filter(c => parseFloat(c.saldo_pendiente || '0') > 0)
    .sort((a, b) => parseFloat(b.saldo_pendiente) - parseFloat(a.saldo_pendiente))

  const total = ordenados.reduce((s, c) => s + parseFloat(c.saldo_pendiente || '0'), 0)

  if (total === 0 || ordenados.length === 0) {
    return (
      <div className="card">
        <h2 className="font-semibold text-slate-900 mb-1 flex items-center gap-2">
          <Users size={18} /> Concentración de clientes
        </h2>
        <p className="text-xs text-slate-500 mb-3">Riesgo de dependencia comercial</p>
        <div className="text-center py-6 text-slate-400">
          <div className="text-3xl mb-1">🎉</div>
          <div className="text-sm">Sin saldos pendientes — no hay riesgo de concentración hoy</div>
        </div>
      </div>
    )
  }

  const top1 = ordenados[0]
  const top1Pct = (parseFloat(top1.saldo_pendiente) / total) * 100
  const top3 = ordenados.slice(0, 3)
  const top3Total = top3.reduce((s, c) => s + parseFloat(c.saldo_pendiente), 0)
  const top3Pct = (top3Total / total) * 100
  const top5 = ordenados.slice(0, 5)
  const top5Total = top5.reduce((s, c) => s + parseFloat(c.saldo_pendiente), 0)
  const top5Pct = (top5Total / total) * 100

  // Coeficiente Herfindahl-Hirschman simplificado (suma de cuadrados de %)
  const hhi = ordenados.reduce((acc, c) => {
    const pct = (parseFloat(c.saldo_pendiente) / total) * 100
    return acc + pct * pct
  }, 0)

  // Interpretación HHI:
  // < 1500: mercado diversificado
  // 1500-2500: concentración moderada
  // > 2500: alta concentración
  const riesgoNivel = hhi > 2500 ? 'alto' : hhi > 1500 ? 'medio' : 'bajo'
  const riesgoMsg = {
    alto:  '🚨 Riesgo alto — Esplendida depende mucho de pocos clientes',
    medio: '⚠ Riesgo medio — Conviene diversificar',
    bajo:  '✅ Riesgo bajo — Cartera diversificada',
  }[riesgoNivel]

  const colorBarra = (pct: number): string => {
    if (pct > 40) return 'bg-rose-500'
    if (pct > 25) return 'bg-amber-500'
    if (pct > 15) return 'bg-yellow-500'
    return 'bg-emerald-500'
  }

  return (
    <div className="card">
      <div className="flex items-start justify-between gap-2 mb-1">
        <h2 className="font-semibold text-slate-900 flex items-center gap-2">
          <Users size={18} /> Concentración de clientes
        </h2>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
          riesgoNivel === 'alto'  ? 'bg-rose-100 text-rose-700' :
          riesgoNivel === 'medio' ? 'bg-amber-100 text-amber-700' :
                                    'bg-emerald-100 text-emerald-700'
        }`}>
          {riesgoMsg.split(' ')[0]} Riesgo {riesgoNivel}
        </span>
      </div>
      <p className="text-xs text-slate-500 mb-4">{ordenados.length} clientes con saldo · Total Gs. {fmtM(total)}</p>

      {/* Top concentrations */}
      <div className="space-y-3 mb-4">
        <ConcentrationRow label="Top 1" pct={top1Pct} amount={parseFloat(top1.saldo_pendiente)} extra={top1.cliente} />
        <ConcentrationRow label="Top 3" pct={top3Pct} amount={top3Total} />
        <ConcentrationRow label="Top 5" pct={top5Pct} amount={top5Total} />
      </div>

      {/* Lista de top clientes */}
      <div className="border-t border-slate-100 pt-3">
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
          Top 5 clientes
        </div>
        <div className="space-y-1.5">
          {top5.map((c, i) => {
            const pct = (parseFloat(c.saldo_pendiente) / total) * 100
            return (
              <div key={c.cliente_id} className="flex items-center gap-2 text-xs">
                <span className="text-slate-400 font-mono w-5">#{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-700 truncate">{c.cliente}</div>
                  <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${colorBarra(pct)} rounded-full transition-all`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-slate-900">{pct.toFixed(1)}%</div>
                  <div className="text-[10px] text-slate-500">Gs. {fmtM(parseFloat(c.saldo_pendiente))}</div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Alerta si concentración alta */}
      {riesgoNivel === 'alto' && (
        <div className="mt-3 p-2.5 bg-rose-50 border-l-3 border-rose-500 rounded text-[11px] text-rose-800 flex gap-2 items-start">
          <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
          <span>
            <strong>Recomendación:</strong> diversificá la cartera. Buscá nuevos clientes para reducir
            la dependencia. Si {top1.cliente} dejara de comprar, perderías {top1Pct.toFixed(0)}% de los ingresos.
          </span>
        </div>
      )}
    </div>
  )
}

function ConcentrationRow({ label, pct, amount, extra }: {
  label: string
  pct: number
  amount: number
  extra?: string
}) {
  const color = pct > 60 ? '#ef4444' : pct > 40 ? '#f59e0b' : pct > 25 ? '#eab308' : '#10b981'

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-slate-700">
          {label}{extra && <span className="text-slate-400 font-normal"> · {extra}</span>}
        </span>
        <span className="text-sm font-bold" style={{ color }}>
          {pct.toFixed(1)}%
        </span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  )
}
