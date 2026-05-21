export type Rol = 'admin' | 'operador' | 'viewer'

export interface Usuario {
  id: string
  empresa_id: string
  nombre: string
  apellido?: string | null
  email: string
  telefono?: string | null
  cargo?: string | null
  rol: Rol
}

export interface Empresa {
  id: string
  nombre: string
  ruc?: string | null
  direccion?: string | null
  telefono?: string | null
  email?: string | null
  moneda_principal?: string | null
  logo_url?: string | null
  activa: boolean
  fecha_creacion: string
}

export interface AuthState {
  token: string | null
  usuario: Usuario | null
  empresaId: string | null
}

export interface Cliente {
  id: string
  empresa_id: string
  nombre: string
  ruc?: string
  telefono?: string
  email?: string
  direccion?: string | null
  notas?: string | null
  activo: boolean
  fecha_creacion: string
}

export interface Proveedor extends Cliente {}

export interface ItemInventario {
  id: string
  empresa_id: string
  descripcion: string
  codigo?: string
  cantidad_actual: string   // string para mantener precisión decimal
  costo_unitario: string
  punto_reorden: string
  unidad_medida?: string
  activo: boolean
  fecha_creacion: string
}

export interface DetalleComprobante {
  id: string
  descripcion: string
  cantidad: string
  precio_unitario: string
  porcentaje_iva: string
  subtotal: string
  iva_monto: string
}

export interface Comprobante {
  id: string
  empresa_id: string
  tipo_id?: string | null
  comprobante_origen_id?: string | null
  numero_comprobante: string
  fecha_emision: string
  monto_total: string
  monto_pagado?: string | null
  saldo_pendiente: string
  estado_pago?: 'pagado' | 'no_pagado' | 'pago_parcial' | 'anulado' | 'rechazado' | 'no_aplica' | null
  metodo_carga: 'manual' | 'ocr_pdf' | 'ocr_imagen'
  estado_validacion: 'pendiente_revision' | 'confirmado' | 'rechazado' | 'anulado'
  condicion?: 'contado' | 'credito'
  medio_pago_contado?: 'efectivo' | 'transferencia' | 'cheque' | 'tarjeta' | 'otro' | null
  ruta_archivo?: string | null
  ubicacion_fisica?: string | null
  fecha_vencimiento?: string | null
  contraparte?: string | null
  tipo?: 'venta' | 'compra' | null
  cliente_id?: string | null
  proveedor_id?: string | null
  notas?: string | null
  descripcion?: string | null
  cant_items?: number | null
  cargado_por?: string | null
  fecha_creacion: string
  detalle?: DetalleComprobante[]
  notas_vinculadas?: Array<{
    id: string
    numero_comprobante: string
    fecha_emision: string
    monto_total: string
    estado_validacion: 'pendiente_revision' | 'confirmado' | 'rechazado' | 'anulado'
    tipo_nombre?: string | null
    notas?: string | null
  }>
}

export interface TipoComprobante {
  id: string
  empresa_id: string
  nombre: string
}

export interface ResumenDashboard {
  total_facturas_pendientes: number
  monto_por_cobrar: string
  monto_por_pagar: string
  items_bajo_stock: number
  ultima_actualizacion: string
}

export interface SaldoCliente {
  cliente_id: string
  cliente: string
  total_facturado: string
  total_cobrado: string
  saldo_pendiente: string
}

export interface SaldoProveedor {
  proveedor_id: string
  proveedor: string
  total_facturado: string
  total_pagado: string
  saldo_pendiente: string
}

// Offline queue
export interface SyncItem {
  id?: number
  tabla: string
  operacion: 'INSERT' | 'UPDATE' | 'DELETE'
  payload: Record<string, unknown>
  endpoint: string
  method: string
  estado: 'pendiente' | 'sincronizado' | 'error'
  intentos: number
  fecha_creacion: Date
}
