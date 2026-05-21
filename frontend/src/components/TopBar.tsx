'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowDownUp,
  Bot,
  Building2,
  FileText,
  History,
  LayoutDashboard,
  LogOut,
  Package,
  Receipt,
  ScanLine,
  Settings,
  Shield,
  ShieldCheck,
  Truck,
  Users,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react'
import clsx from 'clsx'
import { empresaApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { offlineQueue } from '@/lib/offline'

type NavEntry = {
  href: string
  label: string
  icon: any
  write?: boolean
  admin?: boolean
}

const NAV: NavEntry[] = [
  { href: '/dashboard', label: 'Inicio', icon: LayoutDashboard },
  { href: '/comprobantes', label: 'Facturas', icon: FileText },
  { href: '/ocr', label: 'Foto', icon: ScanLine, write: true },
  { href: '/movimientos', label: 'Cobros y pagos', icon: ArrowDownUp },
  { href: '/reportes/iva', label: 'IVA', icon: Receipt },
  { href: '/clientes', label: 'Clientes', icon: Users },
  { href: '/proveedores', label: 'Proveedores', icon: Truck },
  { href: '/inventario', label: 'Inventario', icon: Package },
  { href: '/asistente', label: 'Asistente', icon: Bot },
]

export default function TopBar() {
  const pathname = usePathname()
  const { usuario, logout, puedeEscribir } = useAuth()
  const [online, setOnline] = useState(true)
  const [pendientes, setPendientes] = useState(0)
  const [menuAbierto, setMenuAbierto] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const esAdmin = usuario?.rol === 'admin'

  const { data: empresa } = useQuery<{ nombre?: string; logo_url?: string | null }>({
    queryKey: ['empresa'],
    queryFn: () => empresaApi.obtener().then(r => r.data),
    enabled: !!usuario,
    staleTime: 60_000,
  })

  useEffect(() => {
    const update = () => setOnline(navigator.onLine)
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    update()
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])

  useEffect(() => {
    const interval = setInterval(async () => {
      setPendientes(await offlineQueue.contarPendientes())
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!menuAbierto) return
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuAbierto(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [menuAbierto])

  const visibleParaUsuario = (entry: NavEntry) =>
    !entry.write || puedeEscribir()

  const logoSrc = empresa?.logo_url || null

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-3 sm:px-6">
        <div className="flex items-center gap-2 sm:gap-4 h-14">
          {/* Logo + nombre empresa */}
          <Link href="/dashboard" className="flex items-center gap-2 flex-shrink-0">
            <div className="w-8 h-8 bg-blue-700 rounded-lg flex items-center justify-center overflow-hidden">
              {logoSrc
                ? <img src={logoSrc} alt="Logo" className="w-full h-full object-contain" />
                : <Building2 size={16} className="text-white" />
              }
            </div>
            <span className="font-semibold text-slate-900 text-sm hidden sm:block truncate max-w-[160px]">
              {empresa?.nombre ?? 'Mi Negocio'}
            </span>
          </Link>

          {/* Nav principal */}
          <nav className="flex-1 overflow-x-auto hidden md:flex">
            <div className="flex items-center gap-0.5">
              {NAV.filter(visibleParaUsuario).map(entry => {
                const active = pathname.startsWith(entry.href)
                const Icon = entry.icon
                return (
                  <Link
                    key={entry.href}
                    href={entry.href}
                    className={clsx(
                      'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all whitespace-nowrap',
                      active
                        ? 'bg-blue-50 text-blue-700 font-semibold'
                        : 'text-slate-600 hover:bg-slate-100',
                    )}
                  >
                    <Icon size={15} />
                    <span>{entry.label}</span>
                  </Link>
                )
              })}
            </div>
          </nav>

          <div className="flex-1 md:hidden" />

          {/* Estado conexion */}
          <div className={clsx(
            'hidden sm:flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg',
            online ? 'text-emerald-600' : 'text-amber-600',
          )}>
            {online ? <Wifi size={13} /> : <WifiOff size={13} />}
            {!online && pendientes > 0 && (
              <span className="bg-amber-500 text-white rounded-full px-1.5 py-0.5 text-[10px] font-bold">
                {pendientes}
              </span>
            )}
          </div>

          {/* Globo de ajustes y usuario */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuAbierto(o => !o)}
              className={clsx(
                'flex items-center gap-2 rounded-full pl-1 pr-3 py-1 transition-all',
                menuAbierto
                  ? 'bg-blue-700 text-white shadow-md'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700',
              )}
              aria-label="Ajustes y usuario"
            >
              <span className={clsx(
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold',
                menuAbierto ? 'bg-white/20 text-white' : 'bg-blue-700 text-white',
              )}>
                {usuario?.nombre?.charAt(0).toUpperCase() ?? 'U'}
              </span>
              <Settings size={14} className={menuAbierto ? '' : 'text-slate-500'} />
            </button>

            {menuAbierto && (
              <div className="absolute right-0 mt-2 w-[calc(100vw-1.5rem)] max-w-72 bg-white rounded-2xl shadow-xl ring-1 ring-slate-200 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
                {/* Cabecera usuario */}
                <div className="p-4 border-b border-slate-100 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-700 text-white flex items-center justify-center font-bold">
                    {usuario?.nombre?.charAt(0).toUpperCase() ?? 'U'}
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-sm text-slate-900 truncate">
                      {usuario?.nombre ?? '-'}{usuario?.apellido ? ` ${usuario.apellido}` : ''}
                    </p>
                    <p className="text-xs text-slate-500 capitalize">{usuario?.rol ?? ''}</p>
                  </div>
                  <button
                    onClick={() => setMenuAbierto(false)}
                    className="ml-auto text-slate-400 hover:text-slate-700"
                    aria-label="Cerrar"
                  >
                    <X size={16} />
                  </button>
                </div>

                {/* Items */}
                <div className="py-1">
                  <MenuLink href="/perfil/seguridad" icon={ShieldCheck} label="Mi seguridad" onClick={() => setMenuAbierto(false)} />
                  <MenuLink href="/actividad" icon={History} label="Actividad" onClick={() => setMenuAbierto(false)} />
                  {esAdmin && (
                    <>
                      <div className="my-1 border-t border-slate-100" />
                      <p className="px-4 pt-2 pb-1 text-[10px] uppercase tracking-widest text-slate-400 font-semibold">
                        Administracion
                      </p>
                      <MenuLink href="/admin/empresa" icon={Building2} label="Mi empresa" onClick={() => setMenuAbierto(false)} />
                      <MenuLink href="/admin/usuarios" icon={Shield} label="Usuarios" onClick={() => setMenuAbierto(false)} />
                    </>
                  )}
                </div>

                {/* Estado conexion mobile */}
                <div className="px-4 py-2 border-t border-slate-100 sm:hidden">
                  <div className={clsx(
                    'flex items-center gap-2 text-xs',
                    online ? 'text-emerald-600' : 'text-amber-600',
                  )}>
                    {online ? <Wifi size={13} /> : <WifiOff size={13} />}
                    <span>{online ? 'Conectado' : 'Sin conexion'}</span>
                    {!online && pendientes > 0 && (
                      <span className="ml-auto bg-amber-500 text-white rounded-full px-1.5 py-0.5 font-bold">
                        {pendientes} pendientes
                      </span>
                    )}
                  </div>
                </div>

                {/* Logout */}
                <button
                  onClick={() => { setMenuAbierto(false); logout() }}
                  className="w-full flex items-center gap-2 px-4 py-3 text-sm text-rose-600 hover:bg-rose-50 transition-colors border-t border-slate-100"
                >
                  <LogOut size={15} />
                  Cerrar sesion
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

function MenuLink({ href, icon: Icon, label, onClick }: {
  href: string; icon: any; label: string; onClick?: () => void
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className="flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
    >
      <Icon size={15} className="text-slate-400" />
      <span>{label}</span>
    </Link>
  )
}
