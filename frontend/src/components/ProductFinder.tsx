/**
 * "Find a product": search the catalogue, then walk the shopper there.
 *
 * Nothing here guesses. The shelf comes from the database and the route from
 * the backend's A* — so the same query always gives the same answer, with no
 * network beyond our own API.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Footprints, MapPin, Navigation, Search, X } from 'lucide-react'

import { api, ApiError } from '../api'
import StoreMap from './StoreMap'
import { formatAZN, formatSeconds } from '../utils/format'
import type { FoundProduct, RouteResponse, StoreMapData } from '../types'

const DEBOUNCE_MS = 200
const POPULAR = ['süd', 'çörək', 'diş pastası', 'çips', 'qəhvə', 'uşaq bezi']

interface Props {
  basketId: string
  /** Where the basket is now; a change re-routes automatically. */
  position: { x: number; y: number } | null
  map: StoreMapData | null
  /** Barcode of the product being navigated to, so the page can say "found". */
  onTargetChange: (product: FoundProduct | null) => void
  /** "I am here" — tapping an aisle cell on the map. */
  onMove: (x: number, y: number) => void
  onClose: () => void
}

export default function ProductFinder({
  basketId,
  position,
  map,
  onTargetChange,
  onMove,
  onClose,
}: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<FoundProduct[]>([])
  const [suggestions, setSuggestions] = useState<FoundProduct[]>([])
  const [searched, setSearched] = useState(false)
  const [busy, setBusy] = useState(false)
  const [target, setTarget] = useState<FoundProduct | null>(null)
  const [route, setRoute] = useState<RouteResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const runSearch = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed) {
        setResults([])
        setSuggestions([])
        setSearched(false)
        return
      }
      setBusy(true)
      try {
        const body = await api.search(trimmed, basketId)
        setResults(body.results)
        setSuggestions(body.suggestions)
        setSearched(true)
        setError(null)
      } catch (cause) {
        setError(cause instanceof ApiError ? cause.message : 'Xəta baş verdi')
      } finally {
        setBusy(false)
      }
    },
    [basketId],
  )

  // Search as the shopper types, but not on every keystroke.
  useEffect(() => {
    const timer = window.setTimeout(() => void runSearch(query), DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [query, runSearch])

  const loadRoute = useCallback(
    async (product: FoundProduct) => {
      try {
        setRoute(await api.route(basketId, product.id))
        setError(null)
      } catch (cause) {
        setError(cause instanceof ApiError ? cause.message : 'Yol tapılmadı')
      }
    },
    [basketId],
  )

  function choose(product: FoundProduct) {
    setTarget(product)
    onTargetChange(product)
    void loadRoute(product)
  }

  function clearTarget() {
    setTarget(null)
    setRoute(null)
    onTargetChange(null)
  }

  // The basket moved (a scan, or a tap on the map) — re-route from there.
  const positionKey = position ? `${position.x},${position.y}` : ''
  const lastPosition = useRef(positionKey)
  useEffect(() => {
    if (positionKey === lastPosition.current) return
    lastPosition.current = positionKey
    if (target) void loadRoute(target)
  }, [positionKey, target, loadRoute])

  // --- Navigating ---------------------------------------------------------

  if (target) {
    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Yol göstərişi"
        className="fixed inset-0 z-50 flex flex-col bg-white"
      >
        <header className="flex items-center gap-3 border-b border-slate-200 px-4 py-3">
          <span className="text-2xl" aria-hidden>
            {target.emoji}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate font-bold">{target.name}</p>
            <p className="truncate text-sm text-slate-500">
              {target.zone_name} · {target.aisle} · {target.level} rəf
            </p>
          </div>
          <button
            type="button"
            onClick={clearTarget}
            aria-label="Bağla"
            className="flex size-11 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="size-5" aria-hidden />
          </button>
        </header>

        {route && (
          <div className="flex items-center justify-center gap-4 bg-brand-600 px-4 py-3 text-white">
            <span className="flex items-center gap-1.5 text-2xl font-extrabold tabular-nums">
              <Footprints className="size-6" aria-hidden />
              {route.distance_m} m
            </span>
            <span className="text-lg opacity-90">
              ~{formatSeconds(route.eta_seconds)}
            </span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-3">
          {error && (
            <p className="mb-2 rounded-xl bg-red-50 px-3 py-2 text-red-700">{error}</p>
          )}

          <StoreMap
            map={map}
            path={route?.path ?? null}
            target={
              target.shelf_x !== null && target.shelf_y !== null
                ? { x: target.shelf_x, y: target.shelf_y }
                : null
            }
            position={position}
            onCellClick={onMove}
          />

          <ol className="mt-3 space-y-2">
            {route?.steps.map((step, index) => (
              <li
                key={index}
                className="flex items-start gap-3 rounded-xl border border-slate-200 px-3 py-2.5"
              >
                <span
                  className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                    index === route.steps.length - 1
                      ? 'bg-brand-600 text-white'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {index === route.steps.length - 1 ? (
                    <MapPin className="size-4" aria-hidden />
                  ) : (
                    index + 1
                  )}
                </span>
                <span className="pt-0.5 font-medium text-slate-800">{step}</span>
              </li>
            ))}
          </ol>

          <p className="mt-3 text-center text-xs text-slate-400">
            Xəritədə olduğunuz yerə toxunaraq mövqeyinizi dəqiqləşdirə bilərsiniz.
            Real versiyada bu, BLE mayakları ilə avtomatik baş verir.
          </p>
        </div>
      </div>
    )
  }

  // --- Searching ----------------------------------------------------------

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Məhsul tap"
      className="fixed inset-0 z-50 flex flex-col justify-end bg-slate-900/60"
      onClick={onClose}
    >
      <div
        className="flex max-h-[88vh] flex-col rounded-t-3xl bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
          <Search className="size-6 text-brand-600" aria-hidden />
          <p className="flex-1 font-bold">Məhsul tap</p>
          <button
            type="button"
            onClick={onClose}
            aria-label="Bağla"
            className="flex size-11 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="size-5" aria-hidden />
          </button>
        </header>

        <div className="border-b border-slate-200 p-3">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Məhsulun adını yazın…"
            aria-label="Məhsul axtar"
            autoFocus
            className="min-h-12 w-full rounded-xl border border-slate-300 px-4 text-lg focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
          />
          <div className="mt-2 flex gap-1.5 overflow-x-auto pb-1">
            {POPULAR.map((term) => (
              <button
                key={term}
                type="button"
                onClick={() => setQuery(term)}
                className="shrink-0 rounded-full border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition hover:border-brand-400 hover:text-brand-700"
              >
                {term}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {error && (
            <p className="mb-2 rounded-xl bg-red-50 px-3 py-2 text-red-700">{error}</p>
          )}

          {!searched && !busy && (
            <p className="py-10 text-center text-slate-500">
              Axtardığınız məhsulun adını yazın — yerini xəritədə göstərəcəyəm.
            </p>
          )}

          {searched && results.length === 0 && (
            <div className="py-8 text-center">
              <p className="text-4xl" aria-hidden>
                🔍
              </p>
              <p className="mt-2 font-semibold text-slate-800">
                Bu məhsul mağazamızda yoxdur
              </p>
              {suggestions.length > 0 && (
                <p className="mt-1 text-sm text-slate-500">Bunları nəzərdən keçirin:</p>
              )}
            </div>
          )}

          <ul className="space-y-2">
            {(results.length > 0 ? results : suggestions).map((product) => (
              <li key={product.id}>
                <button
                  type="button"
                  onClick={() => choose(product)}
                  className="flex w-full items-center gap-3 rounded-2xl border border-slate-200 px-3 py-3 text-left transition hover:border-brand-400 hover:bg-brand-50"
                >
                  <span className="text-3xl" aria-hidden>
                    {product.emoji}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold text-slate-900">
                      {product.name}
                    </span>
                    <span className="block truncate text-sm text-slate-500">
                      {product.zone_name} · {product.aisle} · {product.level} rəf
                      {product.distance_m !== null && ` · ${product.distance_m} m`}
                    </span>
                    {product.stock <= 0 && (
                      <span className="text-xs font-semibold text-red-600">
                        Stokda yoxdur
                      </span>
                    )}
                  </span>
                  <span className="shrink-0 text-right">
                    <span className="block font-bold text-brand-700">
                      {formatAZN(product.price_qepik)}
                    </span>
                    <span className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-slate-500">
                      <Navigation className="size-3.5" aria-hidden />
                      Yolu göstər
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
