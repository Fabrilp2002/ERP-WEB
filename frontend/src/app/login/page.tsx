'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, Loader2, Lock, User, Zap, Wifi, WifiOff, RefreshCw } from 'lucide-react'
import { authApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { API_BASE_URL } from '@/lib/config'

// Auto-login local: si están seteadas estas variables en .env.local,
// la página de login entra sola. Sirve para desarrollo, NO para producción.
const DEV_EMAIL = process.env.NEXT_PUBLIC_DEV_EMAIL
const DEV_PASSWORD = process.env.NEXT_PUBLIC_DEV_PASSWORD
const DEV_AUTOLOGIN = !!(DEV_EMAIL && DEV_PASSWORD)

type ServerStatus = 'checking' | 'ready' | 'slow' | 'offline'

function normalizeLoginInput(raw: string): string {
  const value = raw.trim().toLowerCase()
  if (!value) return value
  if (value.includes('@')) return value
  if (value === 'admin') return 'admin@demo.com'
  return `${value}@erp.local`
}

function loginErrorMessage(err: any): string {
  const status = err?.response?.status
  const detail = err?.response?.data?.detail
  const text = typeof detail === 'string' ? detail : ''

  if (err?.code === 'ECONNABORTED' || err?.code === 'ERR_NETWORK') {
    return 'El servidor está tardando en responder. Reintentando automáticamente…'
  }
  if (!err?.response) return 'No pude conectarme con el servidor. Reintentando…'
  if (status === 401 || status === 403) return text || 'Usuario o contraseña incorrectos.'
  if (status === 423) return text || 'La cuenta está bloqueada temporalmente por intentos fallidos.'
  if (status === 404) return 'No encontramos ese usuario. Revisá lo que escribiste.'
  if (status >= 500) return 'El servidor no pudo validar el acceso. Intentá de nuevo en un momento.'
  return text || 'No se pudo iniciar sesión.'
}

function isRetryableError(err: any): boolean {
  return (
    err?.code === 'ECONNABORTED' ||
    err?.code === 'ERR_NETWORK' ||
    !err?.response ||
    (err?.response?.status ?? 0) >= 500
  )
}

/** Hace ping al /health del backend y devuelve true si respondió OK */
async function pingBackend(): Promise<boolean> {
  try {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 60_000)
    const res = await fetch(`${API_BASE_URL}/health`, {
      signal: ctrl.signal,
      cache: 'no-store',
    })
    clearTimeout(timer)
    return res.ok
  } catch {
    return false
  }
}

export default function LoginPage() {
  const [usuario, setUsuario] = useState(DEV_EMAIL || '')
  const [password, setPassword] = useState(DEV_PASSWORD || '')
  const [showPwd, setShowPwd] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [autoLoginAttempted, setAutoLoginAttempted] = useState(false)
  const [serverStatus, setServerStatus] = useState<ServerStatus>('checking')
  const [retryIn, setRetryIn] = useState<number | null>(null)
  const { login, token } = useAuth()
  const router = useRouter()
  const retryTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pendingRetry = useRef<{ email: string; pwd: string } | null>(null)

  // ── Pre-calentamiento del backend ────────────────────────────────────────
  useEffect(() => {
    let alive = true
    const slowTimer = setTimeout(() => {
      if (alive) setServerStatus('slow')
    }, 5_000)

    pingBackend().then(ok => {
      if (!alive) return
      clearTimeout(slowTimer)
      setServerStatus(ok ? 'ready' : 'offline')
    })

    return () => {
      alive = false
      clearTimeout(slowTimer)
    }
  }, [])

  // ── Auto-retry countdown ─────────────────────────────────────────────────
  const startRetryCountdown = useCallback((email: string, pwd: string, seconds = 8) => {
    pendingRetry.current = { email, pwd }
    setRetryIn(seconds)

    if (retryTimerRef.current) clearInterval(retryTimerRef.current)
    retryTimerRef.current = setInterval(() => {
      setRetryIn(prev => {
        if (prev === null || prev <= 1) {
          clearInterval(retryTimerRef.current!)
          return null
        }
        return prev - 1
      })
    }, 1_000)
  }, [])

  // Cuando llega a 0, ejecutar el retry
  useEffect(() => {
    if (retryIn !== null) return
    const pending = pendingRetry.current
    if (!pending) return
    pendingRetry.current = null
    doLogin(pending.email, pending.pwd, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retryIn])

  useEffect(() => () => {
    if (retryTimerRef.current) clearInterval(retryTimerRef.current)
  }, [])

  // ── Lógica de login ──────────────────────────────────────────────────────
  const doLogin = useCallback(async (email: string, pwd: string, isRetry = false) => {
    setLoading(true)
    if (!isRetry) setError('')
    const emailFinal = normalizeLoginInput(email)
    try {
      const { data } = await authApi.login(emailFinal, pwd)
      login(data.access_token, {
        id: data.usuario_id || '',
        empresa_id: data.empresa_id,
        nombre: data.usuario_nombre,
        apellido: data.usuario_apellido ?? null,
        email: emailFinal,
        rol: data.rol,
      })
      router.replace('/dashboard')
    } catch (err: any) {
      setLoading(false)
      if (isRetryableError(err)) {
        setError(loginErrorMessage(err))
        // Si el servidor está en cold start, esperar y reintentar automáticamente
        if (serverStatus !== 'ready') {
          startRetryCountdown(email, pwd, 8)
        }
      } else {
        setError(loginErrorMessage(err))
        pendingRetry.current = null
        setRetryIn(null)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [login, router, serverStatus, startRetryCountdown])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (retryIn !== null) {
      // Cancelar countdown y reintentar inmediatamente
      if (retryTimerRef.current) clearInterval(retryTimerRef.current)
      pendingRetry.current = null
      setRetryIn(null)
    }
    await doLogin(usuario, password)
  }

  // Auto-login en dev
  useEffect(() => {
    if (DEV_AUTOLOGIN && !token && !autoLoginAttempted && !loading) {
      setAutoLoginAttempted(true)
      doLogin(DEV_EMAIL!, DEV_PASSWORD!)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // ── Indicador de estado del servidor ────────────────────────────────────
  const StatusBadge = () => {
    if (serverStatus === 'ready') return null  // no molestar cuando todo está bien

    const map: Record<ServerStatus, { icon: React.ReactNode; text: string; cls: string }> = {
      checking: {
        icon: <Loader2 size={13} className="animate-spin shrink-0" />,
        text: 'Conectando con el servidor…',
        cls: 'bg-slate-50 border-slate-200 text-slate-500',
      },
      slow: {
        icon: <Loader2 size={13} className="animate-spin shrink-0 text-amber-500" />,
        text: 'El servidor está arrancando, puede tardar hasta 30s la primera vez.',
        cls: 'bg-amber-50 border-amber-200 text-amber-700',
      },
      offline: {
        icon: <WifiOff size={13} className="shrink-0 text-rose-500" />,
        text: 'Sin conexión con el servidor. Verificá tu internet o esperá un momento.',
        cls: 'bg-rose-50 border-rose-200 text-rose-700',
      },
      ready: { icon: <Wifi size={13} />, text: '', cls: '' },
    }
    const s = map[serverStatus]
    return (
      <div className={`flex items-center gap-2 text-xs border rounded-xl px-3 py-2.5 mb-4 ${s.cls}`}>
        {s.icon}
        <span>{s.text}</span>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center overflow-x-hidden p-4 bg-slate-50">
      <div className="w-full max-w-[calc(100vw-2rem)] sm:max-w-md min-w-0">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-700 shadow-lg shadow-blue-500/20 mb-4">
            <svg viewBox="0 0 64 64" className="w-9 h-9" aria-hidden="true">
              <path d="M20 22h24v6H20zM20 32h16v6H20zM20 42h20v6H20z" fill="white" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Bienvenido</h1>
          <p className="text-slate-500 text-sm mt-1">Ingresá para entrar a tu negocio</p>
        </div>

        {DEV_AUTOLOGIN && (
          <div className="mb-4 flex items-center gap-2 text-xs bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-3 py-2.5">
            <Zap size={14} className="flex-shrink-0" />
            <span>
              <strong>Auto-login activo (modo dev).</strong> Las credenciales vienen de <code className="font-mono">.env.local</code>.
              {loading && <span className="ml-1">Entrando…</span>}
            </span>
          </div>
        )}

        <StatusBadge />

        <div className="bg-white rounded-2xl border border-slate-200 shadow-xl shadow-slate-200/60 p-5 sm:p-7">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5 ml-1">
                Usuario o email
              </label>
              <div className="relative">
                <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-3 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:bg-white focus:border-blue-500 transition-all"
                  placeholder="admin@demo.com"
                  value={usuario}
                  onChange={e => setUsuario(e.target.value)}
                  required
                  autoComplete="username"
                  autoCapitalize="off"
                  spellCheck={false}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5 ml-1">
                Contraseña
              </label>
              <div className="relative">
                <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type={showPwd ? 'text' : 'password'}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-10 pr-11 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:bg-white focus:border-blue-500 transition-all"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd(s => !s)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition"
                  aria-label={showPwd ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  tabIndex={-1}
                >
                  {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2.5 text-rose-700 text-sm bg-rose-50 border border-rose-200 rounded-xl px-3.5 py-3">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500 flex-shrink-0 mt-1.5" />
                <span className="leading-snug flex-1">{error}</span>
                {retryIn !== null && (
                  <span className="shrink-0 text-xs font-mono text-rose-500 ml-1">({retryIn}s)</span>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={loading && retryIn === null}
              className="w-full flex items-center justify-center gap-2 bg-blue-700 text-white px-4 py-3 rounded-xl font-semibold text-sm hover:bg-blue-800 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/25 mt-2"
            >
              {loading && retryIn === null ? (
                <><Loader2 size={16} className="animate-spin" /> Ingresando…</>
              ) : retryIn !== null ? (
                <><RefreshCw size={16} className="animate-spin" /> Reintentando en {retryIn}s — o hacé click para entrar ya</>
              ) : (
                'Entrar'
              )}
            </button>

            <div className="text-center pt-2">
              <a href="/auth/reset-password" className="text-xs text-slate-500 hover:text-blue-600 transition">
                ¿Olvidaste tu contraseña?
              </a>
            </div>
          </form>
        </div>

        <p className="text-center text-slate-400 text-xs mt-6">
          Tu información está protegida
        </p>
      </div>
    </div>
  )
}
