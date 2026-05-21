'use client'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import {
  AlertTriangle, ArrowRight, Clock, Phone, Receipt, ShieldAlert, Users, Truck,
} from 'lucide-react'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import {
  Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { reportesApi } from '@/lib/api'

/**
 * Aging Report — Antigüedad de saldos pendientes.
 *
 * Clasifica las cuentas por cobrar (o por pagar) en 5 buckets de antigüedad:
 *  - Corriente   (no vencido aún)
 *  - 1-30 días vencido
 *  - 31-60 días
 *  - 61-90 días
 *  - +90 días (riesgo de incobrabilidad)
 *
 * Es la herramienta más importante para gestionar el cash flow:
 * permite identificar qué clientes hay que llamar primero y proyectar
 * el deterioro de las cuentas a cobrar.
 */

type AgingResponse = {
  tipo: 'clientes' | 'proveedores'
  filas: Array<{
    contraparte: string
    ruc: string | null
    numero_comprobante: string
    fecha_emision: string
    fecha_vencimiento: string | null
    saldo_pendiente: string
    dias_vencido: number
    tramo: 'corriente' | '1_30' | '31_60' | '61_90' | 'mas_90'
  }>
  resumen: {
    corriente: number
    '1_30': number
    '31_60': number
    '61_90': number
    mas_90: number
  }
  total_general: number
  total_facturas: number
}

const TRAMO_LABELS = {
  corriente: 'Al día (no vencido)',
  '1_30': '1 a 30 días',
  '31_60': '31 a 60 días',
  '61_90': '61 a 90 días',
  mas_90: 'Más de 90 días',
}

const TRAMO_COLORS = {
  corriente: '#10b981', // emerald
  '1_30':    '#84cc16', // lime
  '31_60':   '#f59e0b', // amber
  '61_90':   '#f97316', // orange
  mas_90:    '#ef4444', // red
}

const TRAMO_DESCRIPTION = {
  corriente: '✓ Sin problemas',
  '1_30':    'Seguimiento',
  '31_60':   'Llamar para coordinar',
  '61_90':   '⚠ Insistir cobro',
  mas_90:    '🚨 Riesgo alto — considerar acciones legales',
}

function fmt(v: string | number) {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

export default function AgingPage() {
  const [tipo, setTipo] = useState<'clientes' | 'proveedores'>('clientes')

  const { data, isLoading } = useQuery<AgingResponse>({
    queryKey: ['reportes', 'aging', tipo],
    queryFn: () => reportesApi.aging(tipo).then(r => r.data),
  })

  const chartData = useMemo(() => {
    if (!data) return []
    return [
      { tramo: 'corriente', label: 'Al día',     monto: data.resumen.corriente, color: TRAMO_COLORS.corriente },
      { tramo: '1_30',      label: '1-30 d',     monto: data.resumen['1_30'],   color: TRAMO_COLORS['1_30'] },
      { tramo: '31_60',     label: '31-60 d',    monto: data.resumen['31_60'],  color: TRAMO_COLORS['31_60'] },
      { tramo: '61_90',     label: '61-90 d',    monto: data.resumen['61_90'],  color: TRAMO_COLORS['61_90'] },
      { tramo: 'mas_90',    label: '+90 d',      monto: data.resumen.mas_90,    color: TRAMO_COLORS.mas_90 },
    ]
  }, [data])

  // Agrupar filas por contraparte para sumar saldo total adeudado por cada uno
  const porContraparte = useMemo(() => {
    if (!data) return []
    const map: Record<string, {
      contraparte: string
      ruc: string | null
      total: number
      facturas: number
      maxDias: number
      peorTramo: keyof typeof TRAMO_COLORS
    }> = {}
    for (const f of data.filas) {
      const k = f.contraparte
      if (!map[k]) {
        map[k] = { contraparte: f.contraparte, ruc: f.ruc, total: 0, facturas: 0, maxDias: -Infinity, peorTramo: 'corriente' }
      }
      map[k].total += parseFloat(f.saldo_pendiente || '0')
      map[k].facturas += 1
      if (f.dias_vencido > map[k].maxDias) {
        map[k].maxDias = f.dias_vencido
        map[k].peorTramo = f.tramo
      }
    }
    return Object.values(map).sort((a, b) => b.total - a.total)
  }, [data])

  const totalVencido = data
    ? data.resumen['1_30'] + data.resumen['31_60'] + data.resumen['61_90'] + data.resumen.mas_90
    : 0

  const totalGrave = data ? data.resumen['61_90'] + data.resumen.mas_90 : 0

  const pctVencido = data && data.total_general > 0
    ? (totalVencido / data.total_general) * 100
    : 0

  return (
    <div className="p-6 md:p-8 space-y-5 pb-20">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Clock size={24} className="text-indigo-500" />
            {tipo === 'clientes' ? 'Cobros vencidos' : 'Pagos vencidos'}
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {tipo === 'clientes'
              ? 'Facturas que tus clientes deberían haber pagado, agrupadas por cuántos días llevan vencidas.'
              : 'Facturas que vos deberías haber pagado, agrupadas por cuántos días llevan vencidas.'}
          </p>
        </div>
        <div className="inline-flex bg-slate-100 rounded-lg p-1">
          <button
            onClick={() => setTipo('clientes')}
            className={clsx(
              'px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5',
              tipo === 'clientes' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500',
            )}
          >
            <Users size={13} /> Clientes
          </button>
          <button
            onClick={() => setTipo('proveedores')}
            className={clsx(
              'px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5',
              tipo === 'proveedores' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500',
            )}
          >
            <Truck size={13} /> Proveedores
          </button>
        </div>
      </div>

      {/* KPIs principales */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-indigo-500 p-4">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            Total {tipo === 'clientes' ? 'por cobrar' : 'por pagar'}
          </div>
          <div className="text-xl font-bold text-slate-900 mt-1">
            Gs. {fmt(data?.total_general ?? 0)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {data?.total_facturas ?? 0} facturas
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-emerald-500 p-4">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Al día</div>
          <div className="text-xl font-bold text-emerald-600 mt-1">
            Gs. {fmt(data?.resumen.corriente ?? 0)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {data && data.total_general > 0 ? ((data.resumen.corriente / data.total_general) * 100).toFixed(0) : 0}% del total
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-amber-500 p-4">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Vencido</div>
          <div className="text-xl font-bold text-amber-600 mt-1">
            Gs. {fmt(totalVencido)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {pctVencido.toFixed(0)}% del total
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-rose-500 p-4">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Riesgo alto</div>
          <div className="text-xl font-bold text-rose-600 mt-1">
            Gs. {fmt(totalGrave)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">+60 días vencidos</div>
        </div>
      </div>

      {/* Gráfico de barras */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5">
        <h3 className="font-semibold text-slate-900 mb-1 flex items-center gap-2">
          📊 Distribución por antigüedad
        </h3>
        <p className="text-xs text-slate-500 mb-4">Cuánto saldo hay en cada tramo de atraso</p>
        <div className="h-64">
          {isLoading ? (
            <div className="h-full bg-slate-50 animate-pulse rounded-lg" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="horizontal" margin={{ top: 10, right: 30, left: 30, bottom: 10 }}>
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={(v) => `${(Number(v) / 1_000_000).toFixed(0)}M`} tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(v) => `Gs. ${fmt(Number(v ?? 0))}`}
                  contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
                />
                <Bar dataKey="monto" radius={[8, 8, 0, 0]}>
                  {chartData.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
        {/* Descripciones bajo el gráfico */}
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 mt-4 text-[11px]">
          {chartData.map(d => (
            <div key={d.tramo} className="flex items-start gap-2">
              <div className="w-2 h-2 rounded-full flex-shrink-0 mt-1" style={{ background: d.color }} />
              <div>
                <div className="font-semibold text-slate-700">{TRAMO_LABELS[d.tramo as keyof typeof TRAMO_LABELS]}</div>
                <div className="text-slate-500">{TRAMO_DESCRIPTION[d.tramo as keyof typeof TRAMO_DESCRIPTION]}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Alerta de cobro urgente */}
      {totalGrave > 0 && (
        <div className="bg-rose-50 border-l-4 border-rose-500 rounded-xl p-4 flex items-start gap-3">
          <ShieldAlert className="text-rose-600 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <div className="font-semibold text-rose-900">Acción recomendada</div>
            <div className="text-sm text-rose-700 mt-1">
              Tenés <strong>Gs. {fmt(totalGrave)}</strong> con más de 60 días de atraso.
              {tipo === 'clientes' && ' Llamá a estos clientes esta semana o evaluá acciones de cobro más formales.'}
              {tipo === 'proveedores' && ' Considerá pagarlos para evitar suspensión de crédito.'}
            </div>
          </div>
        </div>
      )}

      {/* Tabla por contraparte */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h3 className="font-semibold text-slate-900">
            {tipo === 'clientes' ? 'Clientes que deben' : 'Proveedores a los que debés'}
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Ordenados por mayor saldo pendiente
          </p>
        </div>

        {isLoading && (
          <div className="p-8 space-y-2">
            {[1,2,3,4].map(i => (
              <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {!isLoading && porContraparte.length === 0 && (
          <div className="p-8 text-center">
            <div className="text-4xl mb-2">🎉</div>
            <div className="font-semibold text-slate-700 mb-1">¡Nada pendiente!</div>
            <div className="text-sm text-slate-500">
              {tipo === 'clientes'
                ? 'No tenés saldos por cobrar — todos los clientes están al día.'
                : 'No tenés saldos por pagar — todas las facturas están saldadas.'}
            </div>
          </div>
        )}

        {!isLoading && porContraparte.length > 0 && (
          <div className="overflow-x-auto">
            <table className="responsive-table-wide w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left px-5 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Contraparte</th>
                  <th className="text-center px-3 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Facturas</th>
                  <th className="text-center px-3 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Días máx.</th>
                  <th className="text-center px-3 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Tramo</th>
                  <th className="text-right px-5 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Saldo</th>
                  <th className="px-3 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {porContraparte.map((p, i) => (
                  <tr key={p.contraparte + i} className="hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3">
                      <div className="font-medium text-slate-900">{p.contraparte}</div>
                      {p.ruc && (
                        <div className="text-[11px] text-slate-500 font-mono">{p.ruc}</div>
                      )}
                    </td>
                    <td className="text-center px-3 py-3 text-slate-600">{p.facturas}</td>
                    <td className="text-center px-3 py-3">
                      <span className={clsx(
                        'font-mono text-sm',
                        p.maxDias > 90 ? 'text-rose-700 font-bold' :
                        p.maxDias > 60 ? 'text-orange-600 font-semibold' :
                        p.maxDias > 30 ? 'text-amber-600' :
                        p.maxDias > 0 ? 'text-lime-600' : 'text-emerald-600',
                      )}>
                        {p.maxDias > 0 ? `${p.maxDias}d` : 'Al día'}
                      </span>
                    </td>
                    <td className="text-center px-3 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold"
                        style={{
                          background: `${TRAMO_COLORS[p.peorTramo]}20`,
                          color: TRAMO_COLORS[p.peorTramo],
                        }}>
                        {TRAMO_LABELS[p.peorTramo]}
                      </span>
                    </td>
                    <td className="text-right px-5 py-3">
                      <div className="font-bold text-slate-900">Gs. {fmt(p.total)}</div>
                    </td>
                    <td className="px-3 py-3">
                      <Link
                        href={`/${tipo}`}
                        className="text-slate-400 hover:text-indigo-600 transition-colors"
                        title="Ver ficha"
                      >
                        <ArrowRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detalle de facturas vencidas */}
      {data && data.filas.filter(f => f.tramo !== 'corriente').length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-900 flex items-center gap-2">
              <AlertTriangle size={18} className="text-amber-500" />
              Facturas vencidas (detalle)
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              {data.filas.filter(f => f.tramo !== 'corriente').length} facturas para revisar
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="responsive-table-wide w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left px-5 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Contraparte</th>
                  <th className="text-left px-3 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Factura</th>
                  <th className="text-center px-3 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Vencida hace</th>
                  <th className="text-right px-5 py-3 text-[11px] font-bold text-slate-600 uppercase tracking-wider">Saldo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.filas
                  .filter(f => f.tramo !== 'corriente')
                  .sort((a, b) => b.dias_vencido - a.dias_vencido)
                  .slice(0, 30)
                  .map((f, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="px-5 py-3 font-medium text-slate-900">{f.contraparte}</td>
                      <td className="px-3 py-3 font-mono text-xs text-slate-600">{f.numero_comprobante}</td>
                      <td className="text-center px-3 py-3">
                        <span className="font-mono font-semibold" style={{ color: TRAMO_COLORS[f.tramo] }}>
                          {f.dias_vencido} días
                        </span>
                      </td>
                      <td className="text-right px-5 py-3 font-semibold text-slate-900">
                        Gs. {fmt(f.saldo_pendiente)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {data.filas.filter(f => f.tramo !== 'corriente').length > 30 && (
              <div className="px-5 py-3 text-center text-xs text-slate-500 bg-slate-50">
                Mostrando 30 de {data.filas.filter(f => f.tramo !== 'corriente').length} · Exportá a Excel para verlas todas
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
