'use client'
import { useEffect, useState, useMemo, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { pagosApi, api, comprobantesApi } from '@/lib/api'
import {
  ArrowDownCircle, ArrowUpCircle, Wallet, Calendar,
  FileText, Download, Search, Filter, Receipt, Plus, X, Trash2, ChevronDown,
} from 'lucide-react'
import clsx from 'clsx'
import { useConfirm } from '@/hooks/useConfirm'
import { useUndoToast } from '@/hooks/useUndoToast'
import type { Comprobante } from '@/lib/types'

type Tipo = 'todos' | 'cobro' | 'pago'

interface Movimiento {
  id: string
  comprobante_id: string
  numero_comprobante: string
  cliente_id: string | null
  proveedor_id: string | null
  tipo: 'cobro' | 'pago'
  contraparte: string
  contraparte_ruc: string
  numero_recibo: string | null
  fecha_pago: string
  monto_pagado: string | number
  medio_pago: string
  notas: string | null
  ruta_adjunto: string | null
  fecha_creacion: string
  usuario_nombre: string
}

interface Resp {
  movimientos: Movimiento[]
  total_cobros: number
  total_pagos: number
  balance: number
  cantidad: number
}

const formatGs = (v: string | number) =>
  'G. ' + Number(v || 0).toLocaleString('es-PY', { maximumFractionDigits: 0 })

const MEDIOS_LABEL: Record<string, string> = {
  efectivo: 'Efectivo',
  transferencia: 'Transferencia',
  cheque: 'Cheque',
  tarjeta: 'Tarjeta',
  otro: 'Otro',
}

export default function MovimientosPage() {
  const qc = useQueryClient()
  const confirm = useConfirm()
  const mostrarUndo = useUndoToast()
  const [tipo, setTipo] = useState<Tipo>('todos')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [bajando, setBajando] = useState(false)
  const [mostrarRegistro, setMostrarRegistro] = useState(false)
  const [tipoRegistro, setTipoRegistro] = useState<'cobro' | 'pago'>('cobro')
  const [comprobanteId, setComprobanteId] = useState('')
  const [fechaPago, setFechaPago] = useState(() => new Date().toISOString().slice(0, 10))
  const [monto, setMonto] = useState('')
  const [medio, setMedio] = useState('efectivo')
  const [recibo, setRecibo] = useState('')
  const [notas, setNotas] = useState('')
  const [buscarFactura, setBuscarFactura] = useState('')
  const [comboAbierto, setComboAbierto] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('accion') === 'nuevo') {
      const tipoParam = params.get('tipo')
      setTipoRegistro(tipoParam === 'pago' ? 'pago' : 'cobro')
      setMostrarRegistro(true)
    }
  }, [])

  const { data, isLoading } = useQuery<Resp>({
    queryKey: ['movimientos', tipo, desde, hasta],
    queryFn: () =>
      pagosApi
        .movimientos({
          tipo: tipo === 'todos' ? undefined : tipo,
          desde: desde || undefined,
          hasta: hasta || undefined,
        })
        .then(r => r.data),
  })

  const { data: comprobantes = [] } = useQuery<Comprobante[]>({
    queryKey: ['comprobantes', 'pendientes-para-pago'],
    queryFn: () => comprobantesApi.listar({ estado: 'confirmado' }).then(r => r.data),
  })

  const comprobantesPendientes = useMemo(() => {
    const tipoComprobante = tipoRegistro === 'cobro' ? 'venta' : 'compra'
    return comprobantes
      .filter(c => c.tipo === tipoComprobante && Number(c.saldo_pendiente || 0) > 0)
      .sort((a, b) => String(a.fecha_emision).localeCompare(String(b.fecha_emision)))
  }, [comprobantes, tipoRegistro])

  const comprobanteElegido = comprobantesPendientes.find(c => c.id === comprobanteId) || null

  useEffect(() => {
    if (!comprobanteId && comprobantesPendientes.length > 0) {
      setComprobanteId(comprobantesPendientes[0].id)
      setMonto(String(Math.round(Number(comprobantesPendientes[0].saldo_pendiente || 0))))
    }
  }, [comprobanteId, comprobantesPendientes])

  useEffect(() => {
    if (comprobanteElegido) {
      setMonto(String(Math.round(Number(comprobanteElegido.saldo_pendiente || 0))))
    }
  }, [comprobanteElegido])

  const registrarMutation = useMutation({
    mutationFn: () => pagosApi.registrar({
      comprobante_id: comprobanteId,
      fecha_pago: fechaPago,
      monto_pagado: Number(monto || 0),
      medio_pago: medio,
      numero_recibo: recibo.trim() || undefined,
      notas: notas.trim() || undefined,
    }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['movimientos'] })
      qc.invalidateQueries({ queryKey: ['comprobantes'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      setTipo(tipoRegistro)
      setMostrarRegistro(false)
      const prevComprobanteId = comprobanteId
      const prevMonto = monto
      const prevContraparte = comprobanteElegido?.contraparte
      setComprobanteId('')
      setMonto('')
      setRecibo('')
      setNotas('')
      const pagoId: string | undefined = res?.data?.id
      mostrarUndo({
        mensaje: tipoRegistro === 'cobro' ? 'Cobro registrado' : 'Pago registrado',
        detalle: `G. ${Number(prevMonto || 0).toLocaleString('es-PY')} · ${prevContraparte ?? ''}`,
        onUndo: pagoId ? async () => {
          await pagosApi.eliminar(pagoId)
          qc.invalidateQueries({ queryKey: ['movimientos'] })
          qc.invalidateQueries({ queryKey: ['comprobantes'] })
          qc.invalidateQueries({ queryKey: ['dashboard'] })
        } : undefined,
      })
      void prevComprobanteId
    },
  })

  const eliminarMutation = useMutation({
    mutationFn: (id: string) => pagosApi.eliminar(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['movimientos'] })
      qc.invalidateQueries({ queryKey: ['comprobantes'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const filtrados = useMemo(() => {
    if (!data?.movimientos) return []
    const q = busqueda.trim().toLowerCase()
    if (!q) return data.movimientos
    return data.movimientos.filter(m =>
      m.contraparte?.toLowerCase().includes(q) ||
      m.numero_comprobante?.toLowerCase().includes(q) ||
      m.numero_recibo?.toLowerCase().includes(q) ||
      m.contraparte_ruc?.toLowerCase().includes(q),
    )
  }, [data, busqueda])

  const descargarExcel = async () => {
    setBajando(true)
    try {
      const resp = await api.get('/export/movimientos', {
        params: { desde: desde || undefined, hasta: hasta || undefined },
        responseType: 'blob',
      })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      const disp = resp.headers['content-disposition'] || ''
      const match = disp.match(/filename="?([^"]+)"?/)
      a.download = match ? match[1] : 'Movimientos.xlsx'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      alert('Error al descargar Excel')
    } finally {
      setBajando(false)
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <Wallet size={22} /> Movimientos — Cobros y Pagos
          </h1>
          <p className="text-muted text-sm mt-1">
            Registro completo de cada cobro a cliente y pago a proveedor con la contraparte que lo emitió o al que se imputó.
          </p>
        </div>
        <div className="grid w-full grid-cols-1 gap-2 sm:w-auto sm:grid-cols-3">
        <button
          onClick={() => { setTipoRegistro('cobro'); setComprobanteId(''); setBuscarFactura(''); setComboAbierto(false); setMostrarRegistro(true) }}
          className="btn-primary bg-emerald-600 hover:bg-emerald-700 inline-flex w-full items-center gap-2"
        >
          <Plus size={15} /> Cargar cobro
        </button>
        <button
          onClick={() => { setTipoRegistro('pago'); setComprobanteId(''); setBuscarFactura(''); setComboAbierto(false); setMostrarRegistro(true) }}
          className="btn-primary bg-rose-600 hover:bg-rose-700 inline-flex w-full items-center gap-2"
        >
          <Plus size={15} /> Cargar pago
        </button>
        <button
          onClick={descargarExcel}
          disabled={bajando}
          className="btn-primary inline-flex w-full items-center gap-2 disabled:opacity-60"
        >
          <Download size={15} /> {bajando ? 'Generando…' : 'Descargar Excel'}
        </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="card border-l-4 border-l-emerald-500">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-600">
              <ArrowDownCircle size={20} />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Cobros (Ingresos)</p>
              <p className="text-2xl font-bold text-emerald-600">
                {formatGs(data?.total_cobros ?? 0)}
              </p>
            </div>
          </div>
        </div>
        <div className="card border-l-4 border-l-rose-500">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-rose-50 text-rose-600">
              <ArrowUpCircle size={20} />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Pagos (Egresos)</p>
              <p className="text-2xl font-bold text-rose-600">
                {formatGs(data?.total_pagos ?? 0)}
              </p>
            </div>
          </div>
        </div>
        <div className={clsx(
          'card border-l-4',
          (data?.balance ?? 0) >= 0 ? 'border-l-blue-500' : 'border-l-amber-500',
        )}>
          <div className="flex items-center gap-3">
            <div className={clsx(
              'p-2.5 rounded-lg',
              (data?.balance ?? 0) >= 0 ? 'bg-blue-50 text-blue-600' : 'bg-amber-50 text-amber-600',
            )}>
              <Wallet size={20} />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted">Balance</p>
              <p className={clsx(
                'text-2xl font-bold',
                (data?.balance ?? 0) >= 0 ? 'text-blue-600' : 'text-amber-600',
              )}>
                {formatGs(data?.balance ?? 0)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {mostrarRegistro && (
        <div className="card border-l-4 border-l-blue-500">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <h2 className="font-semibold text-primary flex items-center gap-2">
                {tipoRegistro === 'cobro' ? <ArrowDownCircle size={18} /> : <ArrowUpCircle size={18} />}
                {tipoRegistro === 'cobro' ? 'Cargar cobro de cliente' : 'Cargar pago a proveedor'}
              </h2>
              <p className="text-xs text-muted mt-1">
                Elegi una factura pendiente, registra el monto y se actualiza el saldo.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setMostrarRegistro(false)}
              className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              title="Cerrar"
            >
              <X size={16} />
            </button>
          </div>

          <div className="flex gap-1 mb-4">
            {(['cobro', 'pago'] as const).map(t => (
              <button
                key={t}
                type="button"
                onClick={() => { setTipoRegistro(t); setComprobanteId(''); setBuscarFactura(''); setComboAbierto(false) }}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                  tipoRegistro === t
                    ? t === 'cobro' ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
                )}
              >
                {t === 'cobro' ? 'Cobro' : 'Pago'}
              </button>
            ))}
          </div>

          {comprobantesPendientes.length === 0 ? (
            <div className="rounded-lg bg-slate-50 border border-slate-200 p-4 text-sm text-muted">
              No hay facturas {tipoRegistro === 'cobro' ? 'de venta' : 'de compra'} confirmadas con saldo pendiente.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
              <div className="sm:col-span-2">
                <label className="text-xs font-medium text-muted">Factura pendiente</label>
                <FacturaCombobox
                  opciones={comprobantesPendientes}
                  valor={comprobanteId}
                  buscar={buscarFactura}
                  onBuscar={setBuscarFactura}
                  abierto={comboAbierto}
                  onToggle={() => setComboAbierto(v => !v)}
                  onSelect={(id) => {
                    setComprobanteId(id)
                    setComboAbierto(false)
                    setBuscarFactura('')
                  }}
                  formatGs={formatGs}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-muted">Fecha</label>
                <input className="input-field mt-1 w-full" type="date" value={fechaPago} onChange={e => setFechaPago(e.target.value)} />
              </div>
              <div>
                <label className="text-xs font-medium text-muted">Monto</label>
                <input
                  className="input-field mt-1 w-full font-mono"
                  type="number"
                  min={1}
                  max={Number(comprobanteElegido?.saldo_pendiente || 0)}
                  value={monto}
                  onChange={e => setMonto(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-muted">Medio</label>
                <select className="input-field mt-1 w-full" value={medio} onChange={e => setMedio(e.target.value)}>
                  <option value="efectivo">Efectivo</option>
                  <option value="transferencia">Transferencia</option>
                  <option value="cheque">Cheque</option>
                  <option value="tarjeta">Tarjeta</option>
                  <option value="otro">Otro</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-muted">Nro. recibo</label>
                <input className="input-field mt-1 w-full" value={recibo} onChange={e => setRecibo(e.target.value)} />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-medium text-muted">Notas</label>
                <input className="input-field mt-1 w-full" value={notas} onChange={e => setNotas(e.target.value)} placeholder="Referencia, banco, observacion..." />
              </div>
              <button
                type="button"
                disabled={
                  registrarMutation.isPending ||
                  !comprobanteId ||
                  !fechaPago ||
                  Number(monto || 0) <= 0 ||
                  Number(monto || 0) > Number(comprobanteElegido?.saldo_pendiente || 0)
                }
                onClick={async () => {
                  const c = comprobanteElegido
                  const ok = await confirm({
                    titulo: tipoRegistro === 'cobro' ? '¿Confirmar cobro?' : '¿Confirmar pago?',
                    descripcion: `₲ ${Number(monto || 0).toLocaleString('es-PY')} · ${c?.contraparte ?? c?.numero_comprobante ?? ''}`,
                    labelConfirmar: tipoRegistro === 'cobro' ? 'Sí, registrar cobro' : 'Sí, registrar pago',
                  })
                  if (ok) registrarMutation.mutate()
                }}
                className={clsx(
                  'btn-primary inline-flex w-full items-center justify-center gap-2 disabled:opacity-60',
                  tipoRegistro === 'cobro' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700',
                )}
              >
                {registrarMutation.isPending ? 'Guardando...' : tipoRegistro === 'cobro' ? 'Registrar cobro' : 'Registrar pago'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Filtros */}
      <div className="card">
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="w-full sm:w-auto">
            <label className="text-xs font-medium text-muted flex items-center gap-1">
              <Filter size={12} /> Tipo
            </label>
            <div className="grid grid-cols-3 gap-1 mt-1 sm:flex">
              {(['todos', 'cobro', 'pago'] as Tipo[]).map(t => (
                <button
                  key={t}
                  onClick={() => setTipo(t)}
                  className={clsx(
                    'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                    tipo === t
                      ? t === 'cobro'
                        ? 'bg-emerald-600 text-white'
                        : t === 'pago'
                          ? 'bg-rose-600 text-white'
                          : 'bg-primary-700 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
                  )}
                >
                  {t === 'todos' ? 'Todos' : t === 'cobro' ? 'Solo cobros' : 'Solo pagos'}
                </button>
              ))}
            </div>
          </div>
          <div className="w-full sm:w-auto">
            <label className="text-xs font-medium text-muted flex items-center gap-1">
              <Calendar size={12} /> Desde
            </label>
            <input
              type="date"
              value={desde}
              onChange={e => setDesde(e.target.value)}
              className="input-field mt-1"
            />
          </div>
          <div className="w-full sm:w-auto">
            <label className="text-xs font-medium text-muted flex items-center gap-1">
              <Calendar size={12} /> Hasta
            </label>
            <input
              type="date"
              value={hasta}
              onChange={e => setHasta(e.target.value)}
              className="input-field mt-1"
            />
          </div>
          <div className="w-full sm:flex-1 sm:min-w-[200px]">
            <label className="text-xs font-medium text-muted flex items-center gap-1">
              <Search size={12} /> Buscar contraparte / comprobante / recibo
            </label>
            <input
              type="text"
              value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
              placeholder="ACME, 001-001-0001234, R-0001…"
              className="input-field mt-1 w-full"
            />
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="responsive-table-wide w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600 border-b border-border">
              <tr>
                <th className="text-left px-3 py-2.5">Tipo</th>
                <th className="text-left px-3 py-2.5">Fecha</th>
                <th className="text-left px-3 py-2.5">Contraparte</th>
                <th className="text-left px-3 py-2.5">RUC</th>
                <th className="text-left px-3 py-2.5">N° Comprobante</th>
                <th className="text-left px-3 py-2.5">N° Recibo</th>
                <th className="text-left px-3 py-2.5">Medio</th>
                <th className="text-right px-3 py-2.5">Monto</th>
                <th className="text-left px-3 py-2.5">Usuario</th>
                <th className="px-3 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={10} className="py-10 text-center text-muted">Cargando…</td></tr>
              )}
              {!isLoading && filtrados.length === 0 && (
                <tr><td colSpan={10} className="py-10 text-center text-muted">Sin movimientos con los filtros actuales.</td></tr>
              )}
              {filtrados.map(m => {
                const detalle = m.cliente_id
                  ? `/clientes/${m.cliente_id}`
                  : m.proveedor_id
                    ? `/proveedores/${m.proveedor_id}`
                    : null
                return (
                  <tr key={m.id} className="border-b border-border/50 hover:bg-slate-50/50">
                    <td className="px-3 py-2">
                      <span className={clsx(
                        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                        m.tipo === 'cobro'
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-rose-50 text-rose-700',
                      )}>
                        {m.tipo === 'cobro'
                          ? <><ArrowDownCircle size={11} /> Cobro</>
                          : <><ArrowUpCircle size={11} /> Pago</>
                        }
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">{m.fecha_pago}</td>
                    <td className="px-3 py-2 font-medium">
                      {detalle ? (
                        <Link href={detalle} className="text-blue-600 hover:underline">
                          {m.contraparte}
                        </Link>
                      ) : m.contraparte}
                    </td>
                    <td className="px-3 py-2 text-muted font-mono text-xs">{m.contraparte_ruc || '—'}</td>
                    <td className="px-3 py-2 font-mono text-xs">
                      <span className="inline-flex items-center gap-1">
                        <FileText size={11} /> {m.numero_comprobante}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {m.numero_recibo ? (
                        <span className="inline-flex items-center gap-1">
                          <Receipt size={11} /> {m.numero_recibo}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-3 py-2 capitalize">{MEDIOS_LABEL[m.medio_pago] ?? m.medio_pago}</td>
                    <td className={clsx(
                      'px-3 py-2 text-right font-semibold whitespace-nowrap',
                      m.tipo === 'cobro' ? 'text-emerald-600' : 'text-rose-600',
                    )}>
                      {m.tipo === 'cobro' ? '+ ' : '− '}{formatGs(m.monto_pagado)}
                    </td>
                    <td className="px-3 py-2 text-xs text-muted">{m.usuario_nombre || '—'}</td>
                    <td className="px-3 py-2">
                      <button
                        title="Eliminar movimiento"
                        onClick={async () => {
                          const ok = await confirm({
                            titulo: `¿Eliminar este ${m.tipo === 'cobro' ? 'cobro' : 'pago'}?`,
                            descripcion: `${formatGs(m.monto_pagado)} · ${m.contraparte} — se restaurará el saldo del comprobante.`,
                            labelConfirmar: 'Sí, eliminar',
                            peligro: true,
                          })
                          if (!ok) return
                          // Guardar datos antes de eliminar para poder rehacer
                          const snapshot = { ...m }
                          eliminarMutation.mutate(m.id, {
                            onSuccess: () => {
                              mostrarUndo({
                                mensaje: `${m.tipo === 'cobro' ? 'Cobro' : 'Pago'} eliminado`,
                                detalle: `${formatGs(snapshot.monto_pagado)} · ${snapshot.contraparte}`,
                                onUndo: async () => {
                                  await pagosApi.registrar({
                                    comprobante_id: snapshot.comprobante_id,
                                    fecha_pago: snapshot.fecha_pago,
                                    monto_pagado: Number(snapshot.monto_pagado),
                                    medio_pago: snapshot.medio_pago,
                                    numero_recibo: snapshot.numero_recibo ?? undefined,
                                    notas: snapshot.notas ?? undefined,
                                  })
                                  qc.invalidateQueries({ queryKey: ['movimientos'] })
                                  qc.invalidateQueries({ queryKey: ['comprobantes'] })
                                  qc.invalidateQueries({ queryKey: ['dashboard'] })
                                },
                              })
                            },
                          })
                        }}
                        className="p-1.5 rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {!isLoading && filtrados.length > 0 && (
          <div className="px-3 py-2 bg-slate-50 border-t border-border text-xs text-muted">
            {filtrados.length} movimiento{filtrados.length === 1 ? '' : 's'}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Combobox buscable de facturas pendientes ─────────────────────────────────
function FacturaCombobox({
  opciones,
  valor,
  buscar,
  onBuscar,
  abierto,
  onToggle,
  onSelect,
  formatGs,
}: {
  opciones: Comprobante[]
  valor: string
  buscar: string
  onBuscar: (v: string) => void
  abierto: boolean
  onToggle: () => void
  onSelect: (id: string) => void
  formatGs: (v: string | number) => string
}) {
  const ref = useRef<HTMLDivElement>(null)

  // Cierra al hacer click fuera
  useEffect(() => {
    if (!abierto) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onToggle()
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [abierto, onToggle])

  const filtradas = useMemo(() => {
    const q = buscar.trim().toLowerCase()
    if (!q) return opciones
    return opciones.filter(c =>
      c.numero_comprobante.toLowerCase().includes(q) ||
      (c.contraparte ?? '').toLowerCase().includes(q),
    )
  }, [opciones, buscar])

  const elegida = opciones.find(c => c.id === valor)

  return (
    <div ref={ref} className="relative mt-1">
      {/* Trigger / display del valor elegido */}
      <button
        type="button"
        onClick={onToggle}
        className="input-field w-full flex items-center justify-between gap-2 text-left"
      >
        <span className={clsx('truncate text-sm', !elegida && 'text-slate-400')}>
          {elegida
            ? `${elegida.numero_comprobante} · ${elegida.contraparte || 'Sin contraparte'} · saldo ${formatGs(elegida.saldo_pendiente)}`
            : 'Seleccionar factura…'}
        </span>
        <ChevronDown size={14} className={clsx('shrink-0 text-slate-400 transition-transform', abierto && 'rotate-180')} />
      </button>

      {/* Dropdown */}
      {abierto && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-xl overflow-hidden sm:min-w-[420px]">
          {/* Campo de búsqueda */}
          <div className="p-2 border-b border-slate-100">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                autoFocus
                type="text"
                placeholder="Buscar por número o contraparte…"
                value={buscar}
                onChange={e => onBuscar(e.target.value)}
                className="w-full pl-7 pr-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Lista de opciones */}
          <ul className="max-h-64 overflow-y-auto">
            {filtradas.length === 0 && (
              <li className="px-3 py-4 text-sm text-center text-slate-400">Sin resultados</li>
            )}
            {filtradas.map(c => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  className={clsx(
                    'w-full text-left px-3 py-2.5 hover:bg-slate-50 transition-colors',
                    c.id === valor && 'bg-blue-50',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-slate-700">{c.numero_comprobante}</span>
                    <span className="text-xs font-semibold text-amber-700">Saldo: {formatGs(c.saldo_pendiente)}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 truncate">{c.contraparte || 'Sin contraparte'}</p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
