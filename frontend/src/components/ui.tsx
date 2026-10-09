/** Small shared pieces: page frame, status chip, loading and empty states. */

import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Loader2, ShoppingBasket } from 'lucide-react'

import { BASKET_STATUS_LABEL } from '../utils/format'
import type { BasketStatus } from '../types'

export function Logo({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-extrabold ${className}`}>
      <ShoppingBasket className="size-6 text-brand-600" aria-hidden />
      <span>
        Smart<span className="text-brand-600">Basket</span>
      </span>
    </span>
  )
}

interface PageProps {
  title: string
  subtitle?: string
  /** Shown on the right of the header (actions, status chips). */
  actions?: ReactNode
  /** Hide the "back to home" link on screens meant to run full-screen. */
  back?: boolean
  wide?: boolean
  children: ReactNode
}

export function Page({
  title,
  subtitle,
  actions,
  back = true,
  wide = false,
  children,
}: PageProps) {
  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div
          className={`mx-auto flex items-center gap-3 px-4 py-3 ${wide ? 'max-w-7xl' : 'max-w-5xl'}`}
        >
          {back && (
            <Link
              to="/"
              aria-label="Ana səhifə"
              className="no-print flex size-11 shrink-0 items-center justify-center rounded-xl text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
            >
              <ArrowLeft className="size-5" aria-hidden />
            </Link>
          )}
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-bold text-slate-900">{title}</h1>
            {subtitle && <p className="truncate text-sm text-slate-500">{subtitle}</p>}
          </div>
          {actions}
        </div>
      </header>
      <main className={`mx-auto px-4 py-5 ${wide ? 'max-w-7xl' : 'max-w-5xl'}`}>
        {children}
      </main>
    </div>
  )
}

const STATUS_STYLES: Record<BasketStatus, string> = {
  idle: 'bg-slate-100 text-slate-600 ring-slate-200',
  active: 'bg-brand-50 text-brand-700 ring-brand-200',
  checkout: 'bg-amber-50 text-amber-700 ring-amber-200',
}

export function StatusChip({ status }: { status: BasketStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ${STATUS_STYLES[status]}`}
    >
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {BASKET_STATUS_LABEL[status] ?? status}
    </span>
  )
}

export function Spinner({ label = 'Yüklənir…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
      <Loader2 className="size-6 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  )
}

export function ErrorNote({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-red-800"
    >
      <span className="font-medium">{message}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
        >
          Yenidən cəhd et
        </button>
      )}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  hint,
}: {
  icon: ReactNode
  title: string
  hint?: string
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
      <div className="flex size-20 items-center justify-center rounded-3xl bg-brand-50 text-brand-600">
        {icon}
      </div>
      <p className="text-lg font-semibold text-slate-800">{title}</p>
      {hint && <p className="max-w-sm text-slate-500">{hint}</p>}
    </div>
  )
}

export function Card({
  className = '',
  children,
}: {
  className?: string
  children: ReactNode
}) {
  return (
    <section
      className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}
    >
      {children}
    </section>
  )
}
