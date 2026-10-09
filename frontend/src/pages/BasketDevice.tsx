/**
 * The screen mounted on the basket. Everything the shopper touches.
 *
 * The backend owns the total; this screen polls every 2s so that a payment
 * taken at the till shows up here without any message passing.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Loader2, Minus, Plus, QrCode, ShoppingBasket } from 'lucide-react'

import { api, ApiError } from '../api'
import BarcodeScanner from '../components/BarcodeScanner'
import CartList from '../components/CartList'
import QrModal from '../components/QrModal'
import { useToast } from '../components/Toast'
import { Card, EmptyState, ErrorNote, Page, Spinner, StatusChip } from '../components/ui'
import { beepError, beepPaid, beepRemove, beepSuccess } from '../utils/feedback'
import { formatAZN } from '../utils/format'
import type { Cart, ScanMode } from '../types'

const POLL_MS = 2000
const THANK_YOU_MS = 4000

export default function BasketDevice() {
  const { basketId = 'BSK-001' } = useParams()
  const toast = useToast()

  const [cart, setCart] = useState<Cart | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<ScanMode>('add')
  const [busy, setBusy] = useState(false)
  const [showQr, setShowQr] = useState(false)
  const [paidTotal, setPaidTotal] = useState<number | null>(null)

  // Remembered across polls so a payment elsewhere can be detected here.
  const sessionRef = useRef<number | null>(null)
  const totalRef = useRef(0)

  /** Apply a cart from any source and notice when the session just ended. */
  const applyCart = useCallback(
    (next: Cart) => {
      const previousSession = sessionRef.current
      const previousTotal = totalRef.current

      if (
        previousSession !== null &&
        next.session_id !== previousSession &&
        next.status === 'idle'
      ) {
        // The till took payment: celebrate with the total as it was.
        setPaidTotal(previousTotal)
        beepPaid()
        window.setTimeout(() => setPaidTotal(null), THANK_YOU_MS)
      }

      sessionRef.current = next.session_id
      totalRef.current = next.total_qepik
      setCart(next)
      setError(null)
    },
    [],
  )

  const load = useCallback(() => {
    api
      .cart(basketId)
      .then(applyCart)
      .catch((cause: ApiError) => setError(cause.message))
  }, [basketId, applyCart])

  // Reset remembered state when switching baskets.
  useEffect(() => {
    sessionRef.current = null
    totalRef.current = 0
    setCart(null)
    setPaidTotal(null)
    setMode('add')
    load()
  }, [basketId, load])

  useEffect(() => {
    const timer = window.setInterval(load, POLL_MS)
    return () => window.clearInterval(timer)
  }, [load])

  async function runCartAction(action: () => Promise<Cart>, onOk: (next: Cart) => void) {
    setBusy(true)
    try {
      const next = await action()
      applyCart(next)
      onOk(next)
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message : 'Xəta baş verdi'
      beepError()
      toast.error(message)
    } finally {
      setBusy(false)
    }
  }

  const handleScan = (barcode: string) =>
    runCartAction(
      () => api.scan(basketId, barcode, mode),
      (next) => {
        const product = next.scanned_product
        if (!product) return
        if (mode === 'add') {
          beepSuccess()
          toast.success(
            `${product.emoji} ${product.name} əlavə olundu`,
            `+${formatAZN(product.price_qepik)} · Yekun ${formatAZN(next.total_qepik)}`,
          )
        } else {
          beepRemove()
          toast.info(
            `${product.emoji} ${product.name} çıxarıldı`,
            `−${formatAZN(product.price_qepik)} · Yekun ${formatAZN(next.total_qepik)}`,
          )
        }
      },
    )

  const changeQty = (itemId: number, qty: number) =>
    runCartAction(
      () => api.setItemQty(basketId, itemId, qty),
      () => (qty <= 0 ? beepRemove() : beepSuccess()),
    )

  const removeItem = (itemId: number) =>
    runCartAction(
      () => api.removeItem(basketId, itemId),
      () => {
        beepRemove()
        toast.info('Məhsul səbətdən silindi')
      },
    )

  // --- Full-screen states ------------------------------------------------

  if (paidTotal !== null) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center gap-4 bg-brand-600 p-8 text-center text-white">
        <p className="text-7xl" aria-hidden>
          🎉
        </p>
        <h1 className="text-4xl font-extrabold">Təşəkkür edirik!</h1>
        <p className="text-xl opacity-90">Ödəniş qəbul olundu</p>
        <p className="text-5xl font-extrabold tabular-nums">{formatAZN(paidTotal)}</p>
        <p className="mt-2 rounded-full bg-white/15 px-4 py-2 font-semibold">
          Səbət sıfırlandı · {basketId}
        </p>
      </div>
    )
  }

  if (cart?.status === 'checkout') {
    return (
      <div className="flex min-h-full flex-col items-center justify-center gap-5 bg-slate-900 p-8 text-center text-white">
        <Loader2 className="size-14 animate-spin text-amber-400" aria-hidden />
        <h1 className="text-3xl font-extrabold">Kassada ödəniş gözlənilir…</h1>
        <p className="text-6xl font-extrabold tabular-nums text-amber-400">
          {formatAZN(cart.total_qepik)}
        </p>
        <p className="text-lg opacity-80">
          {cart.item_count} məhsul · {basketId}
        </p>
        <p className="max-w-sm text-sm opacity-60">
          Bu səbət kassada açıqdır. Ödəniş bitənə qədər skan mümkün deyil.
        </p>
      </div>
    )
  }

  if (error && !cart) {
    return (
      <Page title={basketId} subtitle="Səbət cihazı">
        <ErrorNote message={error} onRetry={load} />
      </Page>
    )
  }
  if (!cart) {
    return (
      <Page title={basketId} subtitle="Səbət cihazı">
        <Spinner />
      </Page>
    )
  }

  // --- Normal shopping ----------------------------------------------------

  return (
    <Page
      title={cart.basket_id}
      subtitle={cart.current_zone ? cart.current_zone.name : 'Səbət cihazı'}
      actions={<StatusChip status={cart.status} />}
    >
      {error && (
        <div className="mb-3">
          <ErrorNote message={error} onRetry={load} />
        </div>
      )}

      <Card className="relative overflow-hidden text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Yekun məbləğ
        </p>
        <p className="mt-1 text-6xl font-extrabold tabular-nums leading-none text-brand-700">
          {formatAZN(cart.total_qepik)}
        </p>
        <p className="mt-2 text-slate-500">{cart.item_count} məhsul</p>
        <button
          type="button"
          onClick={() => setShowQr(true)}
          className="mt-4 inline-flex min-h-12 items-center gap-2 rounded-xl bg-slate-900 px-5 font-semibold text-white transition hover:bg-slate-700"
        >
          <QrCode className="size-5" aria-hidden />
          QR kodu göstər
        </button>
      </Card>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => setMode('add')}
          aria-pressed={mode === 'add'}
          className={`flex min-h-14 items-center justify-center gap-2 rounded-2xl text-lg font-bold transition ${
            mode === 'add'
              ? 'bg-brand-600 text-white shadow-md'
              : 'border border-slate-200 bg-white text-slate-500'
          }`}
        >
          <Plus className="size-5" aria-hidden />
          Əlavə et
        </button>
        <button
          type="button"
          onClick={() => setMode('remove')}
          aria-pressed={mode === 'remove'}
          className={`flex min-h-14 items-center justify-center gap-2 rounded-2xl text-lg font-bold transition ${
            mode === 'remove'
              ? 'bg-red-600 text-white shadow-md'
              : 'border border-slate-200 bg-white text-slate-500'
          }`}
        >
          <Minus className="size-5" aria-hidden />
          Çıxart
        </button>
      </div>

      <div className="mt-3">
        <BarcodeScanner onScan={handleScan} disabled={busy} />
      </div>

      <div className="mt-4">
        {cart.items.length === 0 ? (
          <EmptyState
            icon={<ShoppingBasket className="size-9" aria-hidden />}
            title="Məhsulu skan edərək alış-verişə başlayın"
            hint="Barkodu kamera ilə oxudun, skanerdən keçirin və ya “Demo məhsullar” siyahısından seçin."
          />
        ) : (
          <CartList
            items={cart.items}
            onChangeQty={changeQty}
            onRemove={removeItem}
            disabled={busy}
          />
        )}
      </div>

      {showQr && <QrModal basketId={cart.basket_id} onClose={() => setShowQr(false)} />}
    </Page>
  )
}
