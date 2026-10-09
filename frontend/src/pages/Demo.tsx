/**
 * The whole story on one screen, for the projector.
 *
 * Left: the basket device in a phone frame. Right: the till. Across the top:
 * live KPIs. Both panes are the real pages in iframes, not mock-ups — what
 * the audience sees is the running system.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart3, Clock, RefreshCw, ScanLine, ShoppingBasket, Wallet } from 'lucide-react'

import { api, ApiError } from '../api'
import { useToast } from '../components/Toast'
import { Logo } from '../components/ui'
import { formatAZN, formatCount } from '../utils/format'
import type { AnalyticsSummary, Cart } from '../types'

const BASKET_ID = 'BSK-001'
const POLL_MS = 2000

export default function Demo() {
  const toast = useToast()
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [cart, setCart] = useState<Cart | null>(null)
  const [busy, setBusy] = useState(false)
  // Bumping this remounts both frames, which is how the "restart" button works.
  const [frameKey, setFrameKey] = useState(0)
  const errorShown = useRef(false)

  const load = useCallback(async () => {
    try {
      const [nextSummary, nextCart] = await Promise.all([
        api.analytics.summary(),
        api.cart(BASKET_ID),
      ])
      setSummary(nextSummary)
      setCart(nextCart)
      errorShown.current = false
    } catch (cause) {
      // One toast, not one every two seconds.
      if (!errorShown.current) {
        errorShown.current = true
        toast.error(cause instanceof ApiError ? cause.message : 'Server əlçatmazdır')
      }
    }
  }, [toast])

  useEffect(() => {
    void load()
    const timer = window.setInterval(load, POLL_MS)
    return () => window.clearInterval(timer)
  }, [load])

  async function restart() {
    setBusy(true)
    try {
      await api.resetDemo()
      await api.simulate(500)
      await load()
      setFrameKey((key) => key + 1)
      toast.success('Demo sıfırlandı', 'Səbət boş, data yenidən yaradıldı')
    } catch (cause) {
      toast.error(cause instanceof ApiError ? cause.message : 'Sıfırlama alınmadı')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-slate-100">
      <header className="flex shrink-0 flex-wrap items-center gap-x-6 gap-y-2 border-b border-slate-200 bg-white px-4 py-2.5">
        <Logo className="text-lg" />

        <dl className="flex flex-1 flex-wrap items-center gap-x-6 gap-y-1">
          <Stat
            icon={<ShoppingBasket className="size-4" aria-hidden />}
            label="Səbət"
            value={cart ? formatAZN(cart.total_qepik) : '—'}
            hint={cart ? `${cart.item_count} məhsul` : ''}
            accent
          />
          <Stat
            icon={<Wallet className="size-4" aria-hidden />}
            label="Dövriyyə (24s)"
            value={summary ? formatAZN(summary.revenue_qepik) : '—'}
          />
          <Stat
            icon={<BarChart3 className="size-4" aria-hidden />}
            label="Sessiyalar"
            value={summary ? formatCount(summary.sessions_total) : '—'}
          />
          <Stat
            icon={<Clock className="size-4" aria-hidden />}
            label="Qənaət"
            value={summary ? `${summary.saved_hours} saat` : '—'}
          />
        </dl>

        <div className="flex items-center gap-2">
          <Link
            to="/admin"
            className="rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Analitika
          </Link>
          <button
            type="button"
            onClick={restart}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
          >
            <RefreshCw className={`size-4 ${busy ? 'animate-spin' : ''}`} aria-hidden />
            Demonu sıfırla
          </button>
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-[minmax(0,420px)_1fr]">
        <Pane
          title="Səbət cihazı"
          subtitle={BASKET_ID}
          icon={<ShoppingBasket className="size-4" aria-hidden />}
        >
          {/* A phone frame, so the audience reads this pane as the basket. */}
          <div className="flex h-full items-center justify-center p-3">
            <div className="h-full max-h-[760px] w-full max-w-[380px] overflow-hidden rounded-[2rem] border-[10px] border-slate-900 bg-white shadow-2xl">
              <iframe
                key={`basket-${frameKey}`}
                src={`/basket/${BASKET_ID}`}
                title="Səbət cihazı"
                className="size-full border-0"
              />
            </div>
          </div>
        </Pane>

        <Pane title="Kassa" subtitle="QR oxu → ödəniş" icon={<ScanLine className="size-4" aria-hidden />}>
          <iframe
            key={`checkout-${frameKey}`}
            src="/checkout"
            title="Kassa"
            className="size-full border-0"
          />
        </Pane>
      </main>
    </div>
  )
}

function Stat({
  icon,
  label,
  value,
  hint,
  accent = false,
}: {
  icon: React.ReactNode
  label: string
  value: string
  hint?: string
  accent?: boolean
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-slate-400">{icon}</span>
      <div>
        <dt className="text-xs font-medium text-slate-500">{label}</dt>
        <dd
          className={`text-lg font-extrabold tabular-nums leading-tight ${
            accent ? 'text-brand-700' : 'text-slate-900'
          }`}
        >
          {value}
          {hint && <span className="ml-1 text-xs font-medium text-slate-500">{hint}</span>}
        </dd>
      </div>
    </div>
  )
}

function Pane({
  title,
  subtitle,
  icon,
  children,
}: {
  title: string
  subtitle: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <section className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex shrink-0 items-center gap-2 border-b border-slate-200 px-4 py-2">
        <span className="text-slate-400">{icon}</span>
        <h2 className="font-bold text-slate-900">{title}</h2>
        <span className="text-sm text-slate-500">{subtitle}</span>
      </header>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  )
}
