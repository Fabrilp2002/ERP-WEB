'use client'
/**
 * useUndoToast — toast global con botón "Deshacer" y barra de progreso.
 *
 * Uso:
 *   const mostrarUndo = useUndoToast()
 *   mostrarUndo({
 *     mensaje: 'Cobro registrado',
 *     detalle: 'G. 50.000 · CADENA REAL S.A.',
 *     onUndo: async () => { await pagosApi.eliminar(pagoId) },
 *   })
 */
import { createContext, useContext, useState, useCallback, useRef, useEffect, ReactNode } from 'react'
import { CheckCircle2, Undo2, X } from 'lucide-react'

export type UndoOptions = {
  mensaje: string
  detalle?: string
  /** Si no se provee, el toast solo informa (sin botón Deshacer) */
  onUndo?: () => Promise<void>
  duracion?: number   // ms, default 14000
}

type ToastState = UndoOptions & {
  id: number
  progreso: number      // 0–100
  deshaciendo: boolean
  revertido: boolean
}

type UndoCtx = { mostrarUndo: (opts: UndoOptions) => void }

const Ctx = createContext<UndoCtx | null>(null)

export function UndoToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState | null>(null)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  const limpiar = useCallback(() => {
    if (timer.current) clearInterval(timer.current)
    setToast(null)
  }, [])

  const mostrarUndo = useCallback((opts: UndoOptions) => {
    if (timer.current) clearInterval(timer.current)
    const duracion = opts.duracion ?? 14000
    const id = Date.now()
    setToast({ ...opts, id, progreso: 100, deshaciendo: false, revertido: false })

    const step = 100 / (duracion / 100)
    timer.current = setInterval(() => {
      setToast(prev => {
        if (!prev || prev.id !== id || prev.deshaciendo || prev.revertido) return prev
        const next = prev.progreso - step
        if (next <= 0) { clearInterval(timer.current!); return null }
        return { ...prev, progreso: next }
      })
    }, 100)
  }, [])

  const deshacer = useCallback(async () => {
    if (!toast?.onUndo || toast.deshaciendo || toast.revertido) return
    if (timer.current) clearInterval(timer.current)
    setToast(prev => prev ? { ...prev, deshaciendo: true } : null)
    try {
      await toast.onUndo()
      setToast(prev => prev ? { ...prev, deshaciendo: false, revertido: true } : null)
      setTimeout(limpiar, 2000)
    } catch {
      limpiar()
    }
  }, [toast, limpiar])

  useEffect(() => () => { if (timer.current) clearInterval(timer.current) }, [])

  return (
    <Ctx.Provider value={{ mostrarUndo }}>
      {children}

      {toast && (
        <div className="fixed bottom-24 md:bottom-6 right-4 z-[150] w-80 bg-slate-900 text-white rounded-2xl shadow-2xl overflow-hidden pointer-events-auto">
          <div className="px-4 pt-3 pb-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2 flex-1 min-w-0">
                <CheckCircle2 size={16} className={`mt-0.5 shrink-0 ${toast.revertido ? 'text-amber-400' : 'text-emerald-400'}`} />
                <div className="min-w-0">
                  <p className="text-sm font-semibold leading-tight">
                    {toast.revertido ? 'Acción revertida' : toast.mensaje}
                  </p>
                  {!toast.revertido && toast.detalle && (
                    <p className="text-xs text-slate-400 mt-0.5 truncate">{toast.detalle}</p>
                  )}
                </div>
              </div>
              {!toast.deshaciendo && !toast.revertido && (
                <button
                  onClick={limpiar}
                  className="text-slate-500 hover:text-white transition shrink-0 mt-0.5"
                  aria-label="Cerrar"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            {toast.onUndo && !toast.revertido && (
              <button
                onClick={deshacer}
                disabled={toast.deshaciendo}
                className="mt-2.5 w-full flex items-center justify-center gap-1.5 text-xs font-semibold bg-white/10 hover:bg-white/20 active:bg-white/5 transition rounded-lg px-3 py-1.5 disabled:opacity-50"
              >
                <Undo2 size={12} />
                {toast.deshaciendo ? 'Deshaciendo…' : 'Deshacer'}
              </button>
            )}
          </div>

          {/* Barra de progreso (se congela al hacer undo) */}
          {!toast.revertido && (
            <div className="h-[3px] bg-slate-700">
              <div
                className="h-full bg-emerald-400"
                style={{ width: `${toast.progreso}%`, transition: 'width 100ms linear' }}
              />
            </div>
          )}
        </div>
      )}
    </Ctx.Provider>
  )
}

export function useUndoToast() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useUndoToast debe usarse dentro de UndoToastProvider')
  return ctx.mostrarUndo
}
