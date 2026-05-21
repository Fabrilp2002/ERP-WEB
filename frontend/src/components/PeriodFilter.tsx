'use client'

import { useMemo, useState } from 'react'
import { Calendar, ChevronDown, X } from 'lucide-react'
import clsx from 'clsx'

/**
 * Filtro de período reutilizable.
 *
 * Devuelve un rango { desde, hasta } o null (para "todo el tiempo").
 *
 * Vista compacta de pestañas:  [ Mes ] [ 3M ] [ 6M ] [ 12M ] [ Año ] [ Todo ] [▾ Más ]
 * Al hacer click en "▾ Más" se despliega el panel con todas las opciones,
 * incluyendo un selector personalizado de fechas.
 */

export type PeriodValue =
  | 'mes'
  | 'mes_pasado'
  | 'trimestre'
  | 'semestre'
  | 'ult_6_meses'
  | 'ult_12_meses'
  | 'anio'
  | 'anio_pasado'
  | 'todo'
  | 'custom'

export type PeriodRange = {
  desde: string | null
  hasta: string | null
  label: string
  value: PeriodValue
}

type Props = {
  value: PeriodValue
  onChange: (range: PeriodRange) => void
  customDesde?: string | null
  customHasta?: string | null
  compact?: boolean // si true, muestra solo pestañas; si no, agrega dropdown completo
  /** "dark" para usarse sobre fondos coloridos (hero cards). Default: "light". */
  tone?: 'light' | 'dark'
}

function ymd(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}
function endOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0)
}

export function computeRange(
  value: PeriodValue,
  customDesde?: string | null,
  customHasta?: string | null,
): PeriodRange {
  const today = new Date()
  const y = today.getFullYear()
  const m = today.getMonth() // 0-based

  switch (value) {
    case 'mes': {
      return {
        desde: ymd(startOfMonth(today)),
        hasta: ymd(endOfMonth(today)),
        label: 'Este mes',
        value,
      }
    }
    case 'mes_pasado': {
      const prev = new Date(y, m - 1, 1)
      return {
        desde: ymd(startOfMonth(prev)),
        hasta: ymd(endOfMonth(prev)),
        label: 'Mes pasado',
        value,
      }
    }
    case 'trimestre': {
      const q = Math.floor(m / 3) // 0..3
      return {
        desde: ymd(new Date(y, q * 3, 1)),
        hasta: ymd(new Date(y, q * 3 + 3, 0)),
        label: `Trim. ${q + 1} ${y}`,
        value,
      }
    }
    case 'semestre': {
      const s = m < 6 ? 0 : 1
      return {
        desde: ymd(new Date(y, s * 6, 1)),
        hasta: ymd(new Date(y, s * 6 + 6, 0)),
        label: `Sem. ${s + 1} ${y}`,
        value,
      }
    }
    case 'ult_6_meses': {
      const desde = new Date(y, m - 5, 1)
      return {
        desde: ymd(desde),
        hasta: ymd(endOfMonth(today)),
        label: '6 meses',
        value,
      }
    }
    case 'ult_12_meses': {
      const desde = new Date(y, m - 11, 1)
      return {
        desde: ymd(desde),
        hasta: ymd(endOfMonth(today)),
        label: '12 meses',
        value,
      }
    }
    case 'anio': {
      return {
        desde: ymd(new Date(y, 0, 1)),
        hasta: ymd(new Date(y, 11, 31)),
        label: `Año ${y}`,
        value,
      }
    }
    case 'anio_pasado': {
      return {
        desde: ymd(new Date(y - 1, 0, 1)),
        hasta: ymd(new Date(y - 1, 11, 31)),
        label: `Año ${y - 1}`,
        value,
      }
    }
    case 'custom': {
      return {
        desde: customDesde || null,
        hasta: customHasta || null,
        label: customDesde && customHasta
          ? `${customDesde} → ${customHasta}`
          : 'Rango personalizado',
        value,
      }
    }
    case 'todo':
    default:
      return { desde: null, hasta: null, label: 'Todo', value: 'todo' }
  }
}

const QUICK_TABS: { value: PeriodValue; label: string }[] = [
  { value: 'mes',         label: 'Mes'   },
  { value: 'trimestre',   label: 'Trim.' },
  { value: 'semestre',    label: 'Sem.'  },
  { value: 'ult_6_meses', label: '6M'    },
  { value: 'ult_12_meses',label: '12M'   },
  { value: 'anio',        label: 'Año'   },
  { value: 'todo',        label: 'Todo'  },
]

export default function PeriodFilter({
  value,
  onChange,
  customDesde,
  customHasta,
  compact = false,
  tone = 'light',
}: Props) {
  const [open, setOpen] = useState(false)
  const [cDesde, setCDesde] = useState(customDesde || '')
  const [cHasta, setCHasta] = useState(customHasta || '')

  const current = useMemo(
    () => computeRange(value, cDesde, cHasta),
    [value, cDesde, cHasta],
  )

  const select = (v: PeriodValue) => {
    if (v === 'custom') {
      setOpen(true)
      return
    }
    setOpen(false)
    onChange(computeRange(v))
  }

  const applyCustom = () => {
    if (!cDesde || !cHasta) return
    onChange(computeRange('custom', cDesde, cHasta))
    setOpen(false)
  }

  const dark = tone === 'dark'
  const groupBg = dark ? 'bg-white/15 backdrop-blur-sm' : 'bg-slate-100'
  const activeBtn = dark ? 'bg-white text-emerald-700' : 'bg-white text-slate-900 shadow-sm'
  const inactiveBtn = dark
    ? 'text-white/80 hover:text-white hover:bg-white/10'
    : 'text-slate-500 hover:text-slate-800'
  const labelCls = dark ? 'text-white/70' : 'text-slate-500'

  return (
    <div className="relative inline-flex items-center gap-1">
      {/* Pestañas rápidas */}
      <div className={clsx('inline-flex rounded-lg p-0.5', groupBg)}>
        {QUICK_TABS.map(tab => {
          const active = value === tab.value
          return (
            <button
              key={tab.value}
              onClick={() => select(tab.value)}
              className={clsx(
                'text-[11px] font-semibold px-2.5 py-1 rounded-md transition-all',
                active ? activeBtn : inactiveBtn,
              )}
            >
              {tab.label}
            </button>
          )
        })}

        {/* Botón "Más" — abre dropdown */}
        {!compact && (
          <button
            onClick={() => setOpen(o => !o)}
            className={clsx(
              'text-[11px] font-semibold px-2 py-1 rounded-md transition-all flex items-center gap-1',
              (value === 'mes_pasado' || value === 'anio_pasado' || value === 'custom')
                ? activeBtn
                : inactiveBtn,
            )}
            aria-label="Más opciones"
          >
            <ChevronDown size={11} className={clsx('transition-transform', open && 'rotate-180')} />
          </button>
        )}
      </div>

      {/* Etiqueta del rango actual */}
      {value !== 'todo' && (
        <span className={clsx('text-[10px] hidden sm:inline ml-1', labelCls)}>
          ({current.label})
        </span>
      )}

      {/* Dropdown panel */}
      {open && (
        <div className="absolute top-full right-0 mt-2 w-72 bg-white border border-slate-200 rounded-xl shadow-xl z-30 p-3">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
            Períodos extra
          </div>
          <div className="grid grid-cols-2 gap-1.5 mb-3">
            <button
              onClick={() => select('mes_pasado')}
              className={clsx(
                'text-xs px-2.5 py-1.5 rounded-md text-left transition-colors',
                value === 'mes_pasado'
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'hover:bg-slate-100 text-slate-700',
              )}
            >
              Mes pasado
            </button>
            <button
              onClick={() => select('anio_pasado')}
              className={clsx(
                'text-xs px-2.5 py-1.5 rounded-md text-left transition-colors',
                value === 'anio_pasado'
                  ? 'bg-blue-50 text-blue-700 font-semibold'
                  : 'hover:bg-slate-100 text-slate-700',
              )}
            >
              Año pasado
            </button>
          </div>

          <div className="border-t border-slate-100 pt-3">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 flex items-center gap-1">
              <Calendar size={11} /> Rango personalizado
            </div>
            <div className="grid grid-cols-2 gap-2 mb-2">
              <div>
                <label className="text-[10px] text-slate-500">Desde</label>
                <input
                  type="date"
                  className="w-full text-xs border border-slate-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  value={cDesde}
                  onChange={e => setCDesde(e.target.value)}
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500">Hasta</label>
                <input
                  type="date"
                  className="w-full text-xs border border-slate-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  value={cHasta}
                  onChange={e => setCHasta(e.target.value)}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setOpen(false)}
                className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1"
              >
                Cancelar
              </button>
              <button
                onClick={applyCustom}
                disabled={!cDesde || !cHasta}
                className="text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded-md disabled:opacity-50"
              >
                Aplicar
              </button>
            </div>
          </div>

          <button
            onClick={() => setOpen(false)}
            className="absolute top-2 right-2 text-slate-400 hover:text-slate-700"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  )
}
