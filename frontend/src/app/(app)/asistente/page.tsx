'use client'
import { useState, useRef, useEffect, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { chatApi } from '@/lib/api'
import {
  Bot, Send, User, Loader2, AlertCircle,
  ChevronDown, Database, RefreshCw, Sparkles, Search, History, X, Menu,
} from 'lucide-react'
import clsx from 'clsx'
import ActionPreviewCard, { isActionPreview, type ConfirmarAccionResponse } from '@/components/chat/ActionPreviewCard'

// ── Tipos ─────────────────────────────────────────────────────────────────────

type Accion = {
  funcion: string
  argumentos: Record<string, unknown>
  resultado: Record<string, unknown>
}

type Mensaje = {
  id: string
  rol: 'user' | 'assistant'
  contenido: string
  acciones?: Accion[]
  motor?: string
  timestamp: Date
}

// Nombres amigables para cada función del asistente
const NOMBRES_FUNCIONES: Record<string, string> = {
  consultar_saldo_cliente:         'Consulta de saldo — Cliente',
  consultar_saldo_proveedor:       'Consulta de saldo — Proveedor',
  consultar_stock:                 'Consulta de stock',
  listar_comprobantes_pendientes:  'Facturas pendientes',
  resumen_financiero:              'Resumen financiero',
  items_stock_critico:             'Stock crítico',
  buscar_comprobante:              'Búsqueda de comprobante',
}

// Acciones rápidas predefinidas para el usuario
const ACCIONES_RAPIDAS = [
  { label: 'Resumen del día',         mensaje: '¿Cómo está el negocio hoy? Dame un resumen financiero.' },
  { label: 'Stock crítico',           mensaje: '¿Qué productos tienen stock crítico?' },
  { label: 'Facturas por cobrar',     mensaje: 'Listame las facturas pendientes de cobro más importantes.' },
  { label: 'Facturas por pagar',      mensaje: '¿Qué deudas tengo con proveedores?' },
]

// ── Componentes ───────────────────────────────────────────────────────────────

function EstadoIA({ motor }: { motor?: string }) {
  if (!motor) return null
  return (
    <span className={clsx(
      'text-xs px-1.5 py-0.5 rounded-full font-medium',
      motor === 'gemini'
        ? 'bg-purple-100 text-purple-700'
        : 'bg-gray-100 text-gray-500'
    )}>
      {motor === 'gemini' ? '☁ Gemini' : motor}
    </span>
  )
}

function TarjetaAccion({
  accion,
  onConfirmada,
}: {
  accion: Accion
  onConfirmada?: (data: ConfirmarAccionResponse) => void
}) {
  const [abierta, setAbierta] = useState(false)
  const nombre = NOMBRES_FUNCIONES[accion.funcion] ?? accion.funcion

  if (isActionPreview(accion)) {
    return <ActionPreviewCard accion={accion} onConfirmada={onConfirmada} />
  }

  return (
    <div className="mt-2 border border-blue-100 rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setAbierta(!abierta)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-blue-50 hover:bg-blue-100 transition-colors text-left"
      >
        <Database size={12} className="text-blue-500 shrink-0" />
        <span className="text-blue-700 font-medium flex-1">{nombre}</span>
        <ChevronDown
          size={12}
          className={clsx('text-blue-400 transition-transform', abierta && 'rotate-180')}
        />
      </button>
      {abierta && (
        <div className="px-3 py-2 bg-white space-y-1.5">
          {Object.keys(accion.argumentos).length > 0 && (
            <div>
              <p className="text-gray-400 uppercase tracking-wide text-[10px] mb-1">Parámetros</p>
              <pre className="text-gray-600 text-[11px] whitespace-pre-wrap break-all">
                {JSON.stringify(accion.argumentos, null, 2)}
              </pre>
            </div>
          )}
          <div>
            <p className="text-gray-400 uppercase tracking-wide text-[10px] mb-1">Resultado</p>
            <pre className="text-gray-600 text-[11px] whitespace-pre-wrap break-all max-h-40 overflow-y-auto">
              {JSON.stringify(accion.resultado, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

function BurbujaMensaje({
  mensaje,
  onConfirmada,
}: {
  mensaje: Mensaje
  onConfirmada?: (data: ConfirmarAccionResponse) => void
}) {
  const esUsuario = mensaje.rol === 'user'

  return (
    <div className={clsx('flex gap-3 max-w-[85%]', esUsuario ? 'ml-auto flex-row-reverse' : '')}>
      {/* Avatar */}
      <div className={clsx(
        'w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5',
        esUsuario ? 'bg-primary' : 'bg-gradient-to-br from-indigo-500 to-purple-600'
      )}>
        {esUsuario
          ? <User size={16} className="text-white" />
          : <Bot size={16} className="text-white" />
        }
      </div>

      {/* Contenido */}
      <div className={clsx('flex flex-col gap-1', esUsuario ? 'items-end' : 'items-start')}>
        <div className={clsx(
          'px-4 py-3 rounded-2xl text-sm leading-relaxed',
          esUsuario
            ? 'bg-primary text-white rounded-tr-sm'
            : 'bg-white border border-gray-100 text-gray-800 rounded-tl-sm shadow-sm'
        )}>
          {/* Texto con saltos de línea preservados */}
          {mensaje.contenido.split('\n').map((linea, i) => (
            <span key={i}>
              {linea}
              {i < mensaje.contenido.split('\n').length - 1 && <br />}
            </span>
          ))}
        </div>

        {/* Acciones ejecutadas (solo en mensajes del asistente) */}
        {!esUsuario && mensaje.acciones && mensaje.acciones.length > 0 && (
          <div className="w-full space-y-1">
            {mensaje.acciones.map((accion, i) => (
              <TarjetaAccion key={i} accion={accion} onConfirmada={onConfirmada} />
            ))}
          </div>
        )}

        {/* Metadata */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">
            {mensaje.timestamp.toLocaleTimeString('es-PY', { hour: '2-digit', minute: '2-digit' })}
          </span>
          {!esUsuario && <EstadoIA motor={mensaje.motor} />}
        </div>
      </div>
    </div>
  )
}

function BurbujaEscribiendo() {
  return (
    <div className="flex gap-3 max-w-[85%]">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0">
        <Bot size={16} className="text-white" />
      </div>
      <div className="px-4 py-3 bg-white border border-gray-100 rounded-2xl rounded-tl-sm shadow-sm">
        <div className="flex gap-1 items-center h-5">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function AsistentePage() {
  const qc = useQueryClient()
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [input, setInput] = useState('')
  const [cargando, setCargando] = useState(false)
  const [usarGemini, setUsarGemini] = useState(false)
  const [sidebarAbierto, setSidebarAbierto] = useState(false)

  // Sidebar abierto por defecto en desktop, cerrado en mobile
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setSidebarAbierto(window.matchMedia('(min-width: 768px)').matches)
    }
  }, [])
  const [busqueda, setBusqueda] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Verificar estado del motor IA al cargar
  const { data: estadoIA, refetch: refetchEstado } = useQuery({
    queryKey: ['chat-estado'],
    queryFn: () => chatApi.estado().then(r => r.data),
    refetchInterval: 30_000,
  })

  // Auto-scroll al último mensaje
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes, cargando])

  // Mensaje de bienvenida al montar
  useEffect(() => {
    setMensajes([{
      id: 'bienvenida',
      rol: 'assistant',
      contenido: '¡Hola! Soy el asistente contable del ERP. Puedo consultarte saldos de clientes y proveedores, verificar stock, listar facturas pendientes y darte un resumen financiero.\n\n¿En qué te puedo ayudar?',
      timestamp: new Date(),
    }])
  }, [])

  // Construir historial para el backend (formato OpenAI)
  const construirHistorial = () =>
    mensajes
      .filter(m => m.id !== 'bienvenida')
      .map(m => ({
        role: m.rol === 'user' ? 'user' : 'assistant',
        content: m.contenido,
      }))

  const enviar = async (textoMensaje?: string) => {
    const texto = (textoMensaje ?? input).trim()
    if (!texto || cargando) return

    const msgUsuario: Mensaje = {
      id: Date.now().toString(),
      rol: 'user',
      contenido: texto,
      timestamp: new Date(),
    }

    setMensajes(prev => [...prev, msgUsuario])
    setInput('')
    setCargando(true)

    try {
      const historial = construirHistorial()
      const { data } = await chatApi.enviarMensaje(texto, historial, usarGemini)

      const msgAsistente: Mensaje = {
        id: (Date.now() + 1).toString(),
        rol: 'assistant',
        contenido: data.respuesta,
        acciones: data.acciones,
        motor: data.motor_usado,
        timestamp: new Date(),
      }
      setMensajes(prev => [...prev, msgAsistente])
    } catch {
      setMensajes(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        rol: 'assistant',
        contenido: 'Hubo un error al procesar tu consulta. Verifique que el backend esté corriendo.',
        timestamp: new Date(),
      }])
    } finally {
      setCargando(false)
      inputRef.current?.focus()
    }
  }

  const limpiarChat = () => {
    setMensajes([{
      id: 'bienvenida',
      rol: 'assistant',
      contenido: '¡Chat limpiado! ¿En qué te puedo ayudar?',
      timestamp: new Date(),
    }])
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      enviar()
    }
  }

  // Agrupar mensajes por día para el sidebar (excluye bienvenida)
  const grupos = useMemo(() => {
    const reales = mensajes.filter(m => m.id !== 'bienvenida')
    const buckets: Record<string, { key: string; label: string; mensajes: Mensaje[] }> = {}
    const hoy = new Date(); hoy.setHours(0, 0, 0, 0)
    const ayer = new Date(hoy); ayer.setDate(ayer.getDate() - 1)
    for (const m of reales) {
      const d = new Date(m.timestamp); d.setHours(0, 0, 0, 0)
      const key = d.toISOString().slice(0, 10)
      let label: string
      if (d.getTime() === hoy.getTime()) label = 'Hoy'
      else if (d.getTime() === ayer.getTime()) label = 'Ayer'
      else label = d.toLocaleDateString('es-PY', { day: '2-digit', month: 'short', year: 'numeric' })
      if (!buckets[key]) buckets[key] = { key, label, mensajes: [] }
      buckets[key].mensajes.push(m)
    }
    return Object.values(buckets).sort((a, b) => (a.key < b.key ? 1 : -1))
  }, [mensajes])

  // Filtrar mensajes por búsqueda
  const mensajesFiltrados = useMemo(() => {
    if (!busqueda.trim()) return mensajes
    const q = busqueda.toLowerCase()
    return mensajes.filter(m => m.id === 'bienvenida' || m.contenido.toLowerCase().includes(q))
  }, [mensajes, busqueda])

  const irAGrupo = (key: string) => {
    const el = document.getElementById(`grupo-${key}`)
    if (el && scrollContainerRef.current) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
    // En mobile cerrar el sidebar tras seleccionar un grupo
    if (typeof window !== 'undefined' && !window.matchMedia('(min-width: 768px)').matches) {
      setSidebarAbierto(false)
    }
  }

  const handleAccionConfirmada = (_data: ConfirmarAccionResponse) => {
    qc.invalidateQueries({ queryKey: ['comprobantes'] })
    qc.invalidateQueries({ queryKey: ['movimientos'] })
    qc.invalidateQueries({ queryKey: ['dashboard'] })
    qc.invalidateQueries({ queryKey: ['cuentas'] })
  }

  const motorActivo = estadoIA?.gemini_configurado ? 'gemini_solo' : 'sin_ia'

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Backdrop mobile cuando el sidebar está abierto */}
      {sidebarAbierto && (
        <button
          className="md:hidden fixed inset-0 z-30 bg-slate-900/40"
          onClick={() => setSidebarAbierto(false)}
          aria-label="Cerrar historial"
        />
      )}

      {/* Sidebar historial — desktop fijo, mobile slide-over */}
      <aside
        aria-label="Historial de conversaciones"
        className={clsx(
          'border-r border-gray-200 bg-white flex-col transition-all duration-200 overflow-hidden',
          'fixed inset-y-0 left-0 z-40 md:static',
          sidebarAbierto ? 'flex w-72' : 'w-0 md:w-0 hidden md:flex',
        )}
      >
        <div className="px-4 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2 mb-3">
            <History size={16} className="text-indigo-600" />
            <h2 className="text-sm font-semibold text-gray-900">Historial</h2>
          </div>
          <div className="relative">
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
              placeholder="Buscar en mensajes…"
              className="w-full pl-7 pr-7 py-1.5 text-xs bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            {busqueda && (
              <button
                onClick={() => setBusqueda('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                aria-label="Limpiar búsqueda"
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto p-2 space-y-3">
          {grupos.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-6 px-3">
              Las conversaciones aparecen acá agrupadas por día.
            </p>
          ) : grupos.map(g => (
            <div key={g.key}>
              <button
                onClick={() => irAGrupo(g.key)}
                className="w-full text-left px-2 py-1 text-[11px] uppercase tracking-wide font-semibold text-gray-500 hover:text-indigo-700"
              >
                {g.label} · {g.mensajes.filter(m => m.rol === 'user').length} consulta{g.mensajes.filter(m => m.rol === 'user').length === 1 ? '' : 's'}
              </button>
              <ul className="space-y-0.5">
                {g.mensajes.filter(m => m.rol === 'user').slice(0, 5).map(m => (
                  <li key={m.id}>
                    <button
                      onClick={() => irAGrupo(g.key)}
                      className="w-full text-left px-2 py-1 text-xs text-gray-600 hover:bg-indigo-50 rounded truncate"
                      title={m.contenido}
                    >
                      {m.contenido.slice(0, 50)}{m.contenido.length > 50 ? '…' : ''}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-3">
        <button
          onClick={() => setSidebarAbierto(v => !v)}
          className="inline-flex p-1.5 text-gray-500 hover:bg-gray-100 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          title={sidebarAbierto ? 'Ocultar historial' : 'Mostrar historial'}
          aria-label={sidebarAbierto ? 'Ocultar historial' : 'Mostrar historial'}
          aria-expanded={sidebarAbierto}
        >
          <Menu size={16} aria-hidden="true" />
        </button>
        <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl">
          <Bot size={20} className="text-white" />
        </div>
        <div className="flex-1">
          <h1 className="font-bold text-gray-900">Aurora — Asistente</h1>
          <p className="text-xs text-gray-500">Consultas contables en lenguaje natural · Ctrl+J para abrir desde cualquier pantalla</p>
        </div>

        {/* Estado del motor */}
        <div className="flex items-center gap-3">
          {motorActivo === 'gemini_solo' && (
            <div className="flex items-center gap-1.5 text-xs text-purple-600 bg-purple-50 px-3 py-1.5 rounded-full">
              <Sparkles size={12} />
              <span>Gemini (nube)</span>
            </div>
          )}
          {motorActivo === 'sin_ia' && (
            <div className="flex items-center gap-1.5 text-xs text-red-600 bg-red-50 px-3 py-1.5 rounded-full">
              <AlertCircle size={12} />
              <span>IA no disponible</span>
            </div>
          )}

          <button
            onClick={() => refetchEstado()}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="Verificar estado"
          >
            <RefreshCw size={15} />
          </button>

          <button
            onClick={limpiarChat}
            className="text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Limpiar
          </button>
        </div>
      </div>

      {/* Acciones rápidas */}
      {mensajes.length <= 1 && (
        <div className="px-6 pt-4 flex flex-wrap gap-2">
          {ACCIONES_RAPIDAS.map(a => (
            <button
              key={a.label}
              onClick={() => enviar(a.mensaje)}
              disabled={cargando}
              className="text-xs px-3 py-2 bg-white border border-gray-200 rounded-full text-gray-600 hover:border-primary hover:text-primary hover:bg-blue-50 transition-colors disabled:opacity-50"
            >
              {a.label}
            </button>
          ))}
        </div>
      )}

      {/* Área de mensajes */}
      <div
        ref={scrollContainerRef}
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Conversación con Aurora"
        className="flex-1 overflow-y-auto px-6 py-4 space-y-4"
      >
        {busqueda.trim() ? (
          <>
            <p className="text-xs text-gray-500 italic">
              Mostrando {mensajesFiltrados.length} resultado{mensajesFiltrados.length === 1 ? '' : 's'} para “{busqueda}”
            </p>
            {mensajesFiltrados.map(m => (
              <BurbujaMensaje key={m.id} mensaje={m} onConfirmada={handleAccionConfirmada} />
            ))}
          </>
        ) : grupos.length === 0 ? (
          mensajes.map(m => (
            <BurbujaMensaje key={m.id} mensaje={m} onConfirmada={handleAccionConfirmada} />
          ))
        ) : (
          grupos.slice().reverse().map(g => (
            <section key={g.key} id={`grupo-${g.key}`} className="space-y-4 scroll-mt-4">
              <div className="sticky top-0 z-10 -mx-6 px-6 py-1 bg-gray-50/80 backdrop-blur-sm">
                <span className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 bg-white border border-gray-200 rounded-full px-2 py-0.5">
                  {g.label}
                </span>
              </div>
              {g.mensajes.map(m => (
                <BurbujaMensaje key={m.id} mensaje={m} onConfirmada={handleAccionConfirmada} />
              ))}
            </section>
          ))
        )}
        {cargando && <BurbujaEscribiendo />}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        {/* Toggle Gemini */}
        <div className="flex items-center gap-2 mb-3">
          <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer select-none">
            <div
              onClick={() => setUsarGemini(!usarGemini)}
              className={clsx(
                'relative w-8 h-4 rounded-full transition-colors cursor-pointer',
                usarGemini ? 'bg-purple-500' : 'bg-gray-200'
              )}
            >
              <div className={clsx(
                'absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform',
                usarGemini ? 'translate-x-4' : 'translate-x-0.5'
              )} />
            </div>
            Usar Gemini (alta precisión)
          </label>
        </div>

        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Preguntá algo... (Enter para enviar, Shift+Enter para nueva línea)"
            rows={1}
            disabled={cargando}
            className="flex-1 resize-none px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all disabled:opacity-50 max-h-32 overflow-y-auto"
            style={{ minHeight: '46px' }}
            onInput={e => {
              const t = e.target as HTMLTextAreaElement
              t.style.height = 'auto'
              t.style.height = Math.min(t.scrollHeight, 128) + 'px'
            }}
          />
          <button
            onClick={() => enviar()}
            disabled={!input.trim() || cargando}
            className="p-3 bg-primary text-white rounded-xl hover:bg-primary-dark transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            {cargando
              ? <Loader2 size={18} className="animate-spin" />
              : <Send size={18} />
            }
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          Los cobros y pagos preparados por IA requieren confirmacion antes de guardarse
        </p>
      </div>
      </div>
    </div>
  )
}
