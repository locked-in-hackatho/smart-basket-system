/**
 * Stands in for the scanner built into the basket.
 *
 * On a real basket a reader detects every product as it goes in or comes out
 * — the shopper touches nothing. We have no hardware here, so this panel
 * fakes those detections. It is deliberately marked as a demo control and
 * kept apart from the rest of the screen, so nobody mistakes it for
 * something the customer is meant to use.
 */

import { useState } from 'react'
import { ChevronDown, Minus, Plus, Wrench } from 'lucide-react'

import BarcodeScanner from './BarcodeScanner'
import type { ScanMode } from '../types'

export default function ScannerSimulator({
  onDetect,
  disabled = false,
}: {
  onDetect: (barcode: string, mode: ScanMode) => void
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<ScanMode>('add')

  return (
    <section className="rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-3 text-left"
      >
        <Wrench className="size-4 shrink-0 text-slate-500" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
              Demo
            </span>
            <span className="font-semibold text-slate-700">Səbətin skaneri</span>
          </span>
          <span className="mt-0.5 block text-xs text-slate-500">
            Real səbətdə bu avtomatikdir — məhsul qoyulan kimi oxunur
          </span>
        </span>
        <ChevronDown
          className={`size-5 shrink-0 text-slate-400 transition ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>

      {open && (
        <div className="border-t border-dashed border-slate-300 p-3">
          <p className="mb-2 text-xs text-slate-500">
            Bizdə hardware olmadığı üçün skaneri burada əl ilə simulyasiya edirik.
            Müştəri bu paneli görmür.
          </p>

          <div className="mb-3 grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setMode('add')}
              aria-pressed={mode === 'add'}
              className={`flex min-h-12 items-center justify-center gap-2 rounded-xl font-semibold transition ${
                mode === 'add'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'border border-slate-300 bg-white text-slate-500'
              }`}
            >
              <Plus className="size-4" aria-hidden />
              Səbətə qoyulur
            </button>
            <button
              type="button"
              onClick={() => setMode('remove')}
              aria-pressed={mode === 'remove'}
              className={`flex min-h-12 items-center justify-center gap-2 rounded-xl font-semibold transition ${
                mode === 'remove'
                  ? 'bg-red-600 text-white shadow-sm'
                  : 'border border-slate-300 bg-white text-slate-500'
              }`}
            >
              <Minus className="size-4" aria-hidden />
              Səbətdən götürülür
            </button>
          </div>

          <BarcodeScanner
            onScan={(barcode) => onDetect(barcode, mode)}
            disabled={disabled}
          />
        </div>
      )}
    </section>
  )
}
