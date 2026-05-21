'use client'

import Link from 'next/link'
import { ReactNode } from 'react'

/**
 * EmptyState — componente para estados vacíos con guidance accionable.
 *
 * Reemplaza los "Sin items 🤷" genéricos por una invitación clara a la
 * próxima acción que tiene sentido.
 */

type Action = {
  label: string
  href?: string
  onClick?: () => void
  primary?: boolean
}

type Props = {
  emoji?: string
  icon?: ReactNode
  title: string
  description?: string | ReactNode
  actions?: Action[]
  compact?: boolean
  className?: string
}

export default function EmptyState({
  emoji,
  icon,
  title,
  description,
  actions = [],
  compact = false,
  className = '',
}: Props) {
  return (
    <div className={`bg-white rounded-2xl border-2 border-dashed border-slate-200 text-center ${
      compact ? 'py-8 px-4' : 'py-12 px-6'
    } ${className}`}>
      {emoji && (
        <div className={compact ? 'text-3xl mb-2' : 'text-5xl mb-3'}>
          {emoji}
        </div>
      )}
      {icon && !emoji && (
        <div className="text-slate-300 mb-3 flex justify-center">
          {icon}
        </div>
      )}
      <h3 className={`font-semibold text-slate-700 mb-1 ${compact ? 'text-base' : 'text-lg'}`}>
        {title}
      </h3>
      {description && (
        <div className={`text-slate-500 max-w-md mx-auto ${compact ? 'text-xs' : 'text-sm'} mb-4`}>
          {description}
        </div>
      )}
      {actions.length > 0 && (
        <div className="flex flex-wrap gap-2 justify-center mt-4">
          {actions.map((action, i) => {
            const cls = action.primary
              ? 'btn-primary'
              : 'btn-outline'
            if (action.href) {
              return (
                <Link key={i} href={action.href} className={cls}>
                  {action.label}
                </Link>
              )
            }
            return (
              <button key={i} onClick={action.onClick} className={cls}>
                {action.label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
