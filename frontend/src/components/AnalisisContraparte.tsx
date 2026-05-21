'use client'
import { useState, useEffect } from 'react'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import { AlertCircle, TrendingDown, PackageX, X, Info } from 'lucide-react'

export interface AnalisisData {
  contraparte: { id: string; rol: 'cliente' | 'proveedor'; nombre: string; ruc?: string | null; fecha_alta?: string | null }
  resumen: {
    cantidad_facturas: number
    total_facturado: string
    total_devoluciones: string
    total_cargos_extra: string
    compra_neta: string
    ya_cobrado: string
    saldo_pendiente: string
    porcentaje_devolucion: number
  }
  habitos_pago: {
    promedio_dias: number | null
    mejor_dias: number | null
    peor_dias: number | null
    plazo_promedio_dias: number | null
    medio_favorito: string | null
    porcentaje_medio_favorito: number
    ultima_compra: string | null
    dias_desde_ultima_compra: number | null
    tiene_saldo_60_mas: boolean
  }
  score: { color: 'verde' | 'amarillo' | 'rojo' | 'gris'; puntos: number | null; razones: string[] }
  top_productos: { producto: string; cantidad: string; ventas: number; total: string }[]
  devoluciones: {
    top_productos: { producto: string; veces: number; cantidad: string; monto: string }[]
    notas_credito: { id: string; numero: string; fecha: string | null; monto: string; factura_origen_numero?: string | null; factura_origen_id?: string | null }[]
  }
  cargos_extra: {
    notas_debito: { id: string; numero: string; fecha: string | null; monto: string; factura_origen_numero?: string | null; factura_origen_id?: string | null }[]
  }
}

function fmt(v: string | number) {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}
function fmtFecha(s?: string | null) {
  if (!s) return '—'
  try { return new Date(s).toLocaleDateString('es-PY') } catch { return s }
}

const COLOR_BADGE: Record<AnalisisData['score']['color'], { bg: string; text: string; emoji: string; label: string }> = {
  verde:    { bg: 'bg-emerald-100 border-emerald-300', text: 'text-emerald-800', emoji: '🟢', label: 'Saludable' },
  amarillo: { bg: 'bg-amber-100 border-amber-300',    text: 'text-amber-800',    emoji: '🟡', label: 'A revisar' },
  rojo:     { bg: 'bg-rose-100 border-rose-300',      text: 'text-rose-800',     emoji: '🔴', label: 'Riesgo' },
  gris:     { bg: 'bg-slate-100 border-slate-300',    text: 'text-slate-700',    emoji: '⚪', label: 'Sin datos' },
}

export function ScoreBadge({ score }: { score: AnalisisData['score'] }) {
  const [abierto, setAbierto] = useState(false)
  const cfg = COLOR_BADGE[score.color]
  return (
    <div className="relative inline-block">
      <button
        onClick={() => setAbierto(v => !v)}
        className={clsx(
          'inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-sm font-semibold transition',
          cfg.bg, cfg.text, 'hover:shadow-sm',
        )}
        title="Ver por qué"
      >
        <span>{cfg.emoji}</span>
        <span>{cfg.label}</span>
        {score.puntos !== null && (
          <span className="text-xs opacity-75">· {score.puntos}/100</span>
        )}
        <Info size={12} className="opacity-60" />
      </button>
      {abierto && (
        <div className="absolute z-30 left-0 mt-2 w-72 bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-xs text-slate-700">
          <p className="font-semibold text-slate-900 mb-1">Por qué este score</p>
          <ul className="space-y-0.5">
            {score.razones.map((r, i) => (
              <li key={i}>• {r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function AnalisisContraparte({ data, esCliente }: { data: AnalisisData; esCliente: boolean }) {
  const { resumen, habitos_pago: h, devoluciones, top_productos, cargos_extra } = data
  const [modalDev, setModalDev] = useState(false)

  useEffect(() => {
    if (!modalDev) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setModalDev(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [modalDev])

  const tieneDevoluciones = new Decimal(resumen.total_devoluciones).gt(0)
  const tieneCargosExtra = new Decimal(resumen.total_cargos_extra).gt(0)
  const verboCompra = esCliente ? 'compra' : 'compraste'
  const verboPago = esCliente ? 'paga' : 'pagás'

  return (
    <div className="space-y-5">
      {/* ② Resumen del negocio */}
      <section className="card !p-5 space-y-3">
        <p className="text-xs uppercase tracking-widest text-muted">Resumen del negocio</p>
        <div className={clsx(
          'grid gap-4',
          tieneDevoluciones || tieneCargosExtra ? 'grid-cols-2 sm:grid-cols-3' : 'grid-cols-2',
        )}>
          <ResumenItem
            label={esCliente ? 'Total facturado' : 'Total comprado'}
            valor={resumen.total_facturado}
          />
          {tieneDevoluciones && (
            <ResumenItem
              label="Devoluciones"
              valor={resumen.total_devoluciones}
              extra={`${resumen.porcentaje_devolucion.toFixed(1)}%`}
              tone="amber"
            />
          )}
          {tieneCargosExtra && (
            <ResumenItem label="Cargos extra" valor={resumen.total_cargos_extra} tone="violet" />
          )}
          <ResumenItem
            label={esCliente ? 'Compra neta' : 'Compra neta a este proveedor'}
            valor={resumen.compra_neta}
          />
          <ResumenItem
            label={esCliente ? 'Ya cobrado' : 'Ya pagaste'}
            valor={resumen.ya_cobrado}
            tone="emerald"
          />
          <ResumenItem
            label="Saldo pendiente"
            valor={resumen.saldo_pendiente}
            tone={new Decimal(resumen.saldo_pendiente).gt(0) ? 'amber' : 'emerald'}
          />
        </div>
        <p className="text-[11px] text-muted">
          {resumen.cantidad_facturas} factura{resumen.cantidad_facturas === 1 ? '' : 's'} consideradas (sin anuladas ni rechazadas).
        </p>
      </section>

      {/* ③ Hábitos de pago */}
      <section className="card !p-5">
        <p className="text-xs uppercase tracking-widest text-muted mb-2">Hábitos de pago</p>
        {h.promedio_dias !== null ? (
          <p className="text-sm text-slate-700 leading-relaxed">
            {esCliente ? 'Paga' : 'Le pagás'} en promedio en <strong>{h.promedio_dias} días</strong>
            {h.plazo_promedio_dias !== null && (
              <> (plazo otorgado {h.plazo_promedio_dias} d)</>
            )}
            {h.ultima_compra && (
              <> · Última {verboCompra} hace <strong>{h.dias_desde_ultima_compra} días</strong></>
            )}
            {h.medio_favorito && (
              <> · {verboPago.charAt(0).toUpperCase() + verboPago.slice(1)} con <strong className="capitalize">{h.medio_favorito}</strong> ({h.porcentaje_medio_favorito}%)</>
            )}
          </p>
        ) : (
          <p className="text-sm text-muted">Sin pagos registrados todavía.</p>
        )}
        {h.tiene_saldo_60_mas && (
          <p className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-amber-800 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">
            <AlertCircle size={12} /> Tiene facturas vencidas hace más de 60 días
          </p>
        )}
      </section>

      {/* ④ Devoluciones — solo si tiene */}
      {tieneDevoluciones && (
        <section className="card !p-5 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-widest text-muted flex items-center gap-1.5">
              <PackageX size={14} /> Devoluciones
            </p>
            <button
              onClick={() => setModalDev(true)}
              className="text-xs text-primary hover:underline"
            >
              Ver las {devoluciones.notas_credito.length} devolucione{devoluciones.notas_credito.length === 1 ? '' : 's'}
            </button>
          </div>
          <p className="text-sm text-slate-700">
            {esCliente ? 'Te devolvió' : 'Le devolviste'} mercadería <strong>{devoluciones.notas_credito.length} {devoluciones.notas_credito.length === 1 ? 'vez' : 'veces'}</strong> por un total de <strong>₲ {fmt(resumen.total_devoluciones)}</strong> ({resumen.porcentaje_devolucion.toFixed(1)}% de las compras).
          </p>
          {devoluciones.top_productos.length > 0 && (
            <table className="w-full text-sm border-t border-border">
              <thead>
                <tr className="text-muted text-xs">
                  <th className="text-left py-1.5 font-medium">Producto</th>
                  <th className="text-right py-1.5 font-medium">Veces</th>
                  <th className="text-right py-1.5 font-medium">Cantidad</th>
                  <th className="text-right py-1.5 font-medium">Valor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {devoluciones.top_productos.map((d, i) => (
                  <tr key={i}>
                    <td className="py-1.5">{d.producto}</td>
                    <td className="py-1.5 text-right font-mono text-xs">{d.veces}</td>
                    <td className="py-1.5 text-right font-mono text-xs">{fmt(d.cantidad)}</td>
                    <td className="py-1.5 text-right font-mono">₲ {fmt(d.monto)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {/* ⑤ Productos top */}
      {top_productos.length > 0 && (
        <section className="card !p-5 space-y-3">
          <p className="text-xs uppercase tracking-widest text-muted flex items-center gap-1.5">
            <TrendingDown size={14} className="rotate-180" /> Productos que {esCliente ? 'más te compra' : 'más le compraste'}
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted text-xs border-b border-border">
                <th className="text-left py-1.5 font-medium">Producto</th>
                <th className="text-right py-1.5 font-medium">Cantidad</th>
                <th className="text-right py-1.5 font-medium">Facturas</th>
                <th className="text-right py-1.5 font-medium">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {top_productos.map((p, i) => (
                <tr key={i}>
                  <td className="py-1.5">{p.producto}</td>
                  <td className="py-1.5 text-right font-mono text-xs">{fmt(p.cantidad)}</td>
                  <td className="py-1.5 text-right font-mono text-xs">{p.ventas}</td>
                  <td className="py-1.5 text-right font-mono">₲ {fmt(p.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Modal devoluciones completas */}
      {modalDev && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50"
          onClick={() => setModalDev(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-dev-titulo"
        >
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[85vh] overflow-auto shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-border sticky top-0 bg-white">
              <h3 id="modal-dev-titulo" className="font-semibold text-primary">Devoluciones y cargos extra</h3>
              <button
                onClick={() => setModalDev(false)}
                className="p-1 hover:bg-slate-100 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                aria-label="Cerrar modal"
                autoFocus
              >
                <X size={16} aria-hidden="true" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <p className="text-xs uppercase text-muted mb-2">Notas de crédito (devoluciones)</p>
                <ListaDocs items={devoluciones.notas_credito} tone="amber" />
              </div>
              {cargos_extra.notas_debito.length > 0 && (
                <div>
                  <p className="text-xs uppercase text-muted mb-2">Notas de débito (cargos extra)</p>
                  <ListaDocs items={cargos_extra.notas_debito} tone="violet" />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ResumenItem({ label, valor, extra, tone }: { label: string; valor: string; extra?: string; tone?: 'emerald' | 'amber' | 'violet' }) {
  const colors = {
    emerald: 'text-emerald-700',
    amber: 'text-amber-700',
    violet: 'text-violet-700',
  } as const
  return (
    <div>
      <p className="text-xs text-muted uppercase">{label}</p>
      <p className={clsx('text-xl font-bold font-mono mt-0.5', tone ? colors[tone] : 'text-slate-900')}>
        ₲ {fmt(valor)}
      </p>
      {extra && <p className="text-[11px] text-muted">{extra}</p>}
    </div>
  )
}

function ListaDocs({ items, tone }: { items: AnalisisData['devoluciones']['notas_credito']; tone: 'amber' | 'violet' }) {
  const bg = tone === 'amber' ? 'bg-amber-50 border-amber-200' : 'bg-violet-50 border-violet-200'
  if (!items.length) return <p className="text-sm text-muted italic">Sin registros</p>
  return (
    <ul className="space-y-1.5">
      {items.map((d) => (
        <li key={d.id} className={clsx('flex items-center justify-between text-sm border rounded-lg px-3 py-2', bg)}>
          <div>
            <p className="font-mono font-medium">{d.numero}</p>
            <p className="text-xs text-muted">
              {fmtFecha(d.fecha)}
              {d.factura_origen_numero && <> · sobre factura {d.factura_origen_numero}</>}
            </p>
          </div>
          <p className="font-mono font-bold">₲ {fmt(d.monto)}</p>
        </li>
      ))}
    </ul>
  )
}
