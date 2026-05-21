'use client'
import { useParams } from 'next/navigation'
import ContraparteDetail from '@/components/ContraparteDetail'

/**
 * Ficha de detalle de un cliente — reemplaza a `/cuentas/cliente/[id]`.
 * El componente compartido renderiza score, análisis, facturas y cobros.
 */
export default function DetalleClientePage() {
  const { id } = useParams<{ id: string }>()
  if (!id) return null
  return <ContraparteDetail tipo="cliente" id={id} />
}
