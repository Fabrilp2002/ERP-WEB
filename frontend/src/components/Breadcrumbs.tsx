'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight, Home } from 'lucide-react'

/**
 * Breadcrumbs automáticos basados en pathname.
 * Convierte /comprobantes/123/detalle → Inicio › Facturas › 123 › Detalle
 */

const LABELS: Record<string, string> = {
  dashboard: 'Inicio',
  comprobantes: 'Facturas',
  clientes: 'Clientes',
  proveedores: 'Proveedores',
  inventario: 'Inventario',
  movimientos: 'Cobros y pagos',
  cuentas: 'Cuentas bancarias',
  reportes: 'Reportes',
  iva: 'Resumen IVA',
  ocr: 'Foto OCR',
  asistente: 'Asistente IA',
  actividad: 'Actividad',
  admin: 'Administración',
  empresa: 'Empresa',
  usuarios: 'Usuarios',
  perfil: 'Perfil',
  seguridad: 'Mi seguridad',
}

export default function Breadcrumbs() {
  const pathname = usePathname()
  if (!pathname || pathname === '/dashboard' || pathname === '/') return null

  const segments = pathname.split('/').filter(Boolean)

  // Build crumb list
  const crumbs = segments.map((seg, i) => {
    const href = '/' + segments.slice(0, i + 1).join('/')
    const label = LABELS[seg] ?? prettify(seg)
    return { href, label, isLast: i === segments.length - 1 }
  })

  return (
    <nav className="flex items-center gap-1.5 text-xs text-slate-500 mb-3" aria-label="Breadcrumb">
      <Link href="/dashboard" className="hover:text-blue-600 transition-colors flex items-center gap-1">
        <Home size={12} />
        <span>Inicio</span>
      </Link>
      {crumbs.map((c, i) => (
        <span key={c.href} className="flex items-center gap-1.5">
          <ChevronRight size={11} className="text-slate-300" />
          {c.isLast ? (
            <span className="font-semibold text-slate-700">{c.label}</span>
          ) : (
            <Link href={c.href} className="hover:text-blue-600 transition-colors">
              {c.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  )
}

function prettify(seg: string) {
  // If it's a UUID-like string, show "Detalle"
  if (/^[0-9a-f]{8}-/i.test(seg)) return 'Detalle'
  // If it's a number, show as is
  if (/^\d+$/.test(seg)) return seg
  // Otherwise capitalize first letter
  return seg.charAt(0).toUpperCase() + seg.slice(1).replace(/-/g, ' ')
}
