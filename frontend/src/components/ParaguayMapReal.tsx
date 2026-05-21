'use client'

import { useMemo, useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import 'leaflet/dist/leaflet.css'

/**
 * Mapa REAL de Paraguay basado en Leaflet + OpenStreetMap.
 *
 * Reemplaza al SVG simplificado anterior. Usa coordenadas geográficas
 * reales (lat/lng) y geocoding contra un diccionario de ciudades y
 * barrios paraguayos conocidos. Si una entidad no tiene ubicación
 * reconocible, no aparece en el mapa (pero se cuenta en "sin ubicar").
 *
 * Mapa interactivo:
 *   - zoom in/out
 *   - drag para mover
 *   - markers clickeables (filtra la lista)
 *   - tooltip al hover
 *   - clusters cuando hay muchos clientes en una misma ciudad
 */

// Cargar el mapa solo del lado cliente (Leaflet no funciona en SSR)
const ParaguayMapInner = dynamic(() => import('./ParaguayMapInner'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[450px] bg-slate-50 rounded-xl flex items-center justify-center">
      <div className="text-center">
        <div className="text-3xl mb-2">🗺️</div>
        <div className="text-sm text-slate-500">Cargando mapa...</div>
      </div>
    </div>
  ),
})

export type MapEntity = {
  id: string
  nombre: string
  ciudad?: string | null
  direccion?: string | null
  saldo?: number
  status?: 'good' | 'warn' | 'bad'
}

type Props = {
  entities: MapEntity[]
  onSelectCity?: (ciudad: string | null) => void
  selectedCity?: string | null
  height?: number
  title?: string
}

export default function ParaguayMapReal(props: Props) {
  return <ParaguayMapInner {...props} />
}
