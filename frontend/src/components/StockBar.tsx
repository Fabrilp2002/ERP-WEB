'use client'

import Decimal from 'decimal.js'

/**
 * Barra visual de nivel de stock con semáforo.
 *
 * Reglas:
 *   - Si punto_reorden = 0 → no se muestra alerta (gris/azul neutro)
 *   - Si cantidad ≤ punto_reorden → rojo (crítico)
 *   - Si cantidad ≤ 2× punto_reorden → amarillo (atención)
 *   - Sino → verde (OK)
 *
 * El ancho de la barra es porcentual: 100% si cantidad ≥ 3× punto_reorden.
 */

type Props = {
  cantidad: string | number
  puntoReorden: string | number
  className?: string
}

export default function StockBar({ cantidad, puntoReorden, className = '' }: Props) {
  const qty = new Decimal(cantidad || 0)
  const min = new Decimal(puntoReorden || 0)

  const hasMin = min.gt(0)
  const isCritical = hasMin && qty.lte(min)
  const isWarning = hasMin && qty.gt(min) && qty.lte(min.mul(2))

  // Calcular porcentaje: 100% = 3x el punto de reorden
  const maxScale = hasMin ? min.mul(3) : qty.gt(0) ? qty.mul(1.5) : new Decimal(1)
  const pct = qty.gt(0)
    ? Math.min(100, Math.max(2, qty.div(maxScale).mul(100).toNumber()))
    : 0

  const color = isCritical ? 'bg-rose-500'
    : isWarning ? 'bg-amber-500'
    : hasMin ? 'bg-emerald-500'
    : 'bg-slate-300'

  const trackColor = isCritical ? 'bg-rose-100'
    : isWarning ? 'bg-amber-100'
    : 'bg-slate-100'

  return (
    <div className={`w-full h-1.5 rounded-full overflow-hidden ${trackColor} ${className}`}>
      <div
        className={`h-full rounded-full transition-all duration-300 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
