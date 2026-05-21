'use client'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { pagosApi } from '@/lib/api'
import {
  ArrowLeft, FileText, Wallet, Calendar, AlertTriangle, CheckCircle2,
  XCircle, Ban, Filter,
} from 'lucide-react'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import AdjuntoViewer from '@/components/AdjuntoViewer'
import AnalisisContraparte, { ScoreBadge, type AnalisisData } from '@/components/AnalisisContraparte'

/**
 * Ficha de detalle de un contacto (cliente o proveedor).
 *
 * Antes vivía en `/cuentas/[tipo]/[id]/page.tsx`; ahora la consumen las
 * páginas `/clientes/[id]` y `/proveedores/[id]` directamente.
 *
 * Reúne tres bloques de la pantalla:
 *   1. Análisis histórico con score 🟢🟡🔴 (AnalisisContraparte)
 *   2. Listado de facturas del contacto
 *   3. Listado de cobros / pagos del contacto
 *
 * Si el contacto tiene muchas facturas (>20), conviene linkear al usuario
 * a `/comprobantes?cliente_id=X` o `?proveedor_id=X` para que use la
 * paginación de esa pantalla.
 */

function fmt(v: string | number) {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}
function fmtFecha(s?: string | null) {
  if (!s) return '—'
  try { return new Date(s).toLocaleDateString('es-PY') } catch { return s }
}

interface Factura {
  id: string
  numero_comprobante: string
  fecha_emision: string
  fecha_vencimiento?: string | null
  monto_total: string
  saldo_pendiente: string
  estado_pago?: 'pagado' | 'no_pagado' | 'pago_parcial' | 'anulado' | 'rechazado' | 'no_aplica' | null
  estado_validacion: 'pendiente_revision' | 'confirmado' | 'rechazado' | 'anulado'
  condicion: 'contado' | 'credito'
  medio_pago_contado?: string | null
  ruta_archivo?: string | null
}
interface Pago {
  id: string
  numero_recibo?: string
  fecha_pago: string
  monto_pagado: string
  medio_pago: string
  notas?: string
  numero_comprobante: string
  ruta_adjunto?: string | null
}

interface Historial {
  nombre: string
  total_facturado: number
  saldo_pendiente: number
  facturas: Factura[]
  pagos: Pago[]
  total_cobrado?: number
  total_pagado?: number
}

type Props = {
  tipo: 'cliente' | 'proveedor'
  id: string
}

export default function ContraparteDetail({ tipo, id }: Props) {
  const router = useRouter()
  const esCliente = tipo === 'cliente'

  const { data, isLoading } = useQuery<Historial>({
    queryKey: ['historial', tipo, id],
    queryFn: () => (esCliente
      ? pagosApi.historialCliente(id).then(r => r.data)
      : pagosApi.historialProveedor(id).then(r => r.data)),
  })

  const { data: analisis } = useQuery<AnalisisData>({
    queryKey: ['analisis', tipo, id],
    queryFn: () => (esCliente
      ? pagosApi.analisisCliente(id).then(r => r.data)
      : pagosApi.analisisProveedor(id).then(r => r.data)),
    staleTime: 60_000,
  })

  const cobradoPagado = esCliente ? (data?.total_cobrado ?? 0) : (data?.total_pagado ?? 0)
  const linkComprobantesFiltrado = esCliente
    ? `/comprobantes?tipo=venta&cliente_id=${id}`
    : `/comprobantes?tipo=compra&proveedor_id=${id}`

  const estadoFactura = (f: Factura) => {
    if (f.estado_pago === 'pagado')
      return { label: 'Pagada', icon: CheckCircle2, cls: 'bg-emerald-100 text-emerald-700' }
    if (f.estado_pago === 'pago_parcial')
      return { label: 'Pago parcial', icon: AlertTriangle, cls: 'bg-amber-100 text-amber-700' }
    if (f.estado_pago === 'no_pagado')
      return { label: 'No pagada', icon: AlertTriangle, cls: 'bg-rose-100 text-rose-700' }
    if (f.estado_validacion === 'anulado')
      return { label: 'Anulada', icon: Ban, cls: 'bg-slate-200 text-slate-600' }
    if (f.estado_validacion === 'rechazado')
      return { label: 'Rechazada', icon: XCircle, cls: 'bg-red-100 text-red-700' }
    if (f.condicion === 'contado')
      return { label: 'Cobrada', icon: CheckCircle2, cls: 'bg-emerald-100 text-emerald-700' }
    if (new Decimal(f.saldo_pendiente).lte(0))
      return { label: 'Cancelada', icon: CheckCircle2, cls: 'bg-emerald-100 text-emerald-700' }
    if (new Decimal(f.saldo_pendiente).lt(f.monto_total))
      return { label: 'Parcial', icon: AlertTriangle, cls: 'bg-amber-100 text-amber-700' }
    return { label: 'Pendiente', icon: AlertTriangle, cls: 'bg-rose-100 text-rose-700' }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
      <button onClick={() => router.back()} className="btn-ghost text-sm inline-flex items-center gap-1.5">
        <ArrowLeft size={14} /> Volver
      </button>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted">
            {esCliente ? 'Cliente' : 'Proveedor'}
          </p>
          <h1 className="text-2xl font-bold text-primary mt-1">{data?.nombre ?? '—'}</h1>
          {analisis?.contraparte?.ruc && (
            <p className="text-sm text-muted mt-0.5">RUC {analisis.contraparte.ruc}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {analisis?.score && <ScoreBadge score={analisis.score} />}
          <Link
            href={linkComprobantesFiltrado}
            className="btn-outline inline-flex items-center gap-1.5 text-sm"
            title="Ver todas las facturas con filtro y paginación"
          >
            <Filter size={14} /> Ver en Facturas
          </Link>
        </div>
      </div>

      {/* ② ③ ④ ⑤ Análisis histórico */}
      {analisis ? (
        <AnalisisContraparte data={analisis} esCliente={esCliente} />
      ) : (
        <div className="grid sm:grid-cols-3 gap-4">
          <div className="card">
            <p className="text-xs text-muted uppercase">Total facturado</p>
            <p className="text-2xl font-bold font-mono">₲ {fmt(data?.total_facturado ?? 0)}</p>
          </div>
          <div className="card">
            <p className="text-xs text-muted uppercase">{esCliente ? 'Total cobrado' : 'Total pagado'}</p>
            <p className="text-2xl font-bold font-mono text-emerald-700">₲ {fmt(cobradoPagado)}</p>
          </div>
          <div className="card">
            <p className="text-xs text-muted uppercase">Saldo pendiente</p>
            <p className={clsx(
              'text-2xl font-bold font-mono',
              new Decimal(data?.saldo_pendiente ?? 0).gt(0) ? 'text-amber-700' : 'text-emerald-700'
            )}>
              ₲ {fmt(data?.saldo_pendiente ?? 0)}
            </p>
          </div>
        </div>
      )}

      {/* Facturas */}
      <div className="card !p-0 overflow-hidden">
        <div className="flex items-center gap-2 p-4 border-b border-border">
          <FileText size={16} className="text-primary" />
          <h2 className="font-semibold text-primary">Facturas ({data?.facturas.length ?? 0})</h2>
        </div>
        {isLoading ? (
          <p className="text-center text-muted py-8">Cargando…</p>
        ) : !data?.facturas.length ? (
          <p className="text-center text-muted py-8">Sin facturas</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="responsive-table w-full text-sm">
              <thead className="bg-surface border-b border-border">
                <tr>
                  <th className="text-left px-4 py-2.5 font-semibold">N° Comprobante</th>
                  <th className="text-left px-4 py-2.5 font-semibold">Fecha</th>
                  <th className="text-left px-4 py-2.5 font-semibold">Vencimiento</th>
                  <th className="text-left px-4 py-2.5 font-semibold">Condición</th>
                  <th className="text-right px-4 py-2.5 font-semibold">Monto total</th>
                  <th className="text-right px-4 py-2.5 font-semibold">Saldo</th>
                  <th className="text-center px-4 py-2.5 font-semibold">Estado</th>
                  <th className="text-center px-4 py-2.5 font-semibold w-14">Adj.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.facturas.map(f => {
                  const est = estadoFactura(f)
                  const Icon = est.icon
                  return (
                    <tr key={f.id} className="hover:bg-surface">
                      <td className="px-4 py-2.5 font-mono font-medium">{f.numero_comprobante}</td>
                      <td className="px-4 py-2.5 text-muted"><Calendar size={12} className="inline mr-1" />{fmtFecha(f.fecha_emision)}</td>
                      <td className="px-4 py-2.5 text-muted">{fmtFecha(f.fecha_vencimiento)}</td>
                      <td className="px-4 py-2.5">
                        <div className="flex flex-col gap-0.5">
                          <span className={clsx(
                            'text-xs px-2 py-0.5 rounded-full font-medium w-fit',
                            f.condicion === 'contado' ? 'bg-sky-100 text-sky-700' : 'bg-violet-100 text-violet-700'
                          )}>
                            {f.condicion === 'contado' ? 'Contado' : 'Crédito'}
                          </span>
                          {f.condicion === 'contado' && f.medio_pago_contado && (
                            <span className="text-[10px] text-sky-700 capitalize pl-2">
                              {f.medio_pago_contado}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono">₲ {fmt(f.monto_total)}</td>
                      <td className={clsx(
                        'px-4 py-2.5 text-right font-mono font-bold',
                        new Decimal(f.saldo_pendiente).gt(0) ? 'text-amber-700' : 'text-emerald-700'
                      )}>
                        ₲ {fmt(f.saldo_pendiente)}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium inline-flex items-center gap-1', est.cls)}>
                          <Icon size={11} /> {est.label}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <AdjuntoViewer url={f.ruta_archivo} compacto label={`Factura ${f.numero_comprobante}`} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Cobros / Pagos */}
      <div className="card !p-0 overflow-hidden">
        <div className="flex items-center gap-2 p-4 border-b border-border">
          <Wallet size={16} className="text-emerald-600" />
          <h2 className="font-semibold text-primary">
            {esCliente ? 'Cobros recibidos' : 'Pagos emitidos'} ({data?.pagos.length ?? 0})
          </h2>
        </div>
        {!data?.pagos.length ? (
          <p className="text-center text-muted py-8">Sin movimientos</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="responsive-table w-full text-sm">
              <thead className="bg-surface border-b border-border">
                <tr>
                  <th className="text-left px-4 py-2.5 font-semibold">Fecha</th>
                  <th className="text-left px-4 py-2.5 font-semibold">Factura</th>
                  <th className="text-left px-4 py-2.5 font-semibold">Recibo</th>
                  <th className="text-left px-4 py-2.5 font-semibold">Medio</th>
                  <th className="text-right px-4 py-2.5 font-semibold">Monto</th>
                  <th className="text-left px-4 py-2.5 font-semibold">Notas</th>
                  <th className="text-center px-4 py-2.5 font-semibold w-14">Adj.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.pagos.map(p => (
                  <tr key={p.id} className="hover:bg-surface">
                    <td className="px-4 py-2.5 text-muted">{fmtFecha(p.fecha_pago)}</td>
                    <td className="px-4 py-2.5 font-mono">{p.numero_comprobante}</td>
                    <td className="px-4 py-2.5 font-mono text-xs">{p.numero_recibo ?? '—'}</td>
                    <td className="px-4 py-2.5 capitalize">{p.medio_pago}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-emerald-700 font-bold">₲ {fmt(p.monto_pagado)}</td>
                    <td className="px-4 py-2.5 text-xs text-muted">{p.notas ?? '—'}</td>
                    <td className="px-4 py-2.5 text-center">
                      <AdjuntoViewer url={p.ruta_adjunto} compacto label={`Recibo ${p.numero_recibo ?? p.numero_comprobante}`} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
