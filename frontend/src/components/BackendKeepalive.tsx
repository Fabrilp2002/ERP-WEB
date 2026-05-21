'use client'

/**
 * BackendKeepalive — mantiene caliente al backend Render mientras hay un usuario
 * con la app abierta. Sin esto, el free tier de Render duerme tras ~15 min de
 * inactividad y el siguiente request tarda ~50s en levantarse.
 *
 * Estrategia (defensa en profundidad):
 *  1. GitHub Actions cron `keepalive-backend.yml` cada 5 min — protege la app
 *     cuando NADIE la tiene abierta.
 *  2. Vercel Cron en `vercel.json` cada 5 min — redundancia para 1.
 *  3. ESTE componente — mientras al menos una pestaña esté abierta, hace ping
 *     cada 4 minutos. Garantiza que el backend NUNCA se duerma si el usuario
 *     está usando la app.
 *  4. Pre-warm en `/login` page mount.
 *
 * Se monta en el AppLayout (zona autenticada). No renderiza nada visible.
 */
import { useEffect, useRef } from 'react'
import { API_BASE_URL } from '@/lib/config'

const PING_INTERVAL_MS = 4 * 60 * 1000  // 4 minutos
const MIN_PING_GAP_MS  = 60 * 1000      // anti-thrash: no pingear si pinguamos hace menos de 1 min

async function pingHealth(reason: string) {
  try {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 15_000)
    await fetch(`${API_BASE_URL}/health`, {
      signal: ctrl.signal,
      cache: 'no-store',
      headers: { 'X-Warmup': `client-${reason}` },
    })
    clearTimeout(timer)
  } catch {
    // Si el ping falla, no hacemos ruido — el cron de GitHub Actions cubre.
  }
}

export default function BackendKeepalive() {
  const lastPingRef = useRef<number>(0)

  useEffect(() => {
    const tryPing = (reason: string) => {
      const now = Date.now()
      if (now - lastPingRef.current < MIN_PING_GAP_MS) return
      lastPingRef.current = now
      pingHealth(reason)
    }

    // Ping inicial al montar (mantiene el backend warm si justo despertó)
    tryPing('mount')

    // Ping periódico mientras la pestaña esté abierta
    const interval = setInterval(() => {
      // Solo pingueamos si la pestaña está visible — ahorra recursos y
      // pings inútiles si el usuario dejó la app abierta en background.
      if (document.visibilityState === 'visible') {
        tryPing('interval')
      }
    }, PING_INTERVAL_MS)

    // Ping al volver a la pestaña tras estar oculta (puede haber pasado mucho tiempo)
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        tryPing('visibility')
      }
    }
    document.addEventListener('visibilitychange', onVisibility)

    // Ping al recuperar foco (otro indicador de que el usuario volvió a usar la app)
    const onFocus = () => tryPing('focus')
    window.addEventListener('focus', onFocus)

    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('focus', onFocus)
    }
  }, [])

  return null
}
