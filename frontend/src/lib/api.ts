import axios from 'axios'
import { useAuth } from './auth'
import { offlineQueue } from './offline'
import { API_BASE_URL } from './config'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  timeoutErrorMessage: 'El servidor esta tardando demasiado en responder. Espera un minuto y proba de nuevo.',
})

api.interceptors.request.use((config) => {
  const token = useAuth.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const isOffline = !navigator.onLine || error.code === 'ERR_NETWORK'
    const req = error.config

    if (isOffline && req.method !== 'get' && !req._retry) {
      await offlineQueue.encolar({
        tabla: req.url?.split('/')[1] ?? 'desconocido',
        operacion: req.method === 'post' ? 'INSERT'
          : req.method === 'put' || req.method === 'patch' ? 'UPDATE'
            : 'DELETE',
        payload: (() => {
          try {
            return req.data && typeof req.data === 'string' ? JSON.parse(req.data) : {}
          } catch {
            return {}
          }
        })(),
        endpoint: req.url ?? '',
        method: req.method?.toUpperCase() ?? 'POST',
        estado: 'pendiente',
        intentos: 0,
        fecha_creacion: new Date(),
      })
      return { data: { _offline: true }, status: 202 }
    }

    if (error.response?.status === 401 && !String(req?.url || '').includes('/auth/token')) {
      const detail = String(error.response?.data?.detail || '').toLowerCase()
      const esTokenInvalido = detail.includes('token') || detail.includes('autenticado') || detail.includes('credenciales')
      if (esTokenInvalido) useAuth.getState().logout()
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/token', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  pedirResetPassword: (email: string) =>
    api.post('/auth/reset-password', { email }),
  confirmarResetPassword: (token: string, passwordNueva: string) =>
    api.post('/auth/reset-password/confirm', { token, password_nueva: passwordNueva }),
  confirmarSeteoPassword: (token: string, passwordNueva: string) =>
    api.post('/auth/seteo-password/confirm', { token, password_nueva: passwordNueva }),
  invitarUsuario: (data: { email: string; nombre: string; apellido?: string; rol: 'admin' | 'operador' | 'viewer' }) =>
    api.post('/auth/invitar-usuario', data),
}

export const dashboardApi = {
  resumen: (desde?: string, hasta?: string) =>
    api.get('/dashboard/resumen', { params: { desde, hasta } }),
  // v7.2 — `cuentasCorrientes` removido: era el feed del antiguo /cuentas que
  // se consolidó en /comprobantes. El endpoint backend `/dashboard/cuentas-corrientes`
  // sigue vivo por compatibilidad pero ya no se consume desde el frontend.
  stockCritico: () => api.get('/dashboard/stock-critico'),
  flujoMensual: (meses = 6, desde?: string, hasta?: string) =>
    api.get('/dashboard/flujo-mensual', { params: { meses, desde, hasta } }),
  topClientes: (limite = 5, desde?: string, hasta?: string) =>
    api.get('/dashboard/top-clientes', { params: { limite, desde, hasta } }),
  mediosPago: (desde?: string, hasta?: string) =>
    api.get('/dashboard/medios-pago', { params: { desde, hasta } }),
  ultimosComprobantes: (limite = 6, desde?: string, hasta?: string) =>
    api.get('/dashboard/ultimos-comprobantes', { params: { limite, desde, hasta } }),
}

export const clientesApi = {
  listar: (buscar?: string) => api.get('/clientes', { params: { buscar } }),
  crear: (data: object) => api.post('/clientes', data),
  actualizar: (id: string, data: object) => api.put(`/clientes/${id}`, data),
  eliminar: (id: string) => api.delete(`/clientes/${id}`),
  saldo: (id: string) => api.get(`/clientes/${id}/saldo`),
}

export const proveedoresApi = {
  listar: (buscar?: string) => api.get('/proveedores', { params: { buscar } }),
  crear: (data: object) => api.post('/proveedores', data),
  actualizar: (id: string, data: object) => api.put(`/proveedores/${id}`, data),
  eliminar: (id: string) => api.delete(`/proveedores/${id}`),
  saldo: (id: string) => api.get(`/proveedores/${id}/saldo`),
}

export type ComprobantesListadoConTotal<T = unknown> = {
  items: T[]
  total: number
  /** Suma de monto_total de TODAS las filas filtradas (no paginadas). */
  suma_monto_total: number
  /** Suma de saldo_pendiente de TODAS las filas filtradas. */
  suma_saldo_pendiente: number
  page: number
  page_size: number
}

export const comprobantesApi = {
  /** Listado clásico (devuelve array directo). Usado por /movimientos y /timeline. */
  listar: (params?: object) => api.get('/comprobantes', { params }),
  /** Listado paginado con total — para la UI de `/comprobantes` que muestra "Página N de M". */
  listarPaginado: <T = unknown>(params: {
    page?: number
    page_size?: number
    estado?: string
    estado_pago?: string
    tipo?: 'venta' | 'compra'
    cliente_id?: string
    proveedor_id?: string
    /** Texto libre — matchea número o nombre de cliente/proveedor (ILIKE). */
    buscar?: string
    /** Una clave de _ORDER_BY_MAP en el backend (fecha_desc, monto_asc, etc.). */
    order_by?: string
  }) =>
    api.get<ComprobantesListadoConTotal<T>>('/comprobantes', { params: { ...params, with_total: true } }),
  tipos: () => api.get('/comprobantes/tipos'),
  obtener: (id: string) => api.get(`/comprobantes/${id}`),
  crear: (data: object) => api.post('/comprobantes', data),
  validar: (id: string, estado: 'confirmado' | 'rechazado') =>
    api.patch(`/comprobantes/${id}/validar`, null, { params: { estado } }),
  anular: (id: string, motivo: string) =>
    api.patch(`/comprobantes/${id}/anular`, { motivo }),
}

export const pagosApi = {
  listarPorComprobante: (comprobante_id: string) =>
    api.get('/pagos', { params: { comprobante_id } }),
  registrar: (data: {
    comprobante_id: string
    fecha_pago: string
    monto_pagado: number | string
    medio_pago: string
    numero_recibo?: string
    notas?: string
  }) => api.post('/pagos', data),
  eliminar: (id: string) => api.delete(`/pagos/${id}`),
  saldosClientes: () => api.get('/pagos/saldos/clientes'),
  saldosProveedores: () => api.get('/pagos/saldos/proveedores'),
  historialCliente: (id: string) => api.get(`/pagos/cliente/${id}/historial`),
  historialProveedor: (id: string) => api.get(`/pagos/proveedor/${id}/historial`),
  analisisCliente: (id: string) => api.get(`/pagos/analisis-cliente/${id}`),
  analisisProveedor: (id: string) => api.get(`/pagos/analisis-proveedor/${id}`),
  movimientos: (params?: { tipo?: 'cobro' | 'pago'; desde?: string; hasta?: string }) =>
    api.get('/pagos/movimientos', { params }),
}

export const usuariosApi = {
  me: () => api.get('/usuarios/me'),
  seguridad: () => api.get('/usuarios/me/seguridad'),
  exportarMisDatos: () => api.get('/usuarios/me/exportar-datos', { responseType: 'blob' }),
  eliminarMiCuenta: () => api.delete('/usuarios/me'),
  listar: () => api.get('/usuarios'),
  crear: (data: { nombre: string; apellido?: string; email: string; telefono?: string; cargo?: string; password: string; rol: 'admin'|'operador'|'viewer' }) =>
    api.post('/usuarios', data),
  actualizar: (id: string, data: Partial<{ nombre: string; apellido: string; telefono: string; cargo: string; rol: string; activo: boolean; password: string }>) =>
    api.patch(`/usuarios/${id}`, data),
  eliminar: (id: string) => api.delete(`/usuarios/${id}`),
}

export const adjuntosApi = {
  subirComprobante: (comprobante_id: string, archivo: File) => {
    const fd = new FormData()
    fd.append('archivo', archivo)
    return api.post(`/adjuntos/comprobante/${comprobante_id}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  quitarComprobante: (comprobante_id: string) => api.delete(`/adjuntos/comprobante/${comprobante_id}`),
  subirPago: (pago_id: string, archivo: File) => {
    const fd = new FormData()
    fd.append('archivo', archivo)
    return api.post(`/adjuntos/pago/${pago_id}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  quitarPago: (pago_id: string) => api.delete(`/adjuntos/pago/${pago_id}`),
}

export const empresaApi = {
  obtener: () => api.get('/empresa'),
  actualizar: (data: Partial<{ nombre: string; ruc: string; direccion: string; telefono: string; email: string; moneda_principal: string }>) =>
    api.patch('/empresa', data),
  subirLogo: (archivo: File) => {
    const fd = new FormData()
    fd.append('archivo', archivo)
    return api.post('/empresa/logo', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  quitarLogo: () => api.delete('/empresa/logo'),
}

export const inventarioApi = {
  listar: (params?: object) => api.get('/inventario', { params }),
  crear: (data: object) => api.post('/inventario', data),
  actualizar: (id: string, data: object) => api.put(`/inventario/${id}`, data),
  eliminar: (id: string) => api.delete(`/inventario/${id}`),
  ajustarCantidad: (id: string, cantidad: number) =>
    api.patch(`/inventario/${id}/cantidad`, null, { params: { cantidad_nueva: cantidad } }),
}

export const actividadApi = {
  listar: (params?: { tabla?: string; accion?: string; usuario_id?: string; desde?: string; hasta?: string; limite?: number }) =>
    api.get('/actividad', { params }),
}

export const reportesApi = {
  ivaVentas: (params?: { mes?: string; desde?: string; hasta?: string }) =>
    api.get('/reportes/iva/ventas', { params }),
  ivaCompras: (params?: { mes?: string; desde?: string; hasta?: string }) =>
    api.get('/reportes/iva/compras', { params }),
  ivaLiquidacion: (params?: { mes?: string; desde?: string; hasta?: string }) =>
    api.get('/reportes/iva/liquidacion', { params }),
  aging: (tipo: 'clientes' | 'proveedores' = 'clientes') =>
    api.get('/reportes/aging', { params: { tipo } }),
}

// ── Lotes de inventario (v7.1) ───────────────────────────────────────────────
export type LoteResumen = {
  id: string
  numero_lote: string
  cantidad: number
  cantidad_inicial: number
  costo_unitario: number
  fecha_ingreso: string | null
  fecha_vencimiento: string | null
  inventario_id?: string
  inventario_codigo?: string | null
  inventario_descripcion?: string
  unidad_medida?: string | null
  proveedor_nombre?: string | null
}

export type LoteVencimiento = {
  lote_id: string
  numero_lote: string
  cantidad: number
  costo_unitario: number
  valor_lote: number
  fecha_ingreso: string | null
  fecha_vencimiento: string
  dias_restantes: number
  vencido: boolean
  inventario_id: string
  inventario_codigo: string | null
  inventario_descripcion: string
  unidad_medida: string | null
}

export const lotesApi = {
  listar: (params?: { solo_con_vencimiento?: boolean; limit?: number }) =>
    api.get<LoteResumen[]>('/inventario/lotes/', { params }),
  porItem: (inventarioId: string, incluirAgotados = false) =>
    api.get<LoteResumen[]>(`/inventario/lotes/por-item/${inventarioId}`, {
      params: { incluir_agotados: incluirAgotados },
    }),
  vencimientos: (dias?: number) =>
    api.get<LoteVencimiento[]>('/inventario/lotes/vencimientos', {
      params: dias != null ? { dias } : undefined,
    }),
  crear: (data: {
    inventario_id: string
    numero_lote: string
    cantidad: number | string
    costo_unitario: number | string
    fecha_ingreso?: string
    fecha_vencimiento?: string
    proveedor_id?: string
    comprobante_id?: string
    notas?: string
  }) => api.post('/inventario/lotes/', data),
}

// ── Recetas (Bill of Materials / BOM) ─────────────────────────────────────────
export const recetasApi = {
  listar: (params?: { activas?: boolean; producto_id?: string }) =>
    api.get('/recetas/', { params }),
  obtener: (id: string) =>
    api.get(`/recetas/${id}`),
  crear: (data: object) =>
    api.post('/recetas/', data),
  actualizar: (id: string, data: object) =>
    api.put(`/recetas/${id}`, data),
  eliminar: (id: string) =>
    api.delete(`/recetas/${id}`),
  capacidad: (id: string) =>
    api.get(`/recetas/${id}/capacidad`),
  // Lotes
  listarLotes: (estado?: string) =>
    api.get('/recetas/lotes/listar', { params: estado ? { estado } : undefined }),
  crearLote: (data: object) =>
    api.post('/recetas/lotes', data),
}

export type ChatStreamEvent =
  | { type: 'token'; text: string }
  | { type: 'accion'; accion: { funcion: string; argumentos: Record<string, unknown>; resultado: Record<string, unknown> } }
  | { type: 'done'; acciones: { funcion: string; argumentos: Record<string, unknown>; resultado: Record<string, unknown> }[] }
  | { type: 'error'; message: string }

/** Consume el endpoint /chat/mensaje-stream (text/event-stream) y emite eventos parseados. */
async function* streamChat(
  mensaje: string,
  historial: object[],
  forzarGemini = false,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent, void, void> {
  const token = useAuth.getState().token
  const resp = await fetch(`${API_BASE_URL}/chat/mensaje-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ mensaje, historial, forzar_gemini: forzarGemini }),
    signal,
  })
  if (!resp.ok || !resp.body) {
    yield { type: 'error', message: `El asistente no pudo responder (HTTP ${resp.status}).` }
    return
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // SSE events terminan con doble \n\n. Procesamos eventos completos.
    let idx: number
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const eventBlock = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      for (const line of eventBlock.split('\n')) {
        if (!line.startsWith('data:')) continue
        const payload = line.slice(5).trim()
        if (!payload) continue
        try {
          yield JSON.parse(payload) as ChatStreamEvent
        } catch {
          /* ignorar chunk roto */
        }
      }
    }
  }
}

export const chatApi = {
  enviarMensaje: (mensaje: string, historial: object[], forzarGemini = false) =>
    api.post('/chat/mensaje', { mensaje, historial, forzar_gemini: forzarGemini }),
  enviarMensajeStream: streamChat,
  confirmarAccion: (actionToken: string, historial: object[] = []) =>
    api.post('/chat/confirmar-accion', { action_token: actionToken, historial }),
  estado: () => api.get('/chat/estado'),
}
