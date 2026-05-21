'use client'
import { useParams } from 'next/navigation'
import ContraparteDetail from '@/components/ContraparteDetail'

/**
 * Ficha de detalle de un proveedor — reemplaza a `/cuentas/proveedor/[id]`.
 */
export default function DetalleProveedorPage() {
  const { id } = useParams<{ id: string }>()
  if (!id) return null
  return <ContraparteDetail tipo="proveedor" id={id} />
}
