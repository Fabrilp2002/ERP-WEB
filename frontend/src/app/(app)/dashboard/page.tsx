'use client'

// (useMemo y useState se importan más abajo, eliminado este duplicado)
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Boxes,
  Camera,
  FileText,
  Receipt,
  Truck,
  UserPlus,
  Users,
  Wallet,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { dashboardApi, empresaApi, lotesApi, pagosApi, reportesApi, type LoteVencimiento } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import CashBalance from '@/components/CashBalance'
import ClientConcentration from '@/components/ClientConcentration'
import PeriodFilter, { computeRange, type PeriodValue, type PeriodRange } from '@/components/PeriodFilter'
import { useState, useMemo } from 'react'

function fmt(monto: string | number | Decimal) {
  return new Decimal(monto || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function money(monto: string | number | Decimal) {
  return `Gs. ${fmt(monto)}`
}

function saludo() {
  const h = new Date().getHours()
  if (h < 12) return 'Buen dia'
  if (h < 19) return 'Buenas tardes'
  return 'Buenas noches'
}

interface ResumenDashboard {
  total_facturas_pendientes: number
  facturas_pendientes_cobrar?: number
  facturas_pendientes_pagar?: number
  monto_por_cobrar: string
  monto_por_pagar: string
  items_bajo_stock: number
}

interface FlujoItem {
  periodo: string
  etiqueta: string
  /** Facturado emitido (ventas) por mes — sobre comprobantes.fecha_emision */
  ingresos: number
  /** Facturado recibido (compras) por mes — sobre comprobantes.fecha_emision */
  egresos: number
  facturas: number
  /** Caja real cobrada de clientes en el mes — sobre pagos.fecha_pago */
  cobros?: number
  /** Caja real pagada a proveedores en el mes — sobre pagos.fecha_pago */
  pagos_realizados?: number
}

interface SaldoProveedor {
  proveedor_id: string
  proveedor: string
  saldo_pendiente: string
}

interface SaldoCliente {
  cliente_id: string
  cliente: string
  saldo_pendiente: string
}

interface LiquidacionIva {
  total_iva_debito: number
  total_iva_credito: number
  saldo_iva: number
  situacion: 'a_pagar' | 'a_favor' | 'neutro'
}

const PIE_COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

export default function DashboardPage() {
  const { usuario, puedeEscribir } = useAuth()

  const { data: empresa } = useQuery<{ nombre?: string }>({
    queryKey: ['empresa'],
    queryFn: () => empresaApi.obtener().then(r => r.data),
    staleTime: 60_000,
  })

  const { data: resumen } = useQuery<ResumenDashboard>({
    queryKey: ['dashboard', 'resumen'],
    queryFn: () => dashboardApi.resumen().then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  // ── Período del gráfico Ingresos vs Egresos ─────────────────────────────
  // Permite filtrar el gráfico por Mes / Trim. / Sem. / 6M / 12M / Año / Todo.
  const [flujoPeriodo, setFlujoPeriodo] = useState<PeriodRange>(
    computeRange('ult_12_meses')
  )

  const { data: flujo = [] } = useQuery<FlujoItem[]>({
    queryKey: ['dashboard', 'flujo', flujoPeriodo.value, flujoPeriodo.desde, flujoPeriodo.hasta],
    queryFn: () => dashboardApi
      .flujoMensual(6, flujoPeriodo.desde ?? undefined, flujoPeriodo.hasta ?? undefined)
      .then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  // Comparativa estacional: traer datos del mismo período del año anterior
  // para superponer en el gráfico y detectar tendencias reales vs estacionales.
  const [comparaAnioAnt, setComparaAnioAnt] = useState(false)

  const periodoAnioAnt = useMemo(() => {
    if (!flujoPeriodo.desde || !flujoPeriodo.hasta) return { desde: undefined, hasta: undefined }
    const restarAnio = (s: string) => {
      const [y, m, d] = s.split('-')
      return `${Number(y) - 1}-${m}-${d}`
    }
    return {
      desde: restarAnio(flujoPeriodo.desde),
      hasta: restarAnio(flujoPeriodo.hasta),
    }
  }, [flujoPeriodo])

  const { data: flujoAnioAnt = [] } = useQuery<FlujoItem[]>({
    queryKey: ['dashboard', 'flujo-anio-ant', periodoAnioAnt.desde, periodoAnioAnt.hasta],
    queryFn: () => dashboardApi
      .flujoMensual(6, periodoAnioAnt.desde, periodoAnioAnt.hasta)
      .then(r => r.data),
    enabled: comparaAnioAnt && !!periodoAnioAnt.desde,
  })

  // Mergear ambas series por etiqueta (mes)
  const flujoComparado = useMemo(() => {
    if (!comparaAnioAnt) return flujo
    const antMap: Record<string, number> = {}
    for (const f of flujoAnioAnt) {
      // Quitar año de etiqueta para emparejar mes con mes
      const key = (f.etiqueta || '').slice(0, 3) // "May" del "May 2025"
      antMap[key] = f.ingresos || 0
    }
    return flujo.map(f => {
      const key = (f.etiqueta || '').slice(0, 3)
      return {
        ...f,
        ingresos_anio_ant: antMap[key] ?? 0,
      }
    })
  }, [flujo, flujoAnioAnt, comparaAnioAnt])

  const { data: proveedores = [] } = useQuery<SaldoProveedor[]>({
    queryKey: ['dashboard', 'saldos-proveedores'],
    queryFn: () => pagosApi.saldosProveedores().then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  const { data: clientes = [] } = useQuery<SaldoCliente[]>({
    queryKey: ['dashboard', 'saldos-clientes'],
    queryFn: () => pagosApi.saldosClientes().then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  // v7.1 — Alerta de lotes con vencimiento cercano
  const { data: vencimientos = [] } = useQuery<LoteVencimiento[]>({
    queryKey: ['dashboard', 'vencimientos'],
    queryFn: () => lotesApi.vencimientos().then(r => r.data),
    staleTime: 60_000,
  })

  const rangoMes = useMemo(() => {
    const hoy = new Date()
    const desde = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
    const hasta = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0)
    const prevDesde = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)
    const prevHasta = new Date(hoy.getFullYear(), hoy.getMonth(), 0)
    const fmt = (d: Date) => d.toISOString().slice(0, 10)
    return {
      desde: fmt(desde),
      hasta: fmt(hasta),
      prevDesde: fmt(prevDesde),
      prevHasta: fmt(prevHasta),
      mes: hoy.toISOString().slice(0, 7),
    }
  }, [])

  const { data: iva } = useQuery<LiquidacionIva>({
    queryKey: ['dashboard', 'iva-simple', rangoMes.mes],
    queryFn: () => reportesApi.ivaLiquidacion({ mes: rangoMes.mes }).then(r => r.data),
  })

  // Para evitar problemas con filtros de fecha en el backend, pedimos TODOS
  // los movimientos de cobro y filtramos por mes en frontend. La cantidad
  // total de movimientos es razonable para este tipo de empresa.
  const { data: movimientosCobro } = useQuery<{
    movimientos: { fecha_pago: string; monto_pagado: string | number }[]
    total_cobros: number
    cantidad: number
  }>({
    queryKey: ['dashboard', 'movimientos-cobro'],
    queryFn: () => pagosApi.movimientos({ tipo: 'cobro' }).then(r => r.data),
    staleTime: 0,
    refetchOnMount: 'always',
  })

  // Helper local YYYY-MM-DD compatible con el formato del backend
  const ymd = (d: Date) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }

  // Período seleccionable por el usuario para el card "Ingresos cobrados".
  // Default: mes en curso.
  const [cobrosPeriodo, setCobrosPeriodo] = useState<PeriodRange>(computeRange('mes'))

  // Suma cobros cuyo fecha_pago cae en el rango [desde, hasta] (incl).
  // Si rango es null/null (Todo), suma absolutamente todo.
  const sumarCobrosEnRango = (desde: string | null, hasta: string | null) => {
    if (!movimientosCobro?.movimientos) return { total: 0, cantidad: 0 }
    let total = 0
    let cantidad = 0
    for (const m of movimientosCobro.movimientos) {
      const f = m.fecha_pago
      if (typeof f !== 'string') continue
      if (desde && f < desde) continue
      if (hasta && f > hasta) continue
      total += Number(m.monto_pagado || 0)
      cantidad += 1
    }
    return { total, cantidad }
  }

  // Resta un mes a la fecha YYYY-MM-DD para obtener el período anterior
  // (usado para la pill "Vs período ant.")
  const restarUnMes = (s: string | null) => {
    if (!s) return null
    const [y, m, d] = s.split('-').map(Number)
    const dt = new Date(y, m - 2, d)
    return ymd(dt)
  }

  const periodoAntCobros = useMemo(() => {
    const days = (() => {
      if (!cobrosPeriodo.desde || !cobrosPeriodo.hasta) return null
      return {
        desde: restarUnMes(cobrosPeriodo.desde),
        hasta: restarUnMes(cobrosPeriodo.hasta),
      }
    })()
    return days
  }, [cobrosPeriodo])

  const cobrosMes = useMemo(() => {
    const s = sumarCobrosEnRango(cobrosPeriodo.desde, cobrosPeriodo.hasta)
    return { total_cobros: s.total, cantidad: s.cantidad }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [movimientosCobro, cobrosPeriodo])
  const cobrosMesAnt = useMemo(() => {
    if (!periodoAntCobros) return { total_cobros: 0 }
    const s = sumarCobrosEnRango(periodoAntCobros.desde, periodoAntCobros.hasta)
    return { total_cobros: s.total }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [movimientosCobro, periodoAntCobros])

  const porCobrar = new Decimal(resumen?.monto_por_cobrar || 0)
  const porPagar = new Decimal(resumen?.monto_por_pagar || 0)
  const balance = porCobrar.minus(porPagar)
  const ingresosCobrados = new Decimal(cobrosMes?.total_cobros || 0)
  const ingresosCobradosAnt = new Decimal(cobrosMesAnt?.total_cobros || 0)
  const variacionCobros = ingresosCobradosAnt.gt(0)
    ? Number(ingresosCobrados.minus(ingresosCobradosAnt).div(ingresosCobradosAnt).times(100))
    : 0

  const topProveedores = useMemo(
    () => proveedores
      .filter(p => new Decimal(p.saldo_pendiente || 0).gt(0))
      .sort((a, b) => new Decimal(b.saldo_pendiente || 0).cmp(a.saldo_pendiente || 0))
      .slice(0, 5),
    [proveedores],
  )

  const topClientes = useMemo(
    () => clientes
      .filter(c => new Decimal(c.saldo_pendiente || 0).gt(0))
      .sort((a, b) => new Decimal(b.saldo_pendiente || 0).cmp(a.saldo_pendiente || 0))
      .slice(0, 5),
    [clientes],
  )

  const deudaProveedorTotal = topProveedores.reduce((s, p) => s.plus(p.saldo_pendiente || 0), new Decimal(0))
  const clientesTotal = topClientes.reduce((s, c) => s.plus(c.saldo_pendiente || 0), new Decimal(0))
  const pieDeudas = [
    { name: 'Por cobrar', value: Number(clientesTotal) },
    { name: 'Por pagar', value: Number(deudaProveedorTotal) },
    { name: 'IVA', value: Math.abs(Number(iva?.saldo_iva || 0)) },
  ].filter(i => i.value > 0)

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-5 animate-fade-in">
      <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-3 pt-2">
        <div>
          <p className="text-sm text-slate-500">{saludo()},</p>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            {usuario?.nombre ?? 'Hola'}
          </h1>
          {empresa?.nombre && <p className="text-xs text-slate-400 mt-0.5">{empresa.nombre}</p>}
        </div>
        <p className="text-xs text-slate-500 capitalize">
          {new Date().toLocaleDateString('es-PY', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
      </header>

      {/* El resumen narrativo se delegó al chatbot —
          ahora podés preguntarle directamente cosas como:
          "¿Cuánto me deben?", "¿Cuál es mi cliente con más deuda?",
          "¿Cuántas facturas están vencidas?", "¿Qué IVA voy a pagar?". */}

      <section className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
        <Link href="/comprobantes?tipo=venta&estado_pago=no_pagado" className="group">
          <HeroCard
            variant="azul"
            eyebrow="Por cobrar"
            value={money(porCobrar)}
            subtitle="A clientes · toca para ver facturas"
            pills={[
              { label: 'Clientes con deuda', value: String(topClientes.length || 0) },
              { label: 'Pendientes cobro', value: String(resumen?.facturas_pendientes_cobrar ?? 0) },
              { label: 'Balance', value: money(balance), positive: balance.gte(0) },
            ]}
          />
        </Link>
        <Link href="/comprobantes?tipo=compra&estado_pago=no_pagado" className="group">
          <HeroCard
            variant="rosa"
            eyebrow="Por pagar"
            value={money(porPagar)}
            subtitle="A proveedores · toca para ver facturas"
            pills={[
              { label: 'Proveedores con saldo', value: String(topProveedores.length || 0) },
              { label: 'Pendientes pago', value: String(resumen?.facturas_pendientes_pagar ?? 0) },
            ]}
          />
        </Link>
        <HeroCard
          variant="verde"
          eyebrow="Ingresos cobrados"
          value={money(ingresosCobrados)}
          subtitle={`${cobrosPeriodo.label} · ${cobrosMes?.cantidad ?? 0} cobros`}
          headerExtra={
            <PeriodFilter
              value={cobrosPeriodo.value}
              onChange={setCobrosPeriodo}
              compact
              tone="dark"
            />
          }
          pills={
            variacionCobros !== 0
              ? [{ label: 'Vs período ant.', value: `${Math.abs(variacionCobros).toFixed(1)}%`, positive: variacionCobros >= 0 }]
              : [{ label: 'Vs período ant.', value: '—' }]
          }
          chart={
            <AreaChart data={flujo}>
              <defs>
                <linearGradient id="ingresosHero" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ffffff" stopOpacity={0.55} />
                  <stop offset="100%" stopColor="#ffffff" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="cobros" stroke="#fff" strokeWidth={2} fill="url(#ingresosHero)" />
            </AreaChart>
          }
        />
      </section>

      <section>
        <p className="text-sm font-semibold text-slate-700 mb-3 px-1">Que queres hacer?</p>
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
          {puedeEscribir() && <QuickAction href="/ocr" icon={Camera} label="Cargar factura" sublabel="foto o Excel" color="blue" />}
          {puedeEscribir() && <QuickAction href="/ocr?modo=manual" icon={FileText} label="Factura manual" sublabel="sin foto" color="slate" />}
          {puedeEscribir() && <QuickAction href="/movimientos?accion=nuevo&tipo=cobro" icon={ArrowDownRight} label="Cargar cobro" sublabel="cliente" color="emerald" />}
          {puedeEscribir() && <QuickAction href="/movimientos?accion=nuevo&tipo=pago" icon={ArrowUpRight} label="Cargar pago" sublabel="proveedor" color="rose" />}
          {puedeEscribir() && <QuickAction href="/clientes" icon={UserPlus} label="Nuevo cliente" color="emerald" />}
          <QuickAction href="/comprobantes?tipo=venta&estado_pago=no_pagado" icon={Users} label="Ver deudas" sublabel="clientes" color="violet" />
          <QuickAction href="/comprobantes?tipo=compra&estado_pago=no_pagado" icon={Truck} label="Por pagar" sublabel="proveedores" color="amber" />
          <QuickAction href="/reportes/iva" icon={Receipt} label="Resumen IVA" color="rose" />
          <QuickAction href="/movimientos" icon={Wallet} label="Cobros y pagos" color="slate" />
        </div>
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <MetricCard label="IVA del mes" value={money(iva?.saldo_iva || 0)} icon={Receipt} tone={iva?.situacion === 'a_favor' ? 'emerald' : 'amber'} />
        <MetricCard label="Pendientes de cobro" value={String(resumen?.facturas_pendientes_cobrar ?? 0)} icon={FileText} tone="blue" />
        <MetricCard label="Pendientes de pago"  value={String(resumen?.facturas_pendientes_pagar ?? 0)} icon={FileText} tone="amber" />
      </section>

      {/* v7.1 — Alerta de lotes por vencer */}
      {vencimientos.length > 0 && (
        <Link href="/inventario/lotes" className="block">
          <section className={clsx(
            'card flex items-center gap-3 hover:shadow-md transition',
            vencimientos.some(v => v.vencido) ? 'border-rose-300 bg-rose-50' : 'border-amber-300 bg-amber-50',
          )}>
            <div className={clsx(
              'w-10 h-10 rounded-xl flex items-center justify-center',
              vencimientos.some(v => v.vencido) ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700',
            )}>
              <Boxes size={20} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-900">
                {vencimientos.filter(v => v.vencido).length > 0
                  ? `${vencimientos.filter(v => v.vencido).length} lote${vencimientos.filter(v => v.vencido).length === 1 ? '' : 's'} vencido${vencimientos.filter(v => v.vencido).length === 1 ? '' : 's'}`
                  : `${vencimientos.length} lote${vencimientos.length === 1 ? '' : 's'} próximo${vencimientos.length === 1 ? '' : 's'} a vencer`}
              </p>
              <p className="text-xs text-slate-600">
                {vencimientos.slice(0, 2).map(v => v.inventario_descripcion).join(' · ')}
                {vencimientos.length > 2 && ` · +${vencimientos.length - 2} más`}
              </p>
            </div>
            <ArrowRight size={16} className="text-slate-400" />
          </section>
        </Link>
      )}

      <section className="grid lg:grid-cols-3 gap-4">
        <div className="card lg:col-span-2">
          <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
            <div>
              <h2 className="font-semibold text-primary flex items-center gap-2"><BarChart3 size={18} /> Ingresos y egresos</h2>
              <p className="text-xs text-muted">{flujoPeriodo.label}</p>
            </div>
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
              <label className="flex items-center gap-1.5 text-[11px] text-slate-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={comparaAnioAnt}
                  onChange={e => setComparaAnioAnt(e.target.checked)}
                  className="rounded border-slate-300"
                />
                <span>Comparar año anterior</span>
              </label>
              <PeriodFilter value={flujoPeriodo.value} onChange={setFlujoPeriodo} />
            </div>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={flujoComparado}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="etiqueta" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => `${Number(v) / 1000000}M`} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value) => money(Number(value))} />
                <Bar dataKey="ingresos" name="Ventas (facturado)" fill="#10b981" radius={[5, 5, 0, 0]} />
                <Bar dataKey="egresos" name="Compras (facturado)" fill="#ef4444" radius={[5, 5, 0, 0]} />
                {comparaAnioAnt && (
                  <Bar dataKey="ingresos_anio_ant" name="Ventas año anterior" fill="#a7f3d0" radius={[5, 5, 0, 0]} />
                )}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <CashBalance
          porCobrar={porCobrar.toString()}
          porPagar={porPagar.toString()}
          ivaSaldo={iva?.saldo_iva ?? 0}
        />
      </section>

      {/* Concentración de clientes — riesgo de dependencia comercial */}
      <ClientConcentration clientes={clientes} />

      <section className="grid lg:grid-cols-2 gap-4">
        <ListCard
          title="Clientes que deben"
          icon={Users}
          empty="No hay deudas de clientes."
          href="/comprobantes?tipo=venta&estado_pago=no_pagado"
          rows={topClientes.map(c => ({ label: c.cliente, value: money(c.saldo_pendiente) }))}
          tone="emerald"
        />
        <ListCard
          title="Facturas por pagar"
          icon={Truck}
          empty="No hay deudas con proveedores."
          href="/comprobantes?tipo=compra&estado_pago=no_pagado"
          rows={topProveedores.map(p => ({ label: p.proveedor, value: money(p.saldo_pendiente) }))}
          tone="amber"
        />
      </section>

    </div>
  )
}

type HeroVariant = 'azul' | 'rosa' | 'verde'

function HeroCard({
  variant,
  eyebrow,
  value,
  subtitle,
  pills,
  chart,
  headerExtra,
}: {
  variant: HeroVariant
  eyebrow: string
  value: string
  subtitle: string
  pills: Array<{ label: string; value: string; positive?: boolean }>
  chart?: React.ReactNode
  /** Slot opcional alineado a la derecha del eyebrow (ej: filtro de período). */
  headerExtra?: React.ReactNode
}) {
  const palette = {
    azul: 'bg-blue-700 shadow-blue-500/20',
    rosa: 'bg-rose-600 shadow-rose-500/20',
    verde: 'bg-emerald-600 shadow-emerald-500/20',
  }[variant]
  const pillBg = {
    azul: 'bg-white/15 text-blue-50',
    rosa: 'bg-white/15 text-rose-50',
    verde: 'bg-white/15 text-emerald-50',
  }[variant]
  return (
    <div className={clsx('rounded-2xl text-white p-5 shadow-xl flex flex-col gap-3 overflow-hidden', palette)}>
      <p className="text-xs font-semibold uppercase tracking-wider opacity-90">{eyebrow}</p>
      {headerExtra && (
        <div className="-mx-1 overflow-x-auto no-scrollbar">{headerExtra}</div>
      )}
      <p className="break-words text-xl sm:text-2xl lg:text-3xl font-bold tabular-nums leading-tight">{value}</p>
      <p className="text-xs opacity-90">{subtitle}</p>
      <div className="flex flex-wrap gap-1.5 mt-auto">
        {pills.map((p, i) => (
          <span
            key={i}
            className={clsx(
              'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold',
              pillBg,
              p.positive === false && 'bg-red-300/30',
            )}
          >
            {p.label}: {p.value}
          </span>
        ))}
      </div>
      {chart && (
        <div className="h-20 -mx-2 -mb-2">
          <ResponsiveContainer width="100%" height="100%">
            {chart as React.ReactElement}
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

function QuickAction({ href, icon: Icon, label, sublabel, color }: {
  href: string
  icon: any
  label: string
  sublabel?: string
  color: 'blue' | 'emerald' | 'violet' | 'amber' | 'rose' | 'slate'
}) {
  const palette = {
    blue: 'bg-blue-50 text-blue-700 ring-blue-200 hover:bg-blue-100',
    emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-200 hover:bg-emerald-100',
    violet: 'bg-violet-50 text-violet-700 ring-violet-200 hover:bg-violet-100',
    amber: 'bg-amber-50 text-amber-700 ring-amber-200 hover:bg-amber-100',
    rose: 'bg-rose-50 text-rose-700 ring-rose-200 hover:bg-rose-100',
    slate: 'bg-slate-50 text-slate-700 ring-slate-200 hover:bg-slate-100',
  }[color]

  return (
    <Link href={href} className="group flex min-h-[132px] flex-col items-center justify-center gap-2 rounded-2xl bg-white p-3 sm:p-4 ring-1 ring-slate-200 shadow-sm hover:shadow-md hover:-translate-y-0.5 active:scale-95 transition-all">
      <span className={clsx('w-12 h-12 rounded-2xl flex items-center justify-center ring-1 transition-colors', palette)}>
        <Icon size={22} />
      </span>
      <span className="text-center text-xs sm:text-sm font-semibold text-slate-800 leading-tight">{label}</span>
      {sublabel && <span className="text-[10px] text-slate-500 -mt-1.5 uppercase tracking-wider">{sublabel}</span>}
    </Link>
  )
}

function MetricCard({ label, value, icon: Icon, tone }: {
  label: string
  value: string
  icon: any
  tone: 'emerald' | 'rose' | 'amber' | 'blue'
}) {
  const palette = {
    emerald: 'bg-emerald-50 text-emerald-600',
    rose: 'bg-rose-50 text-rose-600',
    amber: 'bg-amber-50 text-amber-600',
    blue: 'bg-blue-50 text-blue-600',
  }[tone]

  return (
    <div className="card !p-4 card-hover">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-slate-500 truncate">{label}</p>
          <p className="text-xl font-bold text-slate-900 mt-1 tabular-nums truncate">{value}</p>
        </div>
        <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', palette)}>
          <Icon size={18} />
        </div>
      </div>
    </div>
  )
}

function ListCard({ title, icon: Icon, empty, href, rows, tone }: {
  title: string
  icon: any
  empty: string
  href: string
  rows: Array<{ label: string; value: string }>
  tone: 'emerald' | 'amber'
}) {
  const iconClass = tone === 'emerald' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold text-primary flex items-center gap-2">
          <span className={clsx('w-8 h-8 rounded-lg flex items-center justify-center', iconClass)}>
            <Icon size={17} />
          </span>
          {title}
        </h2>
        <Link href={href} className="text-xs font-semibold text-blue-600 flex items-center gap-1">
          Ver <ArrowRight size={12} />
        </Link>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted py-8 text-center">{empty}</p>
      ) : (
        <div className="space-y-2">
          {rows.map(row => (
            <div key={row.label} className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
              <span className="text-sm text-slate-700 truncate">{row.label}</span>
              <span className="text-sm font-semibold tabular-nums text-slate-900">{row.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
