/**
 * The till. The cashier reads one QR code and the whole basket is priced.
 *
 * The screen has exactly two states: waiting for a basket, and showing one.
 * The total is rendered huge so it is readable from the customer's side.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Banknote, CreditCard, ScanLine, Timer, X } from 'lucide-react'

import { api, ApiError } from '../api'
import BarcodeScanner from '../components/BarcodeScanner'
import CartList from '../components/CartList'
import Receipt from '../components/Receipt'
import { useToast } from '../components/Toast'
import { Card, ErrorNote, Page } from '../components/ui'
import { NEXT_CUSTOMER_MS, traditionalCheckoutSeconds } from '../constants'
import { beepError, beepPaid, beepSuccess } from '../utils/feedback'
import { formatAZN, formatSeconds } from '../utils/format'
import type { BasketSummary, Cart, PaymentMethod, Receipt as ReceiptData } from '../types'

export default function CheckoutPage() {
  const toast = useToast()
  const [cart, setCart] = useState<Cart | null>(null)
  const [receipt, setReceipt] = useState<ReceiptData | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [baskets, setBaskets] = useState<BasketSummary[]>([])

  /** When the cashier scanned, so the saving can be shown live. */
  const scannedAtRef = useRef<number>(0)
  const [elapsed, setElapsed] = useState(0)

  // Fallback basket picker: only baskets that actually have something in them.
  const loadBaskets = useCallback(() => {
    api
      .baskets()
      .then((all) => setBaskets(all.filter((basket) => basket.item_count > 0)))
      .catch(() => setBaskets([]))
  }, [])

  useEffect(() => {
    if (cart || receipt) return
    loadBaskets()
    const timer = window.setInterval(loadBaskets, 2000)
    return () => window.clearInterval(timer)
  }, [cart, receipt, loadBaskets])

  // Live stopwatch while a basket is open at the till.
  useEffect(() => {
    if (!cart) return
    const timer = window.setInterval(() => {
      setElapsed((Date.now() - scannedAtRef.current) / 1000)
    }, 200)
    return () => window.clearInterval(timer)
  }, [cart])

  async function lookup(qrPayload: string) {
    if (busy || cart) return
    setBusy(true)
    setError(null)
    try {
      const found = await api.lookup(qrPayload)
      scannedAtRef.current = Date.now()
      setElapsed(0)
      setCart(found)
      beepSuccess()
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message : 'Xəta baş verdi'
      beepError()
      setError(message)
      toast.error(message)
    } finally {
      setBusy(false)
    }
  }

  async function takePayment(method: PaymentMethod) {
    if (!cart?.session_id || busy) return
    setBusy(true)
    try {
      const paid = await api.pay(cart.session_id, method)
      beepPaid()
      setReceipt(paid)
      setCart(null)
      toast.success(
        `Ödəniş qəbul olundu · ${formatAZN(paid.amount_qepik)}`,
        `${paid.basket_id} sıfırlandı`,
      )
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message : 'Xəta baş verdi'
      beepError()
      toast.error(message)
    } finally {
      setBusy(false)
    }
  }

  async function cancel() {
    if (!cart?.session_id || busy) return
    setBusy(true)
    try {
      await api.cancelCheckout(cart.session_id)
      setCart(null)
      toast.info('Ləğv edildi — səbət mağazaya qaytarıldı')
    } catch (cause) {
      toast.error(cause instanceof ApiError ? cause.message : 'Xəta baş verdi')
    } finally {
      setBusy(false)
    }
  }

  // The receipt clears itself so the next customer finds the till ready.
  useEffect(() => {
    if (!receipt) return
    const timer = window.setTimeout(() => setReceipt(null), NEXT_CUSTOMER_MS)
    return () => window.clearTimeout(timer)
  }, [receipt])

  // --- Waiting for a basket ----------------------------------------------

  if (!cart) {
    return (
      <Page title="Kassa" subtitle="Səbətin QR kodunu oxudun">
        {error && (
          <div className="mb-3">
            <ErrorNote message={error} />
          </div>
        )}

        <Card className="text-center">
          <ScanLine className="mx-auto size-12 text-brand-600" aria-hidden />
          <p className="mt-2 text-xl font-bold">Səbətin QR kodunu oxudun</p>
          <p className="text-slate-500">
            Kamera, əl skaneri və ya aşağıdakı siyahıdan seçim
          </p>
        </Card>

        <div className="mt-3">
          <BarcodeScanner onScan={lookup} showProducts={false} qrOnly disabled={busy} />
        </div>

        <Card className="mt-3">
          <p className="font-semibold text-slate-700">Aktiv səbətlər</p>
          {baskets.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">
              Hazırda dolu səbət yoxdur. Səbət cihazından məhsul skan edin.
            </p>
          ) : (
            <ul className="mt-2 grid gap-2 sm:grid-cols-2">
              {baskets.map((basket) => (
                <li key={basket.id}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => lookup(basket.id)}
                    className="flex min-h-14 w-full items-center gap-3 rounded-xl border border-slate-200 px-4 text-left transition hover:border-brand-400 hover:bg-brand-50 disabled:opacity-40"
                  >
                    <span className="font-mono font-bold">{basket.id}</span>
                    <span className="text-sm text-slate-500">
                      {basket.item_count} məhsul
                    </span>
                    <span className="ml-auto font-bold tabular-nums">
                      {formatAZN(basket.total_qepik)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {receipt && <Receipt receipt={receipt} onClose={() => setReceipt(null)} />}
      </Page>
    )
  }

  // --- A basket is open at the till --------------------------------------

  const traditional = traditionalCheckoutSeconds(cart.item_count)

  return (
    <Page title="Kassa" subtitle={`${cart.basket_id} · ${cart.item_count} məhsul`} wide>
      {/* Not <Card>: it sets bg-white, and Tailwind resolves conflicting
          utilities by stylesheet order, so the dark background would lose. */}
      <section className="rounded-2xl bg-slate-900 p-5 text-center text-white shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-widest text-slate-400">
          Ödəniləcək məbləğ
        </p>
        <p className="mt-1 text-7xl font-extrabold tabular-nums leading-none sm:text-8xl">
          {formatAZN(cart.total_qepik)}
        </p>
        <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-sm">
          <Timer className="size-4" aria-hidden />
          {formatSeconds(elapsed)} · ənənəvi kassada ~{formatSeconds(traditional)}
        </p>
      </section>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_20rem]">
        <div>
          <p className="mb-2 font-semibold text-slate-700">Səbətin tərkibi</p>
          <CartList items={cart.items} readOnly />
        </div>

        <div className="grid gap-2 lg:content-start">
          <button
            type="button"
            disabled={busy}
            onClick={() => takePayment('cash')}
            className="flex min-h-20 items-center justify-center gap-3 rounded-2xl bg-brand-600 text-2xl font-bold text-white shadow-md transition hover:bg-brand-700 disabled:opacity-50"
          >
            <Banknote className="size-7" aria-hidden />
            Nağd
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => takePayment('card')}
            className="flex min-h-20 items-center justify-center gap-3 rounded-2xl bg-sky-600 text-2xl font-bold text-white shadow-md transition hover:bg-sky-700 disabled:opacity-50"
          >
            <CreditCard className="size-7" aria-hidden />
            Kart
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={cancel}
            className="flex min-h-14 items-center justify-center gap-2 rounded-2xl border border-slate-300 font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
          >
            <X className="size-5" aria-hidden />
            Ləğv et
          </button>
          <p className="px-1 text-xs text-slate-400">
            Ləğv ediləndə səbət mağazaya qaytarılır və müştəri skan etməyə davam edə
            bilər.
          </p>
        </div>
      </div>

      {receipt && <Receipt receipt={receipt} onClose={() => setReceipt(null)} />}
    </Page>
  )
}
