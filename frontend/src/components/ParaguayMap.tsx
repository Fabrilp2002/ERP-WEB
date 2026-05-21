'use client'

import { useMemo, useState } from 'react'

/**
 * Mapa interactivo de Paraguay con marcadores por ciudad.
 *
 * Recibe una lista de entidades (clientes o proveedores) cada una con
 * una dirección/ciudad opcional. Geo-codifica esa dirección usando un
 * diccionario interno de ciudades conocidas y dibuja un marcador.
 *
 * El tamaño del marcador refleja la cantidad de entidades en esa ciudad.
 * El color refleja el "estado de salud" (saldo, pagos, etc.).
 */

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

// Coordenadas SVG (viewBox 400x440) de ciudades y barrios conocidos.
// Posiciones aproximadas dentro del SVG simplificado.
const CITY_COORDS: Record<string, { x: number; y: number }> = {
  // Asunción y barrios
  'asuncion':            { x: 145, y: 250 },
  'asunción':            { x: 145, y: 250 },
  'españa':              { x: 142, y: 248 },
  'espana':              { x: 142, y: 248 },
  'los laureles':        { x: 148, y: 246 },
  'molas lopez':         { x: 144, y: 252 },
  'molas lópez':         { x: 144, y: 252 },
  'perseverancia':       { x: 138, y: 252 },
  'sausalito':           { x: 144, y: 245 },
  'villa morra':         { x: 152, y: 248 },
  'carmelitas':          { x: 145, y: 244 },
  'recoleta':            { x: 148, y: 254 },
  'trinidad':            { x: 150, y: 244 },
  // Departamento Central
  'fernando de la mora': { x: 156, y: 252 },
  'lambare':             { x: 148, y: 258 },
  'lambaré':             { x: 148, y: 258 },
  'san lorenzo':         { x: 162, y: 248 },
  'luque':               { x: 158, y: 240 },
  'capiata':             { x: 168, y: 252 },
  'capiatá':             { x: 168, y: 252 },
  'mariano roque alonso':{ x: 152, y: 238 },
  'ñemby':               { x: 152, y: 262 },
  'nemby':               { x: 152, y: 262 },
  'itagua':              { x: 178, y: 255 },
  'itauguá':             { x: 178, y: 255 },
  'villa elisa':         { x: 144, y: 266 },
  'limpio':              { x: 148, y: 232 },
  'central':             { x: 155, y: 255 },
  'ciudad del este':     { x: 320, y: 235 },
  'cde':                 { x: 320, y: 235 },
  'alto parana':         { x: 320, y: 235 },
  'alto paraná':         { x: 320, y: 235 },
  'presidente franco':   { x: 322, y: 240 },
  'encarnacion':         { x: 230, y: 365 },
  'encarnación':         { x: 230, y: 365 },
  'itapua':              { x: 230, y: 365 },
  'itapúa':              { x: 230, y: 365 },
  'pedro juan caballero':{ x: 295, y: 95 },
  'amambay':             { x: 295, y: 95 },
  'pjc':                 { x: 295, y: 95 },
  'concepcion':          { x: 220, y: 110 },
  'concepción':          { x: 220, y: 110 },
  'caacupe':             { x: 195, y: 240 },
  'caacupé':             { x: 195, y: 240 },
  'cordillera':          { x: 200, y: 235 },
  'villarrica':          { x: 230, y: 290 },
  'guaira':              { x: 230, y: 290 },
  'guairá':              { x: 230, y: 290 },
  'caaguazu':            { x: 250, y: 245 },
  'caaguazú':            { x: 250, y: 245 },
  'coronel oviedo':      { x: 245, y: 248 },
  'paraguari':           { x: 178, y: 285 },
  'paraguarí':           { x: 178, y: 285 },
  'san pedro':           { x: 200, y: 175 },
  'san juan bautista':   { x: 168, y: 320 },
  'misiones':            { x: 168, y: 320 },
  'pilar':               { x: 105, y: 350 },
  'ñeembucu':            { x: 105, y: 350 },
  'ñeembucú':            { x: 105, y: 350 },
  'caazapa':             { x: 215, y: 310 },
  'caazapá':             { x: 215, y: 310 },
  'salto del guaira':    { x: 320, y: 175 },
  'canindeyu':           { x: 295, y: 165 },
  'canindeyú':           { x: 295, y: 165 },
  'mariscal estigarribia':{ x: 100, y: 150 },
  'boqueron':            { x: 100, y: 150 },
  'boquerón':            { x: 100, y: 150 },
  'filadelfia':          { x: 130, y: 165 },
  'loma plata':          { x: 135, y: 170 },
  'villa hayes':         { x: 130, y: 240 },
  'presidente hayes':    { x: 110, y: 215 },
  'fuerte olimpo':       { x: 200, y: 75 },
  'alto paraguay':       { x: 180, y: 80 },
}

/**
 * Trata de inferir la ciudad de un texto libre (dirección).
 * Busca substring matching contra el diccionario.
 */
function geocode(input?: string | null): { x: number; y: number; city: string } | null {
  if (!input) return null
  const normalized = input.toLowerCase().trim()
  // Direct match
  if (CITY_COORDS[normalized]) {
    return { ...CITY_COORDS[normalized], city: normalized }
  }
  // Substring match (longest first to avoid "san" matching "san lorenzo" too early)
  const keys = Object.keys(CITY_COORDS).sort((a, b) => b.length - a.length)
  for (const k of keys) {
    if (normalized.includes(k)) return { ...CITY_COORDS[k], city: k }
  }
  return null
}

const STATUS_COLOR: Record<NonNullable<MapEntity['status']>, string> = {
  good: '#10b981',
  warn: '#f59e0b',
  bad:  '#ef4444',
}

function titleCase(s: string) {
  return s.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

export default function ParaguayMap({
  entities,
  onSelectCity,
  selectedCity,
  height = 460,
  title,
}: Props) {
  const [hoveredCity, setHoveredCity] = useState<string | null>(null)

  // Agrupar entidades por ciudad geo-codificada
  const clusters = useMemo(() => {
    const map: Record<string, {
      x: number; y: number; entities: MapEntity[]; totalSaldo: number; worstStatus: 'good' | 'warn' | 'bad'
    }> = {}
    let unlocated = 0

    for (const e of entities) {
      // Intentar geo-codificar primero por ciudad explícita, luego dirección,
      // y finalmente por el nombre (muchas empresas paraguayas incluyen
      // la sucursal/ciudad en el nombre: "CASA RICA - ESPAÑA").
      const coord = geocode(e.ciudad) || geocode(e.direccion) || geocode(e.nombre)
      if (!coord) { unlocated++; continue }
      const key = coord.city
      if (!map[key]) {
        map[key] = { x: coord.x, y: coord.y, entities: [], totalSaldo: 0, worstStatus: 'good' }
      }
      map[key].entities.push(e)
      map[key].totalSaldo += e.saldo ?? 0
      // worst status wins
      if (e.status === 'bad') map[key].worstStatus = 'bad'
      else if (e.status === 'warn' && map[key].worstStatus !== 'bad') map[key].worstStatus = 'warn'
    }
    return { clusters: map, unlocated }
  }, [entities])

  const totalEntities = entities.length
  const locatedEntities = totalEntities - clusters.unlocated

  const fmt = (n: number) =>
    n.toLocaleString('es-PY', { maximumFractionDigits: 0 })

  const handleClick = (city: string) => {
    if (onSelectCity) onSelectCity(selectedCity === city ? null : city)
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
      <div className="flex items-baseline justify-between mb-1">
        <h4 className="text-sm font-bold text-slate-800">
          {title ?? 'Mapa de Paraguay'}
        </h4>
        <span className="text-[10px] text-slate-500">
          {locatedEntities}/{totalEntities} ubicados
        </span>
      </div>
      {clusters.unlocated > 0 && (
        <p className="text-[10px] text-amber-600 mb-2">
          ⚠ {clusters.unlocated} sin dirección o ciudad reconocible
        </p>
      )}

      <div
        className="relative rounded-xl overflow-hidden"
        style={{
          background: 'linear-gradient(180deg, #f0f9ff 0%, #e0f2fe 100%)',
          height,
        }}
      >
        <svg viewBox="0 0 400 440" className="w-full h-full">
          {/* Departments — simplified shapes */}
          <g fill="#cbd5e1" stroke="#fff" strokeWidth="1">
            {/* Chaco Boquerón (Northwest, large) */}
            <path d="M 30 50 L 200 40 L 220 180 L 100 240 L 20 200 Z" />
            {/* Concepción/San Pedro */}
            <path d="M 200 40 L 320 60 L 320 200 L 220 180 Z" />
            {/* Amambay band */}
            <path d="M 240 40 L 320 40 L 320 100 L 260 100 Z" fill="#a5b4fc" />
            {/* Canindeyú */}
            <path d="M 290 130 L 340 130 L 340 200 L 290 200 Z" />
            {/* Central — Asunción */}
            <path d="M 100 240 L 220 180 L 240 270 L 130 300 Z" fill="#c7d2fe" />
            {/* Caaguazú */}
            <path d="M 220 180 L 320 200 L 280 280 L 240 270 Z" />
            {/* Alto Paraná */}
            <path d="M 320 200 L 340 200 L 340 280 L 280 280 Z" fill="#a5b4fc" />
            {/* Guairá / Caazapá / Paraguarí */}
            <path d="M 130 300 L 240 270 L 280 280 L 290 340 L 160 360 Z" />
            {/* Itapúa */}
            <path d="M 160 360 L 290 340 L 290 400 L 200 410 Z" fill="#a5b4fc" />
            {/* Misiones / Ñeembucú */}
            <path d="M 100 290 L 160 360 L 200 410 L 90 410 L 80 350 Z" />
          </g>

          {/* Department labels */}
          <g fill="#475569" fontSize="9" fontWeight="600" textAnchor="middle" pointerEvents="none">
            <text x="110" y="140">CHACO</text>
            <text x="265" y="135">CONCEPCIÓN</text>
            <text x="280" y="170">SAN PEDRO</text>
            <text x="295" y="75" fill="#3730a3">AMAMBAY</text>
            <text x="315" y="165">CANINDEYÚ</text>
            <text x="170" y="245" fill="#3730a3">CENTRAL</text>
            <text x="265" y="245">CAAGUAZÚ</text>
            <text x="310" y="245" fill="#3730a3">A. PARANÁ</text>
            <text x="200" y="335">GUAIRÁ</text>
            <text x="235" y="385" fill="#3730a3">ITAPÚA</text>
            <text x="140" y="385">MISIONES</text>
          </g>

          {/* Markers per cluster */}
          {Object.entries(clusters.clusters).map(([city, c]) => {
            const baseRadius = Math.min(15, 6 + Math.log(1 + c.entities.length) * 3)
            const isSelected = selectedCity === city
            const isHovered = hoveredCity === city
            const r = isSelected || isHovered ? baseRadius + 2 : baseRadius
            const color = STATUS_COLOR[c.worstStatus]
            return (
              <g
                key={city}
                style={{ cursor: 'pointer' }}
                onClick={() => handleClick(city)}
                onMouseEnter={() => setHoveredCity(city)}
                onMouseLeave={() => setHoveredCity(null)}
              >
                {/* Halo on hover/select */}
                {(isSelected || isHovered) && (
                  <circle cx={c.x} cy={c.y} r={r + 6} fill={color} opacity="0.2" />
                )}
                <circle
                  cx={c.x} cy={c.y} r={r}
                  fill={color}
                  stroke="white"
                  strokeWidth={isSelected ? 3 : 2}
                  className="transition-all"
                />
                {c.entities.length > 1 && (
                  <text
                    x={c.x} y={c.y + 4}
                    fill="white"
                    fontSize={r > 10 ? '11' : '9'}
                    fontWeight="700"
                    textAnchor="middle"
                    pointerEvents="none"
                  >
                    {c.entities.length}
                  </text>
                )}
                <text
                  x={c.x} y={c.y - r - 4}
                  fill="#1e293b"
                  fontSize="9"
                  fontWeight="600"
                  textAnchor="middle"
                  pointerEvents="none"
                  style={{ textShadow: '0 0 3px white, 0 0 3px white' }}
                >
                  {titleCase(city)}
                </text>
              </g>
            )
          })}

          {/* Tooltip on hover */}
          {hoveredCity && clusters.clusters[hoveredCity] && (() => {
            const c = clusters.clusters[hoveredCity]
            const tooltipX = c.x > 250 ? c.x - 130 : c.x + 18
            const tooltipY = c.y - 10
            return (
              <g pointerEvents="none">
                <rect
                  x={tooltipX} y={tooltipY}
                  width={125} height={42}
                  rx={6}
                  fill="#0f172a"
                  opacity="0.95"
                />
                <text x={tooltipX + 8} y={tooltipY + 16} fill="white" fontSize="10" fontWeight="700">
                  {titleCase(hoveredCity)}
                </text>
                <text x={tooltipX + 8} y={tooltipY + 30} fill="#cbd5e1" fontSize="9">
                  {c.entities.length} {c.entities.length === 1 ? 'registro' : 'registros'}
                  {c.totalSaldo > 0 && ` · Gs. ${fmt(c.totalSaldo / 1_000_000)}M`}
                </text>
              </g>
            )
          })()}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 mt-3 text-[11px] text-slate-600">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-emerald-500" />
          <span>Al día</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-amber-500" />
          <span>Atención</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-rose-500" />
          <span>Vencido</span>
        </div>
        <div className="ml-auto text-slate-400">
          💡 Click en un marcador para filtrar
        </div>
      </div>
    </div>
  )
}
