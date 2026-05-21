'use client'

import clsx from 'clsx'

/**
 * Componente Skeleton — placeholder animado para carga de datos.
 *
 * Reemplaza los "Cargando..." de texto plano por una versión visual
 * que da la impresión de que la app es más rápida.
 *
 * Uso:
 *   <Skeleton className="h-4 w-32" />
 *   <SkeletonText lines={3} />
 *   <SkeletonCard />
 *   <SkeletonTable rows={5} cols={4} />
 */

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={clsx(
      'bg-slate-200 rounded-md animate-pulse',
      className,
    )} />
  )
}

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={clsx('h-3', i === lines - 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
    </div>
  )
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={clsx(
      'bg-white rounded-2xl border border-slate-200 p-5 space-y-3',
      className,
    )}>
      <div className="flex items-center gap-3">
        <Skeleton className="w-10 h-10 rounded-xl" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-3 w-1/4" />
        </div>
      </div>
      <SkeletonText lines={3} />
    </div>
  )
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="bg-slate-50 px-4 py-3 grid gap-4 border-b border-slate-200"
        style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-3/4" />
        ))}
      </div>
      <div className="divide-y divide-slate-100">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="px-4 py-3 grid gap-4"
            style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
            {Array.from({ length: cols }).map((__, j) => (
              <Skeleton
                key={j}
                className={clsx('h-3', j === 0 ? 'w-full' : 'w-2/3')}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function SkeletonGrid({ count = 6, columns = 'md:grid-cols-3' }: {
  count?: number
  columns?: string
}) {
  return (
    <div className={clsx('grid grid-cols-2 gap-3', columns)}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <Skeleton className="h-24 rounded-none rounded-t-2xl" />
          <div className="p-3 space-y-2">
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-3 w-1/2" />
            <Skeleton className="h-1.5 w-full" />
            <div className="flex justify-between">
              <Skeleton className="h-3 w-1/3" />
              <Skeleton className="h-3 w-1/4" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
