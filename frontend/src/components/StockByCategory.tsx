'use client'

import { useMemo } from 'react'
import Decimal from 'decimal.js'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { detectCategory } from './ProductCard'

/**
 * Donut de valor invertido en stock por categoría.
 * Responde la pregunta: "¿En qué categoría tengo más capital parado?"
 *
 * Útil para decidir compras, identificar sobrestock y planificar caja.
 */

type Item = {
  id: string
  descripcion: string
  codigo?: string | null
  cantidad_actual: string
  costo_unitario: string
}

type Props = {
  items: Item[]
}

const CATEGORY_META: Record<string, { label: string; color: string; emoji: string }> = {
  bronceador:    { label: 'Bronceadores',  color: '#f59e0b', emoji: '🧴' },
  crema:         { label: 'Cremas',        color: '#ec4899', emoji: '🫧' },
  frasco:        { label: 'Frascos',       color: '#3b82f6', emoji: '🍶' },
  tapa:          { label: 'Tapas',         color: '#8b5cf6', emoji: '🔒' },
  etiqueta:      { label: 'Etiquetas',     color: '#10b981', emoji: '🏷️' },
  materia_prima: { label: 'Materia prima', color: '#fb923c', emoji: '🌿' },
  insumo:        { label: 'Otros insumos', color: '#64748b', emoji: '📦' },
}

function fmt(v: number): string {
  return Math.round(v).toLocaleString('es-PY')
}

function fmtM(v: number): string {
  if (v >= 100_000_000) return (v / 1_000_000).toFixed(0) + 'M'
  if (v >= 10_000_000)  return (v / 1_000_000).toFixed(1) + 'M'
  if (v >= 1_000_000)   return (v / 1_000_000).toFixed(2) + 'M'
  if (v >= 1_000)       return (v / 1_000).toFixed(0) + 'K'
  return Math.round(v).toString()
}

export default function StockByCategory({ items }: Props) {
  const data = useMemo(() => {
    const byCategory: Record<string, { valor: number; cantidad: number; count: number }> = {}
    let total = 0

    for (const item of items) {
      const cat = detectCategory(item.descripcion, item.codigo)
      const valor = new Decimal(item.cantidad_actual || 0)
        .mul(item.costo_unitario || 0)
        .toNumber()
      const cantidad = parseFloat(item.cantidad_actual || '0')

      if (!byCategory[cat.key]) {
        byCategory[cat.key] = { valor: 0, cantidad: 0, count: 0 }
      }
      byCategory[cat.key].valor += valor
      byCategory[cat.key].cantidad += cantidad
      byCategory[cat.key].count += 1
      total += valor
    }

    const chartData = Object.entries(byCategory)
      .filter(([_, v]) => v.valor > 0)
      .sort((a, b) => b[1].valor - a[1].valor)
      .map(([key, v]) => ({
        key,
        name: CATEGORY_META[key]?.label || key,
        color: CATEGORY_META[key]?.color || '#94a3b8',
        emoji: CATEGORY_META[key]?.emoji || '📦',
        valor: v.valor,
        cantidad: v.cantidad,
        items: v.count,
        pct: total > 0 ? (v.valor / total) * 100 : 0,
      }))

    return { chartData, total }
  }, [items])

  if (data.chartData.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-5">
        <h3 className="font-semibold text-slate-900 mb-1">📊 Stock por categoría</h3>
        <div className="text-center py-8 text-slate-400">
          <div className="text-3xl mb-1">📦</div>
          <div className="text-sm">Sin valor de stock para mostrar</div>
        </div>
      </div>
    )
  }

  const topCategory = data.chartData[0]

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5">
      <div className="flex items-start justify-between mb-1">
        <h3 className="font-semibold text-slate-900">📊 Capital invertido por categoría</h3>
        <span className="text-[10px] text-slate-500">
          Total: Gs. {fmtM(data.total)}
        </span>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Dónde está parado el capital del inventario
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
        {/* Donut */}
        <div className="h-56 relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data.chartData}
                dataKey="valor"
                nameKey="name"
                innerRadius={58}
                outerRadius={90}
                paddingAngle={2}
              >
                {data.chartData.map((d, i) => (
                  <Cell key={i} fill={d.color} stroke="white" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v, _name, props: any) => [
                  `Gs. ${fmt(Number(v ?? 0))} (${props.payload.pct.toFixed(1)}%)`,
                  props.payload.name,
                ]}
                contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
          {/* Etiqueta central */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-widest">Total</div>
            <div className="text-base font-bold text-slate-900">Gs. {fmtM(data.total)}</div>
          </div>
        </div>

        {/* Lista de categorías */}
        <div className="space-y-1.5">
          {data.chartData.map(d => (
            <div key={d.key} className="flex items-center gap-2 text-xs">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: d.color }} />
              <span className="text-base">{d.emoji}</span>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-slate-700 truncate">{d.name}</div>
                <div className="text-[10px] text-slate-500">{d.items} items</div>
              </div>
              <div className="text-right">
                <div className="font-bold text-slate-900">Gs. {fmtM(d.valor)}</div>
                <div className="text-[10px] text-slate-500">{d.pct.toFixed(1)}%</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Insight */}
      {topCategory.pct > 50 && (
        <div className="mt-4 p-2.5 bg-amber-50 border-l-3 border-amber-400 rounded text-[11px] text-amber-800">
          💡 <strong>{topCategory.pct.toFixed(0)}% de tu capital de inventario</strong> está en <strong>{topCategory.name}</strong>.
          {topCategory.key === 'frasco' && ' Si tenés mucho stock de envases pero poco producto terminado, podés estar sobrecomprando packaging.'}
          {topCategory.key === 'materia_prima' && ' Buena posición para producir, pero asegurate de no tener materia prima que se venza.'}
        </div>
      )}
    </div>
  )
}
