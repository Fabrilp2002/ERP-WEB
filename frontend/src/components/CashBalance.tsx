'use client'

import Decimal from 'decimal.js'
import { ArrowDownLeft, ArrowUpRight, TrendingUp, TrendingDown } from 'lucide-react'

/**
 * Visualización de "posición de caja proyectada" — reemplaza la dona
 * confusa que mezclaba conceptos. Muestra en barras horizontales
 * contrapuestas: lo que va a entrar vs lo que va a salir, con el neto destacado.
 *
 * Es la pregunta gerencial fundamental:
 * "Si todo el mundo paga y pago todo lo que debo, ¿con cuánto me quedo?"
 */

type Props = {
  porCobrar: string | number | Decimal
  porPagar: string | number | Decimal
  ivaSaldo?: number
}

function fmt(v: string | number | Decimal): string {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function fmtM(v: string | number | Decimal): string {
  const n = new Decimal(v || 0).div(1_000_000).toNumber()
  if (n >= 100) return n.toFixed(0) + 'M'
  if (n >= 10)  return n.toFixed(1) + 'M'
  return n.toFixed(2) + 'M'
}

export default function CashBalance({ porCobrar, porPagar, ivaSaldo = 0 }: Props) {
  const cobrar = new Decimal(porCobrar || 0)
  const pagar = new Decimal(porPagar || 0)
  // IVA saldo positivo = a pagar (sale plata); negativo = a favor (no resta)
  const ivaAPagar = ivaSaldo > 0 ? new Decimal(ivaSaldo) : new Decimal(0)
  const totalEntrante = cobrar
  const totalSaliente = pagar.plus(ivaAPagar)
  const neto = totalEntrante.minus(totalSaliente)
  const positivo = neto.gte(0)

  // Escalar para barras: el más grande llena el 100%
  const maxVal = Decimal.max(totalEntrante, totalSaliente, new Decimal(1))
  const pctEntrante = totalEntrante.div(maxVal).mul(100).toNumber()
  const pctPagar    = pagar.div(maxVal).mul(100).toNumber()
  const pctIva      = ivaAPagar.div(maxVal).mul(100).toNumber()

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-1">
        <h2 className="font-semibold text-slate-900 flex items-center gap-2">
          ⚖️ Posición de caja proyectada
        </h2>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Si todos te pagan y pagás todo lo que debés
      </p>

      {/* Barra 1: A favor (entrante) */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1.5">
            <ArrowDownLeft size={11} />
            A favor (van a entrar)
          </span>
          <span className="text-sm font-bold text-emerald-600">
            +Gs. {fmt(totalEntrante.toString())}
          </span>
        </div>
        <div className="h-7 bg-emerald-50 rounded-md overflow-hidden relative">
          <div
            className="h-full rounded-md transition-all duration-500 flex items-center justify-end pr-2"
            style={{
              width: `${pctEntrante}%`,
              background: 'linear-gradient(90deg, #34d399, #10b981)',
            }}
          >
            {pctEntrante > 30 && (
              <span className="text-[10px] font-bold text-white">
                Cobros: Gs. {fmtM(cobrar)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Barra 2: En contra (saliente) */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] font-semibold text-rose-700 flex items-center gap-1.5">
            <ArrowUpRight size={11} />
            En contra (van a salir)
          </span>
          <span className="text-sm font-bold text-rose-600">
            −Gs. {fmt(totalSaliente.toString())}
          </span>
        </div>
        <div className="h-7 bg-rose-50 rounded-md overflow-hidden flex">
          {pctPagar > 0 && (
            <div
              className="h-full transition-all duration-500 flex items-center justify-end pr-2"
              style={{
                width: `${pctPagar}%`,
                background: 'linear-gradient(90deg, #fb7185, #ef4444)',
              }}
              title={`Pagos: Gs. ${fmt(pagar.toString())}`}
            >
              {pctPagar > 30 && (
                <span className="text-[10px] font-bold text-white">
                  Pagos: Gs. {fmtM(pagar)}
                </span>
              )}
            </div>
          )}
          {pctIva > 0 && (
            <div
              className="h-full transition-all duration-500 flex items-center justify-end pr-2"
              style={{
                width: `${pctIva}%`,
                background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
              }}
              title={`IVA a pagar: Gs. ${fmt(ivaAPagar.toString())}`}
            >
              {pctIva > 20 && (
                <span className="text-[10px] font-bold text-white">
                  IVA: Gs. {fmtM(ivaAPagar)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Resultado neto destacado */}
      <div className={`rounded-lg p-3 border-l-4 ${
        positivo ? 'bg-emerald-50 border-emerald-500' : 'bg-rose-50 border-rose-500'
      }`}>
        <div className="flex items-center gap-3">
          {positivo ? (
            <TrendingUp className="text-emerald-600" size={20} />
          ) : (
            <TrendingDown className="text-rose-600" size={20} />
          )}
          <div className="flex-1">
            <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600">
              Posición neta proyectada
            </div>
            <div className={`text-xl font-extrabold ${
              positivo ? 'text-emerald-600' : 'text-rose-600'
            }`}>
              {positivo ? '+' : '−'}Gs. {fmt(neto.abs().toString())}
            </div>
          </div>
          <div className={`text-right text-[11px] ${positivo ? 'text-emerald-700' : 'text-rose-700'}`}>
            {positivo
              ? 'Tu negocio va a tener efectivo positivo'
              : '⚠ Estás endeudado más de lo que vas a cobrar'}
          </div>
        </div>
      </div>

      {/* Legenda IVA si aplica */}
      {ivaSaldo > 0 && (
        <p className="text-[11px] text-slate-500 mt-3">
          💡 El cálculo incluye el IVA que vas a tener que pagar (Gs. {fmt(ivaSaldo)}).
        </p>
      )}
    </div>
  )
}
