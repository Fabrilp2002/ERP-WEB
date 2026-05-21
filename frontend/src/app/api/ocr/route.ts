/**
 * Proxy Next.js → FastAPI para upload de facturas.
 * Pasa el body crudo (ArrayBuffer) para preservar el boundary del multipart.
 */
import { API_BASE_URL } from '@/lib/config'
import { parseBackendResponse, proxyErrorResponse, timeoutSignal } from './proxy-utils'

export const maxDuration = 60

export async function POST(req: Request) {
  const timeout = timeoutSignal()
  try {
    const auth = req.headers.get('Authorization') ?? ''
    const contentType = req.headers.get('content-type') ?? ''

    // Leer el body completo como bytes crudos
    const body = await req.arrayBuffer()

    // Reenviar a FastAPI con el mismo Content-Type (incluye el boundary)
    const res = await fetch(`${API_BASE_URL}/ocr/extraer`, {
      method: 'POST',
      signal: timeout.signal,
      headers: {
        Authorization: auth,
        'content-type': contentType,
      },
      body: Buffer.from(body),
    })

    // Leer respuesta como texto primero por si no es JSON válido
    const data = await parseBackendResponse(res)

    return Response.json(data, { status: res.status })
  } catch (err: unknown) {
    return proxyErrorResponse(err)
  } finally {
    timeout.done()
  }
}
