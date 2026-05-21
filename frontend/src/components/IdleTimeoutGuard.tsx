'use client'
import { Clock, LogOut } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { useIdleTimeout } from '@/lib/idle-timeout'

export default function IdleTimeoutGuard({ minutos = 30 }: { minutos?: number }) {
  const logout = useAuth(s => s.logout)
  const { showWarning, secondsLeft, stayActive } = useIdleTimeout(minutos, logout)

  if (!showWarning) return null

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-slate-200">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-amber-100 p-2 text-amber-700">
            <Clock size={22} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">¿Seguís trabajando?</h2>
            <p className="mt-1 text-sm text-slate-600">
              Por seguridad vamos a cerrar tu sesión en <b>{secondsLeft}s</b> si no confirmás actividad.
            </p>
          </div>
        </div>
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button type="button" onClick={logout} className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <LogOut size={16} /> Salir ahora
          </button>
          <button type="button" onClick={stayActive} className="inline-flex items-center justify-center rounded-lg bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800">
            Seguir trabajando
          </button>
        </div>
      </div>
    </div>
  )
}
