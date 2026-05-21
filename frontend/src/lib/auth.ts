import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthState, Usuario } from './types'

interface AuthStore extends AuthState {
  login: (token: string, usuario: Usuario) => void
  logout: () => void
  puedeEscribir: () => boolean
}

export const useAuth = create<AuthStore>()(
  persist(
    (set, get) => ({
      token: null,
      usuario: null,
      empresaId: null,

      login: (token, usuario) =>
        set({ token, usuario, empresaId: usuario.empresa_id }),

      logout: () => {
        set({ token: null, usuario: null, empresaId: null })
        window.location.href = '/login'
      },

      puedeEscribir: () => {
        const rol = get().usuario?.rol
        return rol === 'admin' || rol === 'operador'
      },
    }),
    { name: 'erp-auth' }
  )
)
