'use client'

import Decimal from 'decimal.js'
import { Sparkles, TrendingUp, TrendingDown, AlertTriangle, Trophy } from 'lucide-react'

/**
 * "Resumen inteligente" del dashboard — convierte datos crudos en una
 * historia entendible en lenguaje natural. Pensado para que el dueño
 * de Esplendida abra el sistema y entienda la situación del negocio
 * en 5 segundos sin tener que interpretar gráficos.
 */

type Props = {
  cobrosMesActual?: number
  cobrosMesAnterior?: number
  porCobrar?: string | number
  porPagar?: string | number
  vencidasCount?: number
  topClienteNombre?: string
  topClienteSaldo?: string | number
  stockCriticoCount?: number
  stockCriticoEjemplo?: string
  ivaSaldo?: number
}

function fmtGs(v: string | number | Decimal): string {
  const n = new Decimal(v || 0).toFixed(0)
  return n.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function fmtM(v: string | number | Decimal): string {
  const n = new Decimal(v || 0).div(1_000_000).toNumber()
  if (n >= 100) return n.toFixed(0) + 'M'
  if (n >= 10)  return n.toFixed(1) + 'M'
  return n.toFixed(2) + 'M'
}

export default function SmartSummary({
  cobrosMesActual = 0,
  cobrosMesAnterior = 0,
  porCobrar = 0,
  porPagar = 0,
  vencidasCount = 0,
  topClienteNombre,
  topClienteSaldo = 0,
  stockCriticoCount = 0,
  stockCriticoEjemplo,
  ivaSaldo = 0,
}: Props) {
  const cobrosActual = new Decimal(cobrosMesActual || 0)
  const cobrosAnt    = new Decimal(cobrosMesAnterior || 0)
  const porCobrarD   = new Decimal(porCobrar || 0)
  const porPagarD    = new Decimal(porPagar || 0)
  const balance      = porCobrarD.minus(porPagarD)

  const variacion = cobrosAnt.gt(0)
    ? Number(cobrosActual.minus(cobrosAnt).div(cobrosAnt).times(100))
    : 0

  const insights: Array<{ icon: React.ReactNode; text: React.ReactNode; tone: 'good' | 'bad' | 'info' }> = []

  // Insight 1: variación de cobros
  if (cobrosAnt.gt(0)) {
    if (variacion >= 5) {
      insights.push({
        icon: <TrendingUp size={14} />,
        tone: 'good',
        text: <>Cobraste <strong>{variacion.toFixed(0)}%</strong> más este mes (Gs. {fmtM(cobrosActual)}) que el anterior. 📈</>,
      })
    } else if (variacion <= -5) {
      insights.push({
        icon: <TrendingDown size={14} />,
        tone: 'bad',
        text: <>Cobraste <strong>{Math.abs(variacion).toFixed(0)}%</strong> menos este mes que el anterior. Hay <strong>Gs. {fmtM(cobrosAnt.minus(cobrosActual))}</strong> menos en caja. 📉</>,
      })
    }
  } else if (cobrosActual.gt(0)) {
    insights.push({
      icon: <TrendingUp size={14} />,
      tone: 'good',
      text: <>Ya cobraste <strong>Gs. {fmtM(cobrosActual)}</strong> este mes.</>,
    })
  }

  // Insight 2: balance neto
  if (porCobrarD.gt(0) || porPagarD.gt(0)) {
    if (balance.gt(0)) {
      insights.push({
        icon: <Sparkles size={14} />,
        tone: 'info',
        text: <>Si todos te pagaran lo que deben, recuperarías <strong>Gs. {fmtM(porCobrarD)}</strong> y aún tendrías <strong>Gs. {fmtM(balance)}</strong> de saldo positivo.</>,
      })
    } else if (balance.lt(0)) {
      insights.push({
        icon: <AlertTriangle size={14} />,
        tone: 'bad',
        text: <>Debés <strong>Gs. {fmtM(porPagarD.minus(porCobrarD))}</strong> más de lo que te deben. Conviene priorizar cobros.</>,
      })
    }
  }

  // Insight 3: facturas vencidas
  if (vencidasCount > 0) {
    insights.push({
      icon: <AlertTriangle size={14} />,
      tone: 'bad',
      text: <><strong>{vencidasCount}</strong> {vencidasCount === 1 ? 'factura está vencida' : 'facturas están vencidas'} y todavía sin cobrar. ⚠</>,
    })
  }

  // Insight 4: top cliente
  if (topClienteNombre && new Decimal(topClienteSaldo).gt(1_000_000)) {
    insights.push({
      icon: <Trophy size={14} />,
      tone: 'info',
      text: <>Tu cliente con mayor saldo es <strong>{topClienteNombre}</strong> (Gs. {fmtM(topClienteSaldo)}).</>,
    })
  }

  // Insight 5: stock crítico
  if (stockCriticoCount > 0) {
    insights.push({
      icon: <AlertTriangle size={14} />,
      tone: 'bad',
      text: <>Tenés <strong>{stockCriticoCount}</strong> {stockCriticoCount === 1 ? 'item' : 'items'} con stock crítico
        {stockCriticoEjemplo && <>, por ejemplo <em>{stockCriticoEjemplo}</em></>}. 🔴 Reponer antes que se agote.</>,
    })
  }

  // Insight 6: IVA
  if (ivaSaldo > 5_000_000) {
    insights.push({
      icon: <AlertTriangle size={14} />,
      tone: 'info',
      text: <>Vas a tener que pagar <strong>Gs. {fmtM(ivaSaldo)}</strong> de IVA este período (débito − crédito).</>,
    })
  }

  if (insights.length === 0) {
    insights.push({
      icon: <Sparkles size={14} />,
      tone: 'info',
      text: <>Sin movimientos relevantes para destacar. Cargá facturas y pagos para ver el resumen inteligente.</>,
    })
  }

  return (
    <div className="rounded-2xl p-5 shadow-sm border border-indigo-100 relative overflow-hidden"
      style={{ background: 'linear-gradient(135deg, #fce7f3 0%, #e0e7ff 50%, #ddd6fe 100%)' }}
    >
      {/* Decorative sparkles */}
      <div className="absolute top-2 right-3 text-xl opacity-30">✨</div>
      <div className="absolute bottom-2 right-12 text-base opacity-20">⭐</div>

      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-xl bg-white/60 backdrop-blur flex items-center justify-center text-xl">
          🎯
        </div>
        <div>
          <div className="text-[10px] font-bold text-indigo-700 uppercase tracking-widest">
            Resumen inteligente del día
          </div>
          <div className="text-base font-bold text-slate-900 mt-0.5">
            Esto es lo que está pasando en tu negocio
          </div>
        </div>
      </div>

      <ul className="space-y-2">
        {insights.slice(0, 4).map((ins, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-slate-800 bg-white/40 backdrop-blur rounded-lg px-3 py-2">
            <span className={
              ins.tone === 'good' ? 'text-emerald-600 mt-0.5' :
              ins.tone === 'bad'  ? 'text-rose-600 mt-0.5'    :
              'text-indigo-600 mt-0.5'
            }>
              {ins.icon}
            </span>
            <span className="flex-1 leading-relaxed">{ins.text}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
