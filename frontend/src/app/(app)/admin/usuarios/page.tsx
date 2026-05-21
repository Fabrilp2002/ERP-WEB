'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usuariosApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { UserPlus, Shield, ShieldAlert, Eye, X, Power, KeyRound, AlertCircle, Trash2, Mail, Send, CheckCircle2 } from 'lucide-react'
import clsx from 'clsx'
import { authApi } from '@/lib/api'
import PasswordStrength, { isStrongPassword, passwordErrorMessage } from '@/components/PasswordStrength'

interface Usuario {
  id: string
  nombre: string
  apellido?: string | null
  email: string
  telefono?: string | null
  cargo?: string | null
  rol: 'admin' | 'operador' | 'viewer'
  activo: boolean
  fecha_creacion: string
  ultimo_acceso?: string | null
}

const ROL_META: Record<string, { label: string; icon: any; cls: string; desc: string }> = {
  admin:    { label: 'Admin',    icon: Shield,      cls: 'bg-primary-100 text-primary-700', desc: 'Acceso total + gestión de usuarios' },
  operador: { label: 'Operador', icon: ShieldAlert, cls: 'bg-amber-100 text-amber-700',     desc: 'Puede cargar y editar datos' },
  viewer:   { label: 'Viewer',   icon: Eye,         cls: 'bg-slate-100 text-slate-700',     desc: 'Solo lectura — dashboards y reportes' },
}

function apiError(e: any, fallback: string) {
  const detail = e.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail?.errores)) return detail.errores.join(' · ')
  return fallback
}

export default function AdminUsuariosPage() {
  const { usuario } = useAuth()
  const qc = useQueryClient()
  const [showCrear, setShowCrear] = useState(false)
  const [showInvitar, setShowInvitar] = useState(false)
  const [pwdModal, setPwdModal] = useState<Usuario | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [invitacionExitosa, setInvitacionExitosa] = useState<string | null>(null)

  const { data: usuarios = [], isLoading } = useQuery<Usuario[]>({
    queryKey: ['usuarios'],
    queryFn: () => usuariosApi.listar().then(r => r.data),
    enabled: usuario?.rol === 'admin',
  })

  const crearMut = useMutation({
    mutationFn: (data: { nombre: string; apellido?: string; email: string; telefono?: string; cargo?: string; password: string; rol: 'admin'|'operador'|'viewer' }) =>
      usuariosApi.crear(data),
    onSuccess: () => {
      setShowCrear(false); setErr(null)
      qc.invalidateQueries({ queryKey: ['usuarios'] })
    },
    onError: (e: any) => setErr(apiError(e, 'Error al crear')),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => usuariosApi.actualizar(id, data),
    onSuccess: () => {
      setPwdModal(null); setErr(null)
      qc.invalidateQueries({ queryKey: ['usuarios'] })
    },
    onError: (e: any) => setErr(apiError(e, 'Error al actualizar')),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => usuariosApi.eliminar(id),
    onSuccess: () => {
      setErr(null)
      qc.invalidateQueries({ queryKey: ['usuarios'] })
    },
    onError: (e: any) => setErr(apiError(e, 'Error al eliminar')),
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
                Solo los administradores pueden gestionar usuarios. Tu rol actual es <b>{usuario?.rol}</b>.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <Shield size={22} /> Administración de usuarios
          </h1>
          <p className="text-muted text-sm mt-1">Creá, editá o desactivá los usuarios de tu empresa.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowInvitar(true); setErr(null); setInvitacionExitosa(null) }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 text-white font-medium text-sm hover:bg-emerald-700 transition shadow-sm"
            title="Mandar email para que el usuario active su cuenta y elija su contraseña"
          >
            <Mail size={16} /> Invitar por email
          </button>
          <button onClick={() => { setShowCrear(true); setErr(null) }} className="btn-primary inline-flex items-center gap-2">
            <UserPlus size={16} /> Nuevo usuario
          </button>
        </div>
      </div>

      {/* Banner de éxito al invitar */}
      {invitacionExitosa && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-800 flex items-start gap-2">
          <CheckCircle2 size={18} className="mt-0.5 flex-shrink-0" />
          <div>{invitacionExitosa}</div>
          <button onClick={() => setInvitacionExitosa(null)} className="ml-auto text-emerald-600 hover:text-emerald-800">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Modal de invitar */}
      {showInvitar && (
        <ModalInvitar
          onCerrar={() => setShowInvitar(false)}
          onExito={(mensaje) => {
            setShowInvitar(false)
            setInvitacionExitosa(mensaje)
            qc.invalidateQueries({ queryKey: ['usuarios'] })
          }}
        />
      )}

      {err && !showCrear && !pwdModal && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center gap-2">
          <AlertCircle size={14} /> {err}
        </div>
      )}

      <div className="card !p-0 overflow-hidden">
        <table className="responsive-table w-full text-sm">
          <thead className="bg-surface border-b border-border">
            <tr>
              <th className="text-left px-4 py-2.5 font-semibold">Nombre</th>
              <th className="text-left px-4 py-2.5 font-semibold">Email / Teléfono</th>
              <th className="text-left px-4 py-2.5 font-semibold">Cargo</th>
              <th className="text-left px-4 py-2.5 font-semibold">Rol</th>
              <th className="text-center px-4 py-2.5 font-semibold">Estado</th>
              <th className="text-right px-4 py-2.5 font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading && <tr><td colSpan={6} className="text-center py-8 text-muted">Cargando…</td></tr>}
            {usuarios.map(u => {
              const rolMeta = ROL_META[u.rol]
              const Icon = rolMeta?.icon ?? Shield
              const esMiUsuario = u.id === usuario?.id
              return (
                <tr key={u.id} className={clsx('hover:bg-surface', !u.activo && 'opacity-50')}>
                  <td className="px-4 py-2.5 font-medium">
                    {u.nombre}{u.apellido ? ` ${u.apellido}` : ''}
                    {esMiUsuario && <span className="text-xs text-slate-400 ml-2">(vos)</span>}
                  </td>
                  <td className="px-4 py-2.5 text-muted">
                    <div>{u.email}</div>
                    {u.telefono && <div className="text-xs text-slate-400">{u.telefono}</div>}
                  </td>
                  <td className="px-4 py-2.5 text-muted text-xs">{u.cargo ?? '—'}</td>
                  <td className="px-4 py-2.5">
                    <select
                      value={u.rol}
                      disabled={esMiUsuario || !u.activo}
                      onChange={e => updateMut.mutate({ id: u.id, data: { rol: e.target.value } })}
                      className={clsx(
                        'text-xs px-2 py-1 rounded-full font-medium border-0 cursor-pointer',
                        rolMeta?.cls,
                        esMiUsuario && 'cursor-not-allowed'
                      )}
                    >
                      <option value="admin">Admin</option>
                      <option value="operador">Operador</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span className={clsx(
                      'text-xs px-2 py-0.5 rounded-full font-medium',
                      u.activo ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'
                    )}>
                      {u.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="inline-flex gap-1">
                      <button
                        onClick={() => setPwdModal(u)}
                        className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                        title="Cambiar contraseña"
                      >
                        <KeyRound size={14} />
                      </button>
                      <button
                        onClick={() => !esMiUsuario && updateMut.mutate({ id: u.id, data: { activo: !u.activo } })}
                        disabled={esMiUsuario}
                        className={clsx('p-1.5 rounded',
                          esMiUsuario ? 'opacity-30 cursor-not-allowed' : 'hover:bg-slate-100 text-slate-600'
                        )}
                        title={u.activo ? 'Desactivar' : 'Activar'}
                      >
                        <Power size={14} />
                      </button>
                      <button
                        onClick={() => {
                          if (esMiUsuario) return
                          if (confirm(`¿Eliminar permanentemente a ${u.nombre}${u.apellido ? ' ' + u.apellido : ''}?\n\nEsta acción no se puede deshacer.`)) {
                            deleteMut.mutate(u.id)
                          }
                        }}
                        disabled={esMiUsuario}
                        className={clsx('p-1.5 rounded',
                          esMiUsuario ? 'opacity-30 cursor-not-allowed' : 'hover:bg-red-50 text-red-600'
                        )}
                        title="Eliminar definitivamente"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Info por rol */}
      <div className="grid sm:grid-cols-3 gap-3">
        {Object.entries(ROL_META).map(([k, v]) => {
          const Icon = v.icon
          return (
            <div key={k} className="card">
              <div className="flex items-center gap-2">
                <div className={clsx('p-1.5 rounded-lg', v.cls)}>
                  <Icon size={14} />
                </div>
                <p className="font-semibold text-sm">{v.label}</p>
              </div>
              <p className="text-xs text-muted mt-2">{v.desc}</p>
            </div>
          )
        })}
      </div>

      {/* Modal Crear */}
      {showCrear && (
        <ModalCrearUsuario
          onClose={() => setShowCrear(false)}
          onSubmit={data => crearMut.mutate(data)}
          loading={crearMut.isPending}
          error={err}
        />
      )}
      {/* Modal Cambiar pwd */}
      {pwdModal && (
        <ModalCambiarPassword
          usuario={pwdModal}
          onClose={() => setPwdModal(null)}
          onSubmit={pwd => updateMut.mutate({ id: pwdModal.id, data: { password: pwd } })}
          loading={updateMut.isPending}
          error={err}
        />
      )}
    </div>
  )
}

// ── Modal Crear ───────────────────────────────────────────────────────────────

function ModalCrearUsuario({ onClose, onSubmit, loading, error }: {
  onClose: () => void
  onSubmit: (d: { nombre: string; apellido?: string; email: string; telefono?: string; cargo?: string; password: string; rol: 'admin'|'operador'|'viewer' }) => void
  loading: boolean
  error: string | null
}) {
  const [form, setForm] = useState({ nombre: '', apellido: '', email: '', telefono: '', cargo: '', password: '', rol: 'operador' as 'admin'|'operador'|'viewer' })
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="font-bold text-primary">Nuevo usuario</h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded"><X size={16} /></button>
        </div>
        <form
          onSubmit={e => {
            e.preventDefault()
            if (!isStrongPassword(form.password)) return
            onSubmit(form)
          }}
          className="p-5 space-y-3"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted font-medium">Nombre</label>
              <input required minLength={2} value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })}
                className="input-field w-full mt-1" />
            </div>
            <div>
              <label className="text-xs text-muted font-medium">Apellido</label>
              <input value={form.apellido} onChange={e => setForm({ ...form, apellido: e.target.value })}
                className="input-field w-full mt-1" />
            </div>
          </div>
          <div>
            <label className="text-xs text-muted font-medium">Email <span className="text-red-500">*</span></label>
            <input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
              className="input-field w-full mt-1" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted font-medium">Teléfono</label>
              <input value={form.telefono} onChange={e => setForm({ ...form, telefono: e.target.value })}
                placeholder="+595…" className="input-field w-full mt-1" />
            </div>
            <div>
              <label className="text-xs text-muted font-medium">Cargo</label>
              <input value={form.cargo} onChange={e => setForm({ ...form, cargo: e.target.value })}
                placeholder="Ej: Contador" className="input-field w-full mt-1" />
            </div>
          </div>
          <div>
            <label className="text-xs text-muted font-medium">Contraseña inicial</label>
            <input type="password" required minLength={8} value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
              className="input-field w-full mt-1" />
            <PasswordStrength password={form.password} />
            {form.password && !isStrongPassword(form.password) && (
              <p className="text-xs text-red-600 mt-1">{passwordErrorMessage(form.password)}</p>
            )}
          </div>
          <div>
            <label className="text-xs text-muted font-medium">Rol</label>
            <select value={form.rol} onChange={e => setForm({ ...form, rol: e.target.value as any })}
              className="input-field w-full mt-1">
              <option value="operador">Operador — carga y edita</option>
              <option value="admin">Admin — acceso total</option>
              <option value="viewer">Viewer — solo lectura</option>
            </select>
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Creando…' : 'Crear usuario'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ModalCambiarPassword({ usuario, onClose, onSubmit, loading, error }: {
  usuario: Usuario
  onClose: () => void
  onSubmit: (pwd: string) => void
  loading: boolean
  error: string | null
}) {
  const [pwd, setPwd] = useState('')
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="font-bold text-primary">Cambiar contraseña</h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded"><X size={16} /></button>
        </div>
        <form onSubmit={e => {
          e.preventDefault()
          if (!isStrongPassword(pwd)) return
          onSubmit(pwd)
        }} className="p-5 space-y-3">
          <p className="text-sm text-muted">
            Nueva contraseña para <b>{usuario.nombre}{usuario.apellido ? ` ${usuario.apellido}` : ''}</b>
          </p>
          <input type="password" required minLength={8} value={pwd} onChange={e => setPwd(e.target.value)}
            placeholder="Mínimo 8 caracteres" className="input-field w-full" autoFocus />
          <PasswordStrength password={pwd} />
          {pwd && !isStrongPassword(pwd) && (
            <p className="text-xs text-red-600 mt-1">{passwordErrorMessage(pwd)}</p>
          )}
          {error && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Guardando…' : 'Cambiar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}


// ─── Modal de invitación por email ───────────────────────────────────────────

function ModalInvitar({ onCerrar, onExito }: {
  onCerrar: () => void
  onExito: (mensaje: string) => void
}) {
  const [email, setEmail] = useState('')
  const [nombre, setNombre] = useState('')
  const [apellido, setApellido] = useState('')
  const [rol, setRol] = useState<'admin' | 'operador' | 'viewer'>('operador')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleEnviar = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      const res = await authApi.invitarUsuario({
        email: email.trim().toLowerCase(),
        nombre: nombre.trim(),
        apellido: apellido.trim() || undefined,
        rol,
      })
      const data = res.data
      if (data.warning) {
        onExito(data.warning)
      } else {
        onExito(data.mensaje || `Invitación enviada a ${email}.`)
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'No se pudo enviar la invitación.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-bold text-slate-900 flex items-center gap-2">
            <Mail size={18} className="text-emerald-600" /> Invitar usuario por email
          </h2>
          <button onClick={onCerrar} className="text-slate-400 hover:text-slate-700">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleEnviar} className="p-5 space-y-4">
          <p className="text-sm text-slate-600">
            Le mandamos un email al usuario para que active su cuenta y elija su propia contraseña.
            Es más seguro que crear la contraseña vos.
          </p>

          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              placeholder="usuario@empresa.com"
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                Nombre <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={nombre}
                onChange={e => setNombre(e.target.value)}
                required
                minLength={2}
                placeholder="Juan"
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                Apellido
              </label>
              <input
                type="text"
                value={apellido}
                onChange={e => setApellido(e.target.value)}
                placeholder="Pérez"
                className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Rol
            </label>
            <select
              value={rol}
              onChange={e => setRol(e.target.value as any)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600"
            >
              <option value="operador">Operador — puede cargar y editar datos</option>
              <option value="viewer">Viewer — solo lectura (dashboards)</option>
              <option value="admin">Admin — acceso total + gestión de usuarios</option>
            </select>
          </div>

          {error && (
            <div className="flex items-start gap-2 text-red-700 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
              <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onCerrar}
              className="flex-1 px-4 py-2.5 rounded-lg border border-slate-300 text-sm font-medium hover:bg-slate-50 transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="flex-1 inline-flex items-center justify-center gap-2 bg-emerald-600 text-white px-4 py-2.5 rounded-lg font-medium text-sm hover:bg-emerald-700 transition disabled:opacity-50"
            >
              <Send size={14} /> {enviando ? 'Enviando…' : 'Enviar invitación'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
