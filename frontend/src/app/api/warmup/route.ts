/**
 * GET /api/warmup
 *
 * Endpoint invocado por el Vercel Cron Job cada 5 minutos para mantener
 * el backend de Render despierto. Sin este ping, Render free tier duerme
 * el servicio tras ~15 min de inactividad y el primer login tarda ~50s.
 *
 * También es llamado por la página de login en el mount del componente
 * para pre-calentar el backend mientras el usuario escribe sus credenciales.
 */
import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ||
  'https://erp-web-backend-i5zv.onrender.com'

export async function GET() {
  const start = Date.now()
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 12_000)

    const res = await fetch(`${BACKEND_URL}/health`, {
      signal: controller.signal,
      cache: 'no-store',
      headers: { 'X-Warmup': '1' },
    })
    clearTimeout(timer)

    const ms = Date.now() - start
    let body: unknown = {}
    try { body = await res.json() } catch { /* ignore */ }

    return NextResponse.json({ ok: res.ok, ms, backend: body })
  } catch (e: unknown) {
    const ms = Date.now() - start
    const msg = e instanceof Error ? e.message : String(e)
    return NextResponse.json({ ok: false, ms, error: msg }, { status: 503 })
  }
}
