'use client'
import { useState, useCallback, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, adjuntosApi } from '@/lib/api'
import { API_BASE_URL } from '@/lib/config'
import {
  Upload, FileText, FileImage, Loader2, CheckCircle2,
  XCircle, AlertTriangle, Edit3, RefreshCw, X,
  ScanLine, Settings, Eye, EyeOff, Save, Plus, Trash2,
  ArrowRight, FileSpreadsheet, Camera, Download,
} from 'lucide-react'
import Decimal from 'decimal.js'

function fmt(v: number | string | undefined) {
  return new Decimal(v || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

type TipoFactura = 'venta' | 'compra'
type ModoEntrada = 'auto' | 'manual'

interface ItemFactura {
  codigo: string
  descripcion: string
  cantidad: number
  precio_unitario: number
  porcentaje_iva: 0 | 5 | 10
}

interface DatoFactura {
  numero_comprobante: string
  fecha_emision: string
  ruc_emisor: string
  razon_social_emisor: string
  ruc_cliente: string
  razon_social_cliente: string
  condicion: 'contado' | 'credito'
  medio_pago_contado: 'efectivo' | 'transferencia' | 'cheque' | 'tarjeta' | 'otro'
  fecha_vencimiento?: string
  plazo_dias?: number
  ubicacion_fisica?: string
  monto_total: number
  monto_iva_5: number
  monto_iva_10: number
  monto_subtotal: number
  items: ItemFactura[]
  confianza?: number
  confianza_por_campo?: Record<string, number>
  motor_usado?: string
  warnings?: string[]
}

// Umbral de confianza: campos por debajo se resaltan en amarillo para revisión
const UMBRAL_HITL = 0.7

function claseConfianza(campo: string, conf?: Record<string, number>): string {
  const v = conf?.[campo]
  if (v === undefined) return ''
  if (v < 0.5) return 'ring-2 ring-red-400 bg-red-50'
  if (v < UMBRAL_HITL) return 'ring-2 ring-amber-400 bg-amber-50'
  return ''
}

const ITEM_VACIO: ItemFactura = {
  codigo: '', descripcion: '', cantidad: 1, precio_unitario: 0, porcentaje_iva: 10,
}

const DATO_VACIO: DatoFactura = {
  numero_comprobante: '', fecha_emision: '', ruc_emisor: '',
  razon_social_emisor: '', ruc_cliente: '', razon_social_cliente: '',
  condicion: 'contado',
  medio_pago_contado: 'efectivo',
  fecha_vencimiento: undefined,
  plazo_dias: undefined,
  monto_total: 0, monto_iva_5: 0, monto_iva_10: 0, monto_subtotal: 0,
  items: [],
}

async function leerRespuestaJson(res: Response) {
  const text = await res.text()
  try {
    return text ? JSON.parse(text) : {}
  } catch {
    if (text.toLowerCase().includes('request entity')) {
      return { detail: 'La foto es demasiado pesada para subirla. Proba sacarla un poco mas liviana o recortarla.' }
    }
    return { detail: text || `Error ${res.status}` }
  }
}

async function prepararImagenParaSubida(file: File): Promise<File> {
  if (!file.type.startsWith('image/') || file.size < 1_200_000) return file

  const bitmap = await createImageBitmap(file)
  const maxSide = 1600
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
  const width = Math.max(1, Math.round(bitmap.width * scale))
  const height = Math.max(1, Math.round(bitmap.height * scale))

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return file
  ctx.drawImage(bitmap, 0, 0, width, height)

  const blob = await new Promise<Blob | null>(resolve => {
    canvas.toBlob(resolve, 'image/jpeg', 0.82)
  })
  if (!blob || blob.size >= file.size) return file

  return new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), {
    type: 'image/jpeg',
    lastModified: Date.now(),
  })
}

export default function CargarFacturaPage() {
  const { puedeEscribir } = useAuth()
  const router = useRouter()
  const fileRef = useRef<HTMLInputElement>(null)
  const cameraRef = useRef<HTMLInputElement>(null)

  const [modo, setModo] = useState<ModoEntrada>('auto')
  const [tipoFactura, setTipoFactura] = useState<TipoFactura>('venta')
  const [archivos, setArchivos] = useState<File[]>([])
  const archivo = archivos[0] ?? null  // primario para preview
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [esPdf, setEsPdf] = useState(false)
  const [paginasImg, setPaginasImg] = useState<string[]>([])
  const [cargandoPreview, setCargandoPreview] = useState(false)
  const [progreso, setProgreso] = useState(0)
  const [procesando, setProcesando] = useState(false)
  const progresoRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [datos, setDatos] = useState<DatoFactura>(DATO_VACIO)
  const [datosListos, setDatosListos] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Guardado
  const [guardando, setGuardando] = useState(false)
  const [guardadoOk, setGuardadoOk] = useState<{ id: string; nombre: string; ruc: string } | null>(null)

  // Ajustes de clave Gemini
  const [mostrarAjustes, setMostrarAjustes] = useState(false)
  const [geminiInput, setGeminiInput] = useState('')
  const [mostrarKey, setMostrarKey] = useState(false)
  const [keyGuardada, setKeyGuardada] = useState(false)
  const [guardandoKey, setGuardandoKey] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('modo') === 'manual') {
      setModo('manual')
      setDatosListos(true)
      setDatos(DATO_VACIO)
    }

    api.get('/configuracion/gemini-key')
      .then(r => setKeyGuardada(r.data.configurado))
      .catch(() => {})
  }, [])

  const guardarGeminiKey = async () => {
    if (!geminiInput.trim()) return
    setGuardandoKey(true)
    try {
      await api.post('/configuracion/gemini-key', { api_key: geminiInput.trim() })
      setKeyGuardada(true)
      setGeminiInput('')
      setTimeout(() => setMostrarAjustes(false), 800)
    } catch {
      alert('No se pudo guardar la clave. Verificá que el backend esté corriendo.')
    } finally {
      setGuardandoKey(false)
    }
  }

  useEffect(() => {
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl) }
  }, [previewUrl])

  const seleccionar = useCallback(async (files: File[]) => {
    if (!files.length) return
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    const primero = files[0]
    setArchivos(files)
    setPreviewUrl(URL.createObjectURL(primero))
    setEsPdf(primero.type === 'application/pdf')
    setDatosListos(false)
    setDatos(DATO_VACIO)
    setErrorMsg(null)
    setProgreso(0)
    setPaginasImg([])
    setGuardadoOk(null)

    if (primero.type === 'application/pdf') {
      setCargandoPreview(true)
      try {
        const form = new FormData()
        form.append('archivo', primero)
        const { data } = await api.post('/ocr/preview', form)
        setPaginasImg((data.imagenes || []).map((p: { data: string }) => p.data))
      } catch { /* iframe fallback */ }
      finally { setCargandoPreview(false) }
    }
  }, [previewUrl])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files)
    if (files.length) seleccionar(files)
  }, [seleccionar])

  const iniciarProgreso = () => {
    setProgreso(5); setProcesando(true)
    let p = 5
    progresoRef.current = setInterval(() => {
      p = Math.min(p + (p < 50 ? 3 : p < 80 ? 1 : 0.3), 90)
      setProgreso(Math.round(p))
    }, 600)
  }

  const finalizarProgreso = () => {
    if (progresoRef.current) clearInterval(progresoRef.current)
    setProgreso(100)
    setTimeout(() => { setProcesando(false); setProgreso(0) }, 800)
  }

  const procesarFactura = async () => {
    if (!archivos.length) return
    if (!keyGuardada) { setMostrarAjustes(true); return }

    setErrorMsg(null)
    iniciarProgreso()
    try {
      const token = useAuth.getState().token || ''
      const form = new FormData()
      // Multi-archivo: una MISMA factura en varias imágenes/páginas
      const archivosSubida = await Promise.all(archivos.map(prepararImagenParaSubida))
      archivosSubida.forEach(f => form.append('archivos', f))

      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 120_000)
      const res = await fetch(`${API_BASE_URL}/ocr/extraer`, {
        method: 'POST',
        signal: controller.signal,
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      }).finally(() => clearTimeout(timeout))
      const data = await leerRespuestaJson(res)
      if (!res.ok) throw new Error(data?.detail || `Error ${res.status}`)

      if (data.motor_usado === 'sin_configurar') {
        setMostrarAjustes(true)
        setErrorMsg('Configurá la clave en Ajustes para procesar automáticamente.')
        return
      }

      const items: ItemFactura[] = Array.isArray(data.items)
        ? data.items.map((it: Partial<ItemFactura>) => ({
            codigo: it.codigo || '',
            descripcion: it.descripcion || '',
            cantidad: Number(it.cantidad) || 1,
            precio_unitario: Number(it.precio_unitario) || 0,
            porcentaje_iva: ([0, 5, 10] as const).includes((it.porcentaje_iva ?? 10) as 0|5|10)
              ? (it.porcentaje_iva as 0|5|10) : 10,
          }))
        : []

      setDatos({
        numero_comprobante: data.numero_comprobante || '',
        fecha_emision: data.fecha_emision || '',
        ruc_emisor: data.ruc_emisor || '',
        razon_social_emisor: data.razon_social_emisor || '',
        ruc_cliente: data.ruc_cliente || '',
        razon_social_cliente: data.razon_social_cliente || '',
        condicion: data.condicion === 'credito' ? 'credito' : 'contado',
        medio_pago_contado: (['efectivo','transferencia','cheque','tarjeta','otro'] as const).includes(data.medio_pago_contado)
          ? data.medio_pago_contado : 'efectivo',
        monto_total: Number(data.monto_total) || 0,
        monto_iva_5: Number(data.monto_iva_5) || 0,
        monto_iva_10: Number(data.monto_iva_10) || 0,
        monto_subtotal: Number(data.monto_subtotal) || 0,
        items,
        confianza: data.confianza,
        confianza_por_campo: data.confianza_por_campo && typeof data.confianza_por_campo === 'object'
          ? data.confianza_por_campo as Record<string, number>
          : {},
        motor_usado: data.motor_usado,
        warnings: Array.isArray(data.warnings) ? data.warnings as string[] : [],
      })
      setDatosListos(true)
    } catch (err: unknown) {
      const e = err as { message?: string }
      setErrorMsg(e?.message || 'Error al procesar el archivo')
    } finally {
      finalizarProgreso()
    }
  }

  const guardar = async () => {
    if (!datos.numero_comprobante.trim()) { setErrorMsg('Falta el número de comprobante'); return }
    if (!datos.fecha_emision) { setErrorMsg('Falta la fecha de emisión'); return }

    const contraparte = tipoFactura === 'venta'
      ? { ruc: datos.ruc_cliente, nombre: datos.razon_social_cliente, rol: 'cliente' }
      : { ruc: datos.ruc_emisor, nombre: datos.razon_social_emisor, rol: 'proveedor' }

    if (!contraparte.ruc.trim() && !contraparte.nombre.trim()) {
      setErrorMsg(`Falta identificar al ${contraparte.rol} (RUC o razón social)`)
      return
    }

    setErrorMsg(null)
    setGuardando(true)
    try {
      const token = useAuth.getState().token || ''
      const res = await fetch('/api/ocr/confirmar', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          tipo: tipoFactura,
          numero_comprobante: datos.numero_comprobante,
          fecha_emision: datos.fecha_emision,
          ruc_emisor: datos.ruc_emisor || null,
          razon_social_emisor: datos.razon_social_emisor || null,
          ruc_cliente: datos.ruc_cliente || null,
          razon_social_cliente: datos.razon_social_cliente || null,
          condicion: datos.condicion,
          medio_pago_contado: datos.condicion === 'contado' ? datos.medio_pago_contado : null,
          fecha_vencimiento: datos.condicion === 'credito' ? (datos.fecha_vencimiento || null) : null,
          plazo_dias: datos.condicion === 'credito' && !datos.fecha_vencimiento ? (datos.plazo_dias || null) : null,
          ubicacion_fisica: datos.ubicacion_fisica?.trim() || null,
          monto_subtotal: datos.monto_subtotal,
          monto_iva_5: datos.monto_iva_5,
          monto_iva_10: datos.monto_iva_10,
          monto_total: datos.monto_total,
          items: datos.items,
          confianza: datos.confianza,
          motor_usado: datos.motor_usado,
        }),
      })
      const data = await leerRespuestaJson(res)
      if (!res.ok) {
        // Mensajes amigables según código HTTP
        if (res.status === 409) {
          // Duplicado — mostrar con botón de ver el existente
          throw new Error(
            typeof data?.detail === 'string'
              ? `⚠️ ${data.detail}`
              : `Ya existe un comprobante con ese número para el mismo emisor/tipo.`
          )
        }
        if (res.status === 422) {
          throw new Error(
            typeof data?.detail === 'string'
              ? data.detail
              : 'Hay datos incompletos o inválidos. Revisá los campos obligatorios.'
          )
        }
        throw new Error(typeof data?.detail === 'string' ? data.detail : `Error ${res.status}`)
      }
      setGuardadoOk({
        id: data.comprobante_id,
        nombre: data.contraparte?.nombre || '',
        ruc: data.contraparte?.ruc || '',
      })
    } catch (err: unknown) {
      const e = err as { message?: string }
      setErrorMsg(e?.message || 'No se pudo guardar el comprobante')
    } finally {
      setGuardando(false)
    }
  }

  const setField = (campo: keyof DatoFactura) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const nums = ['monto_total', 'monto_iva_5', 'monto_iva_10', 'monto_subtotal']
      const val = nums.includes(campo) ? parseFloat(e.target.value) || 0 : e.target.value
      setDatos(prev => ({ ...prev, [campo]: val }))
    }

  const setItem = (i: number, campo: keyof ItemFactura, val: string | number) => {
    setDatos(prev => ({
      ...prev,
      items: prev.items.map((it, idx) => idx === i ? { ...it, [campo]: val } : it),
    }))
  }

  const addItem = () => setDatos(prev => ({ ...prev, items: [...prev.items, { ...ITEM_VACIO }] }))
  const removeItem = (i: number) => setDatos(prev => ({ ...prev, items: prev.items.filter((_, idx) => idx !== i) }))

  // Estado: recordamos qué campo de cada item fue autocompletado para mostrar el check verde
  const [lookupMatch, setLookupMatch] = useState<Record<number, 'codigo' | 'descripcion' | undefined>>({})

  // Estado: resumen de la última importación Excel
  const [resumenExcel, setResumenExcel] = useState<{
    creadas: number
    duplicadas: number
    errores: number
    erroresDetalle?: { fila: number; numero: string; error: string }[]
  } | null>(null)
  const [importandoExcel, setImportandoExcel] = useState(false)
  const [descargandoPlantilla, setDescargandoPlantilla] = useState(false)

  const importarExcel = async (file: File) => {
    setErrorMsg(null)
    setResumenExcel(null)
    setImportandoExcel(true)
    try {
      const token = useAuth.getState().token || ''
      const form = new FormData()
      form.append('archivo', file)
      const res = await fetch(`/api/ocr/importar-excel?tipo_default=${tipoFactura}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      const data = await leerRespuestaJson(res)
      if (!res.ok) throw new Error(data?.detail || `Error ${res.status}`)
      const r = data.resumen || {}
      setResumenExcel({
        creadas: r.creadas ?? 0,
        duplicadas: r.duplicadas ?? 0,
        errores: r.errores ?? 0,
        erroresDetalle: data.errores || [],
      })
    } catch (err: unknown) {
      const e = err as { message?: string }
      setErrorMsg(e?.message || 'Error importando Excel')
    } finally {
      setImportandoExcel(false)
    }
  }

  const descargarPlantillaExcel = async () => {
    setErrorMsg(null)
    setDescargandoPlantilla(true)
    try {
      const res = await api.get('/api/ocr/plantilla-excel', { responseType: 'blob', baseURL: '' })
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'modelo_carga_facturas.xlsx'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setErrorMsg(e?.response?.data?.detail || e?.message || 'No se pudo descargar el modelo de Excel')
    } finally {
      setDescargandoPlantilla(false)
    }
  }

  /**
   * Cruce vivo contra inventario:
   * - Si el usuario blurea el campo Código con un valor y la Descripción está vacía,
   *   buscamos el artículo por código y autocompletamos la descripción.
   * - Idem al revés: si blureó la Descripción y no hay código, lo buscamos por descripción.
   * Marca la fila con un check verde cuando hubo match.
   */
  const lookupArticulo = async (i: number, campoFocused: 'codigo' | 'descripcion') => {
    const it = datos.items[i]
    if (!it) return
    const hayCodigo = !!it.codigo.trim()
    const hayDesc = !!it.descripcion.trim()
    if (!hayCodigo && !hayDesc) return
    // Sólo autocompletamos si falta el OTRO campo
    if (campoFocused === 'codigo' && hayDesc) return
    if (campoFocused === 'descripcion' && hayCodigo) return

    try {
      const params = new URLSearchParams()
      if (hayCodigo) params.set('codigo', it.codigo.trim())
      if (hayDesc) params.set('descripcion', it.descripcion.trim())
      const { data } = await api.get(`/ocr/articulo-lookup?${params.toString()}`)
      if (data?.encontrado) {
        setDatos(prev => ({
          ...prev,
          items: prev.items.map((x, idx) =>
            idx === i ? { ...x, codigo: data.codigo || x.codigo, descripcion: data.descripcion || x.descripcion } : x
          ),
        }))
        setLookupMatch(prev => ({ ...prev, [i]: campoFocused }))
        setTimeout(() => setLookupMatch(prev => ({ ...prev, [i]: undefined })), 2500)
      }
    } catch { /* silencioso — el catálogo es opcional */ }
  }

  const recalcularDesdeItems = () => {
    let iva5 = 0, iva10 = 0, exentas = 0
    for (const it of datos.items) {
      const sub = it.cantidad * it.precio_unitario
      if (it.porcentaje_iva === 10) iva10 += sub * 10 / 110
      else if (it.porcentaje_iva === 5) iva5 += sub * 5 / 105
      else exentas += sub
    }
    const total = datos.items.reduce((a, it) => a + it.cantidad * it.precio_unitario, 0)
    setDatos(prev => ({
      ...prev,
      monto_iva_5: Math.round(iva5),
      monto_iva_10: Math.round(iva10),
      monto_subtotal: Math.round(total - iva5 - iva10),
      monto_total: Math.round(total),
    }))
  }

  const limpiar = () => {
    setDatosListos(false); setDatos(DATO_VACIO)
    setArchivos([]); setGuardadoOk(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null); setErrorMsg(null); setPaginasImg([])
  }

  if (!puedeEscribir()) {
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <div className="card text-center py-12">
          <XCircle size={48} className="mx-auto mb-4 text-red-400" />
          <p className="text-muted">Sin acceso a este módulo.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 space-y-5 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="page-header">
          <h1>Cargar Factura</h1>
          <p className="text-sm text-slate-500 mt-1">
            Subí el archivo, revisá los datos y confirmá. Se registra automáticamente en tu sistema.
          </p>
        </div>
        <button
          onClick={() => setMostrarAjustes(v => !v)}
          className={`flex w-full items-center justify-center gap-2 px-3 py-2 rounded-lg border text-sm transition-all sm:w-auto ${
            mostrarAjustes ? 'bg-slate-800 text-white border-slate-800'
            : keyGuardada ? 'border-emerald-300 text-emerald-700 hover:bg-emerald-50'
            : 'border-amber-300 text-amber-700 hover:bg-amber-50'
          }`}
        >
          <Settings size={15} />
          {keyGuardada ? 'Ajustes' : 'Configurar clave'}
          {!keyGuardada && <span className="w-2 h-2 rounded-full bg-amber-400" />}
        </button>
      </div>

      {/* Panel ajustes */}
      {mostrarAjustes && (
        <div className="card p-5 bg-slate-50 space-y-4">
          <div>
            <p className="text-sm font-semibold text-slate-700 mb-1">Clave de procesamiento automático</p>
            <p className="text-xs text-slate-500">
              Se guarda en el servidor. Solo necesitás ingresarla una vez.
              {keyGuardada && ' Ya hay una clave configurada.'}
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <input
                type={mostrarKey ? 'text' : 'password'}
                value={geminiInput}
                onChange={e => setGeminiInput(e.target.value)}
                placeholder={keyGuardada ? 'Ingresá una nueva clave para reemplazar' : 'AIza...'}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm pr-10 font-mono focus:ring-2 focus:ring-blue-500 outline-none bg-white"
                onKeyDown={e => e.key === 'Enter' && guardarGeminiKey()}
              />
              <button onClick={() => setMostrarKey(v => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                {mostrarKey ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
            <button onClick={guardarGeminiKey} disabled={guardandoKey || !geminiInput.trim()}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-blue-700 hover:bg-blue-800 text-white disabled:opacity-50 disabled:cursor-not-allowed">
              {guardandoKey ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              Guardar
            </button>
          </div>
          {keyGuardada && (
            <p className="text-xs text-emerald-600 flex items-center gap-1">
              <CheckCircle2 size={12} /> Clave activa en el servidor
            </p>
          )}
        </div>
      )}

      {/* Éxito */}
      {guardadoOk && (
        <div className="card bg-emerald-50 border border-emerald-200 p-5 space-y-3">
          <div className="flex items-start gap-3">
            <CheckCircle2 size={24} className="text-emerald-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-emerald-900">¡Factura registrada!</h3>
              <p className="text-sm text-emerald-700 mt-1">
                Comprobante N° <span className="font-mono font-medium">{datos.numero_comprobante}</span>{' '}
                guardado y <span className="font-medium">confirmado</span>. Ya aparece en el listado de facturas.
              </p>
              {guardadoOk.nombre && (
                <p className="text-xs text-emerald-600 mt-1">
                  {tipoFactura === 'venta' ? 'Cliente' : 'Proveedor'}: <span className="font-medium">{guardadoOk.nombre}</span>
                  {guardadoOk.ruc && <span className="ml-1 font-mono">({guardadoOk.ruc})</span>}
                </p>
              )}
            </div>
          </div>

          {/* Adjuntar imagen de la factura al comprobante recién creado */}
          <AdjuntarImagenFactura comprobanteId={guardadoOk.id} />

          <div className="flex gap-2">
            <button onClick={limpiar} className="btn-ghost gap-1">
              <RefreshCw size={14} /> Cargar otra factura
            </button>
            <button onClick={() => router.push('/comprobantes')} className="btn-primary gap-2">
              Ver comprobantes <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Tipo de documento */}
      {!guardadoOk && (
        <div className="card p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">¿Esta factura la emitiste o la recibiste?</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <button onClick={() => setTipoFactura('venta')}
              className={`px-4 py-3 rounded-lg border text-sm font-medium transition-all text-left ${
                tipoFactura === 'venta'
                  ? 'bg-blue-700 text-white border-blue-700 shadow-sm'
                  : 'border-slate-300 text-slate-600 hover:border-blue-400 hover:bg-blue-50'
              }`}>
              <span className="block font-semibold">📤 Factura de Venta</span>
              <span className={`text-xs font-normal ${tipoFactura === 'venta' ? 'text-blue-200' : 'text-slate-400'}`}>
                Vos emitís → se registra el CLIENTE
              </span>
            </button>
            <button onClick={() => setTipoFactura('compra')}
              className={`px-4 py-3 rounded-lg border text-sm font-medium transition-all text-left ${
                tipoFactura === 'compra'
                  ? 'bg-blue-700 text-white border-blue-700 shadow-sm'
                  : 'border-slate-300 text-slate-600 hover:border-blue-400 hover:bg-blue-50'
              }`}>
              <span className="block font-semibold">📥 Factura de Compra</span>
              <span className={`text-xs font-normal ${tipoFactura === 'compra' ? 'text-blue-200' : 'text-slate-400'}`}>
                La recibís de un proveedor → se registra el PROVEEDOR
              </span>
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      {!guardadoOk && (
        <div className="flex gap-1 bg-slate-100 rounded-xl p-1 w-fit">
          {([
            { key: 'auto' as ModoEntrada, label: 'Automático', icon: <ScanLine size={15} /> },
            { key: 'manual' as ModoEntrada, label: 'Manual', icon: <Edit3 size={15} /> },
          ]).map(t => (
            <button key={t.key} onClick={() => {
              setModo(t.key)
              if (t.key === 'manual') { setDatosListos(true); setDatos(DATO_VACIO) }
            }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                modo === t.key ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'
              }`}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      )}

      {/* ══ MODO AUTOMÁTICO — upload ══ */}
      {!guardadoOk && modo === 'auto' && (
        <div className="space-y-4">
          {!keyGuardada && !mostrarAjustes && (
            <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl">
              <AlertTriangle size={18} className="text-amber-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-semibold text-amber-800">Clave no configurada</p>
                <p className="text-xs text-amber-700 mt-0.5">
                  Para procesar facturas automáticamente necesitás configurar la clave.{' '}
                  <button onClick={() => setMostrarAjustes(true)} className="underline font-medium">
                    Configurar ahora
                  </button>
                </p>
              </div>
            </div>
          )}

          {!datosListos && (
            <div
              className={`border-2 border-dashed rounded-xl transition-all ${
                archivo ? 'border-blue-300 bg-blue-50' : 'border-slate-300 hover:border-blue-400 bg-slate-50 cursor-pointer'
              }`}
              onClick={() => !archivo && fileRef.current?.click()}
              onDrop={handleDrop} onDragOver={e => e.preventDefault()}
            >
              <input ref={fileRef} type="file" multiple className="hidden"
                accept="image/jpeg,image/png,image/webp,application/pdf"
                onChange={e => {
                  const files = Array.from(e.target.files || [])
                  if (files.length) seleccionar(files)
                }} />
              <input ref={cameraRef} type="file" className="hidden"
                accept="image/*"
                capture="environment"
                onChange={e => {
                  const files = Array.from(e.target.files || [])
                  if (files.length) seleccionar(files)
                }} />

              {previewUrl ? (
                <div className="relative">
                  <button onClick={e => { e.stopPropagation(); limpiar() }}
                    className="absolute top-2 right-2 z-10 bg-white rounded-full p-1 shadow hover:bg-red-50">
                    <X size={14} className="text-slate-500" />
                  </button>

                  {cargandoPreview ? (
                    <div className="flex items-center justify-center h-40 gap-2 text-slate-400">
                      <Loader2 size={18} className="animate-spin" />
                      <span className="text-sm">Generando vista previa...</span>
                    </div>
                  ) : paginasImg.length > 0 ? (
                    <div className="space-y-2 p-2 max-h-96 overflow-y-auto rounded-t-xl bg-slate-100">
                      {paginasImg.map((src, i) => (
                        <div key={i}>
                          {paginasImg.length > 1 && (
                            <p className="text-xs text-slate-500 text-center mb-1">Página {i + 1}</p>
                          )}
                          <img src={src} alt={`Página ${i + 1}`}
                            className="w-full rounded shadow-sm border border-slate-200"
                            onClick={e => e.stopPropagation()} />
                        </div>
                      ))}
                    </div>
                  ) : esPdf ? (
                    <iframe src={previewUrl} className="w-full h-80 rounded-t-xl" title="Vista previa PDF" />
                  ) : (
                    <img src={previewUrl} alt="Vista previa"
                      className="w-full max-h-80 object-contain rounded-t-xl p-3" />
                  )}

                  <div className="px-4 py-2.5 bg-white rounded-b-xl border-t border-slate-200 flex items-center gap-2">
                    {esPdf ? <FileText size={14} className="text-blue-600" /> : <FileImage size={14} className="text-blue-600" />}
                    <span className="text-xs text-slate-600 font-medium truncate">
                      {archivo?.name}
                      {archivos.length > 1 && (
                        <span className="ml-2 text-blue-600 font-semibold">
                          +{archivos.length - 1} {archivos.length === 2 ? 'archivo' : 'archivos'} más
                        </span>
                      )}
                    </span>
                    <span className="text-xs text-slate-400 shrink-0">
                      ({((archivo?.size || 0) / 1024 / 1024).toFixed(1)} MB)
                    </span>
                    {paginasImg.length > 1 && (
                      <span className="text-xs text-slate-400 shrink-0">{paginasImg.length} páginas</span>
                    )}
                    <button onClick={e => { e.stopPropagation(); fileRef.current?.click() }}
                      className="ml-auto text-xs text-blue-600 hover:underline shrink-0">
                      Cambiar
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-14 flex flex-col items-center gap-3 text-slate-400">
                  <Upload size={40} />
                  <button
                    type="button"
                    onClick={e => { e.stopPropagation(); cameraRef.current?.click() }}
                    className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  >
                    <Camera size={16} /> Sacar foto
                  </button>
                  <p className="text-sm font-medium text-slate-500">Arrastrá o hacé clic para subir</p>
                  <p className="text-xs">PDF, JPEG, PNG, WebP — máx. 20 MB</p>
                </div>
              )}
            </div>
          )}

          {procesando && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span className="flex items-center gap-1.5">
                  <Loader2 size={12} className="animate-spin" />
                  {progreso < 40 ? 'Analizando documento...' : progreso < 80 ? 'Extrayendo datos...' : 'Finalizando...'}
                </span>
                <span className="font-medium">{progreso}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-1.5">
                <div className="bg-blue-600 h-1.5 rounded-full transition-all duration-500" style={{ width: `${progreso}%` }} />
              </div>
            </div>
          )}

          {errorMsg && !procesando && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <div className="flex-1">
                <p className="font-semibold text-sm">Hubo un problema</p>
                <p className="text-xs mt-0.5 opacity-80">{errorMsg}</p>
                <button onClick={() => setErrorMsg(null)} className="text-xs underline mt-1 opacity-70 hover:opacity-100">
                  Cerrar
                </button>
              </div>
            </div>
          )}

          {archivo && !datosListos && !procesando && !errorMsg && (
            <div className="flex justify-center gap-3">
              <button onClick={procesarFactura} className="btn-primary gap-2">
                <ScanLine size={16} /> Analizar factura
              </button>
            </div>
          )}

          {/* Importación masiva desde Excel (carga inicial de facturas históricas) */}
          {!archivo && !datosListos && (
            <div className="mt-4 pt-4 border-t border-slate-200">
              <div className="flex items-start gap-3 p-3 rounded-lg bg-emerald-50 border border-emerald-200">
                <FileSpreadsheet size={20} className="text-emerald-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-emerald-900">
                    ¿Tenés tus facturas en Excel?
                  </p>
                  <p className="text-xs text-emerald-700 mt-0.5 mb-2">
                    Cargá un archivo <code className="px-1 bg-emerald-100 rounded">.xlsx</code> con una factura por fila.
                    Detectamos columnas por nombre (número, fecha, RUC cliente, total…).
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={descargarPlantillaExcel}
                      disabled={descargandoPlantilla}
                      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium transition-colors ${
                        descargandoPlantilla
                          ? 'border-slate-200 bg-white text-slate-400 cursor-wait'
                          : 'border-emerald-200 bg-white text-emerald-700 hover:bg-emerald-100'
                      }`}
                    >
                      {descargandoPlantilla
                        ? <><Loader2 size={14} className="animate-spin" /> Descargando...</>
                        : <><Download size={14} /> Descargar modelo</>
                      }
                    </button>
                    <label className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-white text-xs font-medium transition-colors ${
                    importandoExcel ? 'bg-slate-400 cursor-wait' : 'bg-emerald-600 hover:bg-emerald-700 cursor-pointer'
                  }`}>
                    {importandoExcel
                      ? <><Loader2 size={14} className="animate-spin" /> Procesando...</>
                      : <><FileSpreadsheet size={14} /> Subir Excel</>
                    }
                    <input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                      disabled={importandoExcel}
                      className="hidden"
                      onChange={e => {
                        const f = e.target.files?.[0]
                        if (f) importarExcel(f)
                        e.target.value = ''
                      }} />
                    </label>
                  </div>
                </div>
              </div>
              {resumenExcel && (
                <div className="mt-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <p className="text-sm font-semibold text-slate-800 mb-2">Resultado de la importación</p>
                  <div className="flex gap-4 text-xs">
                    <span className="flex items-center gap-1 text-emerald-700">
                      <CheckCircle2 size={13} /> {resumenExcel.creadas} creadas
                    </span>
                    <span className="flex items-center gap-1 text-amber-700">
                      <AlertTriangle size={13} /> {resumenExcel.duplicadas} duplicadas (omitidas)
                    </span>
                    <span className="flex items-center gap-1 text-red-700">
                      <XCircle size={13} /> {resumenExcel.errores} con error
                    </span>
                  </div>
                  {resumenExcel.erroresDetalle && resumenExcel.erroresDetalle.length > 0 && (
                    <details className="mt-2 text-xs">
                      <summary className="cursor-pointer text-slate-600 hover:text-slate-800">Ver detalle de errores</summary>
                      <ul className="mt-1 space-y-0.5 text-red-700 font-mono">
                        {resumenExcel.erroresDetalle.slice(0, 10).map((e, i) => (
                          <li key={i}>Fila {e.fila} ({e.numero}): {e.error}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ══ FORMULARIO DE REVISIÓN ══ */}
      {!guardadoOk && (datosListos || modo === 'manual') && (
        <div className="card space-y-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-base font-semibold text-slate-800">
              {modo === 'auto' ? 'Revisá los datos extraídos' : 'Ingresá los datos del comprobante'}
            </h2>
            {datosListos && modo === 'auto' && (
              <div className="flex flex-wrap items-center gap-2">
                {(datos.confianza ?? 0) > 0 && (
                  <span className={`text-xs font-medium ${
                    (datos.confianza ?? 0) >= 0.75 ? 'text-emerald-600'
                    : (datos.confianza ?? 0) >= 0.5 ? 'text-amber-600' : 'text-red-600'
                  }`}>
                    {Math.round((datos.confianza ?? 0) * 100)}% confianza
                  </span>
                )}
                <button onClick={limpiar} className="btn-ghost text-xs gap-1">
                  <RefreshCw size={12} /> Nuevo archivo
                </button>
              </div>
            )}
          </div>

          {/* Aviso HITL: campos con baja confianza */}
          {datosListos && modo === 'auto' && datos.confianza_por_campo && (() => {
            const bajos = Object.entries(datos.confianza_por_campo).filter(([, v]) => v < UMBRAL_HITL)
            if (bajos.length === 0) return null
            return (
              <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900">
                <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" />
                <div className="text-xs leading-relaxed">
                  <p className="font-semibold mb-0.5">
                    {bajos.length} {bajos.length === 1 ? 'campo necesita' : 'campos necesitan'} revisión manual
                  </p>
                  <p className="text-amber-800">
                    Los campos resaltados en amarillo o rojo tuvieron baja confianza al leerlos.
                    Verificá los valores contra la factura original antes de guardar.
                  </p>
                </div>
              </div>
            )
          })()}

          {/* Avisos aritméticos del backend (montos que no cuadran, IVA calculado) */}
          {datosListos && (datos.warnings?.length ?? 0) > 0 && (
            <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-900">
              <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" />
              <div className="text-xs leading-relaxed space-y-1">
                <p className="font-semibold">Avisos de verificación aritmética</p>
                <ul className="list-disc pl-4 space-y-0.5">
                  {(datos.warnings ?? []).map((w, i) => <li key={i}>{w}</li>)}
                </ul>
                <p className="text-blue-800 italic">
                  Los montos calculados son estimativos (regla IVA incluido Paraguay).
                  Ajustalos a mano si la factura muestra otros valores.
                </p>
              </div>
            </div>
          )}

          {/* Datos generales */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">N° Comprobante</label>
              <input type="text" value={datos.numero_comprobante} onChange={setField('numero_comprobante')}
                placeholder="001-001-0000001"
                title={datos.confianza_por_campo?.numero_comprobante !== undefined
                  ? `Confianza: ${Math.round((datos.confianza_por_campo.numero_comprobante) * 100)}%`
                  : undefined}
                className={`w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none ${claseConfianza('numero_comprobante', datos.confianza_por_campo)}`} />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Fecha de Emisión</label>
              <input type="date" value={datos.fecha_emision} onChange={setField('fecha_emision')}
                title={datos.confianza_por_campo?.fecha_emision !== undefined
                  ? `Confianza: ${Math.round((datos.confianza_por_campo.fecha_emision) * 100)}%`
                  : undefined}
                className={`w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none ${claseConfianza('fecha_emision', datos.confianza_por_campo)}`} />
            </div>
          </div>

          {/* Emisor */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Emisor <span className="normal-case font-normal text-slate-400">(quien emite la factura)</span>
              {tipoFactura === 'compra' && <span className="ml-2 text-blue-600 normal-case font-medium">← se registra como PROVEEDOR</span>}
            </p>
            <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 p-3 rounded-lg border ${
              tipoFactura === 'compra' ? 'bg-blue-50 border-blue-200' : 'bg-slate-50 border-slate-200'
            }`}>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">RUC Emisor</label>
                <input type="text" value={datos.ruc_emisor} onChange={setField('ruc_emisor')}
                  placeholder="80012345-6"
                  title={datos.confianza_por_campo?.ruc_emisor !== undefined
                    ? `Confianza: ${Math.round((datos.confianza_por_campo.ruc_emisor) * 100)}%`
                    : undefined}
                  className={`w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none bg-white ${claseConfianza('ruc_emisor', datos.confianza_por_campo)}`} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Razón Social Emisor</label>
                <input type="text" value={datos.razon_social_emisor} onChange={setField('razon_social_emisor')}
                  placeholder="MP Cosmetics E.A.S."
                  title={datos.confianza_por_campo?.razon_social_emisor !== undefined
                    ? `Confianza: ${Math.round((datos.confianza_por_campo.razon_social_emisor) * 100)}%`
                    : undefined}
                  className={`w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white ${claseConfianza('razon_social_emisor', datos.confianza_por_campo)}`} />
              </div>
            </div>
          </div>

          {/* Cliente */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Cliente <span className="normal-case font-normal text-slate-400">(quien recibe la factura)</span>
              {tipoFactura === 'venta' && <span className="ml-2 text-emerald-700 normal-case font-medium">← se registra como CLIENTE</span>}
            </p>
            <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 p-3 rounded-lg border ${
              tipoFactura === 'venta' ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'
            }`}>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">RUC Cliente</label>
                <input type="text" value={datos.ruc_cliente} onChange={setField('ruc_cliente')}
                  placeholder="600-22877-4"
                  title={datos.confianza_por_campo?.ruc_cliente !== undefined
                    ? `Confianza: ${Math.round((datos.confianza_por_campo.ruc_cliente) * 100)}%`
                    : undefined}
                  className={`w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none bg-white ${claseConfianza('ruc_cliente', datos.confianza_por_campo)}`} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Razón Social Cliente</label>
                <input type="text" value={datos.razon_social_cliente} onChange={setField('razon_social_cliente')}
                  placeholder="FARMA S.A."
                  title={datos.confianza_por_campo?.razon_social_cliente !== undefined
                    ? `Confianza: ${Math.round((datos.confianza_por_campo.razon_social_cliente) * 100)}%`
                    : undefined}
                  className={`w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white ${claseConfianza('razon_social_cliente', datos.confianza_por_campo)}`} />
              </div>
            </div>
          </div>

          {/* Condición */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Condición de pago</p>
            <div className="flex flex-wrap items-center gap-4">
              {(['contado', 'credito'] as const).map(c => (
                <label key={c} className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="condicion" checked={datos.condicion === c}
                    onChange={() => setDatos(p => ({ ...p, condicion: c }))} className="accent-blue-600" />
                  <span className="text-sm font-medium capitalize text-slate-700">{c}</span>
                </label>
              ))}

              {/* Si es contado → elegir medio de pago directamente */}
              {datos.condicion === 'contado' && (
                <div className="flex items-center gap-2 ml-2 pl-4 border-l border-slate-300">
                  <span className="text-xs text-slate-500">Medio:</span>
                  <select
                    value={datos.medio_pago_contado}
                    onChange={e => setDatos(p => ({ ...p, medio_pago_contado: e.target.value as any }))}
                    className="border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="efectivo">Efectivo</option>
                    <option value="transferencia">Transferencia</option>
                    <option value="cheque">Cheque</option>
                    <option value="tarjeta">Tarjeta</option>
                    <option value="otro">Otro</option>
                  </select>
                </div>
              )}
            </div>

            {/* Si es credito → plazo o fecha de vencimiento */}
            {datos.condicion === 'credito' && (
              <div className="mt-3 grid sm:grid-cols-2 gap-3 p-3 bg-violet-50 border border-violet-200 rounded-lg">
                <div>
                  <label className="text-xs font-medium text-violet-800">Plazo estimado</label>
                  <select
                    value={datos.plazo_dias ?? ''}
                    onChange={e => {
                      const val = e.target.value ? Number(e.target.value) : undefined
                      setDatos(p => ({
                        ...p,
                        plazo_dias: val,
                        // Si eligen plazo, calcular fecha_vencimiento para mostrar
                        fecha_vencimiento: val && p.fecha_emision
                          ? new Date(new Date(p.fecha_emision).getTime() + val * 86400000).toISOString().slice(0, 10)
                          : p.fecha_vencimiento,
                      }))
                    }}
                    className="w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white mt-1"
                  >
                    <option value="">— elegir —</option>
                    <option value="7">7 días</option>
                    <option value="15">15 días</option>
                    <option value="30">30 días</option>
                    <option value="45">45 días</option>
                    <option value="60">60 días</option>
                    <option value="90">90 días</option>
                    <option value="120">120 días</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-violet-800">Fecha de vencimiento</label>
                  <input type="date" value={datos.fecha_vencimiento ?? ''}
                    onChange={e => setDatos(p => ({ ...p, fecha_vencimiento: e.target.value, plazo_dias: undefined }))}
                    className="w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white mt-1" />
                </div>
              </div>
            )}

            <p className="text-xs text-slate-400 mt-2">
              {datos.condicion === 'contado'
                ? '✓ Al contado: la factura se registra cobrada/pagada, sin recibo separado.'
                : 'A crédito: elegí plazo o fecha de vencimiento. Los recibos se registran después en Cuentas Corrientes.'}
            </p>

            {/* Ubicacion fisica (factura en papel) */}
            <div className="mt-3">
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Ubicación física <span className="text-slate-400 normal-case">(opcional — si la factura está en papel)</span>
              </label>
              <input
                type="text"
                value={datos.ubicacion_fisica ?? ''}
                onChange={e => setDatos(p => ({ ...p, ubicacion_fisica: e.target.value }))}
                placeholder="Ej: Bibliorato Rojo 2026 / Caja Ventas Abril / Estante 3"
                className="w-full mt-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white"
              />
            </div>
          </div>

          {/* Items */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Detalle de items {datos.items.length > 0 && <span className="text-slate-400 normal-case">({datos.items.length})</span>}
              </p>
              <div className="flex gap-2">
                {datos.items.length > 0 && (
                  <button onClick={recalcularDesdeItems}
                    className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                    <RefreshCw size={12} /> Recalcular totales
                  </button>
                )}
                <button onClick={addItem}
                  className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                  <Plus size={12} /> Agregar item
                </button>
              </div>
            </div>
            {datos.items.length === 0 ? (
              <p className="text-xs text-slate-400 p-3 bg-slate-50 rounded-lg border border-dashed border-slate-200 text-center">
                Sin items. Podés agregar manualmente o editar directamente los montos abajo.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="responsive-table w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase tracking-wide">
                    <tr>
                      <th className="px-2 py-2 text-left font-semibold w-36">Código</th>
                      <th className="px-2 py-2 text-left font-semibold">Descripción</th>
                      <th className="px-2 py-2 text-right font-semibold w-20">Cant.</th>
                      <th className="px-2 py-2 text-right font-semibold w-32">Precio U.</th>
                      <th className="px-2 py-2 text-center font-semibold w-20">IVA</th>
                      <th className="px-2 py-2 text-right font-semibold w-28">Subtotal</th>
                      <th className="w-8" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {datos.items.map((it, i) => (
                      <tr key={i} className={lookupMatch[i] ? 'bg-emerald-50/60' : ''}>
                        <td className="px-2 py-1.5">
                          <div className="relative">
                            <input type="text" value={it.codigo}
                              placeholder="—"
                              onChange={e => setItem(i, 'codigo', e.target.value)}
                              onBlur={() => lookupArticulo(i, 'codigo')}
                              className="w-full border border-slate-200 rounded px-2 py-1 pr-6 text-xs font-mono focus:ring-1 focus:ring-blue-400 outline-none" />
                            {lookupMatch[i] === 'codigo' && (
                              <CheckCircle2 size={12} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-emerald-500" />
                            )}
                          </div>
                        </td>
                        <td className="px-2 py-1.5">
                          <div className="relative">
                            <input type="text" value={it.descripcion}
                              onChange={e => setItem(i, 'descripcion', e.target.value)}
                              onBlur={() => lookupArticulo(i, 'descripcion')}
                              className="w-full border border-slate-200 rounded px-2 py-1 pr-6 text-xs focus:ring-1 focus:ring-blue-400 outline-none" />
                            {lookupMatch[i] === 'descripcion' && (
                              <CheckCircle2 size={12} className="absolute right-1.5 top-1/2 -translate-y-1/2 text-emerald-500" />
                            )}
                          </div>
                        </td>
                        <td className="px-2 py-1.5">
                          <input type="number" value={it.cantidad} min={0} step={1}
                            onChange={e => setItem(i, 'cantidad', parseFloat(e.target.value) || 0)}
                            className="w-full border border-slate-200 rounded px-2 py-1 text-xs text-right font-mono focus:ring-1 focus:ring-blue-400 outline-none" />
                        </td>
                        <td className="px-2 py-1.5">
                          <input type="number" value={it.precio_unitario} min={0} step={1000}
                            onChange={e => setItem(i, 'precio_unitario', parseFloat(e.target.value) || 0)}
                            className="w-full border border-slate-200 rounded px-2 py-1 text-xs text-right font-mono focus:ring-1 focus:ring-blue-400 outline-none" />
                        </td>
                        <td className="px-2 py-1.5">
                          <select value={it.porcentaje_iva}
                            onChange={e => setItem(i, 'porcentaje_iva', parseInt(e.target.value) as 0|5|10)}
                            className="w-full border border-slate-200 rounded px-1 py-1 text-xs focus:ring-1 focus:ring-blue-400 outline-none">
                            <option value={0}>0%</option>
                            <option value={5}>5%</option>
                            <option value={10}>10%</option>
                          </select>
                        </td>
                        <td className="px-2 py-1.5 text-right font-mono text-slate-700">
                          ₲ {fmt(it.cantidad * it.precio_unitario)}
                        </td>
                        <td className="px-2 py-1.5 text-center">
                          <button onClick={() => removeItem(i)}
                            className="text-red-400 hover:text-red-600 p-0.5">
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Montos */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Montos (₲)</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { campo: 'monto_subtotal' as const, label: 'Subtotal' },
                { campo: 'monto_iva_5' as const, label: 'IVA 5%' },
                { campo: 'monto_iva_10' as const, label: 'IVA 10%' },
                { campo: 'monto_total' as const, label: 'TOTAL' },
              ].map(({ campo, label }) => (
                <div key={campo}>
                  <label className="block text-xs text-slate-500 mb-1">{label}</label>
                  <div className="relative">
                    <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-400">₲</span>
                    <input type="number" value={datos[campo] || ''} onChange={setField(campo)}
                      min={0} step={1000} placeholder="0"
                      className={`w-full border rounded-lg pl-6 pr-2 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none ${
                        campo === 'monto_total' ? 'border-blue-400 bg-blue-50 font-bold' : 'border-slate-300'
                      }`} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {errorMsg && (
            <div className="flex items-start gap-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
              <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              <p className="text-xs">{errorMsg}</p>
            </div>
          )}

          <div className="flex flex-col gap-3 pt-3 border-t border-slate-200 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-slate-400">
              {tipoFactura === 'venta' ? '→ Se asociará al cliente identificado arriba' : '→ Se asociará al proveedor identificado arriba'}
            </p>
            <div className="flex flex-col-reverse gap-2 sm:flex-row">
              <button onClick={limpiar} className="btn-ghost justify-center gap-1" disabled={guardando}>
                <X size={14} /> Cancelar
              </button>
              <button onClick={guardar} className="btn-primary gap-2" disabled={guardando}>
                {guardando ? (
                  <><Loader2 size={16} className="animate-spin" /> Guardando...</>
                ) : (
                  <><CheckCircle2 size={16} /> Guardar comprobante</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Subcomponente: adjuntar imagen/PDF al comprobante recién guardado ──────
function AdjuntarImagenFactura({ comprobanteId }: { comprobanteId: string }) {
  const [subiendo, setSubiendo] = useState(false)
  const [ok, setOk] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [nombre, setNombre] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const manejar = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setSubiendo(true); setErr(null); setOk(false)
    try {
      await adjuntosApi.subirComprobante(comprobanteId, f)
      setNombre(f.name)
      setOk(true)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'No se pudo subir el archivo')
    } finally {
      setSubiendo(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="mt-3 p-3 border border-dashed border-slate-300 rounded-lg bg-slate-50">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <p className="text-xs font-semibold text-slate-700">Adjuntar imagen/PDF de la factura (opcional)</p>
          <p className="text-[10px] text-slate-500">Guardar la foto o escaneo para consultarla después. Máx 8 MB.</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,application/pdf"
            onChange={manejar}
            disabled={subiendo}
            className="hidden"
            id={`adj-${comprobanteId}`}
          />
          <label
            htmlFor={`adj-${comprobanteId}`}
            className={`btn-ghost gap-1 cursor-pointer ${subiendo ? 'opacity-60 pointer-events-none' : ''}`}
          >
            {subiendo ? <><Loader2 size={14} className="animate-spin" /> Subiendo...</>
                      : <><Upload size={14} /> Elegir archivo</>}
          </label>
        </div>
      </div>
      {ok && (
        <div className="mt-2 flex items-center justify-between gap-2 text-xs text-emerald-700">
          <span className="flex items-center gap-2">
            <CheckCircle2 size={14} /> Adjunto guardado {nombre ? `(${nombre})` : ''}
          </span>
          <button
            type="button"
            onClick={async () => {
              if (!confirm('¿Quitar el archivo adjunto?')) return
              try {
                await adjuntosApi.quitarComprobante(comprobanteId)
                setOk(false); setNombre(null)
              } catch (e: any) {
                setErr(e?.response?.data?.detail || 'No se pudo quitar el adjunto')
              }
            }}
            className="inline-flex items-center gap-1 px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
          >
            <X size={12} /> Quitar
          </button>
        </div>
      )}
      {err && (
        <div className="mt-2 flex items-center gap-2 text-xs text-red-600">
          <AlertTriangle size={14} /> {err}
        </div>
      )}
    </div>
  )
}
