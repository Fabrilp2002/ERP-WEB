'use client'
import { useState, useEffect, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { comprobantesApi, clientesApi, proveedoresApi } from '@/lib/api'
import { X, Plus, Trash2, ScanLine } from 'lucide-react'
import Decimal from 'decimal.js'
import type { Comprobante, TipoComprobante } from '@/lib/types'

interface Linea {
  descripcion: string
  cantidad: string
  precio_unitario: string
  porcentaje_iva: string
}

type NotaTipo = 'credito' | 'debito'

type Props = {
  onClose: () => void
  origen?: Comprobante | null
  notaTipo?: NotaTipo
}

function normalizar(s: string) {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

function formato(v: Decimal) {
  return v.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

export default function NuevoComprobanteModal({ onClose, origen = null, notaTipo }: Props) {
  const qc = useQueryClient()
  const esNota = Boolean(origen && notaTipo)
  const [tipo, setTipo] = useState<'cliente' | 'proveedor'>(
    origen?.cliente_id ? 'cliente' : 'proveedor'
  )
  const [condicion, setCondicion] = useState<'contado' | 'credito'>('credito')
  const [medioPago, setMedioPago] = useState('efectivo')
  const [ocrCargado, setOcrCargado] = useState(false)
  const [form, setForm] = useState({
    numero_comprobante: '',
    fecha_emision: new Date().toISOString().split('T')[0],
    fecha_vencimiento: '',
    cliente_id: origen?.cliente_id ?? '',
    proveedor_id: origen?.proveedor_id ?? '',
    metodo_carga: 'manual',
    notas: esNota
      ? `Nota de ${notaTipo === 'credito' ? 'credito' : 'debito'} vinculada a ${origen?.numero_comprobante}`
      : '',
  })
  const [lineas, setLineas] = useState<Linea[]>([
    {
      descripcion: esNota
        ? `Nota de ${notaTipo === 'credito' ? 'credito' : 'debito'} sobre ${origen?.numero_comprobante}`
        : '',
      cantidad: '1',
      precio_unitario: '0',
      porcentaje_iva: '10',
    },
  ])

  useEffect(() => {
    if (esNota) return
    try {
      const raw = sessionStorage.getItem('ocr_datos')
      if (!raw) return
      const datos = JSON.parse(raw)
      sessionStorage.removeItem('ocr_datos')

      setOcrCargado(true)
      setForm(prev => ({
        ...prev,
        numero_comprobante: datos.numero_comprobante || prev.numero_comprobante,
        fecha_emision: datos.fecha_emision || prev.fecha_emision,
        metodo_carga: 'ocr_imagen',
        notas: `OCR (${datos.motor_usado || '?'}) - Confianza: ${((datos.confianza || 0) * 100).toFixed(0)}%`,
      }))

      if (datos.items?.length) {
        setLineas(datos.items.map((it: { descripcion: string; cantidad: number; precio_unitario: number; porcentaje_iva: number }) => ({
          descripcion: it.descripcion || '',
          cantidad: String(it.cantidad || 1),
          precio_unitario: String(it.precio_unitario || 0),
          porcentaje_iva: String(it.porcentaje_iva || 10),
        })))
      }
    } catch { /* ignore */ }
  }, [esNota])

  const { data: tipos = [] } = useQuery<TipoComprobante[]>({
    queryKey: ['tipos-comprobante'],
    queryFn: () => comprobantesApi.tipos().then(r => r.data),
  })
  const { data: clientes = [] } = useQuery({
    queryKey: ['clientes-select'],
    queryFn: () => clientesApi.listar().then(r => r.data),
  })
  const { data: proveedores = [] } = useQuery({
    queryKey: ['proveedores-select'],
    queryFn: () => proveedoresApi.listar().then(r => r.data),
  })

  const tipoSeleccionado = useMemo(() => {
    const objetivo = esNota
      ? `nota ${notaTipo === 'credito' ? 'credito' : 'debito'}`
      : `factura ${tipo === 'cliente' ? 'venta' : 'compra'}`
    return tipos.find(t => {
      const nombre = normalizar(t.nombre)
      return objetivo.split(' ').every(p => nombre.includes(p))
    }) ?? null
  }, [esNota, notaTipo, tipo, tipos])

  const calcTotales = () => {
    let subtotal = new Decimal(0)
    let iva = new Decimal(0)
    let total = new Decimal(0)
    lineas.forEach(l => {
      const cant = new Decimal(l.cantidad || 0)
      const precio = new Decimal(l.precio_unitario || 0)
      const pct = new Decimal(l.porcentaje_iva || 0)
      const bruto = cant.mul(precio)
      const ivaLinea = pct.eq(10)
        ? bruto.div(11)
        : pct.eq(5)
          ? bruto.div(21)
          : new Decimal(0)
      total = total.add(bruto)
      iva = iva.add(ivaLinea)
      subtotal = subtotal.add(bruto.sub(ivaLinea))
    })
    return { subtotal, iva, total }
  }

  const { subtotal, iva, total } = calcTotales()

  const mutation = useMutation({
    mutationFn: (data: object) => comprobantesApi.crear(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['comprobantes'] })
      qc.invalidateQueries({ queryKey: ['historial'] })
      onClose()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!tipoSeleccionado) return
    const { subtotal, iva, total } = calcTotales()
    mutation.mutate({
      ...form,
      tipo_id: tipoSeleccionado.id,
      fecha_vencimiento: condicion === 'credito' && form.fecha_vencimiento ? form.fecha_vencimiento : null,
      cliente_id: tipo === 'cliente' ? form.cliente_id || null : null,
      proveedor_id: tipo === 'proveedor' ? form.proveedor_id || null : null,
      monto_subtotal: subtotal.toFixed(2),
      monto_iva: iva.toFixed(2),
      monto_total: total.toFixed(2),
      condicion,
      medio_pago_contado: condicion === 'contado' ? medioPago : null,
      comprobante_origen_id: origen?.id ?? null,
      detalle: lineas.map(l => ({
        descripcion: l.descripcion,
        cantidad: l.cantidad,
        precio_unitario: l.precio_unitario,
        porcentaje_iva: l.porcentaje_iva,
      })),
    })
  }

  const addLinea = () =>
    setLineas(prev => [...prev, { descripcion: '', cantidad: '1', precio_unitario: '0', porcentaje_iva: '10' }])

  const updateLinea = (i: number, field: keyof Linea, val: string) =>
    setLineas(prev => prev.map((l, idx) => idx === i ? { ...l, [field]: val } : l))

  const removeLinea = (i: number) =>
    setLineas(prev => prev.filter((_, idx) => idx !== i))

  const bloquearSubmit = mutation.isPending || !tipoSeleccionado || total.lte(0)

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-primary">
              {esNota ? `Nueva Nota de ${notaTipo === 'credito' ? 'Credito' : 'Debito'}` : 'Nuevo Comprobante'}
            </h2>
            {ocrCargado && (
              <span className="flex items-center gap-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                <ScanLine size={12} /> Datos OCR
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-surface" aria-label="Cerrar">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="flex gap-3">
            {(['proveedor', 'cliente'] as const).map(t => (
              <button
                key={t}
                type="button"
                disabled={esNota}
                onClick={() => setTipo(t)}
                className={`flex-1 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
                  tipo === t
                    ? 'bg-primary text-white border-primary'
                    : 'bg-white text-muted border-border hover:border-primary'
                } ${esNota ? 'opacity-75 cursor-not-allowed' : ''}`}
              >
                {t === 'proveedor' ? 'Factura de Compra' : 'Factura de Venta'}
              </button>
            ))}
          </div>

          {esNota && origen && (
            <div className="rounded-lg bg-surface border border-border p-3 text-sm">
              <span className="text-muted">Factura origen:</span>{' '}
              <span className="font-mono font-semibold">{origen.numero_comprobante}</span>{' '}
              <span className="text-muted">Saldo actual:</span>{' '}
              <span className="font-mono font-semibold">Gs. {formato(new Decimal(origen.saldo_pendiente || 0))}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Nro. Comprobante *</label>
              <input
                className="input font-mono"
                placeholder="001-001-0000123"
                value={form.numero_comprobante}
                onChange={e => setForm(p => ({ ...p, numero_comprobante: e.target.value }))}
                required
              />
            </div>
            <div>
              <label className="label">Fecha de emision *</label>
              <input
                type="date"
                className="input"
                value={form.fecha_emision}
                onChange={e => setForm(p => ({ ...p, fecha_emision: e.target.value }))}
                required
              />
            </div>
            <div className="col-span-2">
              <label className="label">{tipo === 'proveedor' ? 'Proveedor' : 'Cliente'} *</label>
              <select
                className="input"
                value={tipo === 'proveedor' ? form.proveedor_id : form.cliente_id}
                onChange={e => setForm(p =>
                  tipo === 'proveedor'
                    ? { ...p, proveedor_id: e.target.value }
                    : { ...p, cliente_id: e.target.value }
                )}
                disabled={esNota}
                required
              >
                <option value="">Seleccionar...</option>
                {(tipo === 'proveedor' ? proveedores : clientes).map((c: { id: string; nombre: string }) => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
            </div>
            {!esNota && (
              <>
                <div>
                  <label className="label">Condicion</label>
                  <select className="input" value={condicion} onChange={e => setCondicion(e.target.value as 'contado' | 'credito')}>
                    <option value="credito">Credito</option>
                    <option value="contado">Contado</option>
                  </select>
                </div>
                <div>
                  <label className="label">{condicion === 'credito' ? 'Vencimiento' : 'Medio de pago'}</label>
                  {condicion === 'credito' ? (
                    <input
                      type="date"
                      className="input"
                      value={form.fecha_vencimiento}
                      onChange={e => setForm(p => ({ ...p, fecha_vencimiento: e.target.value }))}
                    />
                  ) : (
                    <select className="input" value={medioPago} onChange={e => setMedioPago(e.target.value)}>
                      <option value="efectivo">Efectivo</option>
                      <option value="transferencia">Transferencia</option>
                      <option value="cheque">Cheque</option>
                      <option value="tarjeta">Tarjeta</option>
                      <option value="otro">Otro</option>
                    </select>
                  )}
                </div>
              </>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="label mb-0">Detalle</label>
              <button type="button" onClick={addLinea}
                className="text-primary-light text-sm flex items-center gap-1 hover:underline">
                <Plus size={14} /> Agregar linea
              </button>
            </div>
            <div className="space-y-2">
              {lineas.map((l, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                  <input className="input col-span-5" placeholder="Descripcion"
                    value={l.descripcion} onChange={e => updateLinea(i, 'descripcion', e.target.value)} required />
                  <input className="input col-span-2 text-right" placeholder="Cantidad"
                    type="number" step="0.0001" min="0.0001"
                    value={l.cantidad} onChange={e => updateLinea(i, 'cantidad', e.target.value)} />
                  <input className="input col-span-2 text-right" placeholder="Precio"
                    type="number" step="0.01" min="0"
                    value={l.precio_unitario} onChange={e => updateLinea(i, 'precio_unitario', e.target.value)} />
                  <select className="input col-span-2"
                    value={l.porcentaje_iva} onChange={e => updateLinea(i, 'porcentaje_iva', e.target.value)}>
                    <option value="0">0%</option>
                    <option value="5">5%</option>
                    <option value="10">10%</option>
                  </select>
                  <button type="button" onClick={() => removeLinea(i)}
                    className="col-span-1 p-1.5 text-red-400 hover:text-red-600 flex justify-center"
                    aria-label="Eliminar linea">
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-surface rounded-lg p-4 space-y-1.5 text-sm">
            <div className="flex justify-between text-muted">
              <span>Subtotal</span><span>Gs. {formato(subtotal)}</span>
            </div>
            <div className="flex justify-between text-muted">
              <span>IVA</span><span>Gs. {formato(iva)}</span>
            </div>
            <div className="flex justify-between font-bold text-primary text-base border-t border-border pt-1.5">
              <span>Total</span><span>Gs. {formato(total)}</span>
            </div>
          </div>

          {!tipoSeleccionado && (
            <p className="text-xs text-red-600">
              No se encontro un tipo de comprobante compatible en el catalogo.
            </p>
          )}

          <div>
            <label className="label">Notas</label>
            <textarea className="input resize-none" rows={2}
              value={form.notas} onChange={e => setForm(p => ({ ...p, notas: e.target.value }))} />
          </div>

          <div className="flex gap-3 justify-end">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary" disabled={bloquearSubmit}>
              {mutation.isPending ? 'Guardando...' : esNota ? 'Guardar nota' : 'Guardar comprobante'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
