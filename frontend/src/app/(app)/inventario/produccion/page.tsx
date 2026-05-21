'use client'
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { Factory, AlertTriangle, Beaker, CheckCircle2, TrendingDown, Package } from 'lucide-react'
import Decimal from 'decimal.js'
import { recetasApi } from '@/lib/api'

/**
 * Página de Capacidad de Producción
 * =================================
 *
 * Muestra para cada receta activa: cuántas unidades del producto terminado
 * se pueden producir con el stock actual de insumos.
 *
 * Es la pantalla que el jefe de producción mira cada mañana para decidir
 * qué fabricar y qué insumos pedir.
 */

type Receta = {
  id: string
  producto_id: string
  producto_nombre?: string
  producto_codigo?: string
  nombre: string
  rendimiento: string
  unidad_rendimiento: string
  costo_unitario?: string
  activa: boolean
  cantidad_items?: number
}

type CapacidadResp = {
  receta_id: string
  producto_id: string
  producto_nombre: string
  batches_posibles: number
  unidades_posibles: number
  insumo_limitante: string | null
  items_status: Array<{
    insumo_nombre: string
    codigo: string | null
    unidad_medida: string
    stock_actual: number
    cantidad_requerida: number
    batches_posibles: number
    es_limitante: boolean
  }>
}

function fmt(v: string | number): string {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

export default function ProduccionPage() {
  const { data: recetas = [], isLoading } = useQuery<Receta[]>({
    queryKey: ['recetas', 'activas'],
    queryFn: () => recetasApi.listar({ activas: true }).then(r => r.data),
  })

  return (
    <div className="p-6 md:p-8 space-y-5 pb-20">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Factory size={24} className="text-indigo-500" />
            Capacidad de producción
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Cuántas unidades de cada producto podés fabricar con el stock actual de insumos
          </p>
        </div>
        <Link href="/inventario/recetas" className="btn-outline flex items-center gap-2">
          <Beaker size={15} /> Ver recetas
        </Link>
      </div>

      {/* Aviso si no hay recetas */}
      {!isLoading && recetas.length === 0 && (
        <div className="card text-center py-16">
          <div className="text-5xl mb-3">🧪</div>
          <h3 className="text-lg font-semibold text-slate-700 mb-1">
            No tenés recetas activas
          </h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mb-4">
            Para ver cuánto podés producir, primero cargá las recetas de tus productos terminados.
          </p>
          <Link
            href="/inventario/recetas"
            className="btn-primary inline-flex items-center gap-2"
          >
            Crear una receta →
          </Link>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="grid gap-3">
          {[1,2,3].map(i => (
            <div key={i} className="card animate-pulse h-32 bg-slate-100" />
          ))}
        </div>
      )}

      {/* Lista de productos producibles */}
      {!isLoading && recetas.length > 0 && (
        <div className="space-y-4">
          {recetas.map(receta => (
            <ProduccionCard key={receta.id} receta={receta} />
          ))}
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// CARD DE PRODUCCIÓN POR RECETA
// ═══════════════════════════════════════════════════════════════════════════

function ProduccionCard({ receta }: { receta: Receta }) {
  const { data: capacidad, isLoading } = useQuery<CapacidadResp>({
    queryKey: ['receta-capacidad', receta.id],
    queryFn: () => recetasApi.capacidad(receta.id).then(r => r.data),
    staleTime: 30_000,
  })

  if (isLoading || !capacidad) {
    return <div className="card animate-pulse h-40 bg-slate-50" />
  }

  const puedeProducir = capacidad.batches_posibles > 0
  const valorPotencial = capacidad.unidades_posibles * parseFloat(receta.costo_unitario || '0')

  // Items ordenados: limitantes primero
  const items = [...capacidad.items_status].sort((a, b) => {
    if (a.es_limitante !== b.es_limitante) return a.es_limitante ? -1 : 1
    return a.batches_posibles - b.batches_posibles
  })

  return (
    <div className={`bg-white rounded-2xl border-2 ${puedeProducir ? 'border-emerald-200' : 'border-rose-200'} overflow-hidden`}>
      {/* Cabecera */}
      <div className={`px-5 py-4 ${puedeProducir ? 'bg-emerald-50' : 'bg-rose-50'}`}>
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-start gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl ${
              puedeProducir ? 'bg-emerald-500' : 'bg-rose-500'
            } text-white`}>
              {puedeProducir ? <CheckCircle2 size={20} /> : <AlertTriangle size={20} />}
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">
                {receta.producto_nombre}
              </h3>
              <p className="text-xs text-slate-600">
                Receta: <strong>{receta.nombre}</strong> · {receta.cantidad_items ?? 0} ingredientes
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className={`text-2xl font-extrabold ${puedeProducir ? 'text-emerald-600' : 'text-rose-600'}`}>
              {puedeProducir ? `${fmt(capacidad.unidades_posibles)} unidades` : 'No podés producir'}
            </div>
            {puedeProducir && (
              <div className="text-xs text-slate-600 mt-0.5">
                {capacidad.batches_posibles} batches posibles · Valor potencial: Gs. {fmt(valorPotencial)}
              </div>
            )}
          </div>
        </div>

        {/* Mensaje del cuello de botella */}
        {capacidad.insumo_limitante && (
          <div className={`mt-3 flex items-start gap-2 text-xs ${
            puedeProducir ? 'text-emerald-800' : 'text-rose-800'
          }`}>
            <TrendingDown size={14} className="flex-shrink-0 mt-0.5" />
            <span>
              <strong>Cuello de botella:</strong> <em>{capacidad.insumo_limitante}</em>.
              {!puedeProducir && ' Reponé este insumo para poder producir.'}
              {puedeProducir && ' Si tuvieras más de este insumo, podrías producir más unidades.'}
            </span>
          </div>
        )}
      </div>

      {/* Detalle de insumos */}
      <div className="p-5">
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">
          Estado de cada ingrediente
        </div>
        <div className="space-y-2">
          {items.map((it, idx) => {
            const stockOk = it.batches_posibles >= capacidad.batches_posibles && it.batches_posibles > 0
            const stockCero = it.batches_posibles === 0
            const ratio = it.cantidad_requerida > 0
              ? it.stock_actual / it.cantidad_requerida
              : 0

            return (
              <div key={idx} className="flex items-center gap-3">
                <div className="flex-shrink-0">
                  {stockCero ? (
                    <div className="w-6 h-6 rounded-full bg-rose-100 flex items-center justify-center">
                      <AlertTriangle size={11} className="text-rose-600" />
                    </div>
                  ) : it.es_limitante ? (
                    <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center">
                      <TrendingDown size={11} className="text-amber-600" />
                    </div>
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center">
                      <CheckCircle2 size={11} className="text-emerald-600" />
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="text-sm font-medium text-slate-900 truncate">
                      {it.insumo_nombre}
                      {it.es_limitante && (
                        <span className="ml-2 text-[10px] font-bold bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded uppercase">
                          Limitante
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-600 flex-shrink-0">
                      <span className="font-mono">
                        {fmt(it.stock_actual)} {it.unidad_medida}
                      </span>
                      <span className="text-slate-400 mx-1">/</span>
                      <span className="font-mono text-slate-500">
                        {fmt(it.cantidad_requerida)} req.
                      </span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        stockCero ? 'bg-rose-500' :
                        it.es_limitante ? 'bg-amber-500' :
                        'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, ratio * 100 / capacidad.batches_posibles || 0)}%` }}
                    />
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Alcanza para <strong>{it.batches_posibles}</strong> batches
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
