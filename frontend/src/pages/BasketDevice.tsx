/**
 * The screen mounted on the basket. Everything the shopper touches.
 *
 * The backend owns the total; this screen polls every 2s so that a payment
 * taken at the till shows up here without any message passing.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ListChecks, Loader2, Map, QrCode, Search, ShoppingBasket, Sparkles } from 'lucide-react'

import { api, ApiError } from '../api'
import ScannerSimulator from '../components/ScannerSimulator'
import CartList from '../components/CartList'
import QrModal from '../components/QrModal'
import ProductFinder from '../components/ProductFinder'
import StoreMap from '../components/StoreMap'
import { useToast } from '../components/Toast'
import { Card, EmptyState, ErrorNote, Page, Spinner, StatusChip } from '../components/ui'
import { beepError, beepPaid, beepRemove, beepSuccess } from '../utils/feedback'
import { formatAZN } from '../utils/format'
import type { Cart, FoundProduct, ScanMode, StoreMapData } from '../types'

const POLL_MS = 2000
const THANK_YOU_MS = 4000

export default function BasketDevice() {
  const { basketId = 'BSK-001' } = useParams()
  const toast = useToast()

  const [cart, setCart] = useState<Cart | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [showQr, setShowQr] = useState(false)
  const [paidTotal, setPaidTotal] = useState<number | null>(null)
  const [tab, setTab] = useState<'shop' | 'map'>('shop')
  const [showFinder, setShowFinder] = useState(false)
  const [target, setTarget] = useState<FoundProduct | null>(null)
  const [map, setMap] = useState<StoreMapData | null>(null)

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
    setTab('shop')
    setShowFinder(false)
    setTarget(null)
    load()
  }, [basketId, load])

  useEffect(() => {
    const timer = window.setInterval(load, POLL_MS)
    return () => window.clearInterval(timer)
  }, [load])

  useEffect(() => {
    api
      .map()
      .then(setMap)
      .catch(() => setMap(null))
  }, [])

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

  /** The basket's scanner reported a product going in or coming out. */
  const handleDetection = (barcode: string, mode: ScanMode) =>
    runCartAction(
      () => api.scan(basketId, barcode, mode),
      (next) => {
        const product = next.scanned_product
        if (!product) return

        if (target && product.id === target.id) {
          toast.success('✅ Tapdınız!', `${target.name} səbətə əlavə olundu`)
          setTarget(null)
          setShowFinder(false)
        }

        if (mode === 'add') {
          beepSuccess()
          toast.success(
            `${product.emoji} ${product.name} səbətə qoyuldu`,
            `+${formatAZN(product.price_qepik)} · Yekun ${formatAZN(next.total_qepik)}`,
          )
        } else {
          beepRemove()
          toast.info(
            `${product.emoji} ${product.name} səbətdən götürüldü`,
            `−${formatAZN(product.price_qepik)} · Yekun ${formatAZN(next.total_qepik)}`,
          )
        }
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
          Bu səbət kassada açıqdır. Ödəniş bitənə qədər səbətə məhsul qoymaq mümkün deyil.
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

      <div className="mt-3 flex gap-1 rounded-xl bg-slate-100 p-1">
        {(
          [
            ['shop', 'Səbət', ListChecks],
            ['map', 'Xəritə', Map],
          ] as const
        ).map(([id, label, Icon]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            aria-pressed={tab === id}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2.5 font-semibold transition ${
              tab === id
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Icon className="size-4" aria-hidden />
            {label}
          </button>
        ))}
      </div>

      {tab === 'shop' ? (
        <>
          <div className="mt-4">
            {cart.items.length === 0 ? (
              <EmptyState
                icon={<ShoppingBasket className="size-9" aria-hidden />}
                title="Məhsulu səbətə qoyun"
                hint="Səbətin skaneri hər məhsulu avtomatik oxuyur — siz heç nə etməli deyilsiniz."
              />
            ) : (
              <>
                <p className="mb-2 flex items-center gap-1.5 text-sm text-slate-500">
                  <Sparkles className="size-4 text-brand-600" aria-hidden />
                  Səbətin skaneri bu məhsulları oxudu
                </p>
                <CartList items={cart.items} readOnly />
              </>
            )}
          </div>

          <div className="mt-4">
            <ScannerSimulator onDetect={handleDetection} disabled={busy} />
          </div>
        </>
      ) : (
        <div className="mt-3">
          <StoreMap
            map={map}
            position={cart.position}
            onCellClick={moveTo}
          />
          <p className="mt-2 text-center text-sm text-slate-500">
            {cart.current_zone
              ? `Hazırda: ${cart.current_zone.name}`
              : 'Zona hələ müəyyən edilməyib'}
          </p>
          <p className="mt-1 text-center text-xs text-slate-400">
            Keçid xanasına toxunaraq yerinizi dəyişə bilərsiniz. Real versiyada bu,
            BLE mayakları ilə avtomatik baş verir.
          </p>
        </div>
      )}

      {/* Floating finder button: reachable from anywhere on the screen. */}
      <button
        type="button"
        onClick={() => setShowFinder(true)}
        className="fixed bottom-5 right-4 z-40 flex min-h-14 items-center gap-2 rounded-full bg-slate-900 px-5 font-bold text-white shadow-xl transition hover:bg-slate-700"
      >
        <Search className="size-5" aria-hidden />
        Məhsul tap
      </button>

      {showQr && <QrModal basketId={cart.basket_id} onClose={() => setShowQr(false)} />}

      {showFinder && (
        <ProductFinder
          basketId={cart.basket_id}
          position={cart.position}
          map={map}
          onTargetChange={setTarget}
          onMove={moveTo}
          onClose={() => setShowFinder(false)}
        />
      )}
    </Page>
  )
}
