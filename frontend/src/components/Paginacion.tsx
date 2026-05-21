'use client'
import clsx from 'clsx'
import { ChevronFirst, ChevronLast, ChevronLeft, ChevronRight } from 'lucide-react'

/**
 * Controles de paginación reusables.
 *
 * Espera: total real (no paginado), página actual, tamaño de página y callbacks.
 * El "selector de tamaño" incluye una opción especial "todas" que mapea a un page_size grande
 * (1000 por default — ajustar con prop `allPageSize`).
 */
type Props = {
  /** Número total de items (no paginado). Lo devuelve el backend cuando se pide `with_total=true`. */
  total: number
  page: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
  /** Opciones del selector. La última debería ser el "todas" (page_size grande). */
  pageSizeOptions?: { label: string; value: number }[]
  /** Texto opcional descriptivo a la izquierda (ej: "1.234 facturas filtradas"). */
  leftLabel?: string
}

const DEFAULT_OPTIONS = [
  { label: '50', value: 50 },
  { label: '100', value: 100 },
  { label: '200', value: 200 },
  { label: 'Todas', value: 1000 },
]

export default function Paginacion({
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = DEFAULT_OPTIONS,
  leftLabel,
}: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(1, page), pages)
  const desde = total === 0 ? 0 : (safePage - 1) * pageSize + 1
  const hasta = Math.min(safePage * pageSize, total)

  const btn = (active: boolean, disabled = false) =>
    clsx(
      'inline-flex items-center justify-center w-8 h-8 rounded-md text-sm transition-colors',
      disabled && 'opacity-40 cursor-not-allowed',
      !disabled && (active
        ? 'bg-blue-600 text-white font-semibold'
        : 'text-slate-700 hover:bg-slate-100 border border-slate-200'),
    )

  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 py-3 px-3 border-t border-slate-200 bg-slate-50/50">
      <div className="text-xs text-slate-600">
        {leftLabel ? <>{leftLabel} · </> : null}
        Mostrando <strong>{desde}–{hasta}</strong> de <strong>{total.toLocaleString('es-PY')}</strong>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <label className="text-xs text-slate-500 flex items-center gap-1.5">
          Mostrar:
          <select
            value={pageSize}
            onChange={e => {
              onPageSizeChange(Number(e.target.value))
              onPageChange(1)
            }}
            className="border border-slate-200 rounded-md text-xs px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
          >
            {pageSizeOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>

        <div className="flex items-center gap-1">
          <button
            onClick={() => onPageChange(1)}
            disabled={safePage <= 1}
            className={btn(false, safePage <= 1)}
            aria-label="Primera página"
          >
            <ChevronFirst size={14} />
          </button>
          <button
            onClick={() => onPageChange(safePage - 1)}
            disabled={safePage <= 1}
            className={btn(false, safePage <= 1)}
            aria-label="Anterior"
          >
            <ChevronLeft size={14} />
          </button>
          <span className="text-xs text-slate-600 px-2 tabular-nums">
            Página <strong>{safePage}</strong> de <strong>{pages}</strong>
          </span>
          <button
            onClick={() => onPageChange(safePage + 1)}
            disabled={safePage >= pages}
            className={btn(false, safePage >= pages)}
            aria-label="Siguiente"
          >
            <ChevronRight size={14} />
          </button>
          <button
            onClick={() => onPageChange(pages)}
            disabled={safePage >= pages}
            className={btn(false, safePage >= pages)}
            aria-label="Última página"
          >
            <ChevronLast size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
