'use client'
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { AlertTriangle, Download, KeyRound, Loader2, Lock, ShieldCheck, Trash2 } from 'lucide-react'
import { usuariosApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'

type EventoSeguridad = {
  fecha: string
  accion: string
  tabla_afectada?: string | null
  datos_nuevos?: { evento?: string; [key: string]: unknown } | null
  origen?: string | null
  ip_origen?: string | null
  user_agent?: string | null
}

type SeguridadResponse = {
  usuario: {
    ultimo_acceso?: string | null
    failed_login_attempts?: number
    last_failed_login?: string | null
    locked_until?: string | null
    password_changed_at?: string | null
  }
  eventos: EventoSeguridad[]
}

function fmtFecha(v?: string | null) {
  if (!v) return '—'
  return new Intl.DateTimeFormat('es-PY', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(v))
}

function eventoLabel(e: EventoSeguridad) {
  const evento = e.datos_nuevos?.evento
  const map: Record<string, string> = {
    login: 'Inicio de sesión correcto',
    login_fallido: 'Intento fallido de login',
    password_reset_confirmado: 'Contraseña cambiada por reset',
    seteo_password_inicial: 'Contraseña inicial creada',
    perfil_propio: 'Perfil actualizado',
    delete_account_self: 'Cuenta anonimizada',
  }
  return evento ? (map[evento] || evento) : `${e.accion} ${e.tabla_afectada || ''}`.trim()
}

export default function MiSeguridadPage() {
  const logout = useAuth(s => s.logout)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const { data, isLoading, error } = useQuery<SeguridadResponse>({
    queryKey: ['mi-seguridad'],
    queryFn: () => usuariosApi.seguridad().then(r => r.data),
  })

  const exportMutation = useMutation({
    mutationFn: () => usuariosApi.exportarMisDatos(),
    onSuccess: (res) => {
      const blob = new Blob([res.data], { type: 'application/zip' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'mis_datos_erp.zip'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => usuariosApi.eliminarMiCuenta(),
    onSuccess: () => logout(),
  })

  if (isLoading) {
    return <div className="p-4 sm:p-6 lg:p-8"><Loader2 className="animate-spin text-slate-400" /></div>
  }

  if (error) {
    return <div className="p-4 sm:p-6 lg:p-8"><div className="card border-red-200 bg-red-50 text-red-700">No pudimos cargar tu seguridad.</div></div>
  }

  const usuario = data?.usuario
  const bloqueado = usuario?.locked_until && new Date(usuario.locked_until) > new Date()

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <ShieldCheck size={24} /> Mi seguridad
        </h1>
        <p className="text-sm text-muted mt-1">Revisá accesos, actividad sensible y opciones de privacidad de tu cuenta.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="card">
          <p className="text-xs uppercase tracking-wide text-muted font-semibold">Último acceso</p>
          <p className="mt-2 font-semibold text-primary">{fmtFecha(usuario?.ultimo_acceso)}</p>
        </div>
        <div className="card">
          <p className="text-xs uppercase tracking-wide text-muted font-semibold">Contraseña cambiada</p>
          <p className="mt-2 font-semibold text-primary">{fmtFecha(usuario?.password_changed_at)}</p>
        </div>
        <div className={`card ${bloqueado ? 'border-amber-300 bg-amber-50' : ''}`}>
          <p className="text-xs uppercase tracking-wide text-muted font-semibold">Estado login</p>
          <p className="mt-2 font-semibold text-primary">
            {bloqueado ? `Bloqueada hasta ${fmtFecha(usuario?.locked_until)}` : 'Activa'}
          </p>
          {!!usuario?.failed_login_attempts && <p className="text-xs text-muted mt-1">Intentos fallidos recientes: {usuario.failed_login_attempts}</p>}
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="font-bold text-primary flex items-center gap-2"><Lock size={18} /> Últimos eventos</h2>
            <p className="text-xs text-muted mt-1">Se muestran los últimos 10 eventos sensibles registrados para tu usuario.</p>
          </div>
        </div>
        <div className="divide-y divide-border">
          {data?.eventos?.length ? data.eventos.map((e, idx) => (
            <div key={`${e.fecha}-${idx}`} className="py-3 flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-medium text-primary">{eventoLabel(e)}</p>
                <p className="text-xs text-muted">{fmtFecha(e.fecha)} · IP {e.ip_origen || 'no registrada'}</p>
              </div>
              <p className="text-xs text-muted md:text-right max-w-md truncate" title={e.user_agent || ''}>
                {e.user_agent || 'Dispositivo no registrado'}
              </p>
            </div>
          )) : <p className="text-sm text-muted py-4">Todavía no hay eventos registrados.</p>}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <h2 className="font-bold text-primary flex items-center gap-2"><Download size={18} /> Exportar mis datos</h2>
          <p className="text-sm text-muted mt-2">Descarga un ZIP con tu perfil, comprobantes cargados, pagos registrados y auditoría asociada.</p>
          <button
            type="button"
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending}
            className="btn-primary mt-4 inline-flex items-center gap-2"
          >
            {exportMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            Descargar ZIP
          </button>
        </div>

        <div className="card border-red-200 bg-red-50">
          <h2 className="font-bold text-red-900 flex items-center gap-2"><Trash2 size={18} /> Eliminar mi cuenta</h2>
          <p className="text-sm text-red-800 mt-2">Anonimiza tu usuario y cierra el acceso. Los registros contables se preservan por auditoría.</p>
          {!confirmDelete ? (
            <button type="button" onClick={() => setConfirmDelete(true)} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">
              <AlertTriangle size={16} /> Quiero eliminar mi cuenta
            </button>
          ) : (
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending} className="inline-flex items-center gap-2 rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-800 disabled:opacity-50">
                {deleteMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
                Confirmar eliminación
              </button>
              <button type="button" onClick={() => setConfirmDelete(false)} className="btn-ghost">Cancelar</button>
            </div>
          )}
        </div>
      </div>

      <div className="card bg-blue-50 border-blue-200 text-blue-900">
        <h2 className="font-bold flex items-center gap-2"><KeyRound size={18} /> Recomendación</h2>
        <p className="text-sm mt-1">Si ves actividad que no reconocés, cerrá sesión y pedí al administrador un cambio de contraseña.</p>
      </div>
    </div>
  )
}
