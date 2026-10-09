/** A single headline number. The number *is* the chart — no sparkline, no bar. */

import type { ReactNode } from 'react'

interface Props {
  label: string
  value: string
  hint?: string
  icon?: ReactNode
  /** Draws attention to the figure the pitch rests on. */
  highlight?: boolean
}

export default function KpiCard({ label, value, hint, icon, highlight = false }: Props) {
  return (
    <div
      className={`rounded-2xl border p-4 shadow-sm ${
        highlight
          ? 'border-brand-200 bg-brand-50'
          : 'border-slate-200 bg-white'
      }`}
    >
      <p className="flex items-center gap-1.5 text-sm font-medium text-slate-500">
        {icon}
        {label}
      </p>
      <p
        className={`mt-1 text-3xl font-extrabold tabular-nums ${
          highlight ? 'text-brand-700' : 'text-slate-900'
        }`}
      >
        {value}
      </p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}
