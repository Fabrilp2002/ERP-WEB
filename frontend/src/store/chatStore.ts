'use client'
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export type ChatAccion = {
  funcion: string
  argumentos: Record<string, unknown>
  resultado: Record<string, unknown>
}

export type ChatMsg = {
  rol: 'user' | 'assistant'
  contenido: string
  acciones?: ChatAccion[]
  ts?: number
}

type ChatState = {
  historial: ChatMsg[]
  abierto: boolean
  ultimoUso: number | null
  agregar: (msg: ChatMsg) => void
  reemplazarUltimo: (msg: ChatMsg) => void
  setHistorial: (h: ChatMsg[]) => void
  limpiar: () => void
  setAbierto: (v: boolean) => void
  toggleAbierto: () => void
}

const MAX_MSGS = 50

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      historial: [],
      abierto: false,
      ultimoUso: null,
      agregar: (msg) =>
        set((s) => ({
          historial: [...s.historial, { ...msg, ts: msg.ts ?? Date.now() }].slice(-MAX_MSGS),
          ultimoUso: Date.now(),
        })),
      reemplazarUltimo: (msg) =>
        set((s) => {
          if (s.historial.length === 0) return s
          const copia = s.historial.slice(0, -1)
          return {
            historial: [...copia, { ...msg, ts: msg.ts ?? Date.now() }].slice(-MAX_MSGS),
            ultimoUso: Date.now(),
          }
        }),
      setHistorial: (h) => set({ historial: h.slice(-MAX_MSGS) }),
      limpiar: () => set({ historial: [], ultimoUso: null }),
      setAbierto: (v) => set({ abierto: v }),
      toggleAbierto: () => set((s) => ({ abierto: !s.abierto })),
    }),
    {
      name: 'erp.chat.v1',
      storage: createJSONStorage(() => (typeof window === 'undefined' ? undefined as never : localStorage)),
      partialize: (s) => ({ historial: s.historial, ultimoUso: s.ultimoUso }),
      version: 1,
    },
  ),
)
