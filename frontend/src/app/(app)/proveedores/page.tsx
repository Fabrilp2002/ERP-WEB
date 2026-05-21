'use client'
import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { proveedoresApi, pagosApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { Plus, Search, LayoutGrid, Table as TableIcon, Map as MapIcon, X } from 'lucide-react'
import type { Proveedor, SaldoProveedor } from '@/lib/types'
import Decimal from 'decimal.js'
import clsx from 'clsx'
import PartyCard from '@/components/PartyCard'
import ParaguayMap, { type MapEntity } from '@/components/ParaguayMapReal'
import Avatar from '@/components/Avatar'

function fmt(v: string | number) {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

type ViewMode = 'cards' | 'table'

function statusFromSaldo(saldo: number): 'good' | 'warn' | 'bad' {
  if (saldo <= 0) return 'good'
  if (saldo > 10_000_000) return 'bad'
  if (saldo > 1_000_000) return 'warn'
  return 'good'
}

export default function ProveedoresPage() {
  const router = useRouter()
  const { puedeEscribir } = useAuth()
  const qc = useQueryClient()
  const [buscar, setBuscar] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('cards')
  const [showForm, setShowForm] = useState(false)
  const [selectedCity, setSelectedCity] = useState<string | null>(null)
  const [form, setForm] = useState({ nombre: '', ruc: '', telefono: '', email: '', direccion: '' })

  const { data: proveedores = [], isLoading } = useQuery<Proveedor[]>({
    queryKey: ['proveedores', buscar],
    queryFn: () => proveedoresApi.listar(buscar || undefined).then(r => r.data),
  })

  const { data: saldos = [] } = useQuery<SaldoProveedor[]>({
    queryKey: ['pagos', 'saldos-proveedores'],
    queryFn: () => pagosApi.saldosProveedores().then(r => r.data),
    staleTime: 30_000,
  })

  const saldoMap = useMemo(() => {
    const m: Record<string, number> = {}
    for (const s of saldos) {
      m[s.proveedor_id] = parseFloat(s.saldo_pendiente || '0')
    }
    return m
  }, [saldos])

  const crearMutation = useMutation({
    mutationFn: () => proveedoresApi.crear(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['proveedores'] })
      setForm({ nombre: '', ruc: '', telefono: '', email: '', direccion: '' })
      setShowForm(false)
    },
  })

  const enriched = useMemo(() => {
    return proveedores.map(p => {
      const saldo = saldoMap[p.id] ?? 0
      return { ...p, saldo, status: statusFromSaldo(saldo) }
    })
  }, [proveedores, saldoMap])

  const filteredByCity = useMemo(() => {
    if (!selectedCity) return enriched
    const cityLower = selectedCity.toLowerCase()
    return enriched.filter(p => {
      const haystack = [p.nombre, (p as any).direccion ?? '', (p as any).ciudad ?? '']
        .join(' ').toLowerCase()
      return haystack.includes(cityLower)
    })
  }, [enriched, selectedCity])

  const stats = useMemo(() => {
    const total = enriched.length
    const conSaldo = enriched.filter(p => p.saldo > 0).length
    const altos = enriched.filter(p => p.status === 'bad').length
    const totalDeuda = enriched.reduce((acc, p) => acc + Math.max(0, p.saldo), 0)
    return { total, conSaldo, altos, totalDeuda }
  }, [enriched])

  const mapEntities: MapEntity[] = useMemo(() =>
    enriched.map(p => ({
      id: p.id,
      nombre: p.nombre,
      ciudad: (p as any).ciudad ?? null,
      direccion: (p as any).direccion ?? null,
      saldo: p.saldo,
      status: p.status,
    })), [enriched])

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-5 pb-20">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Proveedores</h1>
          <p className="text-slate-500 text-sm mt-1">
            {stats.total} proveedores · {stats.conSaldo} con saldo a pagar
            {stats.altos > 0 && (
              <span className="ml-2 text-rose-600 font-semibold">
                · {stats.altos} con saldo alto
              </span>
            )}
            {stats.totalDeuda > 0 && (
              <span className="ml-2">· Gs. {fmt(stats.totalDeuda)} por pagar</span>
            )}
          </p>
        </div>
        {puedeEscribir() && (
          <button onClick={() => setShowForm(!showForm)} className="btn-primary flex w-full items-center gap-2 sm:w-auto">
            <Plus size={16} /> Nuevo proveedor
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total proveedores" value={stats.total.toString()} color="blue" icon="🏭" />
        <StatCard label="Al día" value={(stats.total - stats.conSaldo).toString()} color="green" icon="✓" />
        <StatCard label="Con saldo" value={stats.conSaldo.toString()} color="amber" icon="⚠" />
        <StatCard label="Saldo alto" value={stats.altos.toString()} color="red" icon="🔴" />
      </div>

      {showForm && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-900">Nuevo proveedor</h3>
            <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-700">
              <X size={18} />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="md:col-span-2">
              <label className="text-xs font-semibold text-slate-600">Nombre / Razón Social *</label>
              <input className="input mt-1" value={form.nombre}
                onChange={e => setForm(p => ({ ...p, nombre: e.target.value }))} required />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">RUC</label>
              <input className="input mt-1" value={form.ruc}
                onChange={e => setForm(p => ({ ...p, ruc: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600">Teléfono</label>
              <input className="input mt-1" value={form.telefono}
                onChange={e => setForm(p => ({ ...p, telefono: e.target.value }))} />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs font-semibold text-slate-600">Dirección / Ciudad</label>
              <input
                className="input mt-1"
                placeholder="Ej: Av. España, Asunción"
                value={form.direccion}
                onChange={e => setForm(p => ({ ...p, direccion: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex flex-col-reverse gap-3 mt-4 sm:flex-row sm:justify-end">
            <button className="btn-outline w-full sm:w-auto" onClick={() => setShowForm(false)}>Cancelar</button>
            <button className="btn-primary w-full sm:w-auto" onClick={() => crearMutation.mutate()}
              disabled={!form.nombre || crearMutation.isPending}>
              {crearMutation.isPending ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full sm:flex-1 sm:max-w-sm sm:min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9" placeholder="Buscar por nombre o RUC..."
            value={buscar} onChange={e => setBuscar(e.target.value)} />
        </div>

        {selectedCity && (
          <button
            onClick={() => setSelectedCity(null)}
            className="flex items-center gap-1.5 text-xs bg-blue-50 text-blue-700 border border-blue-200 px-3 py-1.5 rounded-full hover:bg-blue-100"
          >
            <MapIcon size={12} />
            Filtrado por: <strong className="capitalize">{selectedCity}</strong>
            <X size={12} className="ml-1" />
          </button>
        )}

        <div className="w-full sm:ml-auto sm:w-auto inline-flex bg-slate-100 rounded-lg p-1">
          <button
            onClick={() => setViewMode('cards')}
            className={clsx('px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5',
              viewMode === 'cards' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500')}
          >
            <LayoutGrid size={13} /> Tarjetas
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={clsx('px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1.5',
              viewMode === 'table' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500')}
          >
            <TableIcon size={13} /> Tabla
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-5 items-start">
        <div className="space-y-2">
          {isLoading && (
            <div className="card text-center py-8 text-slate-500">Cargando proveedores...</div>
          )}

          {!isLoading && filteredByCity.length === 0 && (
            <div className="card text-center py-12">
              <div className="text-3xl mb-2">🤷</div>
              <p className="text-slate-500 text-sm">
                {selectedCity ? `Sin proveedores en "${selectedCity}"` : 'No hay proveedores que coincidan'}
              </p>
            </div>
          )}

          {viewMode === 'cards' && (
            <div className="space-y-2">
              {filteredByCity.map(p => (
                <PartyCard
                  key={p.id}
                  party={{
                    id: p.id,
                    nombre: p.nombre,
                    ruc: p.ruc,
                    telefono: p.telefono,
                    email: p.email,
                    saldo: p.saldo,
                  }}
                  saldoColor={p.status === 'bad' ? 'red' : p.status === 'warn' ? 'amber' : 'green'}
                  onClick={() => router.push(`/proveedores/${p.id}`)}
                />
              ))}
            </div>
          )}

          {viewMode === 'table' && (
            <div className="card !p-0 overflow-hidden overflow-x-auto">
              <table className="responsive-table w-full text-sm">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">Proveedor</th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">RUC</th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">Teléfono</th>
                    <th className="text-right px-4 py-3 font-semibold text-slate-600">Saldo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredByCity.map(p => (
                    <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Avatar name={p.nombre} size={28} />
                          <span className="font-medium">{p.nombre}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-500 font-mono text-xs">{p.ruc ?? '—'}</td>
                      <td className="px-4 py-3 text-slate-500">{p.telefono ?? '—'}</td>
                      <td className={clsx(
                        'px-4 py-3 text-right font-semibold',
                        p.status === 'bad' ? 'text-rose-600' :
                        p.status === 'warn' ? 'text-amber-600' :
                        p.saldo > 0 ? 'text-amber-600' : 'text-slate-400',
                      )}>
                        {p.saldo > 0 ? `Gs. ${fmt(p.saldo)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="lg:sticky lg:top-20 self-start">
          <ParaguayMap
            entities={mapEntities}
            onSelectCity={setSelectedCity}
            selectedCity={selectedCity}
            title="🗺️ Proveedores en Paraguay"
            height={420}
          />
        </div>
      </div>
    </div>
  )
}


function StatCard({ label, value, color, icon }: {
  label: string; value: string; color: 'blue' | 'green' | 'amber' | 'red'; icon: string
}) {
  const colors: Record<string, string> = {
    blue:  'border-l-blue-500 bg-blue-50/40',
    green: 'border-l-emerald-500 bg-emerald-50/40',
    amber: 'border-l-amber-500 bg-amber-50/40',
    red:   'border-l-rose-500 bg-rose-50/40',
  }
  return (
    <div className={clsx('rounded-xl border border-slate-200 border-l-4 p-3', colors[color])}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          {label}
        </span>
        <span>{icon}</span>
      </div>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
    </div>
  )
}
