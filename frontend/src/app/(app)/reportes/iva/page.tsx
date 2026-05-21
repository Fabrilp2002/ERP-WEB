'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Receipt, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react'
import clsx from 'clsx'
import { reportesApi } from '@/lib/api'

interface ResumenIva {
  periodo: string
  iva_debito_10: number
  iva_debito_5: number
  total_iva_debito: number
  iva_credito_10: number
  iva_credito_5: number
  total_iva_credito: number
  saldo_iva: number
  situacion: 'a_pagar' | 'a_favor' | 'neutro'
}

const fmt = (n: number) =>
  Number(n || 0).toLocaleString('es-PY', { maximumFractionDigits: 0 })

const money = (n: number) => `Gs. ${fmt(Math.abs(Number(n || 0)))}`

export default function ResumenIvaPage() {
  const [mes, setMes] = useState(() => new Date().toISOString().slice(0, 7))

  const params = { mes }

  const { data, isLoading, isError, refetch } = useQuery<ResumenIva>({
    queryKey: ['iva-resumen-simple', mes],
    queryFn: () => reportesApi.ivaLiquidacion(params).then(r => r.data),
  })

  const limpiar = () => {
    setMes(new Date().toISOString().slice(0, 7))
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <Receipt size={22} /> Resumen IVA
        </h1>
        <p className="text-sm text-muted">
          Suma mensual del IVA de ventas y compras para controlar cada periodo.
        </p>
      </div>

      <div className="card flex flex-col lg:flex-row gap-3 lg:items-end">
        <div>
          <label className="text-xs font-medium text-muted">Mes</label>
          <input
            type="month"
            value={mes}
            onChange={e => setMes(e.target.value)}
            className="input-field mt-1"
          />
        </div>

        <div className="flex gap-2 lg:ml-auto">
          <button type="button" onClick={limpiar} className="btn-ghost">
            Mes actual
          </button>
          <button type="button" onClick={() => refetch()} className="btn-primary flex items-center gap-2">
            <RefreshCw size={14} /> Actualizar
          </button>
        </div>
      </div>

      {isLoading && <div className="text-center py-10 text-muted">Calculando IVA...</div>}
      {isError && (
        <div className="card border-rose-200 bg-rose-50 text-rose-700">
          No se pudo cargar el resumen IVA. Proba de nuevo en un momento.
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <SummaryCard
              icon={TrendingUp}
              title="IVA ventas"
              subtitle="Debito fiscal"
              amount={data.total_iva_debito}
              tone="rose"
            />
            <SummaryCard
              icon={TrendingDown}
              title="IVA compras"
              subtitle="Credito fiscal"
              amount={data.total_iva_credito}
              tone="emerald"
            />
            <div className={clsx(
              'card border-2',
              data.situacion === 'a_pagar' ? 'border-rose-300 bg-rose-50' :
              data.situacion === 'a_favor' ? 'border-emerald-300 bg-emerald-50' :
              'border-slate-200 bg-slate-50'
            )}>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Diferencia</p>
              <p className={clsx(
                'text-3xl font-bold mt-2',
                data.situacion === 'a_pagar' ? 'text-rose-700' :
                data.situacion === 'a_favor' ? 'text-emerald-700' :
                'text-slate-700'
              )}>
                {money(data.saldo_iva)}
              </p>
              <p className="text-sm mt-2 text-slate-600">
                {data.situacion === 'a_pagar'
                  ? 'IVA estimado a pagar'
                  : data.situacion === 'a_favor'
                    ? 'IVA a favor'
                    : 'Sin diferencia'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Breakdown
              title="Ventas"
              rows={[
                ['IVA 10%', data.iva_debito_10],
                ['IVA 5%', data.iva_debito_5],
              ]}
            />
            <Breakdown
              title="Compras"
              rows={[
                ['IVA 10%', data.iva_credito_10],
                ['IVA 5%', data.iva_credito_5],
              ]}
            />
          </div>

          <p className="text-xs text-muted">
            Mes consultado: {data.periodo}. Este resumen muestra solo sumas de IVA para control interno.
          </p>
        </>
      )}
    </div>
  )
}

function SummaryCard({ icon: Icon, title, subtitle, amount, tone }: {
  icon: any
  title: string
  subtitle: string
  amount: number
  tone: 'rose' | 'emerald'
}) {
  const toneClass = tone === 'rose'
    ? 'bg-rose-50 text-rose-700 border-rose-100'
    : 'bg-emerald-50 text-emerald-700 border-emerald-100'

  return (
    <div className="card">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{subtitle}</p>
          <h2 className="text-lg font-bold text-primary mt-1">{title}</h2>
        </div>
        <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center border', toneClass)}>
          <Icon size={20} />
        </div>
      </div>
      <p className="text-3xl font-bold text-primary mt-4">{money(amount)}</p>
    </div>
  )
}

function Breakdown({ title, rows }: { title: string; rows: Array<[string, number]> }) {
  return (
    <div className="card">
      <h3 className="font-semibold text-primary mb-3">{title}</h3>
      <div className="space-y-2">
        {rows.map(([label, amount]) => (
          <div key={label} className="flex items-center justify-between text-sm">
            <span className="text-muted">{label}</span>
            <span className="font-mono font-semibold text-primary">{money(amount)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
