'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { actividadApi } from '@/lib/api'
import {
  History, User, FileText, CreditCard, Users as UsersIcon, Truck,
  Package, Shield, Building2, Filter, Calendar, Search,
} from 'lucide-react'
import clsx from 'clsx'

interface Evento {
  id: string
  fecha: string | null
  accion: string
  accion_label: string
  tabla: string | null
  tabla_label: string
  registro_id: string | null
  usuario_id: string | null
  usuario_nombre: string
  usuario_email: string
}

interface Resp {
  actividad: Evento[]
  cantidad: number
}

const ICON_TABLA: Record<string, any> = {
  comprobantes: FileText,
  pagos: CreditCard,
  clientes: UsersIcon,
  proveedores: Truck,
  inventario: Package,
  usuarios: Shield,
  empresas: Building2,
}

const COLOR_ACCION: Record<string, string> = {
  INSERT: 'bg-emerald-50 text-emerald-700',
  UPDATE: 'bg-blue-50 text-blue-700',
  DELETE: 'bg-rose-50 text-rose-700',
  LOGIN: 'bg-violet-50 text-violet-700',
  LOGOUT: 'bg-slate-100 text-slate-600',
  EXPORT: 'bg-amber-50 text-amber-700',
  BACKUP: 'bg-sky-50 text-sky-700',
}

const TABLAS = [
  { v: '', label: 'Todas las tablas' },
  { v: 'comprobantes', label: 'Comprobantes' },
  { v: 'pagos', label: 'Pagos / Cobros' },
  { v: 'clientes', label: 'Clientes' },
  { v: 'proveedores', label: 'Proveedores' },
  { v: 'inventario', label: 'Inventario' },
  { v: 'usuarios', label: 'Usuarios' },
  { v: 'empresas', label: 'Empresa' },
]

const ACCIONES = [
  { v: '', label: 'Todas las acciones' },
  { v: 'INSERT', label: 'Creados' },
  { v: 'UPDATE', label: 'Modificados' },
  { v: 'DELETE', label: 'Eliminados' },
  { v: 'LOGIN', label: 'Inicios de sesion' },
]

function formatFecha(iso: string | null): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString('es-PY', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

export default function ActividadPage() {
  const [tabla, setTabla] = useState('')
  const [accion, setAccion] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [busqueda, setBusqueda] = useState('')

  const { data, isLoading } = useQuery<Resp>({
    queryKey: ['actividad', tabla, accion, desde, hasta],
    queryFn: () => actividadApi.listar({
      tabla: tabla || undefined,
      accion: accion || undefined,
      desde: desde || undefined,
      hasta: hasta || undefined,
      limite: 300,
    }).then(r => r.data),
    refetchInterval: 30_000,
  })

  const filtrados = (data?.actividad ?? []).filter(e => {
    if (!busqueda.trim()) return true
    const q = busqueda.trim().toLowerCase()
    return (
      e.usuario_nombre?.toLowerCase().includes(q) ||
      e.usuario_email?.toLowerCase().includes(q) ||
      e.tabla_label?.toLowerCase().includes(q)
    )
  })

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <History size={22} /> Actividad del sistema
        </h1>
        <p className="text-muted text-sm mt-1">
          Quien hizo que en el ERP. Visible para todos los usuarios. Se actualiza cada 30 segundos.
        </p>
      </div>

      {/* Filtros */}
      <div className="card">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="text-xs font-medium text-muted flex items-center gap-1">
              <Filter size={12} /> Tabla
            </label>
            <select value={tabla} onChange={e => setTabla(e.target.value)} className="input-field mt-1">
              {TABLAS.map(t => <option key={t.v} value={t.v}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted flex items-center gap-1">
              <Filter size={12} /> Acción
            </label>
            <select value={accion} onChange={e => setAccion(e.target.value)} className="input-field mt-1">
              {ACCIONES.map(a => <option key={a.v} value={a.v}>{a.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted flex items-center gap-1">
              <Calendar size={12} /> Desde
            </label>
            <input type="date" value={desde} onChange={e => setDesde(e.target.value)} className="input-field mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted flex items-center gap-1">
              <Calendar size={12} /> Hasta
            </label>
            <input type="date" value={hasta} onChange={e => setHasta(e.target.value)} className="input-field mt-1" />
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs font-medium text-muted flex items-center gap-1">
              <Search size={12} /> Buscar usuario
            </label>
            <input
              type="text"
              value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
              placeholder="nombre, email o tabla..."
              className="input-field mt-1 w-full"
            />
          </div>
        </div>
      </div>

      {/* Lista */}
      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="responsive-table-wide w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600 border-b border-border">
              <tr>
                <th className="text-left px-3 py-2.5">Fecha / Hora</th>
                <th className="text-left px-3 py-2.5">Usuario</th>
                <th className="text-left px-3 py-2.5">Acción</th>
                <th className="text-left px-3 py-2.5">Sobre</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={4} className="py-10 text-center text-muted">Cargando…</td></tr>
              )}
              {!isLoading && filtrados.length === 0 && (
                <tr><td colSpan={4} className="py-10 text-center text-muted">Sin actividad con los filtros actuales.</td></tr>
              )}
              {filtrados.map(e => {
                const Icon = ICON_TABLA[e.tabla ?? ''] ?? History
                return (
                  <tr key={e.id} className="border-b border-border/50 hover:bg-slate-50/50">
                    <td className="px-3 py-2 whitespace-nowrap text-xs text-muted font-mono">
                      {formatFecha(e.fecha)}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-bold flex-shrink-0">
                          {(e.usuario_nombre || '?').charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium text-primary truncate">{e.usuario_nombre || 'Sistema'}</p>
                          {e.usuario_email && (
                            <p className="text-[10px] text-muted truncate">{e.usuario_email}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <span className={clsx(
                        'inline-flex px-2 py-0.5 rounded-full text-xs font-medium',
                        COLOR_ACCION[e.accion] ?? 'bg-slate-100 text-slate-600',
                      )}>
                        {e.accion_label}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-1.5 text-slate-700">
                        <Icon size={14} className="text-slate-500" />
                        {e.tabla_label}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {!isLoading && filtrados.length > 0 && (
          <div className="px-3 py-2 bg-slate-50 border-t border-border text-xs text-muted">
            {filtrados.length} evento{filtrados.length === 1 ? '' : 's'}
          </div>
        )}
      </div>
    </div>
  )
}
