'use client'
import clsx from 'clsx'

export function passwordChecks(password: string) {
  return [
    { ok: password.length >= 8, label: '8+ caracteres' },
    { ok: /[A-ZÁÉÍÓÚÑ]/.test(password), label: 'Mayúscula' },
    { ok: /[a-záéíóúñ]/.test(password), label: 'Minúscula' },
    { ok: /\d/.test(password), label: 'Número' },
    { ok: /[^A-Za-z0-9ÁÉÍÓÚÑáéíóúñ]/.test(password), label: 'Símbolo' },
  ]
}

export function isStrongPassword(password: string) {
  return passwordChecks(password).every(c => c.ok)
}

export function passwordErrorMessage(password: string) {
  const missing = passwordChecks(password).filter(c => !c.ok).map(c => c.label.toLowerCase())
  return missing.length ? `La contraseña debe incluir: ${missing.join(', ')}.` : ''
}

export default function PasswordStrength({ password }: { password: string }) {
  const checks = passwordChecks(password)
  const score = checks.filter(c => c.ok).length
  const pct = (score / checks.length) * 100
  const meta = score <= 2
    ? { label: 'Débil', bar: 'bg-red-500', text: 'text-red-700' }
    : score <= 4
      ? { label: 'Media', bar: 'bg-amber-500', text: 'text-amber-700' }
      : { label: 'Fuerte', bar: 'bg-emerald-600', text: 'text-emerald-700' }

  if (!password) {
    return <p className="mt-1.5 text-xs text-slate-500">Usá 8+ caracteres con mayúscula, minúscula, número y símbolo.</p>
  }

  return (
    <div className="mt-2 space-y-2">
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={clsx('h-full transition-all', meta.bar)} style={{ width: `${pct}%` }} />
      </div>
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className={clsx('font-semibold', meta.text)}>{meta.label}</span>
        <span className="text-slate-500">{score}/{checks.length} reglas</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {checks.map(c => (
          <span key={c.label} className={clsx(
            'rounded-full px-2 py-0.5 text-[11px] font-medium',
            c.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
          )}>
            {c.ok ? '✓' : '○'} {c.label}
          </span>
        ))}
      </div>
    </div>
  )
}
