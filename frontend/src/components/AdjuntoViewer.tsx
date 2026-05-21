'use client'
import { useState } from 'react'
import { Paperclip, FileText, Image as ImageIcon, X, Trash2, Upload, ExternalLink } from 'lucide-react'
import { API_BASE_URL } from '@/lib/config'

interface Props {
  url: string | null | undefined
  label?: string
  onReemplazar?: (f: File) => void | Promise<void>
  onQuitar?: () => void | Promise<void>
  /** Render compacto (icono clip) vs. tarjeta completa con vista previa. */
  compacto?: boolean
}

function esPdf(u: string) {
  return u.toLowerCase().endsWith('.pdf')
}

function fullUrl(u: string, bust = true) {
  const base = u.startsWith('http') ? u : `${API_BASE_URL}${u}`
  return bust ? `${base}?v=${Date.now()}` : base
}

export default function AdjuntoViewer({ url, label, onReemplazar, onQuitar, compacto = false }: Props) {
  const [abierto, setAbierto] = useState(false)
  const [busy, setBusy] = useState(false)

  if (!url) {
    // Modo "sin adjunto": solo icono grisáceo si compacto
    if (compacto) {
      return <span className="inline-flex items-center justify-center w-7 h-7 text-slate-300" title="Sin adjunto">
        <Paperclip size={14} />
      </span>
    }
    return null
  }

  const pdf = esPdf(url)

  const handleReemplazar = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f || !onReemplazar) return
    setBusy(true)
    try { await onReemplazar(f) } finally { setBusy(false); e.target.value = '' }
  }

  const handleQuitar = async () => {
    if (!onQuitar) return
    if (!confirm('¿Quitar este archivo adjunto?')) return
    setBusy(true)
    try { await onQuitar(); setAbierto(false) } finally { setBusy(false) }
  }

  // ── Trigger ──
  const trigger = compacto ? (
    <button
      type="button"
      className="inline-flex items-center justify-center w-7 h-7 rounded text-emerald-700 hover:bg-emerald-50 transition"
      onClick={() => setAbierto(true)}
      title={label || (pdf ? 'Ver PDF' : 'Ver imagen')}
    >
      <Paperclip size={14} />
    </button>
  ) : (
    <button
      type="button"
      onClick={() => setAbierto(true)}
      className="group relative flex items-center gap-2 p-2 border border-slate-200 rounded-lg hover:border-emerald-400 hover:bg-emerald-50 transition text-left w-full"
    >
      {pdf ? (
        <div className="w-10 h-10 rounded bg-red-100 flex items-center justify-center text-red-600">
          <FileText size={20} />
        </div>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={fullUrl(url, false)} alt="adj" className="w-10 h-10 object-cover rounded border border-slate-200" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-slate-700 truncate">{label || (pdf ? 'Documento PDF' : 'Imagen adjunta')}</p>
        <p className="text-[10px] text-slate-400">Click para ver</p>
      </div>
      <ExternalLink size={14} className="text-slate-400 group-hover:text-emerald-600" />
    </button>
  )

  return (
    <>
      {trigger}

      {abierto && (
        <div
          className="fixed inset-0 z-[60] bg-black/75 flex items-center justify-center p-4"
          onClick={() => setAbierto(false)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-slate-200 bg-slate-50">
              <div className="flex items-center gap-2 min-w-0">
                {pdf ? <FileText size={16} className="text-red-600" /> : <ImageIcon size={16} className="text-emerald-600" />}
                <span className="text-sm font-semibold text-slate-700 truncate">{label || (pdf ? 'Ver PDF' : 'Ver imagen')}</span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={fullUrl(url, false)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-200 hover:bg-white"
                  title="Abrir en nueva pestaña"
                >
                  <ExternalLink size={12} /> Abrir
                </a>
                {onReemplazar && (
                  <label className={`text-xs inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-200 hover:bg-white cursor-pointer ${busy ? 'opacity-50 pointer-events-none' : ''}`}>
                    <Upload size={12} /> Reemplazar
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp,application/pdf"
                      className="hidden"
                      onChange={handleReemplazar}
                    />
                  </label>
                )}
                {onQuitar && (
                  <button
                    onClick={handleQuitar}
                    disabled={busy}
                    className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50"
                  >
                    <Trash2 size={12} /> Quitar
                  </button>
                )}
                <button
                  onClick={() => setAbierto(false)}
                  className="p-1 rounded hover:bg-slate-200"
                  title="Cerrar (Esc)"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Contenido */}
            <div className="flex-1 overflow-auto bg-slate-900 flex items-center justify-center">
              {pdf ? (
                <iframe
                  src={fullUrl(url)}
                  className="w-full h-[85vh] bg-white"
                  title="PDF"
                />
              ) : (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={fullUrl(url)}
                  alt="adjunto"
                  className="max-w-full max-h-[85vh] object-contain"
                />
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
