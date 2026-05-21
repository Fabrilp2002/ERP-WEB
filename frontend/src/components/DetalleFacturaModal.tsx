'use client'
import { useQuery } from '@tanstack/react-query'
import { X, Printer, FileText, Receipt, CreditCard, FileMinus } from 'lucide-react'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import { comprobantesApi, pagosApi } from '@/lib/api'
import type { Comprobante, DetalleComprobante } from '@/lib/types'

type Pago = {
  id: string
  numero_recibo?: string | null
  fecha_pago: string
  monto_pagado: string
  medio_pago: string
  notas?: string | null
}

function fmt(v?: string | number | Decimal | null) {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function fmtFecha(v?: string | null) {
  if (!v) return '-'
  try { return new Date(v).toLocaleDateString('es-PY') } catch { return v }
}

function totalPorIva(detalle: DetalleComprobante[] = []) {
  return detalle.reduce<Record<string, { subtotal: Decimal; iva: Decimal }>>((acc, item) => {
    const key = new Decimal(item.porcentaje_iva || 0).toFixed(0)
    if (!acc[key]) acc[key] = { subtotal: new Decimal(0), iva: new Decimal(0) }
    acc[key].subtotal = acc[key].subtotal.add(item.subtotal || 0)
    acc[key].iva = acc[key].iva.add(item.iva_monto || 0)
    return acc
  }, {})
}

export default function DetalleFacturaModal({
  comprobanteId,
  onClose,
}: {
  comprobanteId: string
  onClose: () => void
}) {
  const { data: comprobante, isLoading } = useQuery<Comprobante>({
    queryKey: ['comprobante-detalle', comprobanteId],
    queryFn: () => comprobantesApi.obtener(comprobanteId).then(r => r.data),
  })
  const { data: pagos = [] } = useQuery<Pago[]>({
    queryKey: ['pagos-comprobante', comprobanteId],
    queryFn: () => pagosApi.listarPorComprobante(comprobanteId).then(r => r.data),
  })

  const detalle = comprobante?.detalle ?? []
  const ivaTotales = totalPorIva(detalle)
  const notas = comprobante?.notas_vinculadas ?? []
  const pagado = pagos.reduce((acc, p) => acc.add(p.monto_pagado || 0), new Decimal(0))

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-0 sm:p-4">
      <div className="bg-white w-full h-full sm:h-auto sm:max-h-[92vh] sm:max-w-5xl sm:rounded-xl shadow-xl overflow-hidden flex flex-col">
        <div className="px-4 sm:px-6 py-4 border-b border-border flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-primary flex items-center gap-2">
              <FileText size={20} /> Detalle de comprobante
            </h2>
            <p className="text-xs text-muted font-mono truncate">
              {comprobante?.numero_comprobante ?? 'Cargando...'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => window.print()}
              className="p-2 rounded-lg text-muted hover:bg-surface"
              title="Imprimir"
            >
              <Printer size={18} />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-lg text-muted hover:bg-surface"
              aria-label="Cerrar"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {isLoading || !comprobante ? (
          <div className="p-8 text-center text-muted">Cargando detalle...</div>
        ) : (
          <div className="overflow-y-auto p-4 sm:p-6 space-y-5">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-lg bg-surface p-3">
                <p className="text-xs uppercase text-muted">Contraparte</p>
                <p className="font-semibold text-primary truncate">{comprobante.contraparte ?? '-'}</p>
              </div>
              <div className="rounded-lg bg-surface p-3">
                <p className="text-xs uppercase text-muted">Fecha</p>
                <p className="font-semibold text-primary">{fmtFecha(comprobante.fecha_emision)}</p>
              </div>
              <div className="rounded-lg bg-surface p-3">
                <p className="text-xs uppercase text-muted">Total</p>
                <p className="font-mono font-bold text-primary">Gs. {fmt(comprobante.monto_total)}</p>
              </div>
              <div className="rounded-lg bg-surface p-3">
                <p className="text-xs uppercase text-muted">Saldo</p>
                <p className={clsx(
                  'font-mono font-bold',
                  new Decimal(comprobante.saldo_pendiente || 0).gt(0) ? 'text-amber-700' : 'text-emerald-700'
                )}>
                  Gs. {fmt(comprobante.saldo_pendiente)}
                </p>
              </div>
            </div>

            <section className="space-y-3">
              <h3 className="font-semibold text-primary">Items</h3>
              <div className="hidden md:block overflow-x-auto border border-border rounded-lg">
                <table className="responsive-table w-full text-sm">
                  <thead className="bg-surface">
                    <tr>
                      <th className="text-left px-3 py-2">Descripcion</th>
                      <th className="text-right px-3 py-2">Cant.</th>
                      <th className="text-right px-3 py-2">Precio</th>
                      <th className="text-right px-3 py-2">IVA</th>
                      <th className="text-right px-3 py-2">Subtotal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {detalle.map(item => (
                      <tr key={item.id}>
                        <td className="px-3 py-2">{item.descripcion}</td>
                        <td className="px-3 py-2 text-right font-mono">{item.cantidad}</td>
                        <td className="px-3 py-2 text-right font-mono">Gs. {fmt(item.precio_unitario)}</td>
                        <td className="px-3 py-2 text-right">{new Decimal(item.porcentaje_iva || 0).toFixed(0)}%</td>
                        <td className="px-3 py-2 text-right font-mono">Gs. {fmt(item.subtotal)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="md:hidden space-y-2">
                {detalle.map(item => (
                  <div key={item.id} className="rounded-lg border border-border p-3">
                    <p className="font-medium text-primary">{item.descripcion}</p>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted">
                      <span>Cant. {item.cantidad}</span>
                      <span>IVA {new Decimal(item.porcentaje_iva || 0).toFixed(0)}%</span>
                      <span>Precio Gs. {fmt(item.precio_unitario)}</span>
                      <span className="font-semibold text-primary">Subtotal Gs. {fmt(item.subtotal)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <div className="grid gap-4 lg:grid-cols-3">
              <section className="rounded-lg border border-border p-4">
                <h3 className="font-semibold text-primary mb-3">Resumen IVA</h3>
                <div className="space-y-2 text-sm">
                  {Object.entries(ivaTotales).map(([pct, data]) => (
                    <div key={pct} className="flex justify-between gap-3">
                      <span className="text-muted">IVA {pct}%</span>
                      <span className="font-mono">Base Gs. {fmt(data.subtotal)} / IVA Gs. {fmt(data.iva)}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-lg border border-border p-4">
                <h3 className="font-semibold text-primary mb-3 flex items-center gap-2">
                  <CreditCard size={16} /> Pagos
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted">Total pagado</span>
                    <span className="font-mono font-semibold text-emerald-700">Gs. {fmt(pagado.toString())}</span>
                  </div>
                  {pagos.length ? pagos.map(p => (
                    <div key={p.id} className="border-t border-border pt-2">
                      <p className="font-mono text-xs">{p.numero_recibo || 'Sin recibo'} - {fmtFecha(p.fecha_pago)}</p>
                      <p className="text-xs text-muted capitalize">{p.medio_pago} / Gs. {fmt(p.monto_pagado)}</p>
                    </div>
                  )) : <p className="text-xs text-muted">Sin pagos registrados.</p>}
                </div>
              </section>

              <section className="rounded-lg border border-border p-4">
                <h3 className="font-semibold text-primary mb-3 flex items-center gap-2">
                  <FileMinus size={16} /> Notas vinculadas
                </h3>
                <div className="space-y-2 text-sm">
                  {notas.length ? notas.map(n => (
                    <div key={n.id} className="rounded-lg bg-surface p-2">
                      <p className="font-mono text-xs">{n.numero_comprobante}</p>
                      <p className="text-xs text-muted">{n.tipo_nombre ?? 'Nota'} / {fmtFecha(n.fecha_emision)}</p>
                      <p className="font-mono text-sm font-semibold">Gs. {fmt(n.monto_total)}</p>
                      {n.notas && <p className="text-xs text-muted mt-1">{n.notas}</p>}
                    </div>
                  )) : <p className="text-xs text-muted">Sin notas vinculadas.</p>}
                </div>
              </section>
            </div>

            {comprobante.notas && (
              <section className="rounded-lg bg-surface p-4">
                <h3 className="font-semibold text-primary mb-1">Notas internas</h3>
                <p className="text-sm text-muted">{comprobante.notas}</p>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
