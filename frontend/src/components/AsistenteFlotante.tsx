'use client'
import { useRef, useEffect, useCallback, useState } from 'react'
import { Bot, Send, X, Sparkles, Loader2, AlertCircle, CheckCircle2, RefreshCw, Undo2 } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { chatApi, pagosApi, type ChatStreamEvent } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import clsx from 'clsx'
import { useUndoToast } from '@/hooks/useUndoToast'
import ActionPreviewCard, { isActionPreview, type ConfirmarAccionResponse } from '@/components/chat/ActionPreviewCard'
import { useChatStore, type ChatAccion as Accion, type ChatMsg as Msg } from '@/store/chatStore'

const SUGERENCIAS = [
  '¿Cuánto me deben en total?',
  'Cobrá G. 200.000 de la factura 001-001-... en efectivo',
  '¿Qué facturas vencen este mes?',
  '¿Cómo cargo una factura nueva?',
]

const ACCIONES_LABEL: Record<string, string> = {
  registrar_cobro: 'Cobro registrado',
  registrar_pago: 'Pago registrado',
  ayuda_sistema: 'Guía del sistema',
  buscar_cliente: 'Cliente',
  buscar_proveedor: 'Proveedor',
  buscar_comprobante: 'Comprobante',
  resumen_financiero: 'Resumen',
  listar_comprobantes_pendientes: 'Pendientes',
  listar_comprobantes_vencidos: 'Vencidos',
  consultar_stock: 'Stock',
  flujo_mensual: 'Flujo mensual',
}

function TarjetaAccion({
  accion,
  onUndo,
  onConfirmada,
}: {
  accion: Accion
  onUndo?: (pagoId: string) => void
  onConfirmada?: (data: ConfirmarAccionResponse) => void
}) {
  const [deshaciendo, setDeshaciendo] = useState(false)
  const [revertido, setRevertido] = useState(false)
  const esEscritura = accion.funcion === 'registrar_cobro' || accion.funcion === 'registrar_pago'
  const ok = (accion.resultado as { ok?: boolean })?.ok === true
  const error = (accion.resultado as { error?: string })?.error
  const ambiguo = (accion.resultado as { ambiguo?: boolean })?.ambiguo === true
  const nombre = ACCIONES_LABEL[accion.funcion] ?? accion.funcion

  if (esEscritura && isActionPreview(accion)) {
    return (
      <div className="mt-2">
        <ActionPreviewCard accion={accion} onConfirmada={onConfirmada} compact />
      </div>
    )
  }

  if (esEscritura && ok) {
    const r = accion.resultado as Record<string, unknown>
    const pagoId = r.pago_id as string | undefined

    const handleDeshacer = async () => {
      if (!pagoId || deshaciendo || revertido) return
      setDeshaciendo(true)
      try {
        if (onUndo) onUndo(pagoId)
        setRevertido(true)
      } finally {
        setDeshaciendo(false)
      }
    }

    return (
      <div className="mt-2 border border-emerald-200 bg-emerald-50 rounded-lg px-3 py-2 text-xs">
        <div className="flex items-start gap-2">
          <CheckCircle2 size={14} className="text-emerald-600 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            {revertido ? (
              <p className="font-semibold text-slate-600">Acción revertida</p>
            ) : (
              <>
                <p className="font-semibold text-emerald-800">{nombre}</p>
                <p className="text-emerald-700">
                  Factura {String(r.factura_numero)} · {String(r.contraparte)} · ₲{' '}
                  {Number(r.monto || 0).toLocaleString('es-PY')}
                </p>
                <p className="text-emerald-600 text-[11px]">
                  Saldo restante: ₲ {Number(r.saldo_restante || 0).toLocaleString('es-PY')}
                  {r.totalmente_cancelado ? ' · Totalmente cancelada' : ''}
                </p>
              </>
            )}
          </div>
        </div>
        {pagoId && !revertido && (
          <button
            onClick={handleDeshacer}
            disabled={deshaciendo}
            className="mt-2 w-full flex items-center justify-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-100 hover:bg-emerald-200 rounded-md py-1 transition disabled:opacity-50"
          >
            <Undo2 size={11} />
            {deshaciendo ? 'Deshaciendo…' : 'Deshacer'}
          </button>
        )}
      </div>
    )
  }

  if (esEscritura && (error || ambiguo)) {
    return (
      <div className="mt-2 border border-amber-200 bg-amber-50 rounded-lg px-3 py-2 text-xs flex items-start gap-2">
        <AlertCircle size={14} className="text-amber-600 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-amber-800">{nombre} no aplicado</p>
          <p className="text-amber-700">{error || (accion.resultado as Record<string, unknown>).mensaje as string || 'Necesita aclaración.'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-1 inline-flex items-center gap-1 text-[10px] text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full">
      <Sparkles size={10} /> {nombre}
    </div>
  )
}

export default function AsistenteFlotante() {
  const { usuario } = useAuth()
  const qc = useQueryClient()
  const mostrarUndo = useUndoToast()
  const abierto = useChatStore((s) => s.abierto)
  const setAbierto = useChatStore((s) => s.setAbierto)
  const toggleAbierto = useChatStore((s) => s.toggleAbierto)
  const historial = useChatStore((s) => s.historial)
  const agregarMsg = useChatStore((s) => s.agregar)
  const reemplazarUltimo = useChatStore((s) => s.reemplazarUltimo)
  const limpiarStore = useChatStore((s) => s.limpiar)
  const [input, setInput] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [historial, enviando, abierto])

  // Atajos: Ctrl+J (preferido) y Ctrl+/ (legado) abren/cierran. Esc cierra.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey
      if (mod && (e.key === 'j' || e.key === 'J' || e.key === '/')) {
        e.preventDefault()
        toggleAbierto()
      }
      if (e.key === 'Escape' && abierto) setAbierto(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [abierto, toggleAbierto, setAbierto])

  // Foco al abrir
  useEffect(() => {
    if (abierto) setTimeout(() => inputRef.current?.focus(), 100)
  }, [abierto])

  if (!usuario) return null

  // Invalidación + refetch agresivo de TODAS las queries afectadas tras una escritura
  // (cobro/pago/anulación vía chat). refetchType:'all' fuerza refetch incluso de
  // queries inactivas (otras pestañas del SPA que aún no se montaron).
  // Declarado antes de `enviar` para que la dependencia esté disponible.
  const refrescarTrasEscritura = () => {
    // Cubre todas las queries cuyo dato se mueve cuando hay un cobro/pago:
    //  - dashboard (cards + chart cobros + ingresos vs egresos)
    //  - cuentas / historial / analisis (cuenta de cliente o proveedor)
    //  - comprobantes / movimientos (listados)
    //  - reportes (aging, iva, forecast, resultados) — todos derivados de pagos/saldos
    const keys = [
      ['comprobantes'],
      ['movimientos'],
      ['dashboard'],
      ['cuentas'],
      ['historial'],
      ['analisis'],
      ['reportes'],
      ['aging'],
      ['iva-resumen-simple'],
      ['flujo-resultados'],
      ['iva-resultados'],
    ]
    for (const key of keys) {
      qc.invalidateQueries({ queryKey: key, refetchType: 'all' })
    }
  }

  const enviar = useCallback(async (msgTxt?: string) => {
    const mensaje = (msgTxt ?? input).trim()
    if (!mensaje || enviando) return

    agregarMsg({ rol: 'user', contenido: mensaje })
    setInput('')
    setEnviando(true)
    setError(null)

    const historialApi = historial.map(h => ({ role: h.rol, content: h.contenido }))

    // Placeholder del assistant que se va completando con cada token
    let textoStream = ''
    const accionesStream: Accion[] = []
    agregarMsg({ rol: 'assistant', contenido: '', acciones: [] })

    try {
      for await (const ev of chatApi.enviarMensajeStream(mensaje, historialApi) as AsyncGenerator<ChatStreamEvent>) {
        if (ev.type === 'token') {
          textoStream += ev.text
          reemplazarUltimo({ rol: 'assistant', contenido: textoStream, acciones: accionesStream })
        } else if (ev.type === 'accion') {
          accionesStream.push(ev.accion as Accion)
          reemplazarUltimo({ rol: 'assistant', contenido: textoStream, acciones: accionesStream })
        } else if (ev.type === 'error') {
          setError(ev.message)
          reemplazarUltimo({ rol: 'assistant', contenido: textoStream || ev.message, acciones: accionesStream })
        }
        // 'done' termina el loop; no requiere accion
      }

      // Invalidaciones si hubo acciones de escritura ejecutadas (no preview)
      if (accionesStream.some(a =>
        (a.funcion === 'registrar_cobro' || a.funcion === 'registrar_pago') &&
        !isActionPreview(a) &&
        (a.resultado as { ok?: boolean })?.ok === true
      )) {
        refrescarTrasEscritura()
      }
    } catch {
      setError('No pude responder. Probá de nuevo.')
      reemplazarUltimo({ rol: 'assistant', contenido: 'No pude responder. Probá de nuevo.' })
    } finally {
      setEnviando(false)
    }
  }, [input, enviando, historial, qc, agregarMsg, reemplazarUltimo])

  const handleAccionConfirmada = useCallback((_data: ConfirmarAccionResponse) => {
    refrescarTrasEscritura()
    // refrescarTrasEscritura es estable a través del cierre de `qc` (que zustand-react-query estabiliza)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const limpiar = () => {
    limpiarStore()
  }

  const handleUndoPago = useCallback(async (pagoId: string) => {
    try {
      await pagosApi.eliminar(pagoId)
      refrescarTrasEscritura()
      mostrarUndo({ mensaje: 'Acción del asistente revertida', detalle: 'El saldo fue restaurado.' })
    } catch {
      /* silently ignore — el backend puede rechazar si ya fue procesado */
    }
  }, [refrescarTrasEscritura, mostrarUndo])

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      enviar()
    }
  }

  return (
    <>
      {!abierto && (
        <button
          onClick={() => setAbierto(true)}
          className={clsx(
            'fixed bottom-24 right-4 z-40 flex items-center gap-2 text-white px-4 py-3 rounded-full shadow-lg',
            'bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-600',
            'hover:shadow-xl motion-safe:hover:scale-105 motion-safe:active:scale-95 transition-all',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-indigo-600',
            'md:bottom-6 md:right-6',
            'aurora-fab',
          )}
          aria-label="Abrir asistente Aurora (Ctrl+J)"
          title="Asistente Aurora · Ctrl+J"
        >
          <Bot size={20} aria-hidden="true" />
          <span className="hidden sm:inline text-sm font-semibold tracking-wide">Aurora</span>
          <span
            aria-hidden="true"
            className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-400 rounded-full motion-safe:animate-pulse ring-2 ring-white/40"
          />
        </button>
      )}

      {abierto && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Aurora — Asistente"
          className={clsx(
            'fixed z-40 bg-white shadow-2xl flex flex-col',
            'inset-0',
            'md:bottom-6 md:right-6 md:top-auto md:left-auto md:w-[400px] md:h-[640px] md:max-h-[85vh] md:rounded-2xl md:border md:border-slate-200',
          )}>
          <div className="flex items-center justify-between p-4 border-b border-slate-200 bg-gradient-to-br from-indigo-700 via-violet-700 to-fuchsia-700 text-white md:rounded-t-2xl">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                <Bot size={18} />
              </div>
              <div>
                <p className="font-semibold text-sm">Aurora</p>
                <p className="text-xs text-indigo-100 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                  Consulta y registra cobros / pagos
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {historial.length > 0 && (
                <button
                  onClick={limpiar}
                  className="p-1.5 hover:bg-white/20 rounded-lg transition"
                  title="Limpiar conversación"
                >
                  <RefreshCw size={16} />
                </button>
              )}
              <button
                onClick={() => setAbierto(false)}
                className="p-1.5 hover:bg-white/20 rounded-lg transition"
                aria-label="Cerrar"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          <div
            ref={scrollRef}
            role="log"
            aria-live="polite"
            aria-relevant="additions"
            className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50"
          >
            {historial.length === 0 ? (
              <div className="text-center py-6">
                <div className="inline-flex items-center justify-center w-14 h-14 bg-blue-100 rounded-full mb-3">
                  <Sparkles size={26} className="text-blue-700" />
                </div>
                <p className="text-slate-700 font-semibold mb-1">¡Hola! Soy tu asistente.</p>
                <p className="text-sm text-slate-500 mb-4">
                  Pregúntame sobre tu negocio o pedime que registre un cobro o pago.
                </p>
                <div className="space-y-2">
                  {SUGERENCIAS.map(s => (
                    <button
                      key={s}
                      onClick={() => enviar(s)}
                      className="block w-full text-left text-sm text-blue-700 bg-white hover:bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 transition"
                    >
                      {s}
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-slate-400 mt-4">Atajo: Ctrl+J para abrir desde cualquier pantalla</p>
              </div>
            ) : (
              historial.map((m, i) => (
                <div key={i} className={clsx('flex flex-col', m.rol === 'user' ? 'items-end' : 'items-start')}>
                  <div
                    className={clsx(
                      'max-w-[85%] rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap',
                      m.rol === 'user'
                        ? 'bg-blue-700 text-white rounded-br-sm'
                        : 'bg-white text-slate-800 border border-slate-200 rounded-bl-sm',
                    )}
                  >
                    {m.contenido}
                  </div>
                  {m.acciones && m.acciones.length > 0 && (
                    <div className="w-full max-w-[85%] mt-1">
                      {m.acciones.map((a, k) => (
                        <TarjetaAccion
                          key={k}
                          accion={a}
                          onUndo={handleUndoPago}
                          onConfirmada={handleAccionConfirmada}
                        />
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}

            {enviando && (
              <div className="flex justify-start">
                <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-3.5 py-2.5 flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin text-slate-400" />
                  <span className="text-xs text-slate-500">Pensando…</span>
                </div>
              </div>
            )}

            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm text-red-800">
                <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>

          <div className="border-t border-slate-200 p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] bg-white md:rounded-b-2xl md:pb-3">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Escribí tu pregunta o instrucción…"
                rows={1}
                className="flex-1 resize-none border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 max-h-24"
                disabled={enviando}
              />
              <button
                onClick={() => enviar()}
                disabled={enviando || !input.trim()}
                className="p-2.5 bg-blue-700 text-white rounded-xl hover:bg-blue-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
                aria-label="Enviar"
              >
                <Send size={16} />
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-1.5 text-center">
              Powered by Gemini · Enter envía · Shift+Enter línea nueva
            </p>
          </div>
        </div>
      )}
    </>
  )
}
