/**
 * Proxy Next.js → FastAPI para importación masiva de facturas desde Excel.
 * Preserva el boundary del multipart reenviando el body crudo.
 */
import { API_BASE_URL } from '@/lib/config'
import { parseBackendResponse, proxyErrorResponse, timeoutSignal } from '../proxy-utils'

export const maxDuration = 60

export async function POST(req: Request) {
  const timeout = timeoutSignal()
  try {
    const auth = req.headers.get('Authorization') ?? ''
    const contentType = req.headers.get('content-type') ?? ''
    const url = new URL(req.url)
    const tipoDefault = url.searchParams.get('tipo_default') || 'venta'

    const body = await req.arrayBuffer()

    const res = await fetch(
      `${API_BASE_URL}/ocr/importar-excel?tipo_default=${encodeURIComponent(tipoDefault)}`,
      {
        method: 'POST',
        signal: timeout.signal,
        headers: { Authorization: auth, 'content-type': contentType },
        body: Buffer.from(body),
      }
    )

    const data = await parseBackendResponse(res)
    return Response.json(data, { status: res.status })
  } catch (err: unknown) {
    return proxyErrorResponse(err)
  } finally {
    timeout.done()
  }
}
