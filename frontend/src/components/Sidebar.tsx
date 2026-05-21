'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import {
  Activity, ArrowDownUp, Bot, Boxes, Building2, Calendar, ChefHat, Clock, Factory, FileText,
  LayoutDashboard, LogOut, Package, Receipt, ScanLine, ShieldCheck, Truck, Users, Wallet,
  ChevronDown, ChevronLeft, ChevronRight, Sparkles, TrendingUp, Wrench,
} from 'lucide-react'
import clsx from 'clsx'
import { empresaApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'

/**
 * Sidebar lateral simplificada (v7.2 — consolidada).
 *
 * 6 grupos top-level + "Mi cuenta" siempre visible:
 *   • Inicio
 *   • Facturas       (ver facturas / clientes / proveedores / OCR / IVA)
 *   • Cobros y pagos (movimientos — la pantalla ya filtra por cobro/pago)
 *   • Inventario     (stock / lotes / recetas / capacidad)
 *   • Reportes       (aging / P&L / forecast / timeline)
 *   • Asistente
 *   • Mi cuenta      (seguridad / actividad) — sin condicional de rol
 *
 * /cuentas/* fue retirado en v7.2 — los contactos viven dentro de Facturas
 * y la ficha individual está en /clientes/[id] y /proveedores/[id].
 */

type NavItem = {
  href: string
  label: string
  icon: any
  write?: boolean
  hint?: string
}

type NavGroup = {
  title: string
  icon: any
  href?: string          // si está, el grupo es clickeable y va a esa ruta
  items?: NavItem[]      // si no hay items, es un link directo (no colapsa)
}

const GROUPS: NavGroup[] = [
  {
    title: 'Inicio',
    icon: LayoutDashboard,
    href: '/dashboard',
  },
  {
    title: 'Facturas',
    icon: FileText,
    href: '/comprobantes',
    items: [
      { href: '/comprobantes', label: 'Ver facturas',      icon: FileText,   hint: 'Listado de ventas y compras' },
      { href: '/clientes',     label: 'Clientes',          icon: Users,      hint: 'A quiénes les vendés' },
      { href: '/proveedores',  label: 'Proveedores',       icon: Truck,      hint: 'A quiénes les comprás' },
      { href: '/ocr',          label: 'Cargar con foto',   icon: ScanLine,   write: true, hint: 'OCR de fotos/PDF' },
      { href: '/reportes/iva', label: 'IVA del mes',       icon: Receipt,    hint: 'Resumen para liquidar' },
    ],
  },
  {
    title: 'Cobros y pagos',
    icon: ArrowDownUp,
    href: '/movimientos',
  },
  {
    title: 'Inventario',
    icon: Package,
    href: '/inventario',
    items: [
      { href: '/inventario',             label: 'Stock',          icon: Package, hint: 'Productos y materia prima' },
      { href: '/inventario/lotes',       label: 'Lotes',          icon: Boxes,   hint: 'Trazabilidad y vencimientos' },
      { href: '/inventario/recetas',     label: 'Recetas',        icon: ChefHat, hint: 'Qué lleva cada producto' },
      { href: '/inventario/produccion',  label: 'Capacidad',      icon: Factory, hint: 'Cuántas unidades podés hacer' },
    ],
  },
  {
    title: 'Reportes',
    icon: TrendingUp,
    items: [
      { href: '/reportes/aging',      label: 'Cobros vencidos',    icon: Clock,       hint: 'Antigüedad de deudas' },
      { href: '/reportes/resultados', label: 'Resultados (P&L)',   icon: TrendingUp,  hint: 'Ganancia del período' },
      { href: '/finanzas/forecast',   label: 'Forecast de caja',   icon: Calendar,    hint: 'Proyección 30/60/90 días' },
      { href: '/timeline',            label: 'Línea de tiempo',    icon: Calendar,    hint: 'Historial cronológico' },
    ],
  },
  {
    title: 'Asistente',
    icon: Bot,
    href: '/asistente',
  },
]

export default function Sidebar() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { usuario, logout, puedeEscribir } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [openGroup, setOpenGroup] = useState<string | null>(null)
  const esAdmin = usuario?.rol === 'admin'

  const { data: empresa } = useQuery<{ nombre?: string; logo_url?: string | null }>({
    queryKey: ['empresa'],
    queryFn: () => empresaApi.obtener().then(r => r.data),
    enabled: !!usuario,
    staleTime: 60_000,
  })

  const visibleParaUsuario = (item: NavItem) => !item.write || puedeEscribir()

  // Una ruta está activa si pathname coincide; considera query params si los hay
  const isActive = (href: string) => {
    const [path, query] = href.split('?')
    if (!pathname.startsWith(path)) return false
    if (!query) return pathname === path || pathname.startsWith(path + '/')
    if (!searchParams) return false
    const targetParams = new URLSearchParams(query)
    for (const [k, v] of targetParams) {
      if (searchParams.get(k) !== v) return false
    }
    return true
  }

  const groupActive = (group: NavGroup) => {
    if (group.href && isActive(group.href)) return true
    if (group.items?.some(i => isActive(i.href))) return true
    return false
  }

  return (
    <aside
      className={clsx(
        'hidden md:flex flex-col bg-gradient-to-b from-slate-900 via-slate-900 to-indigo-950 text-slate-200',
        'sticky top-0 h-screen z-30 transition-all duration-200',
        'border-r border-slate-800',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      {/* ─── Brand ─── */}
      <Link
        href="/dashboard"
        className={clsx(
          'flex items-center gap-2 px-4 py-4 border-b border-slate-800',
          collapsed && 'justify-center px-0',
        )}
      >
        <div className="w-9 h-9 bg-gradient-to-br from-pink-500 to-indigo-500 rounded-xl flex items-center justify-center flex-shrink-0 overflow-hidden">
          {empresa?.logo_url
            ? <img src={empresa.logo_url} alt="Logo" className="w-full h-full object-contain" />
            : <Sparkles size={16} className="text-white" />}
        </div>
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <div className="text-sm font-bold text-white truncate">
              {empresa?.nombre ?? 'Mi Negocio'}
            </div>
            <div className="text-[10px] text-slate-400 uppercase tracking-widest truncate">
              ERP
            </div>
          </div>
        )}
      </Link>

      {/* ─── Navigation ─── */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {GROUPS.map(group => {
          const visibleItems = group.items?.filter(visibleParaUsuario)
          const hasItems = visibleItems && visibleItems.length > 0
          const Icon = group.icon
          const active = groupActive(group)

          // Grupo sin subitems → link directo
          if (!hasItems) {
            return (
              <Link
                key={group.title}
                href={group.href!}
                title={collapsed ? group.title : group.title}
                className={clsx(
                  'flex items-center gap-3 rounded-lg text-sm mb-1 border-l-2 transition-all',
                  collapsed ? 'px-0 py-2 justify-center' : 'px-3 py-2',
                  active
                    ? 'bg-white/10 text-white border-pink-400 font-semibold'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white border-transparent',
                )}
              >
                <Icon size={16} className="flex-shrink-0" />
                {!collapsed && <span className="flex-1 truncate text-left">{group.title}</span>}
              </Link>
            )
          }

          // Grupo con subitems → colapsable
          const expanded = !collapsed && (openGroup === group.title || (!openGroup && active))
          return (
            <div key={group.title} className="mb-1">
              <button
                type="button"
                onClick={() => setOpenGroup(current => current === group.title ? null : group.title)}
                title={collapsed ? group.title : undefined}
                className={clsx(
                  'flex w-full items-center gap-3 rounded-lg text-sm transition-all border-l-2',
                  collapsed ? 'px-0 py-2 justify-center' : 'px-3 py-2',
                  active || expanded
                    ? 'bg-white/10 text-white border-pink-400 font-semibold'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white border-transparent',
                )}
                aria-expanded={expanded}
              >
                <Icon size={16} className="flex-shrink-0" />
                {!collapsed && (
                  <>
                    <span className="flex-1 truncate text-left">{group.title}</span>
                    <ChevronDown size={14} className={clsx('transition-transform', expanded && 'rotate-180')} />
                  </>
                )}
              </button>

              {expanded && (
                <div className="mt-1 space-y-1 pl-3">
                  {visibleItems!.map(item => {
                    const itemActive = isActive(item.href)
                    const ItemIcon = item.icon
                    return (
                      <Link
                        key={item.href + item.label}
                        href={item.href}
                        className={clsx(
                          'flex items-center gap-2 rounded-lg border-l-2 px-3 py-1.5 text-xs transition-all',
                          itemActive
                            ? 'bg-white/10 text-white border-pink-400 font-semibold'
                            : 'text-slate-400 hover:bg-white/5 hover:text-white border-transparent',
                        )}
                      >
                        <ItemIcon size={13} className="flex-shrink-0" />
                        <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      </Link>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}

        {/* Mi cuenta — visible para todos (admin, operador, viewer) */}
        <div className="mt-3 pt-3 border-t border-slate-800">
          {!collapsed && (
            <div className="px-3 pt-1 pb-1 text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
              <Wrench size={10} /> Mi cuenta
            </div>
          )}
          <Link
            href="/perfil/seguridad"
            title={collapsed ? 'Seguridad' : undefined}
            className={clsx(
              'flex items-center gap-3 rounded-lg text-sm transition-all border-l-2',
              collapsed ? 'px-0 py-2 justify-center' : 'px-3 py-2',
              isActive('/perfil/seguridad')
                ? 'bg-white/10 text-white border-emerald-400 font-semibold'
                : 'text-slate-300 hover:bg-white/5 hover:text-white border-transparent',
            )}
          >
            <ShieldCheck size={16} />
            {!collapsed && <span>Seguridad</span>}
          </Link>
          <Link
            href="/actividad"
            title={collapsed ? 'Mi actividad' : undefined}
            className={clsx(
              'flex items-center gap-3 rounded-lg text-sm transition-all border-l-2',
              collapsed ? 'px-0 py-2 justify-center' : 'px-3 py-2',
              isActive('/actividad')
                ? 'bg-white/10 text-white border-emerald-400 font-semibold'
                : 'text-slate-300 hover:bg-white/5 hover:text-white border-transparent',
            )}
          >
            <Activity size={16} />
            {!collapsed && <span>Mi actividad</span>}
          </Link>
        </div>

        {/* Admin section */}
        {esAdmin && (
          <div className="mt-3 pt-3 border-t border-slate-800">
            {!collapsed && (
              <div className="px-3 pt-1 pb-1 text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                <Wrench size={10} /> Administración
              </div>
            )}
            <Link
              href="/admin/empresa"
              title={collapsed ? 'Empresa' : undefined}
              className={clsx(
                'flex items-center gap-3 rounded-lg text-sm transition-all border-l-2',
                collapsed ? 'px-0 py-2 justify-center' : 'px-3 py-2',
                isActive('/admin/empresa')
                  ? 'bg-white/10 text-white border-pink-400 font-semibold'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white border-transparent',
              )}
            >
              <Building2 size={16} />
              {!collapsed && <span>Empresa</span>}
            </Link>
            <Link
              href="/admin/usuarios"
              title={collapsed ? 'Usuarios' : undefined}
              className={clsx(
                'flex items-center gap-3 rounded-lg text-sm transition-all border-l-2',
                collapsed ? 'px-0 py-2 justify-center' : 'px-3 py-2',
                isActive('/admin/usuarios')
                  ? 'bg-white/10 text-white border-pink-400 font-semibold'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white border-transparent',
              )}
            >
              <Users size={16} />
              {!collapsed && <span>Usuarios</span>}
            </Link>
          </div>
        )}
      </nav>

      {/* ─── User card ─── */}
      <div className="p-3 border-t border-slate-800">
        <div className={clsx(
          'flex items-center gap-2 p-2 rounded-lg bg-slate-800/40',
          collapsed && 'justify-center',
        )}>
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-pink-500 to-indigo-500 text-white flex items-center justify-center font-bold text-xs flex-shrink-0">
            {usuario?.nombre?.charAt(0).toUpperCase() ?? 'U'}
          </div>
          {!collapsed && (
            <>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold text-white truncate">
                  {usuario?.nombre ?? '—'}
                </div>
                <div className="text-[10px] text-slate-400 capitalize truncate">
                  {usuario?.rol ?? ''}
                </div>
              </div>
              <button
                onClick={() => logout()}
                className="p-1.5 rounded-md text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                title="Cerrar sesión"
                aria-label="Cerrar sesión"
              >
                <LogOut size={14} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* ─── Collapse toggle ─── */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="absolute -right-3 top-20 w-6 h-6 bg-white border border-slate-200 rounded-full shadow-md flex items-center justify-center text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-colors"
        aria-label={collapsed ? 'Expandir' : 'Colapsar'}
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>
    </aside>
  )
}
