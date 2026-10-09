/**
 * Three ways to get a barcode in, so a demo never dies on stage:
 *   1. the device camera (html5-qrcode),
 *   2. a USB/Bluetooth scanner, which types like a keyboard,
 *   3. by hand — a text field plus a grid of the seeded demo products.
 */

import { useEffect, useRef, useState } from 'react'
import {
  Camera,
  CameraOff,
  Grid3x3,
  Keyboard,
  Loader2,
  Search,
} from 'lucide-react'
// Loaded on demand: html5-qrcode is ~400 kB and only the camera tab needs it.
import type { Html5Qrcode } from 'html5-qrcode'

import { api } from '../api'
import { formatAZN } from '../utils/format'
import type { Product } from '../types'

/**
 * A barcode held in front of the camera decodes on every frame. Counting the
 * same code again requires the camera to first see this many frames without
 * it — i.e. the item has to leave the view. Otherwise holding a bottle still
 * adds it over and over.
 */
const FRAMES_TO_CLEAR = 6
/**
 * Belt and braces only: if the decoder somehow never reports an empty frame,
 * stop blocking the same code after this long. Deliberately generous — a
 * shopper moves the item away in a second or two, so this should never fire
 * in normal use. At six seconds it did, and a bottle held still was counted
 * twice.
 */
const SAME_CODE_TIMEOUT_MS = 30000
/** A human types slower than this; anything faster is a barcode gun. */
const SCANNER_GAP_MS = 50
const CAMERA_ELEMENT_ID = 'barcode-camera'

type Tab = 'camera' | 'manual' | 'products'

export interface ScanOutcome {
  ok: boolean
  /** What to show — a product name on success, the error otherwise. */
  text: string
}

interface Props {
  onScan: (barcode: string) => void
  /** Result of the last scan, shown over the camera for a few seconds. */
  outcome?: ScanOutcome | null
  /** Hide the demo-product grid where it makes no sense (the till). */
  showProducts?: boolean
  /** QR-only mode for the checkout screen. */
  qrOnly?: boolean
  disabled?: boolean
}

export default function BarcodeScanner({
  onScan,
  outcome = null,
  showProducts = true,
  qrOnly = false,
  disabled = false,
}: Props) {
  const [tab, setTab] = useState<Tab>(showProducts ? 'products' : 'manual')
  const [cameraState, setCameraState] = useState<'off' | 'starting' | 'on' | 'error'>(
    'off',
  )
  const [cameraError, setCameraError] = useState('')
  const [manual, setManual] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [query, setQuery] = useState('')

  // Kept in refs so the long-lived camera and keydown callbacks always see
  // the current handler without being torn down on every render.
  const onScanRef = useRef(onScan)
  const disabledRef = useRef(disabled)
  onScanRef.current = onScan
  disabledRef.current = disabled

  const lastScanRef = useRef<{ code: string; at: number }>({ code: '', at: 0 })
  /** Frames seen with no code since the last accepted camera decode. */
  const clearFramesRef = useRef(0)

  /**
   * A live read-out over the camera. Without it the camera looks identical
   * whether it is working and seeing nothing, or quietly failing — which is
   * exactly the moment a demo goes wrong.
   */
  const [searchingFor, setSearchingFor] = useState(0)
  const lastDecodeRef = useRef(0)

  /**
   * `source` matters: only the camera repeats a code by itself, so only the
   * camera is de-duplicated. Tapping a demo product twice, or scanning two
   * identical items with a gun, must count twice.
   */
  function emit(raw: string, source: 'camera' | 'input' = 'input'): void {
    const code = raw.trim()
    if (!code || disabledRef.current) return

    if (source === 'camera') {
      const now = Date.now()
      lastDecodeRef.current = now
      const last = lastScanRef.current
      const isRepeat = code === last.code
      const cleared = clearFramesRef.current >= FRAMES_TO_CLEAR
      const stale = now - last.at > SAME_CODE_TIMEOUT_MS
      if (isRepeat && !cleared && !stale) return
      lastScanRef.current = { code, at: now }
      clearFramesRef.current = 0
    }
    onScanRef.current(code)
  }

  // --- 2. USB / Bluetooth scanner (keyboard wedge) ------------------------
  useEffect(() => {
    let buffer = ''
    let lastKeyAt = 0

    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      // The manual field submits on its own; don't read it twice.
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return

      const now = Date.now()
      if (now - lastKeyAt > SCANNER_GAP_MS) buffer = ''
      lastKeyAt = now

      if (event.key === 'Enter') {
        if (buffer.length >= 4) {
          emit(buffer)
          event.preventDefault()
        }
        buffer = ''
        return
      }
      if (event.key.length === 1) buffer += event.key
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  // --- 1. Camera ----------------------------------------------------------
  useEffect(() => {
    if (tab !== 'camera') return

    let scanner: Html5Qrcode | null = null
    let stopped = false

    async function start() {
      setCameraState('starting')
      setCameraError('')
      try {
        const { Html5Qrcode, Html5QrcodeSupportedFormats: Formats } = await import(
          'html5-qrcode'
        )
        if (stopped) return
        scanner = new Html5Qrcode(CAMERA_ELEMENT_ID, {
          formatsToSupport: qrOnly
            ? [Formats.QR_CODE]
            : [Formats.EAN_13, Formats.EAN_8, Formats.CODE_128, Formats.QR_CODE],
          // Use the browser's own decoder when it has one: much faster on a
          // phone and noticeably better on 1D codes.
          experimentalFeatures: { useBarCodeDetectorIfSupported: true },
          verbose: false,
        })
        await scanner.start(
          { facingMode: 'environment' },
          {
            fps: 12,
            // Ask for a sharp feed. An EAN-13 is 95 modules wide, so at 640p
            // a barcode filling a third of the frame leaves ~2px per module
            // and will not decode; 720p+ gives the decoder room to work.
            // Note: these belong here, not in the first argument - putting
            // them there stops the camera starting at all.
            videoConstraints: {
              facingMode: 'environment',
              width: { ideal: 1280 },
              height: { ideal: 720 },
            },
            // Anything outside this box is never examined, so its shape has
            // to match the code. A QR is square; an EAN-13 is far wider than
            // it is tall. One shape for both fails: a square box clips a
            // barcode held close enough to read, and a wide, shallow box
            // clips the top and bottom off a QR code.
            qrbox: (viewWidth: number, viewHeight: number) =>
              qrOnly
                ? (() => {
                    const side = Math.floor(Math.min(viewWidth, viewHeight) * 0.8)
                    return { width: side, height: side }
                  })()
                : {
                    width: Math.floor(viewWidth * 0.92),
                    height: Math.floor(
                      Math.min(viewHeight * 0.6, Math.max(viewHeight * 0.3, 160)),
                    ),
                  },
            // Barcodes are often printed on curved or shiny packaging; let
            // the decoder try the mirrored image too.
            disableFlip: false,
          },
          (text) => emit(text, 'camera'),
          () => {
            // Fires for every frame with no code in it — which is how we
            // know the last item has been taken out of view.
            clearFramesRef.current += 1
          },
        )
        if (stopped) return
        setCameraState('on')
      } catch (cause) {
        if (stopped) return
        setCameraState('error')
        setCameraError(
          window.isSecureContext
            ? 'Kameraya icazə verilmədi və ya kamera tapılmadı.'
            : 'Kamera yalnız HTTPS və ya localhost üzərində işləyir. “npm run dev:https” ilə başladın.',
        )
      }
    }

    void start()
    return () => {
      stopped = true
      if (scanner) {
        scanner
          .stop()
          .then(() => scanner?.clear())
          .catch(() => {
            // Already stopped, or the element is gone — nothing to clean up.
          })
      }
    }
  }, [tab, qrOnly])

  // Tick once a second while the camera is on, so the shopper can tell the
  // difference between "looking" and "stuck".
  useEffect(() => {
    if (tab !== 'camera' || cameraState !== 'on') {
      setSearchingFor(0)
      return
    }
    const startedAt = Date.now()
    lastDecodeRef.current = 0
    const timer = window.setInterval(() => {
      const since = lastDecodeRef.current || startedAt
      setSearchingFor(Math.floor((Date.now() - since) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [tab, cameraState])

  // --- 3. Demo product grid ----------------------------------------------
  useEffect(() => {
    if (tab !== 'products' || products.length > 0) return
    api
      .products()
      .then(setProducts)
      .catch(() => setProducts([]))
  }, [tab, products.length])

  const needle = query.trim().toLocaleLowerCase('az')
  const visible = needle
    ? products.filter(
        (product) =>
          product.name.toLocaleLowerCase('az').includes(needle) ||
          product.category.toLocaleLowerCase('az').includes(needle),
      )
    : products

  const tabs: { id: Tab; label: string; icon: typeof Camera }[] = [
    ...(showProducts
      ? [{ id: 'products' as Tab, label: 'Demo məhsullar', icon: Grid3x3 }]
      : []),
    { id: 'camera', label: 'Kamera', icon: Camera },
    { id: 'manual', label: 'Əl ilə', icon: Keyboard },
  ]

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex gap-1 rounded-xl bg-slate-100 p-1">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            aria-pressed={tab === item.id}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-2.5 text-sm font-semibold transition ${
              tab === item.id
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <item.icon className="size-4" aria-hidden />
            <span className="truncate">{item.label}</span>
          </button>
        ))}
      </div>

      <div className="mt-3">
        {tab === 'camera' && (
          <div>
            <div className="relative">
              <div
                id={CAMERA_ELEMENT_ID}
                className="overflow-hidden rounded-xl bg-slate-900 [&_video]:w-full"
              />
              {cameraState === 'on' && (
                <div
                  role="status"
                  aria-live="polite"
                  className={`absolute inset-x-0 top-0 z-10 rounded-t-xl px-3 py-2 text-center text-sm font-semibold text-white ${
                    outcome
                      ? outcome.ok
                        ? 'bg-brand-600'
                        : 'bg-red-600'
                      : searchingFor >= 1
                        ? 'bg-slate-900/80'
                        : 'bg-slate-900/60'
                  }`}
                >
                  {outcome ? (
                    <>
                      {outcome.ok ? '✅ ' : '⚠️ '}
                      {outcome.text}
                      {outcome.ok && (
                        <span className="block text-xs font-medium opacity-90">
                          Növbəti məhsul üçün barkodu kənara çəkin
                        </span>
                      )}
                    </>
                  ) : searchingFor >= 1 ? (
                    <>Oxunmadı · {searchingFor} san — barkodu yaxınlaşdırın</>
                  ) : (
                    <>Barkod axtarılır…</>
                  )}
                </div>
              )}
            </div>
            {cameraState === 'starting' && (
              <p className="flex items-center justify-center gap-2 py-8 text-slate-500">
                <Loader2 className="size-5 animate-spin" aria-hidden />
                Kamera açılır…
              </p>
            )}
            {cameraState === 'error' && (
              <div className="flex flex-col items-center gap-2 py-6 text-center">
                <CameraOff className="size-8 text-red-500" aria-hidden />
                <p className="text-sm text-red-700">{cameraError}</p>
                <p className="text-sm text-slate-500">
                  “Demo məhsullar” və ya “Əl ilə” rejimindən istifadə edin.
                </p>
              </div>
            )}
            {cameraState === 'on' && (
              <p className="pt-2 text-center text-sm text-slate-500">
                Barkodu çərçivəyə tutun — kadrın təxminən yarısını doldursun
              </p>
            )}
          </div>
        )}

        {tab === 'manual' && (
          <form
            onSubmit={(event) => {
              event.preventDefault()
              emit(manual)
              setManual('')
            }}
            className="flex gap-2"
          >
            <input
              value={manual}
              onChange={(event) => setManual(event.target.value)}
              inputMode={qrOnly ? 'text' : 'numeric'}
              autoComplete="off"
              placeholder={qrOnly ? 'BSK-001' : 'Barkodu daxil edin'}
              aria-label="Barkod"
              className="min-h-12 w-full rounded-xl border border-slate-300 px-4 text-lg tabular-nums focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
            />
            <button
              type="submit"
              disabled={disabled || manual.trim().length === 0}
              className="min-h-12 shrink-0 rounded-xl bg-brand-600 px-5 font-semibold text-white transition hover:bg-brand-700 disabled:opacity-40"
            >
              Skan et
            </button>
          </form>
        )}

        {tab === 'products' && (
          <div>
            <label className="relative block">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
                aria-hidden
              />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Demo məhsul axtar…"
                aria-label="Demo məhsullar arasında axtar"
                className="min-h-11 w-full rounded-xl border border-slate-300 pl-9 pr-3 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              />
            </label>
            <div className="mt-2 grid max-h-72 grid-cols-2 gap-2 overflow-y-auto sm:grid-cols-3">
              {visible.map((product) => (
                <button
                  key={product.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => emit(product.barcode)}
                  className="flex min-h-20 flex-col items-center justify-center gap-0.5 rounded-xl border border-slate-200 p-2 text-center transition active:scale-95 hover:border-brand-400 hover:bg-brand-50 disabled:opacity-40"
                >
                  <span className="text-2xl" aria-hidden>
                    {product.emoji}
                  </span>
                  <span className="line-clamp-2 text-xs font-medium leading-tight text-slate-700">
                    {product.name}
                  </span>
                  <span className="text-xs font-bold text-brand-700">
                    {formatAZN(product.price_qepik)}
                  </span>
                </button>
              ))}
              {visible.length === 0 && (
                <p className="col-span-full py-6 text-center text-sm text-slate-500">
                  Məhsul tapılmadı
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      <p className="mt-2 text-center text-xs text-slate-400">
        USB/Bluetooth skaner həmişə aktivdir — sadəcə oxudun
      </p>
    </div>
  )
}
