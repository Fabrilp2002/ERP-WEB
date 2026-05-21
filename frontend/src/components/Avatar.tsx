'use client'

import { useMemo } from 'react'

/**
 * Avatar de iniciales con color generado determinísticamente a partir del nombre.
 * Sirve para clientes, proveedores, usuarios, etc. cuando no hay foto.
 */

type Props = {
  name: string
  size?: number
  className?: string
}

const GRADIENTS = [
  ['#3b82f6', '#8b5cf6'], // blue → violet
  ['#ec4899', '#f59e0b'], // pink → amber
  ['#10b981', '#14b8a6'], // emerald → teal
  ['#ef4444', '#dc2626'], // red shades
  ['#8b5cf6', '#6366f1'], // violet → indigo
  ['#f59e0b', '#ef4444'], // amber → red
  ['#0ea5e9', '#3b82f6'], // sky → blue
  ['#14b8a6', '#0ea5e9'], // teal → sky
  ['#6366f1', '#a855f7'], // indigo → purple
  ['#84cc16', '#10b981'], // lime → emerald
]

function hashCode(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h)
}

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(w => w.length > 0)
  if (words.length === 0) return '?'
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[1][0]).toUpperCase()
}

export default function Avatar({ name, size = 40, className = '' }: Props) {
  const { gradient, ini } = useMemo(() => {
    const idx = hashCode(name) % GRADIENTS.length
    return {
      gradient: GRADIENTS[idx],
      ini: initials(name),
    }
  }, [name])

  return (
    <div
      className={`flex items-center justify-center text-white font-bold flex-shrink-0 ${className}`}
      style={{
        width: size,
        height: size,
        background: `linear-gradient(135deg, ${gradient[0]} 0%, ${gradient[1]} 100%)`,
        borderRadius: size * 0.25,
        fontSize: size * 0.4,
      }}
    >
      {ini}
    </div>
  )
}
