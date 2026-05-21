'use client'
import { useMemo, useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { inventarioApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import {
  Plus, Search, AlertTriangle, LayoutGrid, Table as TableIcon,
  X, Edit2, Trash2, Sparkles,
} from 'lucide-react'
import type { ItemInventario } from '@/lib/types'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import ProductCard, { detectCategory } from '@/components/ProductCard'
import StockBar from '@/components/StockBar'
import StockByCategory from '@/components/StockByCategory'

/**
 * Página de Inventario rediseñada.
 *
 * Mejoras v6.1:
 *   - Items ORDENADOS por descripción (alfabético, A→Z)
 *   - Formulario "Nuevo item" con AUTOCOMPLETAR: muestra items existentes
 *     y "plantillas genéricas" sugeridas para cosméticos
 *   - Cada tarjeta tiene botones de EDITAR y ELIMINAR
 *   - Edición inline en modal con todos los campos
 *   - Confirmación antes de eliminar
 */

function fmt(v: string, dec = 2) {
  return new Decimal(v || 0).toFixed(dec).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

type ViewMode = 'cards' | 'table'
type FilterChip = 'todos' | 'critico' | 'bronceador' | 'crema' | 'frasco' | 'tapa' | 'etiqueta' | 'materia_prima'

// Plantillas genéricas para autocompletar — específicas de un laboratorio cosmético
const PLANTILLAS_GENERICAS = [
  // Bronceadores
  { descripcion: 'Bronceador FPS 15 — 100 ml', categoria: 'bronceador', unidad: 'unidad', codigo: 'BRO-15-100' },
  { descripcion: 'Bronceador FPS 30 — 100 ml', categoria: 'bronceador', unidad: 'unidad', codigo: 'BRO-30-100' },
  { descripcion: 'Bronceador FPS 50 — 100 ml', categoria: 'bronceador', unidad: 'unidad', codigo: 'BRO-50-100' },
  { descripcion: 'Bronceador con Uruku — 150 ml', categoria: 'bronceador', unidad: 'unidad', codigo: 'BRO-URK-150' },
  // Cremas
  { descripcion: 'Crema hidratante facial — 50 ml', categoria: 'crema', unidad: 'unidad', codigo: 'CRE-HID-50' },
  { descripcion: 'Crema corporal nutritiva — 200 ml', categoria: 'crema', unidad: 'unidad', codigo: 'CRE-CRP-200' },
  { descripcion: 'Crema antiarrugas — 30 ml', categoria: 'crema', unidad: 'unidad', codigo: 'CRE-ANT-30' },
  // Frascos
  { descripcion: 'Frasco Oval 100 ml B24-410 Blanco',  categoria: 'frasco', unidad: 'unidad', codigo: 'FR-100-BL' },
  { descripcion: 'Frasco Oval 150 ml B24-410 Blanco',  categoria: 'frasco', unidad: 'unidad', codigo: 'FR-150-BL' },
  { descripcion: 'Frasco Oval 200 ml B24-410 Dorado',  categoria: 'frasco', unidad: 'unidad', codigo: 'FR-200-DO' },
  { descripcion: 'Frasco x 400 ml PP Negro B24-415',   categoria: 'frasco', unidad: 'unidad', codigo: 'FR-400-NE' },
  // Tapas
  { descripcion: 'Tapa Disc Top B24-410 Blanco',       categoria: 'tapa', unidad: 'unidad', codigo: 'TA-DT-BL' },
  { descripcion: 'Tapa Disc Top B24-410 Negro',        categoria: 'tapa', unidad: 'unidad', codigo: 'TA-DT-NE' },
  { descripcion: 'Tapa Atomizador B24-410 Blanco',     categoria: 'tapa', unidad: 'unidad', codigo: 'TA-AT-BL' },
  { descripcion: 'Tapa Atomizador B24-410 Dorado',     categoria: 'tapa', unidad: 'unidad', codigo: 'TA-AT-DO' },
  // Etiquetas
  { descripcion: 'Etiqueta Bronceador Uruku — Frente', categoria: 'etiqueta', unidad: 'unidad', codigo: 'ET-BRO-F' },
  { descripcion: 'Etiqueta Bronceador Uruku — Dorso',  categoria: 'etiqueta', unidad: 'unidad', codigo: 'ET-BRO-D' },
  { descripcion: 'Etiqueta Crema Hidratante — Frente', categoria: 'etiqueta', unidad: 'unidad', codigo: 'ET-CRE-F' },
  // Materias primas
  { descripcion: 'Extracto de Uruku',                  categoria: 'materia_prima', unidad: 'kg', codigo: 'MP-URK' },
  { descripcion: 'Aceite de coco',                     categoria: 'materia_prima', unidad: 'lt', codigo: 'MP-COC' },
  { descripcion: 'Glicerina vegetal',                  categoria: 'materia_prima', unidad: 'lt', codigo: 'MP-GLI' },
  { descripcion: 'Aceite de almendras',                categoria: 'materia_prima', unidad: 'lt', codigo: 'MP-ALM' },
  { descripcion: 'Vitamina E',                         categoria: 'materia_prima', unidad: 'kg', codigo: 'MP-VTE' },
  { descripcion: 'Manteca de karité',                  categoria: 'materia_prima', unidad: 'kg', codigo: 'MP-KAR' },
]

const EMPTY_FORM = {
  descripcion: '', codigo: '', unidad_medida: 'unidad',
  cantidad_actual: '0', costo_unitario: '0', punto_reorden: '0',
}

export default function InventarioPage() {
  const { puedeEscribir } = useAuth()
  const qc = useQueryClient()
  const [buscar, setBuscar] = useState('')
  const [filter, setFilter] = useState<FilterChip>('todos')
  const [viewMode, setViewMode] = useState<ViewMode>('cards')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)

  const { data: items = [], isLoading } = useQuery<ItemInventario[]>({
    queryKey: ['inventario', buscar],
    queryFn: () => inventarioApi.listar({ buscar: buscar || undefined }).then(r => r.data),
  })

  const crearMutation = useMutation({
    mutationFn: () => inventarioApi.crear(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventario'] })
      setShowForm(false)
      setForm(EMPTY_FORM)
    },
  })

  const actualizarMutation = useMutation({
    mutationFn: () => inventarioApi.actualizar(editingId!, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventario'] })
      setShowForm(false)
      setEditingId(null)
      setForm(EMPTY_FORM)
    },
  })

  const eliminarMutation = useMutation({
    mutationFn: (id: string) => inventarioApi.eliminar(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventario'] }),
  })

  // Items enriquecidos con categoría detectada, ordenados alfabéticamente
  const enriched = useMemo(() => {
    return items.map(item => {
      const cat = detectCategory(item.descripcion, item.codigo)
      const qty = new Decimal(item.cantidad_actual || 0)
      const min = new Decimal(item.punto_reorden || 0)
      const isCritical = min.gt(0) && qty.lte(min)
      return { ...item, categoria: cat.key, categoriaLabel: cat.label, isCritical }
    }).sort((a, b) => a.descripcion.localeCompare(b.descripcion, 'es', { sensitivity: 'base' }))
  }, [items])

  // Filtrar por chip
  const filtered = useMemo(() => {
    if (filter === 'todos') return enriched
    if (filter === 'critico') return enriched.filter(i => i.isCritical)
    return enriched.filter(i => i.categoria === filter)
  }, [enriched, filter])

  // Stats por categoría
  const stats = useMemo(() => {
    const byCat: Record<string, { count: number; critical: number; valor: number }> = {}
    let totalCritical = 0
    let totalValor = 0
    for (const item of enriched) {
      const key = item.categoria
      if (!byCat[key]) byCat[key] = { count: 0, critical: 0, valor: 0 }
      byCat[key].count++
      if (item.isCritical) { byCat[key].critical++; totalCritical++ }
      const valor = new Decimal(item.cantidad_actual).mul(item.costo_unitario).toNumber()
      byCat[key].valor += valor
      totalValor += valor
    }
    return { byCat, totalCritical, totalValor, total: enriched.length }
  }, [enriched])

  const chipCount = (chip: FilterChip): number => {
    if (chip === 'todos') return enriched.length
    if (chip === 'critico') return stats.totalCritical
    return stats.byCat[chip]?.count ?? 0
  }

  // Autocomplete: combinar plantillas genéricas + items ya existentes
  const sugerencias = useMemo(() => {
    if (!form.descripcion.trim()) return []
    const q = form.descripcion.toLowerCase().trim()
    if (q.length < 2) return []

    const existentes = items
      .filter(i => i.descripcion.toLowerCase().includes(q))
      .map(i => ({
        descripcion: i.descripcion,
        codigo: i.codigo || '',
        unidad: i.unidad_medida || 'unidad',
        categoria: detectCategory(i.descripcion, i.codigo).key,
        existente: true as const,
      }))

    const plantillas = PLANTILLAS_GENERICAS
      .filter(p => p.descripcion.toLowerCase().includes(q))
      .map(p => ({ ...p, existente: false as const }))

    // Existentes primero, después plantillas (limitado a 6 total)
    return [...existentes, ...plantillas]
      .filter((s, i, arr) => arr.findIndex(x => x.descripcion === s.descripcion) === i)
      .slice(0, 6)
  }, [form.descripcion, items])

  const openCreate = () => {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
  }

  const openEdit = (item: any) => {
    setEditingId(item.id)
    setForm({
      descripcion: item.descripcion,
      codigo: item.codigo || '',
      unidad_medida: item.unidad_medida || 'unidad',
      cantidad_actual: String(item.cantidad_actual || 0),
      costo_unitario: String(item.costo_unitario || 0),
      punto_reorden: String(item.punto_reorden || 0),
    })
    setShowForm(true)
  }

  const handleEliminar = (item: any) => {
    if (!confirm(`¿Eliminar "${item.descripcion}" del inventario?\n\nEl item se desactiva pero queda en el historial — los comprobantes antiguos seguirán mostrándolo.`)) return
    eliminarMutation.mutate(item.id)
  }

  const handleAplicarPlantilla = (s: typeof sugerencias[0]) => {
    setForm(prev => ({
      ...prev,
      descripcion: s.descripcion,
      codigo: s.codigo || prev.codigo,
      unidad_medida: s.unidad || prev.unidad_medida,
    }))
  }

  const isEditing = !!editingId
  const guardar = () => isEditing ? actualizarMutation.mutate() : crearMutation.mutate()

  return (
    <div className="p-6 md:p-8 space-y-5 pb-20">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Inventario</h1>
          <p className="text-slate-500 text-sm mt-1">
            {stats.total} items · Gs. {fmt(stats.totalValor.toString(), 0)} en stock
            {stats.totalCritical > 0 && (
              <span className="ml-2 text-rose-600 font-semibold">
                · {stats.totalCritical} bajo mínimo
              </span>
            )}
          </p>
        </div>
        {puedeEscribir() && (
          <button onClick={openCreate} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> Nuevo item
          </button>
        )}
      </div>

      {/* Donut de capital por categoría */}
      {items.length > 0 && <StockByCategory items={items} />}

      {/* Chips de filtro */}
      <div className="flex flex-wrap gap-2">
        <ChipFilter active={filter==='todos'}        onClick={() => setFilter('todos')}        label="Todos"          emoji="📋" count={chipCount('todos')}        color="slate" />
        <ChipFilter active={filter==='critico'}      onClick={() => setFilter('critico')}      label="Stock bajo"     emoji="⚠️" count={chipCount('critico')}      color="red" />
        <ChipFilter active={filter==='bronceador'}   onClick={() => setFilter('bronceador')}   label="Bronceadores"   emoji="🧴" count={chipCount('bronceador')}   color="amber" />
        <ChipFilter active={filter==='crema'}        onClick={() => setFilter('crema')}        label="Cremas"         emoji="🫧" count={chipCount('crema')}        color="pink" />
        <ChipFilter active={filter==='frasco'}       onClick={() => setFilter('frasco')}       label="Frascos"        emoji="🍶" count={chipCount('frasco')}       color="blue" />
        <ChipFilter active={filter==='tapa'}         onClick={() => setFilter('tapa')}         label="Tapas"          emoji="🔒" count={chipCount('tapa')}         color="purple" />
        <ChipFilter active={filter==='etiqueta'}     onClick={() => setFilter('etiqueta')}     label="Etiquetas"      emoji="🏷️" count={chipCount('etiqueta')}     color="emerald" />
        <ChipFilter active={filter==='materia_prima'}onClick={() => setFilter('materia_prima')}label="Materia prima"  emoji="🌿" count={chipCount('materia_prima')}color="orange" />
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 max-w-sm min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9" placeholder="Buscar producto..."
            value={buscar} onChange={e => setBuscar(e.target.value)} />
        </div>
        <span className="text-[11px] text-slate-400 hidden md:inline">
          Ordenados A → Z
        </span>
        <div className="ml-auto inline-flex bg-slate-100 rounded-lg p-1">
          <button onClick={() => setViewMode('cards')}
            className={clsx('px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5',
              viewMode === 'cards' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500')}>
            <LayoutGrid size={13} /> Tarjetas
          </button>
          <button onClick={() => setViewMode('table')}
            className={clsx('px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5',
              viewMode === 'table' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500')}>
            <TableIcon size={13} /> Tabla
          </button>
        </div>
      </div>

      {/* Vista de tarjetas */}
      {viewMode === 'cards' && (
        <>
          {isLoading && (
            <div className="card text-center py-8 text-slate-500">Cargando inventario...</div>
          )}
          {!isLoading && filtered.length === 0 && (
            <div className="card text-center py-12">
              <div className="text-3xl mb-2">📭</div>
              <p className="text-slate-500 text-sm">Sin items en esta categoría</p>
            </div>
          )}
          {!isLoading && filtered.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              {filtered.map(item => (
                <ProductCardWithActions
                  key={item.id}
                  product={item}
                  canWrite={puedeEscribir()}
                  onEdit={() => openEdit(item)}
                  onDelete={() => handleEliminar(item)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Vista de tabla */}
      {viewMode === 'table' && (
        <div className="card !p-0 overflow-hidden overflow-x-auto">
          <table className="responsive-table-wide w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Producto</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Cat.</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Código</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Cantidad</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600 w-32">Stock</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Costo unit.</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Mín.</th>
                {puedeEscribir() && <th className="text-center px-4 py-3 font-semibold text-slate-600">Acciones</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr><td colSpan={8} className="text-center py-8 text-slate-500">Cargando...</td></tr>
              )}
              {filtered.map(item => (
                <tr key={item.id} className={clsx(
                  'hover:bg-slate-50 transition-colors',
                  item.isCritical && 'bg-rose-50/30',
                )}>
                  <td className="px-4 py-3 font-medium text-slate-900">{item.descripcion}</td>
                  <td className="px-4 py-3"><span className="text-xs text-slate-500">{item.categoriaLabel}</span></td>
                  <td className="px-4 py-3 text-slate-500 font-mono text-xs">{item.codigo ?? '—'}</td>
                  <td className={clsx('px-4 py-3 text-right font-bold',
                    item.isCritical ? 'text-rose-600' : 'text-slate-900')}>
                    {fmt(item.cantidad_actual, 0)} <span className="text-[10px] text-slate-500 font-normal">{item.unidad_medida}</span>
                  </td>
                  <td className="px-4 py-3"><StockBar cantidad={item.cantidad_actual} puntoReorden={item.punto_reorden} /></td>
                  <td className="px-4 py-3 text-right text-slate-700 font-mono text-xs">Gs. {fmt(item.costo_unitario, 0)}</td>
                  <td className="px-4 py-3 text-right text-slate-500">
                    {new Decimal(item.punto_reorden).gt(0) ? fmt(item.punto_reorden, 0) : '—'}
                  </td>
                  {puedeEscribir() && (
                    <td className="px-4 py-3">
                      <div className="flex gap-1 justify-center">
                        <button
                          onClick={() => openEdit(item)}
                          className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                          title="Editar"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => handleEliminar(item)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {!isLoading && filtered.length === 0 && (
                <tr><td colSpan={8} className="text-center py-8 text-slate-500">Sin items en esta categoría</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal de creación/edición */}
      {showForm && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[92vh] flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between flex-shrink-0">
              <h2 className="text-xl font-bold text-slate-900">
                {isEditing ? 'Editar item' : 'Nuevo item de inventario'}
              </h2>
              <button onClick={() => { setShowForm(false); setEditingId(null) }}
                className="text-slate-400 hover:text-slate-700 p-2">
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {/* Descripción con autocomplete */}
              <div className="relative">
                <label className="text-xs font-semibold text-slate-600">Descripción *</label>
                <input
                  className="input mt-1"
                  placeholder="Ej: Frasco Oval 150 ml, Crema hidratante…"
                  value={form.descripcion}
                  onChange={e => setForm(p => ({ ...p, descripcion: e.target.value }))}
                  autoFocus
                />

                {/* Sugerencias */}
                {!isEditing && sugerencias.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-lg max-h-72 overflow-y-auto z-10">
                    <div className="px-3 py-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest bg-slate-50 border-b border-slate-100">
                      <Sparkles size={11} className="inline mr-1" />
                      Sugerencias
                    </div>
                    {sugerencias.map((s, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => handleAplicarPlantilla(s)}
                        className="w-full px-3 py-2 text-left hover:bg-slate-50 border-b border-slate-100 last:border-none flex items-center gap-2"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-slate-800 truncate">{s.descripcion}</div>
                          <div className="text-[11px] text-slate-500">
                            {s.existente
                              ? <span className="text-amber-700">Ya existe — clickeá para usar este nombre</span>
                              : <span className="text-indigo-600">Plantilla genérica · código {s.codigo}</span>
                            }
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                <p className="text-[10px] text-slate-400 mt-1">
                  💡 Empezá a escribir y verás sugerencias. Las plantillas genéricas vienen pre-armadas para productos típicos.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-600">Código</label>
                  <input className="input mt-1 font-mono" placeholder="ej: BRO-15-100"
                    value={form.codigo}
                    onChange={e => setForm(p => ({ ...p, codigo: e.target.value }))} />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-600">Unidad de medida</label>
                  <select className="input mt-1" value={form.unidad_medida}
                    onChange={e => setForm(p => ({ ...p, unidad_medida: e.target.value }))}>
                    {['unidad','kg','lt','m2','m3','caja','bolsa','otro'].map(u =>
                      <option key={u} value={u}>{u}</option>
                    )}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-600">Cantidad actual</label>
                  <input className="input mt-1 text-right" type="number" step="0.0001"
                    value={form.cantidad_actual}
                    onChange={e => setForm(p => ({ ...p, cantidad_actual: e.target.value }))} />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-600">Costo unitario (Gs.)</label>
                  <input className="input mt-1 text-right" type="number" step="0.01"
                    value={form.costo_unitario}
                    onChange={e => setForm(p => ({ ...p, costo_unitario: e.target.value }))} />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs font-semibold text-slate-600">Punto de reorden</label>
                  <input className="input mt-1 text-right" type="number" step="0.0001"
                    value={form.punto_reorden}
                    onChange={e => setForm(p => ({ ...p, punto_reorden: e.target.value }))} />
                  <p className="text-[10px] text-slate-400 mt-1">
                    💡 Dejá en 0 si no querés alerta de stock bajo. Si lo dejas configurado, el sistema te avisa cuando el stock baja a este valor.
                  </p>
                </div>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-slate-200 flex justify-end gap-3 flex-shrink-0">
              <button onClick={() => { setShowForm(false); setEditingId(null) }} className="btn-outline">
                Cancelar
              </button>
              <button onClick={guardar}
                disabled={!form.descripcion || crearMutation.isPending || actualizarMutation.isPending}
                className="btn-primary">
                {(crearMutation.isPending || actualizarMutation.isPending)
                  ? 'Guardando…'
                  : isEditing ? 'Guardar cambios' : 'Crear item'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// Card con acciones (Edit / Delete)
// ═══════════════════════════════════════════════════════════════════════════

function ProductCardWithActions({ product, canWrite, onEdit, onDelete }: {
  product: any
  canWrite: boolean
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <div className="relative group">
      <ProductCard product={product} />
      {canWrite && (
        <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onEdit}
            className="bg-white shadow-md p-1.5 rounded-md text-slate-500 hover:text-indigo-600 hover:bg-indigo-50"
            title="Editar"
          >
            <Edit2 size={12} />
          </button>
          <button
            onClick={onDelete}
            className="bg-white shadow-md p-1.5 rounded-md text-slate-500 hover:text-rose-600 hover:bg-rose-50"
            title="Eliminar"
          >
            <Trash2 size={12} />
          </button>
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// ChipFilter
// ═══════════════════════════════════════════════════════════════════════════

function ChipFilter({ active, onClick, label, emoji, count, color }: {
  active: boolean; onClick: () => void; label: string; emoji: string; count: number
  color: 'slate' | 'red' | 'amber' | 'pink' | 'blue' | 'purple' | 'emerald' | 'orange'
}) {
  const colors: Record<string, { active: string; idle: string }> = {
    slate:   { active: 'bg-slate-900 text-white border-slate-900',          idle: 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50' },
    red:     { active: 'bg-rose-500 text-white border-rose-500',            idle: 'bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100' },
    amber:   { active: 'bg-amber-500 text-white border-amber-500',          idle: 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100' },
    pink:    { active: 'bg-pink-500 text-white border-pink-500',            idle: 'bg-pink-50 text-pink-800 border-pink-200 hover:bg-pink-100' },
    blue:    { active: 'bg-blue-500 text-white border-blue-500',            idle: 'bg-blue-50 text-blue-800 border-blue-200 hover:bg-blue-100' },
    purple:  { active: 'bg-purple-500 text-white border-purple-500',        idle: 'bg-purple-50 text-purple-800 border-purple-200 hover:bg-purple-100' },
    emerald: { active: 'bg-emerald-500 text-white border-emerald-500',      idle: 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100' },
    orange:  { active: 'bg-orange-500 text-white border-orange-500',        idle: 'bg-orange-50 text-orange-800 border-orange-200 hover:bg-orange-100' },
  }
  const c = colors[color]
  return (
    <button
      onClick={onClick}
      className={clsx(
        'px-3 py-1.5 rounded-full border text-xs font-semibold flex items-center gap-1.5 transition-all',
        active ? c.active : c.idle,
      )}
    >
      <span>{emoji}</span>
      <span>{label}</span>
      <span className={clsx(
        'min-w-[18px] px-1 rounded-full text-[10px] font-bold',
        active ? 'bg-white/25' : 'bg-black/10',
      )}>
        {count}
      </span>
    </button>
  )
}
