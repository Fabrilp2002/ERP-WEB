'use client'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Calculator, Info } from 'lucide-react'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import { dashboardApi, reportesApi } from '@/lib/api'
import PeriodFilter, { computeRange, type PeriodRange } from '@/components/PeriodFilter'

/**
 * Estado de Resultados (P&L) — versión simplificada
 *
 * Calcula el resultado del período usando los datos disponibles:
 *   Ventas brutas (facturado)
 *   − CMV estimado (compras de insumos / materia prima)
 *   = Utilidad bruta
 *   − Gastos operativos (compras NO inventariadas — servicios, alquileres, etc.)
 *   = Resultado operativo
 *   − IVA neto a pagar
 *   = Resultado del período
 *
 * Es una versión "rápida" — para el P&L definitivo idealmente
 * necesitamos BOM completo (costo real por venta) y categorización
 * de gastos por plan de cuentas. Pero esto da una primera idea útil.
 */

type FlujoItem = {
  periodo: string
  etiqueta: string
  ingresos: number
  egresos: number
  facturas: number
}

type LiqIva = {
  total_iva_debito: number
  total_iva_credito: number
  saldo_iva: number
  situacion: 'a_pagar' | 'a_favor' | 'neutro'
}

function fmt(v: number | string): string {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function fmtPct(v: number): string {
  return v.toFixed(1) + '%'
}

export default function ResultadosPage() {
  const [periodo, setPeriodo] = useState<PeriodRange>(computeRange('anio'))

  const { data: flujo = [], isLoading: loadingFlujo } = useQuery<FlujoItem[]>({
    queryKey: ['flujo-resultados', periodo.desde, periodo.hasta],
    queryFn: () => dashboardApi
      .flujoMensual(12, periodo.desde ?? undefined, periodo.hasta ?? undefined)
      .then(r => r.data),
  })

  const { data: iva } = useQuery<LiqIva>({
    queryKey: ['iva-resultados', periodo.desde, periodo.hasta],
    queryFn: () => reportesApi
      .ivaLiquidacion({ desde: periodo.desde ?? undefined, hasta: periodo.hasta ?? undefined })
      .then(r => r.data),
  })

  // Cálculos
  const totales = useMemo(() => {
    const ventas = flujo.reduce((s, f) => s + (f.ingresos || 0), 0)
    const compras = flujo.reduce((s, f) => s + (f.egresos || 0), 0)
    // Heurística: ~70% de compras son CMV (insumos), 30% gastos operativos
    // Más adelante con BOM se calculará el CMV real
    const cmv = compras * 0.7
    const gastosOp = compras * 0.3
    const utilidadBruta = ventas - cmv
    const resultadoOperativo = utilidadBruta - gastosOp
    const ivaNeto = iva && iva.saldo_iva > 0 ? iva.saldo_iva : 0
    const resultadoFinal = resultadoOperativo - ivaNeto

    const margenBrutoPct = ventas > 0 ? (utilidadBruta / ventas) * 100 : 0
    const margenOperativoPct = ventas > 0 ? (resultadoOperativo / ventas) * 100 : 0
    const margenNetoPct = ventas > 0 ? (resultadoFinal / ventas) * 100 : 0

    return {
      ventas, compras, cmv, gastosOp,
      utilidadBruta, resultadoOperativo, ivaNeto, resultadoFinal,
      margenBrutoPct, margenOperativoPct, margenNetoPct,
    }
  }, [flujo, iva])

  return (
    <div className="p-6 md:p-8 space-y-5 pb-20">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <TrendingUp size={24} className="text-indigo-500" />
            Estado de Resultados (P&L)
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Cuánto ganó o perdió Esplendida en el período
          </p>
        </div>
        <PeriodFilter value={periodo.value} onChange={setPeriodo} />
      </div>

      {/* Disclaimer */}
      <div className="bg-amber-50 border-l-4 border-amber-400 rounded-lg p-3 flex items-start gap-2 text-xs text-amber-800">
        <Info size={14} className="flex-shrink-0 mt-0.5" />
        <div>
          <strong>Versión simplificada.</strong> El CMV (costo de mercadería vendida) se estima usando una proporción del 70% de las compras del período.
          Para obtener el CMV real, hay que cargar las recetas de cada producto y vincular las ventas (próxima iteración).
        </div>
      </div>

      {/* KPIs principales */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Ventas brutas" value={`Gs. ${fmt(totales.ventas)}`} color="emerald" icon="💰" />
        <KpiCard label="Utilidad bruta" value={`Gs. ${fmt(totales.utilidadBruta)}`} subValue={fmtPct(totales.margenBrutoPct)} color="blue" icon="📈" />
        <KpiCard label="Resultado operativo" value={`Gs. ${fmt(totales.resultadoOperativo)}`} subValue={fmtPct(totales.margenOperativoPct)} color="indigo" icon="⚙️" />
        <KpiCard
          label="Resultado neto"
          value={`Gs. ${fmt(Math.abs(totales.resultadoFinal))}`}
          subValue={`${totales.resultadoFinal >= 0 ? '+' : '−'}${fmtPct(Math.abs(totales.margenNetoPct))}`}
          color={totales.resultadoFinal >= 0 ? 'emerald' : 'red'}
          icon={totales.resultadoFinal >= 0 ? '✓' : '⚠'}
        />
      </div>

      {/* P&L table */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h3 className="font-semibold text-slate-900 flex items-center gap-2">
            <Calculator size={18} />
            Estado de Resultados — {periodo.label}
          </h3>
        </div>
        <table className="responsive-table w-full text-sm">
          <tbody className="divide-y divide-slate-100">
            <PLRow label="Ventas brutas (facturado)" value={totales.ventas} bold positive />

            <PLRow label="(−) Costo de mercadería vendida (CMV est.)" value={-totales.cmv} indent />
            <PLRow
              label="= Utilidad bruta"
              value={totales.utilidadBruta}
              bold
              positive={totales.utilidadBruta > 0}
              highlight
              pct={totales.margenBrutoPct}
            />

            <PLRow label="(−) Gastos operativos (est.)" value={-totales.gastosOp} indent />
            <PLRow
              label="= Resultado operativo"
              value={totales.resultadoOperativo}
              bold
              positive={totales.resultadoOperativo > 0}
              highlight
              pct={totales.margenOperativoPct}
            />

            {totales.ivaNeto > 0 && (
              <PLRow label="(−) IVA neto a pagar" value={-totales.ivaNeto} indent />
            )}
            <PLRow
              label="= Resultado del período"
              value={totales.resultadoFinal}
              bold
              positive={totales.resultadoFinal > 0}
              finalRow
              pct={totales.margenNetoPct}
            />
          </tbody>
        </table>
      </div>

      {/* Interpretación */}
      <div className={`rounded-2xl p-5 ${
        totales.resultadoFinal >= 0
          ? 'bg-emerald-50 border border-emerald-200'
          : 'bg-rose-50 border border-rose-200'
      }`}>
        <div className="flex items-start gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl ${
            totales.resultadoFinal >= 0 ? 'bg-emerald-500 text-white' : 'bg-rose-500 text-white'
          }`}>
            {totales.resultadoFinal >= 0 ? '🎉' : '⚠️'}
          </div>
          <div className="flex-1">
            <div className="font-bold text-slate-900 mb-1">
              {totales.resultadoFinal >= 0
                ? `Esplendida ganó Gs. ${fmt(totales.resultadoFinal)} en ${periodo.label.toLowerCase()}`
                : `Esplendida tuvo pérdida de Gs. ${fmt(Math.abs(totales.resultadoFinal))} en ${periodo.label.toLowerCase()}`}
            </div>
            <div className="text-sm text-slate-700">
              {totales.margenNetoPct >= 15 && '✓ El margen neto es saludable (>15%).'}
              {totales.margenNetoPct >= 0 && totales.margenNetoPct < 15 &&
                '⚠ El margen es positivo pero ajustado. Considerá revisar costos o subir precios.'}
              {totales.margenNetoPct < 0 &&
                '🚨 El negocio está operando en pérdida. Hay que actuar: revisar precios, costos y gastos urgente.'}
            </div>
            <ul className="text-xs text-slate-600 mt-2 space-y-0.5">
              <li>• Margen bruto: <strong>{fmtPct(totales.margenBrutoPct)}</strong></li>
              <li>• Margen operativo: <strong>{fmtPct(totales.margenOperativoPct)}</strong></li>
              <li>• Margen neto: <strong>{fmtPct(totales.margenNetoPct)}</strong></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}


function KpiCard({ label, value, subValue, color, icon }: {
  label: string; value: string; subValue?: string; color: 'emerald' | 'blue' | 'indigo' | 'red'; icon: string
}) {
  const colors: Record<string, string> = {
    emerald: 'border-l-emerald-500 bg-emerald-50/40',
    blue:    'border-l-blue-500 bg-blue-50/40',
    indigo:  'border-l-indigo-500 bg-indigo-50/40',
    red:     'border-l-rose-500 bg-rose-50/40',
  }
  const textColors: Record<string, string> = {
    emerald: 'text-emerald-700',
    blue:    'text-blue-700',
    indigo:  'text-indigo-700',
    red:     'text-rose-700',
  }
  return (
    <div className={`rounded-xl border border-slate-200 border-l-4 p-4 ${colors[color]}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{label}</span>
        <span>{icon}</span>
      </div>
      <div className={`text-lg font-bold ${textColors[color]}`}>{value}</div>
      {subValue && <div className="text-[11px] text-slate-500 mt-0.5">{subValue}</div>}
    </div>
  )
}


function PLRow({ label, value, bold, indent, positive, highlight, finalRow, pct }: {
  label: string
  value: number
  bold?: boolean
  indent?: boolean
  positive?: boolean
  highlight?: boolean
  finalRow?: boolean
  pct?: number
}) {
  return (
    <tr className={clsx(
      finalRow && 'bg-slate-900 text-white',
      highlight && !finalRow && 'bg-indigo-50',
    )}>
      <td className={clsx(
        'px-5 py-3',
        bold && 'font-bold',
        indent && 'pl-10 text-slate-600 text-xs',
        finalRow && 'font-bold text-base',
      )}>
        {label}
      </td>
      {pct !== undefined && (
        <td className={clsx(
          'px-3 py-3 text-right text-xs',
          finalRow ? 'text-emerald-300' : 'text-slate-500',
        )}>
          {fmtPct(pct)}
        </td>
      )}
      {pct === undefined && <td />}
      <td className={clsx(
        'px-5 py-3 text-right font-mono',
        bold && 'font-bold',
        value < 0 && !finalRow && 'text-rose-600',
        positive && bold && !finalRow && 'text-emerald-700',
        finalRow && (value >= 0 ? 'text-emerald-300' : 'text-rose-300'),
      )}>
        {value < 0 ? '−' : ''}Gs. {fmt(Math.abs(value))}
      </td>
    </tr>
  )
}
