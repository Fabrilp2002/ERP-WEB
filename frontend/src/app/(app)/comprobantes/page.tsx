'use client'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { clientesApi, comprobantesApi, proveedoresApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import {
  Plus, Search, Eye, Ban, Wallet, FileMinus, FilePlus,
  ArrowDownRight, ArrowUpRight, Camera, Receipt,
  ArrowUp, ArrowDown, ArrowUpDown,
} from 'lucide-react'
import Link from 'next/link'
import clsx from 'clsx'
import type { Comprobante } from '@/lib/types'
import Decimal from 'decimal.js'
import NuevoComprobanteModal from './NuevoComprobanteModal'
import { pagosApi, adjuntosApi } from '@/lib/api'
import AdjuntoViewer from '@/components/AdjuntoViewer'
import DetalleFacturaModal from '@/components/DetalleFacturaModal'
import Paginacion from '@/components/Paginacion'
import { useConfirm } from '@/hooks/useConfirm'
import { useUndoToast } from '@/hooks/useUndoToast'

function fmt(v: string) {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

const ESTADO_BADGE: Record<string, string> = {
  pendiente_revision: 'badge-pendiente',
  confirmado: 'badge-confirmado',
  rechazado: 'badge-rechazado',
  anulado: 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-200 text-slate-700',
}

const ESTADO_LABEL: Record<string, string> = {
  pendiente_revision: 'Pendiente',
  confirmado: 'Confirmado',
  rechazado: 'Rechazado',
  anulado: 'Anulado',
}

const PAGO_BADGE: Record<string, string> = {
  pagado: 'bg-emerald-100 text-emerald-700',
  no_pagado: 'bg-rose-100 text-rose-700',
  pago_parcial: 'bg-amber-100 text-amber-700',
  anulado: 'bg-slate-200 text-slate-700',
  rechazado: 'bg-red-100 text-red-700',
  no_aplica: 'bg-slate-100 text-slate-600',
}

const PAGO_LABEL: Record<string, string> = {
  pagado: 'Pagado',
  no_pagado: 'No pagado',
  pago_parcial: 'Pago parcial',
  anulado: 'Anulado',
  rechazado: 'Rechazado',
  no_aplica: 'No aplica',
}

export default function ComprobantesPage() {
  const { puedeEscribir } = useAuth()
  const qc = useQueryClient()
  const confirm = useConfirm()
  const mostrarUndo = useUndoToast()
  const searchParams = useSearchParams()
  const [buscar, setBuscar] = useState('')
  const [filtroEstado, setFiltroEstado] = useState('')
  const [filtroTipo, setFiltroTipo] = useState<'todas' | 'venta' | 'compra'>(() => {
    const t = searchParams.get('tipo')
    return (t === 'venta' || t === 'compra') ? t : 'todas'
  })
  const [filtroPago, setFiltroPago] = useState(() => searchParams.get('estado_pago') ?? '')
  const [modalAbierto, setModalAbierto] = useState(false)
  const [notaModal, setNotaModal] = useState<{ comprobante: Comprobante; tipo: 'credito' | 'debito' } | null>(null)
  const [detalleId, setDetalleId] = useState<string | null>(null)

  // v7.2 — filtro por contraparte (cliente o proveedor) en formato "cliente:UUID" / "proveedor:UUID"
  const [filtroContraparte, setFiltroContraparte] = useState<string>(() => {
    const c = searchParams.get('cliente_id')
    const p = searchParams.get('proveedor_id')
    if (c) return `cliente:${c}`
    if (p) return `proveedor:${p}`
    return ''
  })

  // Paginación server-side (v7.2)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  // v7.2+ — Ordenamiento por columna (clickeable en el encabezado).
  // Default fecha descendente (lo más reciente primero).
  type SortKey = 'fecha' | 'numero' | 'contraparte' | 'monto' | 'saldo'
  const [sortKey, setSortKey] = useState<SortKey>('fecha')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const orderBy = `${sortKey}_${sortDir}`

  // v7.2+ — Buscador server-side con debounce (matchea número o nombre de
  // cliente/proveedor en el backend). Sin debounce, cada tecla dispara un
  // request — 200ms es buen balance.
  const [buscarDebounced, setBuscarDebounced] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setBuscarDebounced(buscar.trim()), 200)
    return () => clearTimeout(t)
  }, [buscar])

  // Reset a página 1 cuando cambian filtros (sino quedamos en página 5 con 0 resultados)
  useEffect(() => {
    setPage(1)
  }, [filtroEstado, filtroPago, filtroTipo, filtroContraparte, buscarDebounced, sortKey, sortDir, pageSize])

  // Abrir modal automáticamente si viene con datos OCR
  useEffect(() => {
    if (sessionStorage.getItem('ocr_datos')) {
      setModalAbierto(true)
    }
  }, [])

  // Listas de contrapartes (clientes + proveedores) para el filtro de contraparte
  const { data: listaClientes = [] } = useQuery<Array<{ id: string; nombre: string; ruc?: string | null }>>({
    queryKey: ['clientes', 'lista-filtro'],
    queryFn: () => clientesApi.listar().then(r => r.data),
    staleTime: 60_000,
  })
  const { data: listaProveedores = [] } = useQuery<Array<{ id: string; nombre: string; ruc?: string | null }>>({
    queryKey: ['proveedores', 'lista-filtro'],
    queryFn: () => proveedoresApi.listar().then(r => r.data),
    staleTime: 60_000,
  })

  const [clienteId, proveedorId] = (() => {
    if (!filtroContraparte) return [undefined, undefined]
    const [tipo, id] = filtroContraparte.split(':')
    if (tipo === 'cliente') return [id, undefined]
    if (tipo === 'proveedor') return [undefined, id]
    return [undefined, undefined]
  })()

  const { data: pageData, isLoading } = useQuery({
    queryKey: ['comprobantes', filtroEstado, filtroPago, filtroTipo, clienteId, proveedorId, buscarDebounced, orderBy, page, pageSize],
    queryFn: () => {
      const params: Parameters<typeof comprobantesApi.listarPaginado>[0] = {
        page,
        page_size: pageSize,
        order_by: orderBy,
      }
      if (filtroEstado) params.estado = filtroEstado
      if (filtroPago) params.estado_pago = filtroPago
      if (filtroTipo === 'venta' || filtroTipo === 'compra') params.tipo = filtroTipo
      if (clienteId) params.cliente_id = clienteId
      if (proveedorId) params.proveedor_id = proveedorId
      if (buscarDebounced) params.buscar = buscarDebounced
      return comprobantesApi.listarPaginado<Comprobante>(params).then(r => r.data)
    },
  })

  const comprobantes: Comprobante[] = pageData?.items ?? []
  const totalComprobantes = pageData?.total ?? 0
  const sumaTotal = pageData?.suma_monto_total ?? 0
  const sumaSaldo = pageData?.suma_saldo_pendiente ?? 0

  const anularMutation = useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
      comprobantesApi.anular(id, motivo),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['comprobantes'] })
      setAnularModal(null)
      mostrarUndo({ mensaje: 'Factura anulada', detalle: 'La anulación quedó registrada en el sistema.' })
      void id // la anulación no se puede revertir automáticamente sin endpoint específico
    },
  })

  const pagoMutation = useMutation({
    mutationFn: async (data: {
      comprobante_id: string; fecha_pago: string; monto_pagado: number;
      medio_pago: string; numero_recibo?: string; notas?: string;
      archivo?: File | null;
    }) => {
      const { archivo, ...payload } = data
      const res = await pagosApi.registrar(payload)
      const pagoId = res?.data?.id
      if (archivo && pagoId) {
        try { await adjuntosApi.subirPago(pagoId, archivo) }
        catch (e) { console.warn('No se pudo adjuntar imagen del recibo:', e) }
      }
      return res.data
    },
    onSuccess: (data, vars) => {
      qc.invalidateQueries({ queryKey: ['comprobantes'] })
      qc.invalidateQueries({ queryKey: ['movimientos'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      setPagoModal(null)
      const pagoId: string | undefined = data?.id
      const esVenta = pagoModal?.tipo === 'venta'
      mostrarUndo({
        mensaje: esVenta ? 'Cobro registrado' : 'Pago registrado',
        detalle: `G. ${Number(vars.monto_pagado).toLocaleString('es-PY')} · ${pagoModal?.contraparte ?? ''}`,
        onUndo: pagoId ? async () => {
          await pagosApi.eliminar(pagoId)
          qc.invalidateQueries({ queryKey: ['comprobantes'] })
          qc.invalidateQueries({ queryKey: ['movimientos'] })
          qc.invalidateQueries({ queryKey: ['dashboard'] })
        } : undefined,
      })
    },
  })

  const [anularModal, setAnularModal] = useState<Comprobante | null>(null)
  const [motivoAnular, setMotivoAnular] = useState('')
  const [pagoModal, setPagoModal] = useState<Comprobante | null>(null)

  // El buscador y los filtros ya van al backend. Renderizamos directamente
  // la página actual sin filtrar client-side (las búsquedas matchean numero
  // de comprobante O nombre de cliente/proveedor via ILIKE).
  const filtrados = comprobantes

  // Helper para alternar ordenamiento al hacer click en un encabezado.
  // Click sobre la columna activa = toggle asc/desc. Click sobre otra = setea
  // esa columna con dirección por defecto sensible (fecha/monto = desc, texto = asc).
  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'fecha' || key === 'monto' || key === 'saldo' ? 'desc' : 'asc')
    }
  }

  // Banner when arriving from dashboard with pre-applied filter
  const filtroBanner = (() => {
    if (filtroTipo === 'compra' && (filtroPago === 'no_pagado' || filtroPago === 'pago_parcial')) {
      return { msg: 'Mostrando facturas de compra con saldo pendiente', color: 'amber' }
    }
    if (filtroTipo === 'venta' && (filtroPago === 'no_pagado' || filtroPago === 'pago_parcial')) {
      return { msg: 'Mostrando facturas de venta sin cobrar', color: 'blue' }
    }
    return null
  })()

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary">Facturas</h1>
          <p className="text-muted text-sm mt-1">Comprobantes de compra y venta registrados</p>
        </div>
        {puedeEscribir() && (
          <button onClick={() => setModalAbierto(true)} className="btn-primary flex w-full items-center gap-2 sm:w-auto">
            <Plus size={16} /> Nueva factura
          </button>
        )}
      </div>

      {/* Banner de filtro pre-aplicado */}
      {filtroBanner && (
        <div className={`flex flex-col gap-2 rounded-xl px-4 py-2.5 text-sm font-medium sm:flex-row sm:items-center sm:justify-between ${
          filtroBanner.color === 'amber'
            ? 'bg-amber-50 text-amber-800 border border-amber-200'
            : 'bg-blue-50 text-blue-800 border border-blue-200'
        }`}>
          <span>{filtroBanner.msg}</span>
          <button
            className="text-xs underline opacity-70 hover:opacity-100"
            onClick={() => { setFiltroTipo('todas'); setFiltroPago('') }}
          >
            Quitar filtro
          </button>
        </div>
      )}

      {/* Acciones rapidas (estilo globos del dashboard) */}
      {puedeEscribir() && (
        <section>
          <p className="text-sm font-semibold text-slate-700 mb-3 px-1">Que queres hacer?</p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            <QuickActionBtn onClick={() => setModalAbierto(true)} icon={ArrowUpRight} label="Factura de venta" sublabel="manual" color="emerald" />
            <QuickActionBtn onClick={() => setModalAbierto(true)} icon={ArrowDownRight} label="Factura de compra" sublabel="gasto propio" color="rose" />
            <QuickActionLink href="/ocr" icon={Camera} label="Cargar con foto" sublabel="OCR" color="blue" />
            <QuickActionLink href="/movimientos?accion=nuevo&tipo=cobro" icon={Wallet} label="Registrar cobro" sublabel="cliente" color="emerald" />
            <QuickActionLink href="/movimientos?accion=nuevo&tipo=pago" icon={Receipt} label="Registrar pago" sublabel="proveedor" color="amber" />
          </div>
        </section>
      )}

      {/* Tabs Ventas / Compras / Todas */}
      <div className="w-full overflow-x-auto">
      <div className="flex w-max min-w-full gap-1 bg-slate-100 p-1 rounded-xl sm:min-w-0 sm:w-fit">
        {([
          { key: 'todas', label: filtroTipo === 'todas' ? `Todas (${totalComprobantes})` : 'Todas' },
          { key: 'venta', label: filtroTipo === 'venta' ? `Ventas (${totalComprobantes})` : 'Ventas' },
          { key: 'compra', label: filtroTipo === 'compra' ? `Compras (${totalComprobantes})` : 'Compras' },
        ] as const).map(tab => (
          <button
            key={tab.key}
            onClick={() => setFiltroTipo(tab.key)}
            className={clsx(
              'px-4 py-2 text-sm font-medium rounded-lg transition-all',
              filtroTipo === tab.key
                ? 'bg-white shadow-sm text-primary'
                : 'text-slate-500 hover:text-slate-800',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      </div>

      {/* Filtros */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative w-full sm:flex-1 sm:min-w-48">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            className="input pl-9"
            placeholder="Buscar por número, cliente o proveedor…"
            value={buscar}
            onChange={e => setBuscar(e.target.value)}
          />
        </div>
        <select
          className="input w-full sm:w-auto"
          value={filtroEstado}
          onChange={e => setFiltroEstado(e.target.value)}
        >
          <option value="">Todos los estados</option>
          <option value="confirmado">Confirmados</option>
          <option value="rechazado">Rechazados</option>
          <option value="anulado">Anulados</option>
        </select>
        <select
          className="input w-full sm:w-auto"
          value={filtroPago}
          onChange={e => setFiltroPago(e.target.value)}
          title="Filtrar por estado de cobro/pago"
        >
          <option value="">Todos (cobradas y pendientes)</option>
          <option value="no_pagado">Sin cobrar/pagar</option>
          <option value="pago_parcial">Pago parcial</option>
          <option value="pagado">Cobradas / Pagadas</option>
          <option value="anulado">Anuladas</option>
        </select>
        <select
          className="input w-full sm:w-auto sm:min-w-56"
          value={filtroContraparte}
          onChange={e => setFiltroContraparte(e.target.value)}
          title="Filtrar por cliente o proveedor"
        >
          <option value="">Todas las contrapartes</option>
          {listaClientes.length > 0 && (
            <optgroup label="Clientes">
              {listaClientes.map(c => (
                <option key={`cli-${c.id}`} value={`cliente:${c.id}`}>
                  {c.nombre}{c.ruc ? ` · ${c.ruc}` : ''}
                </option>
              ))}
            </optgroup>
          )}
          {listaProveedores.length > 0 && (
            <optgroup label="Proveedores">
              {listaProveedores.map(p => (
                <option key={`prov-${p.id}`} value={`proveedor:${p.id}`}>
                  {p.nombre}{p.ruc ? ` · ${p.ruc}` : ''}
                </option>
              ))}
            </optgroup>
          )}
        </select>
      </div>

      {/* v7.2 — Sub-total de facturas filtradas (la suma del listado = monto real a cobrar/pagar) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="card !py-3">
          <p className="text-xs uppercase text-muted">Facturas filtradas</p>
          <p className="text-xl font-bold font-mono">{totalComprobantes.toLocaleString('es-PY')}</p>
        </div>
        <div className="card !py-3">
          <p className="text-xs uppercase text-muted">Suma total</p>
          <p className="text-xl font-bold font-mono text-slate-900">
            G. {fmt(String(sumaTotal))}
          </p>
        </div>
        <div className="card !py-3">
          <p className="text-xs uppercase text-muted">Saldo pendiente</p>
          <p className={clsx(
            'text-xl font-bold font-mono',
            sumaSaldo > 0 ? 'text-amber-700' : 'text-emerald-700',
          )}>
            G. {fmt(String(sumaSaldo))}
          </p>
        </div>
      </div>

      {/* Tabla */}
      <div className="card !p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="responsive-table-wide w-full text-sm">
            <thead className="bg-surface border-b border-border">
              <tr>
                <SortableTh label="N° / Descripción" sortKey="numero" activeKey={sortKey} dir={sortDir} onToggle={toggleSort} align="left" />
                <SortableTh label="Fecha"            sortKey="fecha"  activeKey={sortKey} dir={sortDir} onToggle={toggleSort} align="left" />
                <SortableTh label="Contraparte"      sortKey="contraparte" activeKey={sortKey} dir={sortDir} onToggle={toggleSort} align="left" />
                <th className="text-center px-4 py-3 font-semibold text-primary">Tipo</th>
                <th className="text-center px-4 py-3 font-semibold text-primary">Cond.</th>
                <SortableTh label="Total / Cobrado / Saldo" sortKey="monto" activeKey={sortKey} dir={sortDir} onToggle={toggleSort} align="right" />
                <th className="text-center px-4 py-3 font-semibold text-primary">Estado</th>
                <th className="text-left px-4 py-3 font-semibold text-primary">Cargado por</th>
                <th className="text-center px-4 py-3 font-semibold text-primary w-14">Adj.</th>
                {puedeEscribir() && (
                  <th className="text-center px-4 py-3 font-semibold text-primary">Acciones</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading && (
                <tr><td colSpan={10} className="text-center py-8 text-muted">Cargando...</td></tr>
              )}
              {!isLoading && filtrados.length === 0 && (
                <tr><td colSpan={10} className="text-center py-8 text-muted">Sin comprobantes</td></tr>
              )}
              {filtrados.map((c: Comprobante) => (
                <tr key={c.id} className="hover:bg-surface transition-colors cursor-pointer" onDoubleClick={() => setDetalleId(c.id)}>
                  <td className="px-4 py-3 align-top">
                    <div className="font-mono font-medium">{c.numero_comprobante}</div>
                    {(c.descripcion || c.notas) && (
                      <div className="text-[11px] text-slate-500 mt-0.5 max-w-[260px] truncate" title={c.descripcion || c.notas || ''}>
                        {c.descripcion || c.notas}
                        {c.cant_items && c.cant_items > 1 ? ` · +${c.cant_items - 1} item${c.cant_items - 1 > 1 ? 's' : ''}` : ''}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-muted align-top">{c.fecha_emision}</td>
                  <td className="px-4 py-3 text-sm truncate max-w-[200px] align-top">{c.contraparte ?? '—'}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-bold ${c.tipo === 'venta' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
                      {c.tipo ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex flex-col items-center gap-0.5">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${c.condicion === 'contado' ? 'bg-sky-100 text-sky-700' : 'bg-violet-100 text-violet-700'}`}>
                        {c.condicion ?? 'credito'}
                      </span>
                      {c.condicion === 'contado' && c.medio_pago_contado && (
                        <span className="text-[10px] text-sky-700 capitalize">
                          {c.medio_pago_contado}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right align-top">
                    <div className="font-medium">₲ {fmt(c.monto_total)}</div>
                    <div className="text-[11px] text-emerald-600 mt-0.5">
                      Cobrado: ₲ {fmt(c.monto_pagado || (new Decimal(c.monto_total).minus(c.saldo_pendiente)).toString())}
                    </div>
                    <div className="text-[11px] mt-0.5">
                      {c.condicion === 'contado' && c.estado_validacion !== 'anulado' ? (
                        <span className="text-emerald-600 font-semibold">Saldo: ₲ 0</span>
                      ) : (
                        <span className={new Decimal(c.saldo_pendiente || 0).gt(0) ? 'text-amber-700 font-semibold' : 'text-emerald-600 font-semibold'}>
                          Saldo: ₲ {fmt(c.saldo_pendiente)}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex flex-col items-center gap-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PAGO_BADGE[c.estado_pago || 'no_pagado']}`}>
                        {PAGO_LABEL[c.estado_pago || 'no_pagado']}
                      </span>
                      {c.estado_validacion !== 'confirmado' && (
                        <span className={ESTADO_BADGE[c.estado_validacion]}>
                          {ESTADO_LABEL[c.estado_validacion]}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted whitespace-nowrap">
                    {c.cargado_por ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <AdjuntoViewer
                      url={c.ruta_archivo}
                      compacto
                      label={`Factura ${c.numero_comprobante}`}
                      onQuitar={puedeEscribir() && c.ruta_archivo ? async () => {
                        await adjuntosApi.quitarComprobante(c.id)
                        qc.invalidateQueries({ queryKey: ['comprobantes'] })
                      } : undefined}
                      onReemplazar={puedeEscribir() ? async (f) => {
                        await adjuntosApi.subirComprobante(c.id, f)
                        qc.invalidateQueries({ queryKey: ['comprobantes'] })
                      } : undefined}
                    />
                  </td>
                  {puedeEscribir() && (
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        {c.estado_validacion === 'confirmado' && new Decimal(c.saldo_pendiente || 0).gt(0) && (
                          <button
                            title="Registrar pago / cobro"
                            onClick={() => setPagoModal(c)}
                            className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 transition-colors"
                          >
                            <Wallet size={18} />
                          </button>
                        )}
                        {/* El modal de pago ya tiene su propio "Cancelar";
                            el confirm extra se agrega en el botón submit del modal (ver RegistrarPagoModal) */}
                        {c.estado_validacion === 'confirmado' && !c.comprobante_origen_id && (
                          <>
                            <button
                              title="Nota de credito"
                              onClick={() => setNotaModal({ comprobante: c, tipo: 'credito' })}
                              className="p-1.5 rounded-lg text-amber-600 hover:bg-amber-50 transition-colors"
                            >
                              <FileMinus size={18} />
                            </button>
                            <button
                              title="Nota de debito"
                              onClick={() => setNotaModal({ comprobante: c, tipo: 'debito' })}
                              className="p-1.5 rounded-lg text-sky-600 hover:bg-sky-50 transition-colors"
                            >
                              <FilePlus size={18} />
                            </button>
                          </>
                        )}
                        {c.estado_validacion !== 'anulado' && (
                          <button
                            title="Anular comprobante"
                            onClick={() => { setAnularModal(c); setMotivoAnular('') }}
                            className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-red-600 transition-colors"
                          >
                            <Ban size={18} />
                          </button>
                        )}
                        <button
                          title="Ver detalle"
                          onClick={() => setDetalleId(c.id)}
                          className="p-1.5 rounded-lg text-muted hover:bg-surface transition-colors"
                        >
                          <Eye size={18} />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* Paginación server-side (v7.2) */}
        <Paginacion
          total={totalComprobantes}
          page={page}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
          leftLabel={buscar.trim() ? `${filtrados.length} en página actual matchean "${buscar}"` : undefined}
        />
      </div>

      {modalAbierto && (
        <NuevoComprobanteModal onClose={() => setModalAbierto(false)} />
      )}
      {notaModal && (
        <NuevoComprobanteModal
          origen={notaModal.comprobante}
          notaTipo={notaModal.tipo}
          onClose={() => setNotaModal(null)}
        />
      )}
      {detalleId && (
        <DetalleFacturaModal comprobanteId={detalleId} onClose={() => setDetalleId(null)} />
      )}

      {/* Modal: Anular comprobante */}
      {anularModal && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[calc(100vh-2rem)] overflow-y-auto p-4 sm:p-6 space-y-4">
            <div>
              <h2 className="text-lg font-bold text-red-600 flex items-center gap-2">
                <Ban size={20} /> Anular comprobante
              </h2>
              <p className="text-sm text-muted mt-1">
                Comprobante <span className="font-mono">{anularModal.numero_comprobante}</span> —
                ₲ {fmt(anularModal.monto_total)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900">
              Esta acción marca el comprobante como <b>Anulado</b>. Queda registrado con tu usuario,
              fecha y motivo — no se elimina, pero deja de sumar al saldo.
            </div>
            <div>
              <label className="text-sm font-medium text-primary">Motivo de la anulación *</label>
              <textarea
                className="input mt-1"
                rows={3}
                placeholder="Ej: Duplicado, error de carga, factura sustituida por N° XXXX..."
                value={motivoAnular}
                onChange={e => setMotivoAnular(e.target.value)}
                minLength={5}
                maxLength={500}
              />
              <p className="text-xs text-muted mt-1">{motivoAnular.length}/500 (mínimo 5)</p>
            </div>
            <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
              <button className="btn-secondary w-full sm:w-auto" onClick={() => setAnularModal(null)}>Cancelar</button>
              <button
                className="btn-primary w-full bg-red-600 hover:bg-red-700 sm:w-auto"
                disabled={motivoAnular.trim().length < 5 || anularMutation.isPending}
                onClick={() => anularMutation.mutate({ id: anularModal.id, motivo: motivoAnular.trim() })}
              >
                {anularMutation.isPending ? 'Anulando...' : 'Confirmar anulación'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Registrar pago / cobro */}
      {pagoModal && (
        <RegistrarPagoModal
          comprobante={pagoModal}
          onClose={() => setPagoModal(null)}
          onSubmit={async (data) => {
            const esVenta = pagoModal.tipo === 'venta'
            const ok = await confirm({
              titulo: esVenta ? '¿Confirmar cobro?' : '¿Confirmar pago?',
              descripcion: `Se registrará ${esVenta ? 'un cobro' : 'un pago'} de ₲ ${Number(data.monto_pagado).toLocaleString('es-PY')} sobre la factura ${pagoModal.numero_comprobante}.`,
              labelConfirmar: esVenta ? 'Registrar cobro' : 'Registrar pago',
            })
            if (ok) pagoMutation.mutate({ ...data, comprobante_id: pagoModal.id })
          }}
          pending={pagoMutation.isPending}
        />
      )}
    </div>
  )
}

// ── Botones de acciones rapidas (estilo dashboard) ──────────────────────────
type QuickColor = 'blue' | 'emerald' | 'amber' | 'rose' | 'slate'
const QUICK_PALETTE: Record<QuickColor, string> = {
  blue: 'bg-blue-50 text-blue-700 ring-blue-200',
  emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  amber: 'bg-amber-50 text-amber-700 ring-amber-200',
  rose: 'bg-rose-50 text-rose-700 ring-rose-200',
  slate: 'bg-slate-50 text-slate-700 ring-slate-200',
}

function QuickShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="group flex min-h-[126px] flex-col items-center justify-center gap-2 rounded-2xl bg-white p-3 sm:p-4 ring-1 ring-slate-200 shadow-sm hover:shadow-md hover:-translate-y-0.5 active:scale-95 transition-all cursor-pointer">
      {children}
    </div>
  )
}

function QuickInner({ icon: Icon, label, sublabel, color }: {
  icon: any; label: string; sublabel?: string; color: QuickColor
}) {
  return (
    <>
      <span className={clsx('w-12 h-12 rounded-2xl flex items-center justify-center ring-1 transition-colors', QUICK_PALETTE[color])}>
        <Icon size={22} />
      </span>
      <span className="text-center text-xs sm:text-sm font-semibold text-slate-800 leading-tight">{label}</span>
      {sublabel && <span className="text-[10px] text-slate-500 -mt-1.5 uppercase tracking-wider">{sublabel}</span>}
    </>
  )
}

function QuickActionBtn(props: { onClick: () => void; icon: any; label: string; sublabel?: string; color: QuickColor }) {
  return (
    <button onClick={props.onClick} className="text-left">
      <QuickShell><QuickInner {...props} /></QuickShell>
    </button>
  )
}

function QuickActionLink(props: { href: string; icon: any; label: string; sublabel?: string; color: QuickColor }) {
  return (
    <Link href={props.href}>
      <QuickShell><QuickInner {...props} /></QuickShell>
    </Link>
  )
}

// ── Modal: Registrar Pago ───────────────────────────────────────────────────
type PagoForm = {
  fecha_pago: string
  monto_pagado: number
  medio_pago: string
  numero_recibo?: string
  notas?: string
  archivo?: File | null
}
function RegistrarPagoModal({
  comprobante, onClose, onSubmit, pending,
}: {
  comprobante: Comprobante
  onClose: () => void
  onSubmit: (d: PagoForm) => void
  pending: boolean
}) {
  const saldo = new Decimal(comprobante.saldo_pendiente || 0)
  const [fecha, setFecha] = useState(() => new Date().toISOString().slice(0, 10))
  const [monto, setMonto] = useState<string>(saldo.toFixed(0))
  const [medio, setMedio] = useState('efectivo')
  const [numRecibo, setNumRecibo] = useState('')
  const [notas, setNotas] = useState('')
  const [archivo, setArchivo] = useState<File | null>(null)

  const montoDec = new Decimal(monto || 0)
  const invalido = montoDec.lte(0) || montoDec.gt(saldo) || !fecha

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[calc(100vh-2rem)] overflow-y-auto p-4 sm:p-6 space-y-4">
        <div>
          <h2 className="text-lg font-bold text-emerald-700 flex items-center gap-2">
            <Wallet size={20} /> Registrar pago / cobro
          </h2>
          <p className="text-sm text-muted mt-1">
            Comprobante <span className="font-mono">{comprobante.numero_comprobante}</span>
          </p>
          <div className="mt-2 flex justify-between text-sm">
            <span className="text-muted">Saldo pendiente:</span>
            <span className="font-semibold text-warning">₲ {fmt(comprobante.saldo_pendiente)}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium text-primary">Fecha de pago *</label>
            <input type="date" className="input mt-1" value={fecha} onChange={e => setFecha(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium text-primary">Monto (Gs) *</label>
            <input
              type="number"
              className="input mt-1 font-mono"
              value={monto}
              onChange={e => setMonto(e.target.value)}
              max={saldo.toNumber()}
              min={0}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-primary">Medio de pago</label>
            <select className="input mt-1" value={medio} onChange={e => setMedio(e.target.value)}>
              <option value="efectivo">Efectivo</option>
              <option value="transferencia">Transferencia</option>
              <option value="cheque">Cheque</option>
              <option value="tarjeta">Tarjeta</option>
              <option value="otro">Otro</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-primary">N° recibo (opcional)</label>
            <input className="input mt-1" value={numRecibo} onChange={e => setNumRecibo(e.target.value)} />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs font-medium text-primary">Notas (opcional)</label>
            <input className="input mt-1" value={notas} onChange={e => setNotas(e.target.value)} placeholder="Ej: pago parcial, nota del recibo..." />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs font-medium text-primary">Foto/PDF del recibo (opcional)</label>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,application/pdf"
              className="input mt-1"
              onChange={e => setArchivo(e.target.files?.[0] ?? null)}
            />
            {archivo && <p className="text-[11px] text-muted mt-1">Adjunto: {archivo.name}</p>}
          </div>
        </div>

        {montoDec.gt(saldo) && (
          <p className="text-xs text-red-600">El monto no puede superar el saldo pendiente.</p>
        )}

        <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
          <button className="btn-secondary w-full sm:w-auto" onClick={onClose}>Cancelar</button>
          <button
            className="btn-primary w-full bg-emerald-600 hover:bg-emerald-700 sm:w-auto"
            disabled={invalido || pending}
            onClick={() => onSubmit({
              fecha_pago: fecha,
              monto_pagado: montoDec.toNumber(),
              medio_pago: medio,
              numero_recibo: numRecibo.trim() || undefined,
              notas: notas.trim() || undefined,
              archivo,
            })}
          >
            {pending ? 'Registrando...' : 'Registrar pago'}
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * Encabezado de tabla ordenable. Click → activa la columna y alterna asc/desc.
 * Muestra flechita visual: ▲ si activa+asc, ▼ si activa+desc, doble flecha gris si inactiva.
 */
type SortableSortKey = 'fecha' | 'numero' | 'contraparte' | 'monto' | 'saldo'

function SortableTh({
  label,
  sortKey,
  activeKey,
  dir,
  onToggle,
  align = 'left',
}: {
  label: string
  sortKey: SortableSortKey
  activeKey: SortableSortKey
  dir: 'asc' | 'desc'
  onToggle: (key: SortableSortKey) => void
  align?: 'left' | 'right' | 'center'
}) {
  const isActive = activeKey === sortKey
  const Icon = !isActive ? ArrowUpDown : dir === 'asc' ? ArrowUp : ArrowDown
  const alignCls = align === 'right' ? 'justify-end' : align === 'center' ? 'justify-center' : 'justify-start'
  return (
    <th
      className={clsx(
        'px-4 py-3 font-semibold text-primary select-none',
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left',
      )}
    >
      <button
        type="button"
        onClick={() => onToggle(sortKey)}
        className={clsx(
          'inline-flex items-center gap-1 transition rounded hover:bg-slate-100 px-1 -mx-1',
          alignCls,
          isActive ? 'text-blue-700' : 'text-primary',
        )}
        aria-label={`Ordenar por ${label} ${isActive && dir === 'asc' ? 'descendente' : 'ascendente'}`}
      >
        <span>{label}</span>
        <Icon size={12} className={isActive ? 'text-blue-700' : 'text-slate-400'} />
      </button>
    </th>
  )
}
