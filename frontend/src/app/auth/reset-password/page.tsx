'use client'
import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { authApi } from '@/lib/api'
import PasswordStrength, { isStrongPassword, passwordErrorMessage } from '@/components/PasswordStrength'
import { Building2, Lock, Eye, EyeOff, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'

/**
 * Página de "olvidé mi contraseña" + confirmación con token.
 *
 * Dos modos según la URL:
 * - Sin token  → muestra form de email para pedir el link
 * - Con token  → muestra form para escribir nueva password
 *
 * Acceso vía link del email: /auth/reset-password?token=XYZ...
 */
function ResetPasswordContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  // Modo 1: pedir email
  const [email, setEmail] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  // Modo 2: confirmar nueva password
  const [pwd, setPwd] = useState('')
  const [pwd2, setPwd2] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const [exito, setExito] = useState(false)

  // ── Pedir email ────────────────────────────────────────────────────────────
  const handlePedirReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await authApi.pedirResetPassword(email.trim())
      setMensaje('Si tu email está registrado, te llegará un enlace en unos minutos. Revisá tu bandeja de spam si no lo ves.')
    } catch (err: any) {
      // No mostrar errores específicos para no filtrar info
      setMensaje('Si tu email está registrado, te llegará un enlace en unos minutos.')
    } finally {
      setEnviando(false)
    }
  }

  // ── Confirmar nueva password ───────────────────────────────────────────────
  const handleConfirmar = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!isStrongPassword(pwd)) {
      setError(passwordErrorMessage(pwd))
      return
    }
    if (pwd !== pwd2) {
      setError('Las contraseñas no coinciden.')
      return
    }
    if (!token) {
      setError('El enlace no es válido. Pedí uno nuevo.')
      return
    }

    setEnviando(true)
    try {
      await authApi.confirmarResetPassword(token, pwd)
      setExito(true)
      setTimeout(() => router.replace('/login'), 2500)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail?.errores)
            ? detail.errores.join(' · ')
            : 'No se pudo cambiar la contraseña.'
      )
    } finally {
      setEnviando(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex bg-slate-100">
      {/* Panel izquierdo branding (oculto en mobile) */}
      <div className="hidden lg:flex lg:w-5/12 bg-slate-900 flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-700 rounded-xl flex items-center justify-center">
            <Building2 size={20} className="text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-lg leading-tight">Mi Negocio</p>
            <p className="text-slate-400 text-xs">Sistema de Gestión Empresarial</p>
          </div>
        </div>
        <p className="text-slate-600 text-xs">© 2026 Mi Negocio</p>
      </div>

      {/* Panel derecho — form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-10 h-10 bg-blue-700 rounded-xl flex items-center justify-center">
              <Building2 size={20} className="text-white" />
            </div>
            <p className="text-slate-900 font-bold text-lg">Mi Negocio</p>
          </div>

          {/* Caso 1: éxito al confirmar */}
          {exito ? (
            <div className="bg-white rounded-xl border border-green-200 shadow-sm p-8 text-center">
              <CheckCircle2 size={48} className="text-green-500 mx-auto mb-3" />
              <h1 className="text-xl font-semibold text-slate-900 mb-2">¡Contraseña actualizada!</h1>
              <p className="text-sm text-slate-600">Te estamos llevando al inicio de sesión…</p>
            </div>
          ) : token ? (
            /* Caso 2: tiene token → form de nueva password */
            <>
              <div className="mb-8">
                <h1 className="text-2xl font-semibold text-slate-900">Nueva contraseña</h1>
                <p className="text-slate-500 text-sm mt-1">
                  Elegí una contraseña nueva para tu cuenta.
                </p>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                <form onSubmit={handleConfirmar} className="space-y-5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                      Nueva contraseña
                    </label>
                    <div className="relative">
                      <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type={showPwd ? 'text' : 'password'}
                        className="w-full border border-slate-200 rounded-lg pl-9 pr-10 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                        value={pwd}
                        onChange={e => setPwd(e.target.value)}
                        required
                        minLength={8}
                        placeholder="Mín. 8 caracteres"
                        autoFocus
                      />
                      <button
                        type="button"
                        onClick={() => setShowPwd(s => !s)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-700"
                        tabIndex={-1}
                      >
                        {showPwd ? <EyeOff size={15}/> : <Eye size={15}/>}
                      </button>
                    </div>
                    <PasswordStrength password={pwd} />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                      Repetir contraseña
                    </label>
                    <div className="relative">
                      <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                      <input
                        type={showPwd ? 'text' : 'password'}
                        className="w-full border border-slate-200 rounded-lg pl-9 pr-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                        value={pwd2}
                        onChange={e => setPwd2(e.target.value)}
                        required
                        placeholder="Igual que arriba"
                      />
                    </div>
                  </div>

                  {error && (
                    <div className="flex items-start gap-2 text-red-700 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
                      <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={enviando}
                    className="w-full flex items-center justify-center gap-2 bg-blue-700 text-white px-4 py-2.5 rounded-lg font-medium text-sm hover:bg-blue-800 transition-colors disabled:opacity-50 shadow-sm"
                  >
                    {enviando && <Loader2 size={16} className="animate-spin" />}
                    {enviando ? 'Guardando…' : 'Cambiar contraseña'}
                  </button>
                </form>
              </div>
            </>
          ) : (
            /* Caso 3: sin token → form de email */
            <>
              <div className="mb-8">
                <h1 className="text-2xl font-semibold text-slate-900">Recuperar acceso</h1>
                <p className="text-slate-500 text-sm mt-1">
                  Te mandamos un enlace al email para que puedas crear una contraseña nueva.
                </p>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                <form onSubmit={handlePedirReset} className="space-y-5">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                      Tu email
                    </label>
                    <input
                      type="email"
                      className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      required
                      placeholder="vos@empresa.com"
                      autoFocus
                    />
                  </div>

                  {mensaje && (
                    <div className="flex items-start gap-2 text-green-800 text-sm bg-green-50 border border-green-200 rounded-lg px-3 py-2.5">
                      <CheckCircle2 size={16} className="mt-0.5 flex-shrink-0" />
                      <span>{mensaje}</span>
                    </div>
                  )}
                  {error && (
                    <div className="text-red-700 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={enviando}
                    className="w-full flex items-center justify-center gap-2 bg-blue-700 text-white px-4 py-2.5 rounded-lg font-medium text-sm hover:bg-blue-800 transition-colors disabled:opacity-50 shadow-sm"
                  >
                    {enviando && <Loader2 size={16} className="animate-spin" />}
                    {enviando ? 'Enviando…' : 'Mandarme el enlace'}
                  </button>
                </form>

                <div className="mt-5 text-center">
                  <a href="/login" className="text-sm text-blue-700 hover:underline">
                    Volver al inicio de sesión
                  </a>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-slate-100">
      <Loader2 size={32} className="animate-spin text-slate-400" />
    </div>}>
      <ResetPasswordContent />
    </Suspense>
  )
}
