'use client'

import Link from 'next/link'
import { MapPin, Phone, FileText } from 'lucide-react'
import Avatar from './Avatar'

/**
 * Tarjeta visual para clientes O proveedores.
 *
 * Muestra:
 *   - Avatar de iniciales con color generado
 *   - Nombre + RUC
 *   - Ciudad y teléfono (con "—" si falta el dato)
 *   - Semáforo de salud (good/warn/bad)
 *   - Saldo destacado
 *   - Click → expansión del saldo o navegación a detalle
 */

export type PartyData = {
  id: string
  nombre: string
  ruc?: string | null
  telefono?: string | null
  email?: string | null
  ciudad?: string | null
  direccion?: string | null
  saldo?: number | string | null
}

type Props = {
  party: PartyData
  saldoColor?: 'green' | 'amber' | 'red'
  selected?: boolean
  onClick?: () => void
  showSaldoOnlyIfExpanded?: boolean
}

function fmt(v: number | string): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (isNaN(n)) return '0'
  return Math.round(n).toLocaleString('es-PY')
}

function deriveStatus(saldo: number): 'good' | 'warn' | 'bad' {
  if (saldo <= 0) return 'good'
  if (saldo > 10_000_000) return 'bad'
  if (saldo > 1_000_000) return 'warn'
  return 'good'
}

export default function PartyCard({
  party,
  saldoColor = 'green',
  selected = false,
  onClick,
  showSaldoOnlyIfExpanded = false,
}: Props) {
  const saldoNum = typeof party.saldo === 'string' ? parseFloat(party.saldo) : (party.saldo ?? 0)
  const status = deriveStatus(saldoNum || 0)

  const statusDot =
    status === 'good' ? 'bg-emerald-500' :
    status === 'warn' ? 'bg-amber-500' : 'bg-rose-500'

  const statusText =
    status === 'good' ? 'Al día' :
    status === 'warn' ? 'Atención' : 'Saldo alto'

  const saldoColorClass =
    saldoColor === 'green' ? 'text-emerald-600' :
    saldoColor === 'amber' ? 'text-amber-600' :
    'text-rose-600'

  const showSaldo = !showSaldoOnlyIfExpanded || selected

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left bg-white rounded-xl border transition-all p-3 flex items-center gap-3 hover:shadow-md hover:border-blue-300 ${
        selected ? 'border-blue-400 ring-2 ring-blue-100' : 'border-slate-200'
      }`}
    >
      <Avatar name={party.nombre} size={42} />

      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm text-slate-900 truncate">
          {party.nombre}
        </div>
        <div className="flex items-center gap-3 mt-0.5 text-[11px] text-slate-500">
          <span className="flex items-center gap-1 min-w-0">
            <MapPin size={11} className="flex-shrink-0" />
            <span className="truncate">{party.ciudad || party.direccion || 'Sin ubicación'}</span>
          </span>
          <span className="flex items-center gap-1 flex-shrink-0">
            <Phone size={11} />
            <span>{party.telefono || '—'}</span>
          </span>
          <span className="flex items-center gap-1 flex-shrink-0">
            <FileText size={11} />
            <span className="font-mono">{party.ruc || 'Sin RUC'}</span>
          </span>
        </div>
        <div className="flex items-center gap-1 mt-1">
          <span className={`w-1.5 h-1.5 rounded-full ${statusDot}`} />
          <span className="text-[10px] text-slate-500">{statusText}</span>
        </div>
      </div>

      <div className="text-right flex-shrink-0">
        {showSaldo && (
          <>
            <div className={`text-sm font-bold ${saldoColorClass}`}>
              Gs. {fmt(saldoNum || 0)}
            </div>
            <div className="text-[10px] text-slate-500">Saldo</div>
          </>
        )}
        {!showSaldo && (
          <span className="text-[10px] text-slate-400 italic">Click para ver saldo</span>
        )}
      </div>
    </button>
  )
}
