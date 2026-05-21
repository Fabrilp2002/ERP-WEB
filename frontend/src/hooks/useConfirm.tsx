'use client'
/**
 * useConfirm — diálogo de confirmación global.
 *
 * Uso:
 *   const confirm = useConfirm()
 *   const ok = await confirm({ titulo: '¿Confirmar anulación?', peligro: true })
 *   if (!ok) return
 */
import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { AlertTriangle, HelpCircle } from 'lucide-react'

export type ConfirmOptions = {
  titulo: string
  descripcion?: string
  labelConfirmar?: string
  labelCancelar?: string
  peligro?: boolean
}

type ConfirmState = ConfirmOptions & { resolve: (v: boolean) => void }

type ConfirmCtx = { confirm: (opts: ConfirmOptions) => Promise<boolean> }

const Ctx = createContext<ConfirmCtx | null>(null)

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ConfirmState | null>(null)

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> =>
    new Promise(resolve => setState({ ...opts, resolve })),
  [])

  const close = (result: boolean) => {
    state?.resolve(result)
    setState(null)
  }

  return (
    <Ctx.Provider value={{ confirm }}>
      {children}

      {state && (
        <div
          className="fixed inset-0 z-[200] bg-black/50 flex items-center justify-center p-4"
          onMouseDown={e => { if (e.target === e.currentTarget) close(false) }}
        >
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                state.peligro ? 'bg-red-100' : 'bg-blue-100'
              }`}>
                {state.peligro
                  ? <AlertTriangle size={20} className="text-red-600" />
                  : <HelpCircle size={20} className="text-blue-600" />}
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 leading-tight">{state.titulo}</h3>
                {state.descripcion && (
                  <p className="text-sm text-slate-600 mt-1">{state.descripcion}</p>
                )}
              </div>
            </div>

            <div className="flex gap-2 justify-end pt-1">
              <button
                className="btn-secondary"
                onClick={() => close(false)}
                autoFocus
              >
                {state.labelCancelar ?? 'Cancelar'}
              </button>
              <button
                className={`btn-primary ${state.peligro ? 'bg-red-600 hover:bg-red-700' : ''}`}
                onClick={() => close(true)}
              >
                {state.labelConfirmar ?? 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Ctx.Provider>
  )
}

export function useConfirm() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useConfirm debe usarse dentro de ConfirmProvider')
  return ctx.confirm
}
