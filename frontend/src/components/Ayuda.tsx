'use client'
import { useState, useRef, useEffect } from 'react'
import { HelpCircle } from 'lucide-react'
import clsx from 'clsx'

/**
 * Componente <Ayuda texto="..."/> que muestra un ícono ? con tooltip al hover/click.
 *
 * - Click activa el tooltip en mobile (donde no hay hover real).
 * - Auto-cierra al hacer click fuera.
 * - Texto puede ser string corto o JSX si necesitás formato.
 *
 * Uso:
 *   <Ayuda texto="El RUC es el número que tu cliente tiene en la DNIT." />
 *   <Ayuda texto={t('tooltip_ruc')} side="right" />
 */
type Side = 'top' | 'right' | 'bottom' | 'left'

interface AyudaProps {
  texto: React.ReactNode
  side?: Side
  className?: string
  size?: number
}

export function Ayuda({ texto, side = 'top', className, size = 14 }: AyudaProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Cerrar al click fuera
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    window.addEventListener('mousedown', handler)
    return () => window.removeEventListener('mousedown', handler)
  }, [open])

  const positionCls = {
    top:    'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left:   'right-full top-1/2 -translate-y-1/2 mr-2',
    right:  'left-full top-1/2 -translate-y-1/2 ml-2',
  }[side]

  return (
    <div ref={ref} className={clsx('relative inline-flex items-center', className)}>
      <button
        type="button"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onClick={(e) => { e.preventDefault(); setOpen(o => !o) }}
        className="text-slate-400 hover:text-blue-600 focus:outline-none focus:text-blue-600 transition"
        aria-label="Ayuda"
      >
        <HelpCircle size={size} />
      </button>

      {open && (
        <div
          role="tooltip"
          className={clsx(
            'absolute z-50 w-56 max-w-[calc(100vw-2rem)] bg-slate-900 text-white text-xs rounded-lg shadow-lg px-3 py-2 leading-snug',
            'animate-in fade-in zoom-in-95 duration-150',
            positionCls,
          )}
        >
          {texto}
          {/* Flechita */}
          <span
            className={clsx(
              'absolute w-2 h-2 bg-slate-900 rotate-45',
              side === 'top'    && 'top-full left-1/2 -translate-x-1/2 -translate-y-1/2',
              side === 'bottom' && 'bottom-full left-1/2 -translate-x-1/2 translate-y-1/2',
              side === 'left'   && 'left-full top-1/2 -translate-y-1/2 -translate-x-1/2',
              side === 'right'  && 'right-full top-1/2 -translate-y-1/2 translate-x-1/2',
            )}
          />
        </div>
      )}
    </div>
  )
}

export default Ayuda
