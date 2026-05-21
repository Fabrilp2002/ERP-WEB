'use client'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Calendar, TrendingUp, TrendingDown, AlertTriangle, Info } from 'lucide-react'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
  ReferenceLine,
} from 'recharts'
import { reportesApi } from '@/lib/api'

/**
 * Forecast de caja — proyección a 90 días
 * =======================================
 *
 * Toma todas las facturas con saldo pendiente (a cobrar y a pagar)
 * y proyecta la posición de caja día por día asumiendo que cada factura
 * se cobra/paga en su fecha de vencimiento.
 *
 * Permite responder preguntas como:
 *   - "¿Voy a tener plata para pagar la planilla el 28?"
 *   - "¿Qué día estoy más expuesto?"
 *   - "¿Cuándo voy a tener picos de cobranza?"
 *
 * Usa el endpoint de aging (que tiene fechas de vencimiento) y los proyecta.
 */

type AgingResponse = {
  tipo: 'clientes' | 'proveedores'
  filas: Array<{
    contraparte: string
    numero_comprobante: string
    fecha_emision: string
    fecha_vencimiento: string | null
    saldo_pendiente: string
    dias_vencido: number
  }>
  total_general: number
}

function fmt(v: number | string): string {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function fmtM(v: number): string {
  if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
  if (Math.abs(v) >= 1_000) return (v / 1_000).toFixed(0) + 'K'
  return Math.round(v).toString()
}

function daysBetween(a: Date, b: Date): number {
  const ms = b.getTime() - a.getTime()
  return Math.round(ms / (1000 * 60 * 60 * 24))
}

function addDays(d: Date, days: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + days)
  return r
}

function ymd(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export default function ForecastPage() {
  const [saldoInicial, setSaldoInicial] = useState<string>('0')
  const [diasProyeccion, setDiasProyeccion] = useState<30 | 60 | 90>(90)

  const { data: cobros } = useQuery<AgingResponse>({
    queryKey: ['aging', 'clientes-forecast'],
    queryFn: () => reportesApi.aging('clientes').then(r => r.data),
  })
  const { data: pagos } = useQuery<AgingResponse>({
    queryKey: ['aging', 'proveedores-forecast'],
    queryFn: () => reportesApi.aging('proveedores').then(r => r.data),
  })

  const forecast = useMemo(() => {
    if (!cobros || !pagos) return []

    const hoy = new Date()
    hoy.setHours(0, 0, 0, 0)
    const limite = addDays(hoy, diasProyeccion)
    const inicial = new Decimal(saldoInicial || 0)

    // Map: día → monto neto (positivo = entrada, negativo = salida)
    const movimientos: Record<string, { entradas: number; salidas: number }> = {}

    const procesarFila = (fila: any, signo: 1 | -1) => {
      // Si la factura está vencida, se asume cobro/pago HOY
      // (proyección optimista: hoy se cobra todo lo vencido)
      const fechaStr = fila.fecha_vencimiento || fila.fecha_emision
      if (!fechaStr) return
      const fecha = new Date(fechaStr + 'T00:00:00')
      const fechaEfectiva = fecha < hoy ? hoy : fecha
      if (fechaEfectiva > limite) return

      const key = ymd(fechaEfectiva)
      if (!movimientos[key]) movimientos[key] = { entradas: 0, salidas: 0 }
      const monto = parseFloat(fila.saldo_pendiente || '0')
      if (signo > 0) movimientos[key].entradas += monto
      else movimientos[key].salidas += monto
    }

    for (const f of cobros.filas || []) procesarFila(f, 1)
    for (const f of pagos.filas || [])  procesarFila(f, -1)

    // Construir serie diaria
    const serie: Array<{
      fecha: string
      dia: string
      saldo: number
      entradas: number
      salidas: number
      neto: number
    }> = []

    let saldo = inicial.toNumber()
    for (let i = 0; i <= diasProyeccion; i++) {
      const dia = addDays(hoy, i)
      const key = ymd(dia)
      const mov = movimientos[key] || { entradas: 0, salidas: 0 }
      const neto = mov.entradas - mov.salidas
      saldo += neto
      serie.push({
        fecha: key,
        dia: `${dia.getDate()}/${dia.getMonth() + 1}`,
        saldo,
        entradas: mov.entradas,
        salidas: mov.salidas,
        neto,
      })
    }

    return serie
  }, [cobros, pagos, saldoInicial, diasProyeccion])

  const stats = useMemo(() => {
    if (forecast.length === 0) return null
    const saldoFinal = forecast[forecast.length - 1].saldo
    const saldoMin = Math.min(...forecast.map(f => f.saldo))
    const saldoMax = Math.max(...forecast.map(f => f.saldo))
    const diaMin = forecast.find(f => f.saldo === saldoMin)
    const diaMax = forecast.find(f => f.saldo === saldoMax)
    const totalEntradas = forecast.reduce((s, f) => s + f.entradas, 0)
    const totalSalidas = forecast.reduce((s, f) => s + f.salidas, 0)
    const diasNegativos = forecast.filter(f => f.saldo < 0).length
    return {
      saldoFinal, saldoMin, saldoMax, diaMin, diaMax,
      totalEntradas, totalSalidas, diasNegativos,
    }
  }, [forecast])

  return (
    <div className="p-6 md:p-8 space-y-5 pb-20">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Calendar size={24} className="text-indigo-500" />
            Forecast de caja
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Proyección de tu posición de caja día por día durante los próximos {diasProyeccion} días
          </p>
        </div>
        <div className="inline-flex bg-slate-100 rounded-lg p-1">
          {[30, 60, 90].map(d => (
            <button
              key={d}
              onClick={() => setDiasProyeccion(d as 30 | 60 | 90)}
              className={clsx(
                'px-3 py-1.5 rounded-md text-xs font-semibold transition-all',
                diasProyeccion === d ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500',
              )}
            >
              {d} días
            </button>
          ))}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-blue-50 border-l-4 border-blue-400 rounded-lg p-3 flex items-start gap-2 text-xs text-blue-800">
        <Info size={14} className="flex-shrink-0 mt-0.5" />
        <div>
          <strong>Asume escenario optimista:</strong> todos los clientes pagan en la fecha de vencimiento de la factura y vos pagás todo lo tuyo también. Las facturas ya vencidas se asumen cobrables hoy.
        </div>
      </div>

      {/* Saldo inicial */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 max-w-md">
        <label className="text-xs font-semibold text-slate-600">
          Saldo de caja inicial (hoy)
        </label>
        <div className="mt-1 flex items-center gap-2">
          <span className="text-slate-500 text-sm">Gs.</span>
          <input
            type="number"
            className="input flex-1 text-right"
            value={saldoInicial}
            onChange={e => setSaldoInicial(e.target.value)}
            placeholder="0"
          />
        </div>
        <p className="text-[10px] text-slate-500 mt-1">
          💡 Cargá el saldo actual de tus cuentas bancarias + caja chica
        </p>
      </div>

      {/* KPIs */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard
            label={`Saldo final (día ${diasProyeccion})`}
            value={`Gs. ${fmt(stats.saldoFinal)}`}
            color={stats.saldoFinal >= 0 ? 'emerald' : 'red'}
            icon={stats.saldoFinal >= 0 ? '✓' : '⚠'}
          />
          <KpiCard
            label="Total entrante"
            value={`Gs. ${fmt(stats.totalEntradas)}`}
            color="emerald"
            icon="↗"
          />
          <KpiCard
            label="Total saliente"
            value={`Gs. ${fmt(stats.totalSalidas)}`}
            color="red"
            icon="↘"
          />
          <KpiCard
            label="Saldo mínimo"
            value={`Gs. ${fmt(stats.saldoMin)}`}
            sub={stats.diaMin ? `Día ${stats.diaMin.dia}` : ''}
            color={stats.saldoMin >= 0 ? 'amber' : 'red'}
            icon="📉"
          />
        </div>
      )}

      {/* Alerta de caja negativa */}
      {stats && stats.diasNegativos > 0 && (
        <div className="bg-rose-50 border-l-4 border-rose-500 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="text-rose-600 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <div className="font-semibold text-rose-900">¡Atención! Caja proyectada en negativo</div>
            <div className="text-sm text-rose-700 mt-1">
              Durante <strong>{stats.diasNegativos} días</strong> tu saldo proyectado cae por debajo de cero.
              {stats.diaMin && (
                <> El peor momento es el día <strong>{stats.diaMin.dia}</strong>, con un saldo proyectado de
                  <strong> Gs. {fmt(stats.saldoMin)}</strong>.</>
              )}
            </div>
            <div className="text-xs text-rose-700 mt-2">
              💡 Para evitar problemas: priorizá cobranza de facturas vencidas, posponé pagos no críticos
              o asegurate de tener una línea de crédito.
            </div>
          </div>
        </div>
      )}

      {/* Gráfico de proyección */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5">
        <h3 className="font-semibold text-slate-900 mb-1">Línea de caja proyectada</h3>
        <p className="text-xs text-slate-500 mb-4">
          La línea muestra el saldo acumulado día por día. Si cruza por debajo de la línea roja, hay riesgo.
        </p>
        <div className="h-72">
          {forecast.length === 0 ? (
            <div className="h-full flex items-center justify-center text-slate-400 text-sm">
              Cargando proyección...
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={forecast}>
                <defs>
                  <linearGradient id="cajaPositiva" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#10b981" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="dia"
                  tick={{ fontSize: 10 }}
                  interval={Math.max(1, Math.floor(forecast.length / 10))}
                />
                <YAxis
                  tickFormatter={(v) => fmtM(Number(v))}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  formatter={(v, name) => {
                    const labels: Record<string, string> = {
                      saldo: 'Saldo proyectado',
                      entradas: 'Entradas del día',
                      salidas: 'Salidas del día',
                    }
                    const key = String(name)
                    return [`Gs. ${fmt(Number(v ?? 0))}`, labels[key] || key]
                  }}
                  contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }}
                />
                <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="3 3" label={{ value: 'Cero', position: 'right', fill: '#ef4444', fontSize: 10 }} />
                <Area
                  type="monotone"
                  dataKey="saldo"
                  stroke="#10b981"
                  strokeWidth={2}
                  fill="url(#cajaPositiva)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Tabla de movimientos del período */}
      {forecast.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-900">Movimientos proyectados (días con actividad)</h3>
          </div>
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="responsive-table-wide w-full text-sm">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="text-left px-5 py-2 text-[10px] font-bold text-slate-600 uppercase">Día</th>
                  <th className="text-right px-3 py-2 text-[10px] font-bold text-slate-600 uppercase">Entradas</th>
                  <th className="text-right px-3 py-2 text-[10px] font-bold text-slate-600 uppercase">Salidas</th>
                  <th className="text-right px-3 py-2 text-[10px] font-bold text-slate-600 uppercase">Neto</th>
                  <th className="text-right px-5 py-2 text-[10px] font-bold text-slate-600 uppercase">Saldo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {forecast
                  .filter(f => f.entradas > 0 || f.salidas > 0)
                  .map((f, i) => (
                    <tr key={i} className={f.saldo < 0 ? 'bg-rose-50' : 'hover:bg-slate-50'}>
                      <td className="px-5 py-2 font-medium">{f.dia}</td>
                      <td className="text-right px-3 py-2 text-emerald-700 font-mono">
                        {f.entradas > 0 ? `+Gs. ${fmt(f.entradas)}` : '—'}
                      </td>
                      <td className="text-right px-3 py-2 text-rose-700 font-mono">
                        {f.salidas > 0 ? `−Gs. ${fmt(f.salidas)}` : '—'}
                      </td>
                      <td className={clsx(
                        'text-right px-3 py-2 font-mono font-semibold',
                        f.neto >= 0 ? 'text-emerald-600' : 'text-rose-600',
                      )}>
                        {f.neto >= 0 ? '+' : '−'}Gs. {fmt(Math.abs(f.neto))}
                      </td>
                      <td className={clsx(
                        'text-right px-5 py-2 font-bold',
                        f.saldo >= 0 ? 'text-slate-900' : 'text-rose-700',
                      )}>
                        Gs. {fmt(f.saldo)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}


function KpiCard({ label, value, sub, color, icon }: {
  label: string; value: string; sub?: string;
  color: 'emerald' | 'amber' | 'red'; icon: string
}) {
  const colors: Record<string, string> = {
    emerald: 'border-l-emerald-500 bg-emerald-50/40',
    amber:   'border-l-amber-500 bg-amber-50/40',
    red:     'border-l-rose-500 bg-rose-50/40',
  }
  const textColors: Record<string, string> = {
    emerald: 'text-emerald-700',
    amber:   'text-amber-700',
    red:     'text-rose-700',
  }
  return (
    <div className={`rounded-xl border border-slate-200 border-l-4 p-3 ${colors[color]}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{label}</span>
        <span>{icon}</span>
      </div>
      <div className={`text-lg font-bold ${textColors[color]}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-500 mt-0.5">{sub}</div>}
    </div>
  )
}
