'use client'
import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { empresaApi } from '@/lib/api'
import { API_BASE_URL } from '@/lib/config'
import { useAuth } from '@/lib/auth'
import { Building2, Upload, Trash2, Save, AlertCircle, ImageOff } from 'lucide-react'

interface Empresa {
  id: string
  nombre: string
  ruc?: string | null
  direccion?: string | null
  telefono?: string | null
  email?: string | null
  moneda_principal?: string | null
  logo_url?: string | null
  activa?: boolean
  fecha_creacion?: string
}

export default function AdminEmpresaPage() {
  const { usuario } = useAuth()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [form, setForm] = useState<Partial<Empresa>>({})
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const { data: empresa, isLoading } = useQuery<Empresa>({
    queryKey: ['empresa'],
    queryFn: () => empresaApi.obtener().then(r => r.data),
    enabled: !!usuario,
  })

  useEffect(() => { if (empresa) setForm(empresa) }, [empresa])

  const guardarMut = useMutation({
    mutationFn: () => empresaApi.actualizar({
      nombre: form.nombre ?? undefined,
      ruc: form.ruc ?? undefined,
      direccion: form.direccion ?? undefined,
      telefono: form.telefono ?? undefined,
      email: form.email || undefined,
      moneda_principal: form.moneda_principal ?? undefined,
    }),
    onSuccess: () => {
      setMsg({ type: 'ok', text: 'Datos de la empresa actualizados' })
      qc.invalidateQueries({ queryKey: ['empresa'] })
    },
    onError: (e: any) => setMsg({ type: 'err', text: e.response?.data?.detail ?? 'Error al guardar' }),
  })

  const subirMut = useMutation({
    mutationFn: (f: File) => empresaApi.subirLogo(f),
    onSuccess: () => {
      setMsg({ type: 'ok', text: 'Logo actualizado' })
      qc.invalidateQueries({ queryKey: ['empresa'] })
    },
    onError: (e: any) => setMsg({ type: 'err', text: e.response?.data?.detail ?? 'No se pudo subir el logo' }),
  })

  const quitarMut = useMutation({
    mutationFn: () => empresaApi.quitarLogo(),
    onSuccess: () => {
      setMsg({ type: 'ok', text: 'Logo eliminado' })
      qc.invalidateQueries({ queryKey: ['empresa'] })
    },
    onError: (e: any) => setMsg({ type: 'err', text: e.response?.data?.detail ?? 'Error' }),
  })

  if (usuario?.rol !== 'admin') {
    return (
      <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto">
        <div className="card bg-amber-50 border-amber-200">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-amber-600 flex-shrink-0" />
            <div>
              <h2 className="font-bold text-amber-900">Acceso restringido</h2>
              <p className="text-sm text-amber-800 mt-1">
                Solo administradores pueden editar los datos de la empresa.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const logoSrc = empresa?.logo_url
    ? `${empresa.logo_url.startsWith('http') ? empresa.logo_url : `${API_BASE_URL}${empresa.logo_url}`}?v=${empresa.logo_url}`
    : null

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <Building2 size={22} /> Configuración de la empresa
        </h1>
        <p className="text-muted text-sm mt-1">
          Estos datos aparecerán en reportes, recibos y el encabezado del sistema.
        </p>
      </div>

      {msg && (
        <div className={`p-3 rounded-lg text-sm flex items-center gap-2 ${
          msg.type === 'ok' ? 'bg-emerald-50 border border-emerald-200 text-emerald-700'
                            : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          <AlertCircle size={14} /> {msg.text}
        </div>
      )}

      <div className="grid md:grid-cols-[260px_1fr] gap-6">
        {/* Logo */}
        <div className="card text-center space-y-3">
          <p className="text-xs uppercase tracking-widest text-muted">Logo de la empresa</p>
          <div className="w-full aspect-square bg-surface rounded-xl border border-border flex items-center justify-center overflow-hidden">
            {logoSrc
              ? <img src={logoSrc} alt="Logo" className="max-w-full max-h-full object-contain" />
              : <ImageOff size={40} className="text-slate-300" />
            }
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/svg+xml"
            className="hidden"
            onChange={e => {
              const f = e.target.files?.[0]
              if (f) subirMut.mutate(f)
              if (fileRef.current) fileRef.current.value = ''
            }}
          />
          <div className="flex flex-col gap-2">
            <button
              onClick={() => fileRef.current?.click()}
              disabled={subirMut.isPending}
              className="btn-primary inline-flex items-center justify-center gap-2 text-sm"
            >
              <Upload size={14} /> {subirMut.isPending ? 'Subiendo…' : 'Subir logo'}
            </button>
            {empresa?.logo_url && (
              <button
                onClick={() => { if (confirm('¿Quitar el logo actual?')) quitarMut.mutate() }}
                className="btn-ghost inline-flex items-center justify-center gap-2 text-sm text-red-600"
              >
                <Trash2 size={14} /> Quitar logo
              </button>
            )}
          </div>
          <p className="text-[11px] text-muted">PNG, JPG, WEBP o SVG. Máx 2 MB.</p>
        </div>

        {/* Datos */}
        <form
          onSubmit={e => { e.preventDefault(); setMsg(null); guardarMut.mutate() }}
          className="card space-y-3"
        >
          {isLoading ? (
            <p className="text-center text-muted py-6">Cargando datos…</p>
          ) : (
            <>
              <div>
                <label className="text-xs text-muted font-medium">Razón social / Nombre</label>
                <input required minLength={2} value={form.nombre ?? ''}
                  onChange={e => setForm({ ...form, nombre: e.target.value })}
                  className="input-field w-full mt-1" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted font-medium">RUC</label>
                  <input value={form.ruc ?? ''} onChange={e => setForm({ ...form, ruc: e.target.value })}
                    className="input-field w-full mt-1" />
                </div>
                <div>
                  <label className="text-xs text-muted font-medium">Moneda principal</label>
                  <select value={form.moneda_principal ?? 'PYG'}
                    onChange={e => setForm({ ...form, moneda_principal: e.target.value })}
                    className="input-field w-full mt-1">
                    <option value="PYG">Guaraní (PYG)</option>
                    <option value="USD">Dólar (USD)</option>
                    <option value="BRL">Real (BRL)</option>
                    <option value="ARS">Peso argentino (ARS)</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-muted font-medium">Dirección</label>
                <input value={form.direccion ?? ''} onChange={e => setForm({ ...form, direccion: e.target.value })}
                  className="input-field w-full mt-1" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted font-medium">Teléfono</label>
                  <input value={form.telefono ?? ''} onChange={e => setForm({ ...form, telefono: e.target.value })}
                    className="input-field w-full mt-1" />
                </div>
                <div>
                  <label className="text-xs text-muted font-medium">Email de contacto</label>
                  <input type="email" value={form.email ?? ''}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                    className="input-field w-full mt-1" />
                </div>
              </div>
              <div className="flex justify-end pt-2">
                <button type="submit" disabled={guardarMut.isPending}
                  className="btn-primary inline-flex items-center gap-2">
                  <Save size={14} /> {guardarMut.isPending ? 'Guardando…' : 'Guardar cambios'}
                </button>
              </div>
            </>
          )}
        </form>
      </div>
    </div>
  )
}
