export const PROXY_TIMEOUT_MS = 55000

export function backendTimeoutResponse() {
  return Response.json(
    {
      detail:
        'El servidor esta tardando demasiado en responder. Espera un minuto y proba de nuevo.',
    },
    { status: 504 },
  )
}

export function humanDetail(text: string, status: number) {
  const normalized = text.toLowerCase()
  if (normalized.includes('request entity') || normalized.includes('payload too large')) {
    return 'El archivo es demasiado pesado para subirlo. Proba con una foto mas liviana o recortada.'
  }
  if (normalized.includes('not found') || status === 404) {
    return 'No encontre esa funcion en el servidor desplegado. Espera el ultimo deploy y volve a probar.'
  }
  if (normalized.includes('<html') || normalized.includes('<!doctype')) {
    return `El servidor devolvio una pagina de error (${status}). Espera el deploy y volve a intentar.`
  }
  return text || `Error ${status}`
}

export async function parseBackendResponse(res: Response) {
  const text = await res.text()
  try {
    return text ? JSON.parse(text) : {}
  } catch {
    return { detail: humanDetail(text, res.status) }
  }
}

export function timeoutSignal() {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), PROXY_TIMEOUT_MS)
  return { signal: controller.signal, done: () => clearTimeout(timer) }
}

export function proxyErrorResponse(err: unknown) {
  if (err instanceof Error && err.name === 'AbortError') return backendTimeoutResponse()
  const msg = err instanceof Error ? err.message : 'Error en el proxy'
  return Response.json({ detail: msg }, { status: 500 })
}
