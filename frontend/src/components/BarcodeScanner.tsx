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

/** The camera decodes ~10 frames a second; ignore repeats inside this window. */
const DUPLICATE_WINDOW_MS = 1500
/** A human types slower than this; anything faster is a barcode gun. */
const SCANNER_GAP_MS = 50
const CAMERA_ELEMENT_ID = 'barcode-camera'

type Tab = 'camera' | 'manual' | 'products'

interface Props {
  onScan: (barcode: string) => void
  /** Hide the demo-product grid where it makes no sense (the till). */
  showProducts?: boolean
  /** QR-only mode for the checkout screen. */
  qrOnly?: boolean
  disabled?: boolean
}

export default function BarcodeScanner({
  onScan,
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
      const last = lastScanRef.current
      if (code === last.code && now - last.at < DUPLICATE_WINDOW_MS) return
      lastScanRef.current = { code, at: now }
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
          verbose: false,
        })
        await scanner.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 260, height: 180 } },
          (text) => emit(text, 'camera'),
          () => {
            // Fired constantly for frames with no code in them; ignore.
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
            <div
              id={CAMERA_ELEMENT_ID}
              className="overflow-hidden rounded-xl bg-slate-900 [&_video]:w-full"
            />
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
                Barkodu çərçivənin içinə tutun
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
