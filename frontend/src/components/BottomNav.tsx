'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import {
  ArrowDownUp,
  Bot,
  FileText,
  Home,
  MoreHorizontal,
  Package,
  Receipt,
  ScanLine,
  Truck,
  Users,
  X,
} from 'lucide-react'
import { useAuth } from '@/lib/auth'
import clsx from 'clsx'

type NavItem = {
  href: string
  label: string
  icon: any
  write?: boolean
}

const ITEMS: NavItem[] = [
  { href: '/dashboard', label: 'Inicio', icon: Home },
  { href: '/comprobantes', label: 'Facturas', icon: FileText },
  { href: '/movimientos', label: 'Cobros', icon: ArrowDownUp },
]

const GRUPOS_MAS: { title: string; items: NavItem[] }[] = [
  {
    title: 'Facturas',
    items: [
      { href: '/comprobantes', label: 'Ver facturas', icon: FileText },
      { href: '/clientes', label: 'Clientes', icon: Users },
      { href: '/proveedores', label: 'Proveedores', icon: Truck },
      { href: '/ocr', label: 'Cargar con foto', icon: ScanLine, write: true },
      { href: '/reportes/iva', label: 'IVA del mes', icon: Receipt },
    ],
  },
  {
    title: 'Operaciones',
    items: [
      { href: '/inventario', label: 'Inventario', icon: Package },
      { href: '/asistente', label: 'Asistente', icon: Bot },
    ],
  },
]

export default function BottomNav() {
  const pathname = usePathname()
  const { usuario, puedeEscribir } = useAuth()
  const [masOpen, setMasOpen] = useState(false)

  if (!usuario) return null
  if (pathname.startsWith('/login') || pathname.startsWith('/auth/')) return null

  const grupos = GRUPOS_MAS.map(group => ({
    ...group,
    items: group.items.filter(item => !item.write || puedeEscribir()),
  })).filter(group => group.items.length > 0)

  return (
    <>
      {masOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setMasOpen(false)}
        />
      )}

      {masOpen && (
        <div
          role="dialog"
          aria-label="Mas opciones"
          className="fixed bottom-0 left-0 right-0 z-50 max-h-[82vh] overflow-y-auto rounded-t-2xl bg-white p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] shadow-2xl md:hidden"
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Mas opciones</h2>
            <button
              type="button"
              onClick={() => setMasOpen(false)}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-600"
              aria-label="Cerrar mas opciones"
            >
              <X size={18} />
            </button>
          </div>

          <div className="space-y-4">
            {grupos.map(group => (
              <section key={group.title}>
                <p className="mb-2 px-1 text-[11px] font-bold uppercase tracking-widest text-slate-400">
                  {group.title}
                </p>
                <div className="grid gap-2">
                  {group.items.map(item => {
                    const Icon = item.icon
                    const active = pathname.startsWith(item.href)
                    return (
                      <Link
                        key={item.href + item.label}
                        href={item.href}
                        onClick={() => setMasOpen(false)}
                        className={clsx(
                          'flex items-center gap-3 rounded-xl border px-3 py-3 text-sm transition',
                          active
                            ? 'border-blue-200 bg-blue-50 text-blue-800'
                            : 'border-slate-200 bg-white text-slate-700',
                        )}
                      >
                        <span className={clsx(
                          'flex h-9 w-9 items-center justify-center rounded-lg',
                          active ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500',
                        )}>
                          <Icon size={18} />
                        </span>
                        <span className="font-medium">{item.label}</span>
                      </Link>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        </div>
      )}

      <nav
        className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-slate-200 md:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="grid h-16 min-w-0 grid-cols-4">
          {ITEMS.map(item => (
            <NavBtn key={item.href} item={item} pathname={pathname} />
          ))}
          <div className="flex min-w-0 items-center justify-center">
            <button
              type="button"
              onClick={() => setMasOpen(open => !open)}
              className={clsx(
                'flex min-w-0 flex-col items-center justify-center gap-1 text-xs transition',
                masOpen ? 'text-blue-700' : 'text-slate-500 hover:text-slate-800',
              )}
              aria-label="Abrir mas opciones"
              aria-expanded={masOpen}
            >
              <MoreHorizontal size={20} />
              <span className={clsx('max-w-full truncate px-0.5 text-[10px] leading-none sm:text-[11px]', masOpen && 'font-semibold')}>
                Mas
              </span>
            </button>
          </div>
        </div>
      </nav>

      <div className="h-16 md:hidden" aria-hidden="true" />
    </>
  )
}

function NavBtn({ item, pathname }: { item: NavItem; pathname: string }) {
  const active = pathname.startsWith(item.href)
  const Icon = item.icon
  return (
    <Link
      href={item.href}
      className={clsx(
        'flex min-w-0 flex-col items-center justify-center gap-1 text-xs transition',
        active ? 'text-blue-700' : 'text-slate-500 hover:text-slate-800',
      )}
    >
      <Icon size={20} />
      <span className={clsx('max-w-full truncate px-0.5 text-[10px] leading-none sm:text-[11px]', active && 'font-semibold')}>
        {item.label}
      </span>
    </Link>
  )
}
