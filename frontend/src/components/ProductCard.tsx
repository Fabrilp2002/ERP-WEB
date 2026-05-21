'use client'

import { Package, AlertTriangle } from 'lucide-react'
import Decimal from 'decimal.js'
import StockBar from './StockBar'

/**
 * Tarjeta visual de un item del inventario.
 * Categoría se infiere automáticamente de la descripción o código.
 */

type ProductData = {
  id: string
  descripcion: string
  codigo?: string | null
  unidad_medida?: string | null
  cantidad_actual: string
  costo_unitario: string
  punto_reorden: string
}

type Props = {
  product: ProductData
  onClick?: () => void
}

type Category = {
  key: string
  label: string
  icon: string
  gradient: [string, string]
  chipBg: string
  chipText: string
}

const CATEGORIES: Record<string, Category> = {
  bronceador: {
    key: 'bronceador',
    label: 'Bronceador',
    icon: '🧴',
    gradient: ['#fef3c7', '#fbbf24'],
    chipBg: 'bg-amber-100',
    chipText: 'text-amber-800',
  },
  crema: {
    key: 'crema',
    label: 'Crema',
    icon: '🫧',
    gradient: ['#fce7f3', '#ec4899'],
    chipBg: 'bg-pink-100',
    chipText: 'text-pink-800',
  },
  frasco: {
    key: 'frasco',
    label: 'Frasco',
    icon: '🍶',
    gradient: ['#dbeafe', '#3b82f6'],
    chipBg: 'bg-blue-100',
    chipText: 'text-blue-800',
  },
  tapa: {
    key: 'tapa',
    label: 'Tapa',
    icon: '🔒',
    gradient: ['#e9d5ff', '#8b5cf6'],
    chipBg: 'bg-purple-100',
    chipText: 'text-purple-800',
  },
  etiqueta: {
    key: 'etiqueta',
    label: 'Etiqueta',
    icon: '🏷️',
    gradient: ['#d1fae5', '#10b981'],
    chipBg: 'bg-emerald-100',
    chipText: 'text-emerald-800',
  },
  materia_prima: {
    key: 'materia_prima',
    label: 'Materia prima',
    icon: '🌿',
    gradient: ['#fed7aa', '#fb923c'],
    chipBg: 'bg-orange-100',
    chipText: 'text-orange-800',
  },
  insumo: {
    key: 'insumo',
    label: 'Insumo',
    icon: '📦',
    gradient: ['#e2e8f0', '#64748b'],
    chipBg: 'bg-slate-100',
    chipText: 'text-slate-700',
  },
}

/**
 * Heurística para detectar la categoría de un producto a partir de su descripción.
 */
export function detectCategory(descripcion: string, codigo?: string | null): Category {
  const text = (descripcion + ' ' + (codigo ?? '')).toLowerCase()

  if (/bronceador|broncead/.test(text)) return CATEGORIES.bronceador
  if (/crema|hidrat|loci[oó]n|locion/.test(text)) return CATEGORIES.crema
  if (/etiqueta|etiq\.|sticker|adhes/.test(text)) return CATEGORIES.etiqueta
  if (/^tapa|disc top|atomizador.*tapa/.test(text)) return CATEGORIES.tapa
  if (/frasco|envase|bote/.test(text)) return CATEGORIES.frasco
  if (/extracto|aceite|esencia|materia prima|polvo|mp[- ]/.test(text)) return CATEGORIES.materia_prima

  return CATEGORIES.insumo
}

function fmt(v: string, dec = 0): string {
  return new Decimal(v || 0).toFixed(dec).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

export default function ProductCard({ product, onClick }: Props) {
  const cat = detectCategory(product.descripcion, product.codigo)
  const qty = new Decimal(product.cantidad_actual || 0)
  const min = new Decimal(product.punto_reorden || 0)
  const isCritical = min.gt(0) && qty.lte(min)
  const isWarning = !isCritical && min.gt(0) && qty.lte(min.mul(2))

  return (
    <button
      type="button"
      onClick={onClick}
      className="bg-white rounded-2xl border border-slate-200 overflow-hidden text-left hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
    >
      {/* Imagen / ícono de categoría */}
      <div
        className="h-20 flex items-center justify-center text-4xl relative"
        style={{
          background: `linear-gradient(135deg, ${cat.gradient[0]} 0%, ${cat.gradient[1]} 100%)`,
        }}
      >
        <span>{cat.icon}</span>
        {isCritical && (
          <div className="absolute top-2 right-2 bg-rose-500 text-white rounded-full p-1 shadow-md">
            <AlertTriangle size={12} />
          </div>
        )}
      </div>

      <div className="p-3">
        <div className="flex items-center gap-1.5 mb-1.5">
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${cat.chipBg} ${cat.chipText}`}>
            {cat.label}
          </span>
        </div>

        <div className="font-semibold text-[13px] text-slate-900 leading-tight mb-1 line-clamp-2 min-h-[2.6em]">
          {product.descripcion}
        </div>
        <div className="text-[11px] text-slate-500 font-mono mb-2">
          {product.codigo || '—'}
        </div>

        <StockBar
          cantidad={product.cantidad_actual}
          puntoReorden={product.punto_reorden}
          className="mb-1.5"
        />

        <div className="flex items-end justify-between text-[11px]">
          <div>
            <div className={`font-bold text-sm ${
              isCritical ? 'text-rose-600' : isWarning ? 'text-amber-600' : 'text-slate-900'
            }`}>
              {fmt(product.cantidad_actual, 0)} <span className="text-[10px] font-normal text-slate-500">{product.unidad_medida ?? 'u'}</span>
            </div>
            {min.gt(0) ? (
              <div className="text-slate-500 text-[10px]">mín. {fmt(product.punto_reorden, 0)}</div>
            ) : (
              <div className="text-slate-400 text-[10px] italic">sin mínimo</div>
            )}
          </div>
          <div className="text-right">
            <div className="text-slate-500 text-[10px]">Costo</div>
            <div className="font-mono text-[11px] text-slate-700">Gs. {fmt(product.costo_unitario, 0)}</div>
          </div>
        </div>
      </div>
    </button>
  )
}
