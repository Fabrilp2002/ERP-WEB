'use client'
import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import {
  Plus, FlaskConical, Calculator, TrendingUp, TrendingDown,
  AlertCircle, Trash2, ChefHat, Beaker, Search,
} from 'lucide-react'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import { recetasApi, inventarioApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'

/**
 * Recetas (Bill of Materials / BOM)
 * =================================
 *
 * Cada producto terminado puede tener UNA receta activa que define
 * que insumos lo componen y en que cantidad. Esto permite:
 *   - Saber el costo real de cada producto terminado
 *   - Calcular el margen automaticamente si hay precio de venta
 *   - Planificar produccion: "¿con el stock actual cuanto puedo hacer?"
 *
 * Ejemplo Esplendida:
 *   Producto: Bronceador FPS 15 (200ml)
 *   Receta v1, rendimiento: 100 unidades por batch
 *   Ingredientes:
 *     - Extracto de Uruku: 500 g
 *     - Aceite de coco: 5 L
 *     - Frasco Oval 200ml: 100 u
 *     - Tapa Disc Top: 100 u
 *     - Etiqueta frente: 100 u
 *     - Etiqueta dorso: 100 u
 */

type Item = {
  id: string
  descripcion: string
  codigo?: string | null
  cantidad_actual: string
  costo_unitario: string
  unidad_medida?: string | null
  es_producto_terminado?: boolean
  precio_venta?: string | null
}

type RecetaItem = {
  id?: string
  insumo_id: string
  insumo_nombre?: string
  insumo_codigo?: string
  insumo_stock_actual?: string
  insumo_costo_unitario?: string
  cantidad: string
  unidad_medida: string
  orden: number
  es_critico: boolean
  notas?: string
  subtotal_costo?: string
}

type Receta = {
  id: string
  empresa_id: string
  producto_id: string
  producto_nombre?: string
  producto_codigo?: string
  producto_precio_venta?: string
  nombre: string
  version: string
  rendimiento: string
  unidad_rendimiento: string
  activa: boolean
  notas?: string
  costo_total_receta?: string
  costo_unitario?: string
  margen_pct?: string
  cantidad_items?: number
  items?: RecetaItem[]
}

function fmt(v: string | number): string {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function fmtDec(v: string | number, dec = 2): string {
  return new Decimal(v || 0).toFixed(dec).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

export default function RecetasPage() {
  const { puedeEscribir } = useAuth()
  const qc = useQueryClient()
  const [editingReceta, setEditingReceta] = useState<Receta | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [buscar, setBuscar] = useState('')

  const { data: recetas = [], isLoading } = useQuery<Receta[]>({
    queryKey: ['recetas', 'all'],
    queryFn: () => recetasApi.listar().then(r => r.data),
  })

  const { data: items = [] } = useQuery<Item[]>({
    queryKey: ['inventario', 'all-for-recetas'],
    queryFn: () => inventarioApi.listar({}).then(r => r.data),
    staleTime: 60_000,
  })

  // Productos terminados (los que pueden tener receta)
  const productos = useMemo(
    () => items.filter(i => i.es_producto_terminado),
    [items],
  )
  // Insumos (todo lo que NO es terminado)
  const insumos = useMemo(
    () => items.filter(i => !i.es_producto_terminado),
    [items],
  )

  const recetasFiltradas = useMemo(() => {
    if (!buscar) return recetas
    const b = buscar.toLowerCase()
    return recetas.filter(r =>
      r.nombre.toLowerCase().includes(b) ||
      (r.producto_nombre || '').toLowerCase().includes(b)
    )
  }, [recetas, buscar])

  const deleteMut = useMutation({
    mutationFn: (id: string) => recetasApi.eliminar(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recetas'] }),
  })

  // Stats globales
  const stats = useMemo(() => {
    const total = recetas.length
    const activas = recetas.filter(r => r.activa).length
    const costoTotal = recetas.reduce(
      (s, r) => s + parseFloat(r.costo_total_receta || '0'),
      0,
    )
    const sinMargen = recetas.filter(r => {
      const m = parseFloat(r.margen_pct || '0')
      return r.activa && (m < 20 || isNaN(m))
    }).length
    return { total, activas, costoTotal, sinMargen }
  }, [recetas])

  return (
    <div className="p-6 md:p-8 space-y-5 pb-20">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <ChefHat size={24} className="text-indigo-500" />
            Recetas de productos
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Composición y costo real de cada producto terminado (Bill of Materials)
          </p>
        </div>
        {puedeEscribir() && (
          <button
            onClick={() => { setEditingReceta(null); setShowCreate(true) }}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> Nueva receta
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Recetas activas" value={stats.activas.toString()} icon="🧪" color="blue" />
        <StatCard label="Productos con receta" value={productos.length.toString()} icon="📦" color="green" />
        <StatCard label="Costo total recetas" value={`Gs. ${fmt(stats.costoTotal.toString())}`} icon="💰" color="amber" />
        <StatCard label="Margen bajo (<20%)" value={stats.sinMargen.toString()} icon="⚠" color="red" />
      </div>

      {/* Buscador */}
      <div className="relative max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          className="input pl-9"
          placeholder="Buscar receta o producto..."
          value={buscar}
          onChange={e => setBuscar(e.target.value)}
        />
      </div>

      {/* Lista de recetas */}
      {isLoading && (
        <div className="grid md:grid-cols-2 gap-3">
          {[1,2,3,4].map(i => (
            <div key={i} className="card animate-pulse h-32 bg-slate-100" />
          ))}
        </div>
      )}

      {!isLoading && recetasFiltradas.length === 0 && (
        <div className="card text-center py-16">
          <div className="text-5xl mb-3">🧪</div>
          <h3 className="text-lg font-semibold text-slate-700 mb-1">
            {buscar ? `Sin resultados para "${buscar}"` : 'No tenés recetas creadas'}
          </h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mb-4">
            Las recetas te dicen exactamente qué insumos lleva cada producto y cuánto cuesta producirlo.
            Por ejemplo: <em>1 Bronceador 150ml = 75ml de aceite + 1 frasco + 1 tapa + 2 etiquetas</em>.
          </p>
          {puedeEscribir() && !buscar && (
            <button
              onClick={() => { setEditingReceta(null); setShowCreate(true) }}
              className="btn-primary inline-flex items-center gap-2"
            >
              <Plus size={16} /> Crear mi primera receta
            </button>
          )}
        </div>
      )}

      {!isLoading && recetasFiltradas.length > 0 && (
        <div className="grid md:grid-cols-2 gap-3">
          {recetasFiltradas.map(receta => (
            <RecetaCard
              key={receta.id}
              receta={receta}
              onEdit={() => { setEditingReceta(receta); setShowCreate(true) }}
              onDelete={() => deleteMut.mutate(receta.id)}
              canWrite={puedeEscribir()}
            />
          ))}
        </div>
      )}

      {/* Modal de creación/edición */}
      {showCreate && (
        <RecetaEditor
          receta={editingReceta}
          productos={productos}
          insumos={insumos}
          allItems={items}
          onClose={() => { setShowCreate(false); setEditingReceta(null) }}
          onSaved={() => {
            qc.invalidateQueries({ queryKey: ['recetas'] })
            qc.invalidateQueries({ queryKey: ['inventario'] })
            setShowCreate(false)
            setEditingReceta(null)
          }}
        />
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// CARD DE RECETA
// ═══════════════════════════════════════════════════════════════════════════

function RecetaCard({ receta, onEdit, onDelete, canWrite }: {
  receta: Receta
  onEdit: () => void
  onDelete: () => void
  canWrite: boolean
}) {
  const costo = parseFloat(receta.costo_unitario || '0')
  const precio = parseFloat(receta.producto_precio_venta || '0')
  const margenPct = parseFloat(receta.margen_pct || '0')
  const hasMargen = precio > 0 && costo > 0

  const margenColor =
    margenPct >= 40 ? 'text-emerald-600' :
    margenPct >= 20 ? 'text-amber-600' :
    'text-rose-600'

  return (
    <div
      className={clsx(
        'bg-white rounded-2xl border-2 p-4 transition-all hover:shadow-lg',
        receta.activa ? 'border-indigo-200' : 'border-slate-200 opacity-60',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-slate-700 truncate">
            {receta.producto_nombre}
          </div>
          <div className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
            <FlaskConical size={11} />
            <span className="truncate">{receta.nombre}</span>
            <span className="bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">
              {receta.version}
            </span>
            {!receta.activa && (
              <span className="bg-rose-100 text-rose-700 px-1.5 py-0.5 rounded text-[10px] font-semibold">
                ARCHIVADA
              </span>
            )}
          </div>
        </div>
        {canWrite && (
          <div className="flex gap-1 flex-shrink-0">
            <button
              onClick={onEdit}
              className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
              title="Editar receta"
            >
              <Beaker size={14} />
            </button>
            <button
              onClick={() => confirm('¿Archivar esta receta?') && onDelete()}
              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
              title="Archivar"
            >
              <Trash2 size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-3 text-center">
        <div className="bg-slate-50 rounded-lg p-2">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Rendimiento</div>
          <div className="text-sm font-bold text-slate-900">
            {fmtDec(receta.rendimiento, 0)} <span className="text-[10px] font-normal">{receta.unidad_rendimiento}</span>
          </div>
          <div className="text-[10px] text-slate-500">por batch</div>
        </div>
        <div className="bg-amber-50 rounded-lg p-2">
          <div className="text-[10px] text-amber-700 uppercase tracking-wider">Costo unit.</div>
          <div className="text-sm font-bold text-amber-700">Gs. {fmt(costo)}</div>
          <div className="text-[10px] text-amber-600">{receta.cantidad_items ?? 0} ingredientes</div>
        </div>
        {hasMargen ? (
          <div className={`rounded-lg p-2 ${margenPct >= 40 ? 'bg-emerald-50' : margenPct >= 20 ? 'bg-amber-50' : 'bg-rose-50'}`}>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Margen</div>
            <div className={`text-sm font-bold ${margenColor}`}>
              {margenPct.toFixed(1)}%
            </div>
            <div className="text-[10px] text-slate-500">vs Gs. {fmt(precio)}</div>
          </div>
        ) : (
          <div className="bg-slate-100 rounded-lg p-2">
            <div className="text-[10px] text-slate-500">Margen</div>
            <div className="text-sm font-bold text-slate-400">—</div>
            <div className="text-[10px] text-slate-500">sin precio venta</div>
          </div>
        )}
      </div>

      {/* Capacidad de producción */}
      <CapacidadInline recetaId={receta.id} rendimiento={parseFloat(receta.rendimiento || '0')} />
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// CAPACIDAD INLINE (consulta el endpoint /capacidad)
// ═══════════════════════════════════════════════════════════════════════════

function CapacidadInline({ recetaId, rendimiento }: { recetaId: string; rendimiento: number }) {
  const { data } = useQuery({
    queryKey: ['receta-capacidad', recetaId],
    queryFn: () => recetasApi.capacidad(recetaId).then(r => r.data),
    staleTime: 30_000,
  })

  if (!data) {
    return <div className="h-9 bg-slate-50 rounded animate-pulse" />
  }

  const batches = data.batches_posibles || 0
  const unidades = data.unidades_posibles || 0
  const limitante = data.insumo_limitante

  if (batches === 0) {
    return (
      <div className="bg-rose-50 border-l-3 border-rose-500 rounded-md p-2 text-[11px] text-rose-800 flex items-start gap-1.5">
        <AlertCircle size={12} className="flex-shrink-0 mt-0.5" />
        <span>
          <strong>No podés producir.</strong>
          {limitante && <> Falta stock de <em>{limitante}</em>.</>}
        </span>
      </div>
    )
  }

  return (
    <div className="bg-emerald-50 border-l-3 border-emerald-500 rounded-md p-2 text-[11px] text-emerald-800">
      <div className="flex items-center justify-between">
        <span><strong>Podés producir {fmt(unidades.toString())} unidades</strong> ({batches} batches)</span>
      </div>
      {limitante && (
        <div className="text-[10px] text-emerald-700 mt-0.5">
          Cuello de botella: <em>{limitante}</em>
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// EDITOR DE RECETA (modal)
// ═══════════════════════════════════════════════════════════════════════════

function RecetaEditor({ receta, productos, insumos, allItems, onClose, onSaved }: {
  receta: Receta | null
  productos: Item[]
  insumos: Item[]
  allItems: Item[]
  onClose: () => void
  onSaved: () => void
}) {
  const [productoId, setProductoId] = useState(receta?.producto_id || '')
  const [nombre, setNombre] = useState(receta?.nombre || '')
  const [version, setVersion] = useState(receta?.version || 'v1')
  const [rendimiento, setRendimiento] = useState(receta?.rendimiento || '1')
  const [unidadRendimiento, setUnidadRendimiento] = useState(receta?.unidad_rendimiento || 'unidad')
  const [notas, setNotas] = useState(receta?.notas || '')
  const [items, setItems] = useState<RecetaItem[]>(
    receta?.items?.map((it, i) => ({ ...it, orden: it.orden ?? i })) || [],
  )
  const [error, setError] = useState('')

  // Cuando NO hay productos terminados, ofrecer "promover" cualquier item del inventario
  const productosOpts = productos.length > 0 ? productos : allItems

  const calcular = useMemo(() => {
    let costoTotal = new Decimal(0)
    for (const it of items) {
      const ins = allItems.find(x => x.id === it.insumo_id)
      if (!ins) continue
      const cant = new Decimal(it.cantidad || 0)
      const costoUnit = new Decimal(ins.costo_unitario || 0)
      costoTotal = costoTotal.add(cant.mul(costoUnit))
    }
    const rend = new Decimal(rendimiento || 1)
    const costoUnitario = rend.gt(0) ? costoTotal.div(rend) : new Decimal(0)
    return { costoTotal, costoUnitario }
  }, [items, rendimiento, allItems])

  const producto = productosOpts.find(p => p.id === productoId)
  const precioVenta = parseFloat(producto?.precio_venta || '0')
  const margenPct = precioVenta > 0 && calcular.costoUnitario.gt(0)
    ? ((precioVenta - calcular.costoUnitario.toNumber()) / precioVenta) * 100
    : null

  const addItem = () => {
    setItems(prev => [...prev, {
      insumo_id: '',
      cantidad: '1',
      unidad_medida: 'unidad',
      orden: prev.length,
      es_critico: false,
    }])
  }

  const updateItem = (idx: number, patch: Partial<RecetaItem>) => {
    setItems(prev => prev.map((it, i) => i === idx ? { ...it, ...patch } : it))
  }

  const removeItem = (idx: number) => {
    setItems(prev => prev.filter((_, i) => i !== idx))
  }

  const saveMut = useMutation({
    mutationFn: async () => {
      if (!productoId) throw new Error('Elegí el producto terminado')
      if (!nombre.trim()) throw new Error('Poné un nombre a la receta')
      if (items.length === 0) throw new Error('Agregá al menos un ingrediente')
      if (items.some(it => !it.insumo_id || parseFloat(it.cantidad) <= 0))
        throw new Error('Hay items incompletos')

      const payload = {
        producto_id: productoId,
        nombre,
        version,
        rendimiento: parseFloat(rendimiento) || 1,
        unidad_rendimiento: unidadRendimiento,
        activa: true,
        notas,
        items: items.map((it, idx) => ({
          insumo_id: it.insumo_id,
          cantidad: parseFloat(it.cantidad) || 0,
          unidad_medida: it.unidad_medida,
          orden: idx,
          es_critico: it.es_critico,
          notas: it.notas,
        })),
      }

      if (receta) {
        return recetasApi.actualizar(receta.id, payload)
      }
      return recetasApi.crear(payload)
    },
    onSuccess: () => onSaved(),
    onError: (err: any) => {
      setError(err?.message || err?.response?.data?.detail || 'No se pudo guardar')
    },
  })

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between flex-shrink-0">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <ChefHat className="text-indigo-500" size={20} />
              {receta ? 'Editar receta' : 'Nueva receta'}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Definí los ingredientes y cantidades necesarias por batch
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-2">✕</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Producto terminado */}
          <div>
            <label className="text-xs font-semibold text-slate-600">Producto terminado *</label>
            <select
              className="input mt-1"
              value={productoId}
              onChange={e => setProductoId(e.target.value)}
              disabled={!!receta}
            >
              <option value="">— Elegir producto —</option>
              {productosOpts.map(p => (
                <option key={p.id} value={p.id}>
                  {p.descripcion} {p.codigo ? `(${p.codigo})` : ''}
                </option>
              ))}
            </select>
            {productos.length === 0 && (
              <p className="text-[11px] text-amber-600 mt-1">
                💡 No tenés productos terminados marcados aún. Cualquier item que elijas se marcará como "producto terminado" al crear la receta.
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="md:col-span-2">
              <label className="text-xs font-semibold text-slate-600">Nombre de la receta *</label>
              <input
                className="input mt-1"
                placeholder="Ej: Bronceador FPS 15 — Fórmula clásica"
                value={nombre}
                onChange={e => setNombre(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Versión</label>
              <input
                className="input mt-1"
                placeholder="v1"
                value={version}
                onChange={e => setVersion(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Rendimiento *</label>
              <div className="flex gap-1 mt-1">
                <input
                  type="number"
                  step="0.0001"
                  className="input flex-1 text-right"
                  value={rendimiento}
                  onChange={e => setRendimiento(e.target.value)}
                />
                <select
                  className="input w-20"
                  value={unidadRendimiento}
                  onChange={e => setUnidadRendimiento(e.target.value)}
                >
                  {['unidad','kg','lt','m2','m3','caja','bolsa','otro'].map(u =>
                    <option key={u} value={u}>{u}</option>
                  )}
                </select>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                Cuántas unidades produce 1 ejecución de esta receta
              </p>
            </div>
          </div>

          {/* Lista de items / ingredientes */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Ingredientes</h3>
                <p className="text-[11px] text-slate-500">Insumos y cantidades por batch</p>
              </div>
              <button
                onClick={addItem}
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 px-3 py-1 hover:bg-indigo-50 rounded-md"
              >
                <Plus size={13} /> Agregar ingrediente
              </button>
            </div>

            {items.length === 0 ? (
              <div className="text-center py-8 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200">
                <div className="text-3xl mb-1">🧪</div>
                <div className="text-sm text-slate-500 mb-2">Sin ingredientes aún</div>
                <button
                  onClick={addItem}
                  className="text-xs font-semibold text-indigo-600 hover:underline"
                >
                  Agregar el primero
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {items.map((it, idx) => (
                  <ItemRow
                    key={idx}
                    item={it}
                    insumos={insumos}
                    onChange={(patch) => updateItem(idx, patch)}
                    onRemove={() => removeItem(idx)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Notas */}
          <div>
            <label className="text-xs font-semibold text-slate-600">Notas (opcional)</label>
            <textarea
              className="input mt-1 min-h-[60px]"
              placeholder="Ej: Mezclar primero los líquidos, agregar Uruku al final..."
              value={notas}
              onChange={e => setNotas(e.target.value)}
            />
          </div>

          {/* Calculadora de costo */}
          <div className="bg-gradient-to-br from-indigo-50 to-pink-50 rounded-xl p-4 border border-indigo-200">
            <div className="flex items-center gap-2 mb-3">
              <Calculator className="text-indigo-600" size={18} />
              <h3 className="text-sm font-bold text-slate-900">Cálculo en vivo</h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
              <div>
                <div className="text-[10px] font-bold text-slate-500 uppercase">Costo total batch</div>
                <div className="text-base font-bold text-slate-900 mt-1">
                  Gs. {fmt(calcular.costoTotal.toString())}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-slate-500 uppercase">Rendimiento</div>
                <div className="text-base font-bold text-slate-900 mt-1">
                  {fmtDec(rendimiento, 0)} {unidadRendimiento}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-amber-700 uppercase">Costo unitario</div>
                <div className="text-base font-bold text-amber-700 mt-1">
                  Gs. {fmt(calcular.costoUnitario.toString())}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-bold text-slate-500 uppercase">Margen</div>
                <div className={clsx(
                  'text-base font-bold mt-1',
                  margenPct === null ? 'text-slate-400' :
                  margenPct >= 40 ? 'text-emerald-600' :
                  margenPct >= 20 ? 'text-amber-600' :
                  'text-rose-600',
                )}>
                  {margenPct === null ? '—' : `${margenPct.toFixed(1)}%`}
                </div>
                {margenPct === null && (
                  <div className="text-[10px] text-slate-400 mt-0.5">cargá precio de venta</div>
                )}
              </div>
            </div>
          </div>

          {error && (
            <div className="bg-rose-50 border border-rose-200 rounded-lg px-3 py-2 text-sm text-rose-700 flex items-center gap-2">
              <AlertCircle size={14} /> {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-3 flex-shrink-0">
          <button onClick={onClose} className="btn-outline">Cancelar</button>
          <button
            onClick={() => saveMut.mutate()}
            disabled={saveMut.isPending}
            className="btn-primary"
          >
            {saveMut.isPending ? 'Guardando…' : (receta ? 'Actualizar receta' : 'Crear receta')}
          </button>
        </div>
      </div>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// FILA DE INGREDIENTE
// ═══════════════════════════════════════════════════════════════════════════

function ItemRow({ item, insumos, onChange, onRemove }: {
  item: RecetaItem
  insumos: Item[]
  onChange: (patch: Partial<RecetaItem>) => void
  onRemove: () => void
}) {
  const ins = insumos.find(i => i.id === item.insumo_id)
  const cant = parseFloat(item.cantidad || '0')
  const costoUnit = parseFloat(ins?.costo_unitario || '0')
  const subtotal = cant * costoUnit

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 grid grid-cols-12 gap-2 items-end">
      <div className="col-span-12 md:col-span-5">
        <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          Insumo
        </label>
        <select
          className="input text-sm mt-0.5"
          value={item.insumo_id}
          onChange={e => {
            const nuevoIns = insumos.find(i => i.id === e.target.value)
            onChange({
              insumo_id: e.target.value,
              unidad_medida: nuevoIns?.unidad_medida || 'unidad',
            })
          }}
        >
          <option value="">— Elegir —</option>
          {insumos.map(i => (
            <option key={i.id} value={i.id}>
              {i.descripcion} {i.codigo ? `(${i.codigo})` : ''}
            </option>
          ))}
        </select>
      </div>
      <div className="col-span-5 md:col-span-2">
        <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          Cantidad
        </label>
        <input
          type="number"
          step="0.0001"
          className="input text-sm text-right mt-0.5"
          value={item.cantidad}
          onChange={e => onChange({ cantidad: e.target.value })}
        />
      </div>
      <div className="col-span-3 md:col-span-2">
        <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          Unidad
        </label>
        <input
          className="input text-sm mt-0.5"
          value={item.unidad_medida}
          onChange={e => onChange({ unidad_medida: e.target.value })}
        />
      </div>
      <div className="col-span-3 md:col-span-2 text-right">
        <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          Subtotal
        </div>
        <div className="font-bold text-sm text-slate-900">
          Gs. {fmt(subtotal)}
        </div>
        {ins && (
          <div className="text-[10px] text-slate-500">
            unit: Gs. {fmt(ins.costo_unitario)}
          </div>
        )}
      </div>
      <div className="col-span-1 flex justify-end">
        <button
          onClick={onRemove}
          className="text-slate-400 hover:text-rose-600 p-1.5 hover:bg-rose-50 rounded-md"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// STAT CARD
// ═══════════════════════════════════════════════════════════════════════════

function StatCard({ label, value, icon, color }: {
  label: string; value: string; icon: string; color: 'blue' | 'green' | 'amber' | 'red'
}) {
  const colors: Record<string, string> = {
    blue:  'border-l-blue-500',
    green: 'border-l-emerald-500',
    amber: 'border-l-amber-500',
    red:   'border-l-rose-500',
  }
  return (
    <div className={`bg-white rounded-xl border border-slate-200 border-l-4 p-3 ${colors[color]}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">{label}</span>
        <span>{icon}</span>
      </div>
      <div className="text-lg font-bold text-slate-900">{value}</div>
    </div>
  )
}
