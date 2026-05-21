'use client'

import { useMemo, useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

/**
 * Mapa interno (cliente-side) con Leaflet.
 * Renderiza un mapa real de OpenStreetMap centrado en Paraguay con
 * marcadores en ciudades/barrios donde Esplendida tiene clientes.
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

// ─── COORDENADAS REALES (lat, lng) DE CIUDADES Y BARRIOS PARAGUAYOS ──────────
const CITY_COORDS: Record<string, { lat: number; lng: number; depto?: string }> = {
  // ─── Asunción y barrios ───
  'asuncion':            { lat: -25.2637, lng: -57.5759, depto: 'Capital' },
  'asunción':            { lat: -25.2637, lng: -57.5759, depto: 'Capital' },
  'centro':              { lat: -25.2820, lng: -57.6358, depto: 'Capital' },
  'villa morra':         { lat: -25.2891, lng: -57.5775, depto: 'Capital' },
  'recoleta':            { lat: -25.2876, lng: -57.5829, depto: 'Capital' },
  'carmelitas':          { lat: -25.2745, lng: -57.5727, depto: 'Capital' },
  'mariscal lopez':      { lat: -25.2856, lng: -57.5709, depto: 'Capital' },
  'molas lopez':         { lat: -25.2780, lng: -57.5891, depto: 'Capital' },
  'molas lópez':         { lat: -25.2780, lng: -57.5891, depto: 'Capital' },
  'españa':              { lat: -25.2856, lng: -57.5891, depto: 'Capital' },
  'espana':              { lat: -25.2856, lng: -57.5891, depto: 'Capital' },
  'sajonia':             { lat: -25.3040, lng: -57.5905, depto: 'Capital' },
  'los laureles':        { lat: -25.2912, lng: -57.6020, depto: 'Capital' },
  'perseverancia':       { lat: -25.2731, lng: -57.5664, depto: 'Capital' },
  'sausalito':           { lat: -25.3014, lng: -57.5530, depto: 'Capital' },
  'trinidad':            { lat: -25.2519, lng: -57.5650, depto: 'Capital' },
  'fernando de la mora': { lat: -25.3199, lng: -57.5419, depto: 'Central' },
  'lambare':             { lat: -25.3433, lng: -57.6042, depto: 'Central' },
  'lambaré':             { lat: -25.3433, lng: -57.6042, depto: 'Central' },
  'san lorenzo':         { lat: -25.3431, lng: -57.5089, depto: 'Central' },
  'luque':               { lat: -25.2667, lng: -57.4833, depto: 'Central' },
  'capiata':             { lat: -25.3553, lng: -57.4458, depto: 'Central' },
  'capiatá':             { lat: -25.3553, lng: -57.4458, depto: 'Central' },
  'mariano roque alonso':{ lat: -25.2089, lng: -57.5347, depto: 'Central' },
  'ñemby':               { lat: -25.3961, lng: -57.5283, depto: 'Central' },
  'nemby':               { lat: -25.3961, lng: -57.5283, depto: 'Central' },
  'itagua':              { lat: -25.4108, lng: -57.3500, depto: 'Central' },
  'itauguá':             { lat: -25.4108, lng: -57.3500, depto: 'Central' },
  'villa elisa':         { lat: -25.3614, lng: -57.5947, depto: 'Central' },
  'limpio':              { lat: -25.1697, lng: -57.4933, depto: 'Central' },
  'aregua':              { lat: -25.3050, lng: -57.3942, depto: 'Central' },
  'areguá':              { lat: -25.3050, lng: -57.3942, depto: 'Central' },
  'ypacarai':            { lat: -25.4044, lng: -57.2917, depto: 'Central' },
  'ypacaraí':            { lat: -25.4044, lng: -57.2917, depto: 'Central' },
  'ypane':               { lat: -25.4406, lng: -57.5267, depto: 'Central' },
  'ypané':               { lat: -25.4406, lng: -57.5267, depto: 'Central' },
  'guarambare':          { lat: -25.4894, lng: -57.4500, depto: 'Central' },
  'guarambaré':          { lat: -25.4894, lng: -57.4500, depto: 'Central' },
  'san antonio':         { lat: -25.4039, lng: -57.5867, depto: 'Central' },
  'central':             { lat: -25.3500, lng: -57.5000, depto: 'Central' },

  // ─── Departamentos del este ───
  'ciudad del este':     { lat: -25.5152, lng: -54.6116, depto: 'Alto Paraná' },
  'cde':                 { lat: -25.5152, lng: -54.6116, depto: 'Alto Paraná' },
  'alto parana':         { lat: -25.5152, lng: -54.6116, depto: 'Alto Paraná' },
  'alto paraná':         { lat: -25.5152, lng: -54.6116, depto: 'Alto Paraná' },
  'presidente franco':   { lat: -25.5586, lng: -54.6111, depto: 'Alto Paraná' },
  'minga guazu':         { lat: -25.4769, lng: -54.8167, depto: 'Alto Paraná' },
  'minga guazú':         { lat: -25.4769, lng: -54.8167, depto: 'Alto Paraná' },
  'hernandarias':        { lat: -25.4119, lng: -54.6386, depto: 'Alto Paraná' },

  // ─── Sur ───
  'encarnacion':         { lat: -27.3306, lng: -55.8665, depto: 'Itapúa' },
  'encarnación':         { lat: -27.3306, lng: -55.8665, depto: 'Itapúa' },
  'itapua':              { lat: -27.3306, lng: -55.8665, depto: 'Itapúa' },
  'itapúa':              { lat: -27.3306, lng: -55.8665, depto: 'Itapúa' },

  // ─── Norte ───
  'pedro juan caballero':{ lat: -22.5475, lng: -55.7290, depto: 'Amambay' },
  'pjc':                 { lat: -22.5475, lng: -55.7290, depto: 'Amambay' },
  'amambay':             { lat: -22.5475, lng: -55.7290, depto: 'Amambay' },
  'concepcion':          { lat: -23.4064, lng: -57.4344, depto: 'Concepción' },
  'concepción':          { lat: -23.4064, lng: -57.4344, depto: 'Concepción' },

  // ─── Otros departamentos ───
  'caacupe':             { lat: -25.3858, lng: -57.1419, depto: 'Cordillera' },
  'caacupé':             { lat: -25.3858, lng: -57.1419, depto: 'Cordillera' },
  'cordillera':          { lat: -25.3858, lng: -57.1419, depto: 'Cordillera' },
  'villarrica':          { lat: -25.7806, lng: -56.4444, depto: 'Guairá' },
  'guaira':              { lat: -25.7806, lng: -56.4444, depto: 'Guairá' },
  'guairá':              { lat: -25.7806, lng: -56.4444, depto: 'Guairá' },
  'caaguazu':            { lat: -25.4646, lng: -56.0151, depto: 'Caaguazú' },
  'caaguazú':            { lat: -25.4646, lng: -56.0151, depto: 'Caaguazú' },
  'coronel oviedo':      { lat: -25.4439, lng: -56.4400, depto: 'Caaguazú' },
  'san pedro':           { lat: -24.0813, lng: -57.0856, depto: 'San Pedro' },
  'san juan bautista':   { lat: -26.6694, lng: -57.1453, depto: 'Misiones' },
  'misiones':            { lat: -26.6694, lng: -57.1453, depto: 'Misiones' },
  'pilar':               { lat: -26.8567, lng: -58.2933, depto: 'Ñeembucú' },
  'ñeembucu':            { lat: -26.8567, lng: -58.2933, depto: 'Ñeembucú' },
  'ñeembucú':            { lat: -26.8567, lng: -58.2933, depto: 'Ñeembucú' },
  'paraguari':           { lat: -25.6228, lng: -57.1456, depto: 'Paraguarí' },
  'paraguarí':           { lat: -25.6228, lng: -57.1456, depto: 'Paraguarí' },
  'caazapa':             { lat: -26.1923, lng: -56.3681, depto: 'Caazapá' },
  'caazapá':             { lat: -26.1923, lng: -56.3681, depto: 'Caazapá' },
  'salto del guaira':    { lat: -24.0598, lng: -54.3014, depto: 'Canindeyú' },
  'canindeyu':           { lat: -24.0598, lng: -54.3014, depto: 'Canindeyú' },
  'canindeyú':           { lat: -24.0598, lng: -54.3014, depto: 'Canindeyú' },

  // ─── Chaco ───
  'mariscal estigarribia':{ lat: -22.0286, lng: -60.6147, depto: 'Boquerón' },
  'boqueron':            { lat: -22.0286, lng: -60.6147, depto: 'Boquerón' },
  'boquerón':            { lat: -22.0286, lng: -60.6147, depto: 'Boquerón' },
  'filadelfia':          { lat: -22.3528, lng: -60.0357, depto: 'Boquerón' },
  'loma plata':          { lat: -22.3736, lng: -59.8408, depto: 'Boquerón' },
  'villa hayes':         { lat: -25.0962, lng: -57.5232, depto: 'Presidente Hayes' },
  'presidente hayes':    { lat: -25.0962, lng: -57.5232, depto: 'Presidente Hayes' },
  'fuerte olimpo':       { lat: -21.0411, lng: -57.8736, depto: 'Alto Paraguay' },
  'alto paraguay':       { lat: -21.0411, lng: -57.8736, depto: 'Alto Paraguay' },
}

function geocode(input?: string | null): { lat: number; lng: number; city: string; depto?: string } | null {
  if (!input) return null
  const normalized = input.toLowerCase().trim()
  if (CITY_COORDS[normalized]) return { ...CITY_COORDS[normalized], city: normalized }
  // Substring match (más largo primero para evitar matches falsos)
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

function fmt(n: number) {
  return Math.round(n).toLocaleString('es-PY')
}

function fmtM(n: number) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K'
  return Math.round(n).toString()
}


export default function ParaguayMapInner({
  entities,
  onSelectCity,
  selectedCity,
  height = 460,
  title,
}: Props) {
  // Agrupar entidades por ciudad
  const clusters = useMemo(() => {
    const map: Record<string, {
      lat: number; lng: number; depto?: string;
      entities: MapEntity[]; totalSaldo: number;
      worstStatus: 'good' | 'warn' | 'bad'
    }> = {}
    let unlocated = 0

    for (const e of entities) {
      const coord = geocode(e.ciudad) || geocode(e.direccion) || geocode(e.nombre)
      if (!coord) { unlocated++; continue }
      const key = coord.city
      if (!map[key]) {
        map[key] = { lat: coord.lat, lng: coord.lng, depto: coord.depto, entities: [], totalSaldo: 0, worstStatus: 'good' }
      }
      map[key].entities.push(e)
      map[key].totalSaldo += e.saldo ?? 0
      if (e.status === 'bad') map[key].worstStatus = 'bad'
      else if (e.status === 'warn' && map[key].worstStatus !== 'bad') map[key].worstStatus = 'warn'
    }
    return { clusters: map, unlocated }
  }, [entities])

  const totalEntities = entities.length
  const locatedEntities = totalEntities - clusters.unlocated

  // Centro de Paraguay
  const CENTER: [number, number] = [-23.5, -58.0]
  const ZOOM = 6

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
      <div className="flex items-baseline justify-between mb-1">
        <h4 className="text-sm font-bold text-slate-800">
          {title ?? '🗺️ Mapa de Paraguay'}
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

      <div className="relative rounded-xl overflow-hidden border border-slate-200" style={{ height }}>
        <MapContainer
          center={CENTER}
          zoom={ZOOM}
          minZoom={5}
          maxZoom={18}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {Object.entries(clusters.clusters).map(([city, c]) => {
            const baseRadius = Math.min(20, 8 + Math.log(1 + c.entities.length) * 4)
            const isSelected = selectedCity === city
            const color = STATUS_COLOR[c.worstStatus]
            return (
              <CircleMarker
                key={city}
                center={[c.lat, c.lng]}
                radius={isSelected ? baseRadius + 4 : baseRadius}
                pathOptions={{
                  fillColor: color,
                  color: 'white',
                  weight: isSelected ? 3 : 2,
                  fillOpacity: 0.9,
                }}
                eventHandlers={{
                  click: () => onSelectCity?.(selectedCity === city ? null : city),
                }}
              >
                <Tooltip direction="top" offset={[0, -baseRadius]}>
                  <div style={{ fontSize: 12 }}>
                    <strong>{titleCase(city)}</strong>
                    {c.depto && <span style={{ color: '#64748b' }}> · {c.depto}</span>}
                    <br/>
                    <span>{c.entities.length} {c.entities.length === 1 ? 'registro' : 'registros'}</span>
                    {c.totalSaldo > 0 && <><br/><span>Gs. {fmt(c.totalSaldo)}</span></>}
                  </div>
                </Tooltip>
                <Popup>
                  <div style={{ minWidth: 200 }}>
                    <strong style={{ fontSize: 13, color: '#1e293b' }}>{titleCase(city)}</strong>
                    {c.depto && <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{c.depto}</div>}
                    <hr style={{ margin: '6px 0', border: 'none', borderTop: '1px solid #e2e8f0' }} />
                    <div style={{ fontSize: 12, color: '#475569', marginBottom: 4 }}>
                      <strong>{c.entities.length}</strong> {c.entities.length === 1 ? 'registro' : 'registros'}
                      {c.totalSaldo > 0 && <> · Gs. {fmt(c.totalSaldo)}</>}
                    </div>
                    <ul style={{ margin: 0, padding: 0, listStyle: 'none', fontSize: 11, maxHeight: 120, overflowY: 'auto' }}>
                      {c.entities.slice(0, 8).map(e => (
                        <li key={e.id} style={{ padding: '3px 0', borderBottom: '1px dashed #f1f5f9' }}>
                          <span style={{ color: '#0f172a' }}>{e.nombre}</span>
                          {e.saldo && e.saldo > 0 && (
                            <span style={{ float: 'right', color: STATUS_COLOR[e.status || 'good'] }}>
                              Gs. {fmtM(e.saldo)}
                            </span>
                          )}
                        </li>
                      ))}
                      {c.entities.length > 8 && (
                        <li style={{ color: '#94a3b8', textAlign: 'center', padding: '4px 0' }}>
                          + {c.entities.length - 8} más
                        </li>
                      )}
                    </ul>
                    <button
                      onClick={() => onSelectCity?.(selectedCity === city ? null : city)}
                      style={{
                        marginTop: 8,
                        width: '100%',
                        padding: '4px 8px',
                        background: '#6366f1',
                        color: 'white',
                        border: 'none',
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      {selectedCity === city ? 'Quitar filtro' : 'Filtrar por esta ciudad'}
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>
      </div>

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
          <span>Saldo alto</span>
        </div>
        <div className="ml-auto text-slate-400">
          💡 Click en un marcador para ver detalles
        </div>
      </div>
    </div>
  )
}
