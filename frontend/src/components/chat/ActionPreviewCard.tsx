'use client'

import { useState } from 'react'
import { AlertTriangle, CheckCircle2, Clock, Loader2, ShieldCheck, XCircle } from 'lucide-react'
import clsx from 'clsx'
import { chatApi } from '@/lib/api'

export type ChatAccion = {
  funcion: string
  argumentos: Record<string, unknown>
  resultado: Record<string, unknown>
}

export type ConfirmarAccionResponse = {
  ok: boolean
  accion: string
  resultado: Record<string, unknown>
  mensaje: string
}

type Props = {
  accion: ChatAccion
  onConfirmada?: (data: ConfirmarAccionResponse) => void
  compact?: boolean
}

function asString(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function asNumber(value: unknown) {
  if (typeof value === 'number') return value
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function formatGs(value: unknown) {
  const number = asNumber(value)
  if (number === null) return ''
  return `G. ${new Intl.NumberFormat('es-PY', { maximumFractionDigits: 0 }).format(number)}`
}

function getErrorMessage(error: unknown) {
  if (typeof error === 'object' && error && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response
    if (typeof response?.data?.detail === 'string') return response.data.detail
  }
  return 'No se pudo confirmar la accion. Revisa el estado y vuelve a intentar.'
}

export function isActionPreview(accion: ChatAccion) {
  return accion.resultado?.requiere_confirmacion === true && Boolean(accion.resultado?.action_token)
}

export default function ActionPreviewCard({ accion, onConfirmada, compact = false }: Props) {
  const resultado = accion.resultado ?? {}
  const [confirmando, setConfirmando] = useState(false)
  const [cancelada, setCancelada] = useState(false)
  const [confirmada, setConfirmada] = useState<ConfirmarAccionResponse | null>(null)
  const [error, setError] = useState('')

  const token = asString(resultado.action_token)
  const monto = formatGs(resultado.monto ?? resultado.monto_pagado)
  const confirmadoMonto = formatGs(confirmada?.resultado?.monto)
  const tipo = asString(resultado.tipo) || (accion.funcion === 'registrar_cobro' ? 'cobro' : 'pago')
  const titulo = tipo === 'cobro' ? 'Cobro pendiente de confirmacion' : 'Pago pendiente de confirmacion'

  async function confirmar() {
    if (!token || confirmando || confirmada || cancelada) return
    setConfirmando(true)
    setError('')
    try {
      const { data } = await chatApi.confirmarAccion(token)
      setConfirmada(data)
      onConfirmada?.(data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setConfirmando(false)
    }
  }

  if (confirmada?.ok) {
    return (
      <div className={clsx(
        'rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-950',
        compact && 'p-2.5'
      )}>
        <div className="flex items-start gap-2">
          <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-600" />
          <div className="min-w-0 flex-1">
            <p className="font-semibold">Accion ejecutada</p>
            <p className="mt-1 text-emerald-800">
              {confirmada.resultado?.factura_numero ? `Factura ${confirmada.resultado.factura_numero}` : confirmada.mensaje}
              {confirmada.resultado?.contraparte ? ` - ${confirmada.resultado.contraparte}` : ''}
              {confirmadoMonto ? ` - ${confirmadoMonto}` : ''}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (cancelada) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
        <div className="flex items-center gap-2">
          <XCircle className="h-4 w-4 text-slate-500" />
          <span>Accion cancelada. No se registraron movimientos.</span>
        </div>
      </div>
    )
  }

  return (
    <div className={clsx(
      'rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950 shadow-sm',
      compact && 'p-2.5'
    )}>
      <div className="flex items-start gap-2">
        <ShieldCheck className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{titulo}</p>
          <p className="mt-1 text-amber-800">
            {asString(resultado.resumen) || asString(resultado.mensaje) || 'Revise el preview antes de ejecutar.'}
          </p>

          <div className="mt-2 grid gap-1 text-xs text-amber-900">
            {resultado.factura_numero ? <span>Factura: {String(resultado.factura_numero)}</span> : null}
            {resultado.contraparte ? <span>Contraparte: {String(resultado.contraparte)}</span> : null}
            {monto ? <span>Monto: {monto}</span> : null}
            {resultado.medio_pago ? <span>Medio: {String(resultado.medio_pago)}</span> : null}
            {resultado.impacto ? <span>Impacto: {String(resultado.impacto)}</span> : null}
            {resultado.expires_at ? (
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                Vence: {String(resultado.expires_at)}
              </span>
            ) : null}
          </div>

          {error ? (
            <div className="mt-2 flex items-start gap-1.5 rounded-lg bg-white/70 px-2 py-1.5 text-xs text-red-700">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}

          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={confirmar}
              disabled={confirmando}
              className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {confirmando ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
              Confirmar
            </button>
            <button
              type="button"
              onClick={() => setCancelada(true)}
              disabled={confirmando}
              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white/70 px-3 py-1.5 text-xs font-semibold text-amber-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              <XCircle className="h-3.5 w-3.5" />
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
