/**
 * Proxy Next.js → FastAPI para confirmar y guardar la factura extraída.
 * Mismo origen → sin CORS, sin preflight.
 */
import { API_BASE_URL } from '@/lib/config'
import { parseBackendResponse, proxyErrorResponse, timeoutSignal } from '../proxy-utils'

export const maxDuration = 60

export async function POST(req: Request) {
  const timeout = timeoutSignal()
  try {
    const auth = req.headers.get('Authorization') ?? ''
    const body = await req.text()

    const res = await fetch(`${API_BASE_URL}/ocr/confirmar`, {
      method: 'POST',
      signal: timeout.signal,
      headers: {
        Authorization: auth,
        'content-type': 'application/json',
      },
      body,
    })

    const data = await parseBackendResponse(res)

    return Response.json(data, { status: res.status })
  } catch (err: unknown) {
    return proxyErrorResponse(err)
  } finally {
    timeout.done()
  }
}
