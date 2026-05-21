'use client'
import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Sidebar from '@/components/Sidebar'
import TopBar from '@/components/TopBar'
import BottomNav from '@/components/BottomNav'
import AsistenteFlotante from '@/components/AsistenteFlotante'
import IdleTimeoutGuard from '@/components/IdleTimeoutGuard'
import BackendKeepalive from '@/components/BackendKeepalive'
import Breadcrumbs from '@/components/Breadcrumbs'
import { useAuth } from '@/lib/auth'
import { ConfirmProvider } from '@/hooks/useConfirm'
import { UndoToastProvider } from '@/hooks/useUndoToast'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!token) router.replace('/login')
  }, [token, router])

  useEffect(() => {
    const rutasAvanzadas = [
      '/contabilidad',
      '/bancos',
      '/admin/sistema',
      '/admin/auditoria',
      '/exportar',
    ]
    if (rutasAvanzadas.some(ruta => pathname.startsWith(ruta))) {
      router.replace('/dashboard')
    }
  }, [pathname, router])

  if (!token) return null

  return (
    <ConfirmProvider>
      <UndoToastProvider>
        <div className="min-h-screen flex bg-slate-50">
          {/* Sidebar lateral — solo desktop */}
          <Sidebar />

          {/* Contenido principal */}
          <div className="flex-1 flex flex-col min-w-0 w-full">
            {/* TopBar — solo mobile, oculto en desktop (el sidebar reemplaza la nav) */}
            <div className="md:hidden">
              <TopBar />
            </div>

            <main className="flex-1 overflow-auto w-full">
              {/* Breadcrumbs en desktop */}
              <div className="hidden md:block px-6 lg:px-8 pt-4">
                <Breadcrumbs />
              </div>
              {children}
            </main>

            {/* Bottom nav (visible en mobile <md, oculto en desktop) */}
            <BottomNav />
          </div>

          {/* Seguridad: cierre por inactividad */}
          <IdleTimeoutGuard minutos={30} />

          {/* Mantiene caliente al backend mientras la app esté abierta */}
          <BackendKeepalive />

          {/* Asistente IA flotante (visible siempre cuando hay token) */}
          <AsistenteFlotante />
        </div>
      </UndoToastProvider>
    </ConfirmProvider>
  )
}
