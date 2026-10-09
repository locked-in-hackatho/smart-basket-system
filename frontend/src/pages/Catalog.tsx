/**
 * Catalogue management.
 *
 * The barcode is what makes a product exist as far as the baskets are
 * concerned, so this screen is built around getting it right: the code is
 * checked as it is typed, and it can be read with the camera instead of
 * keyed in, which is how a stockroom would actually do it.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  Camera,
  Check,
  Loader2,
  Package,
  Pencil,
  Plus,
  Search as SearchIcon,
  Trash2,
  X,
} from 'lucide-react'

import { api, ApiError, getAdminPin, setAdminPin } from '../api'
import BarcodeScanner from '../components/BarcodeScanner'
import { useToast } from '../components/Toast'
import { Card, ErrorNote, Page, Spinner } from '../components/ui'
import { formatAZN } from '../utils/format'
import type { Product, ProductDraft, Zone } from '../types'

const LEVELS = ['Yuxarı', 'Orta', 'Aşağı']
const EMOJIS = ['📦', '🥛', '🍞', '🧀', '🍎', '🥩', '🍚', '🍵', '☕', '🥤', '🍫', '🧴', '🧻', '🍼', '🧂', '🥚']

const EMPTY: ProductDraft = {
  barcode: '',
  name: '',
  price_qepik: 0,
  zone_code: '',
  category: '',
  stock: 0,
  emoji: '📦',
  keywords: '',
  level: null,
}

type BarcodeState =
  | { kind: 'idle' }
  | { kind: 'checking' }
  | { kind: 'ok' }
  | { kind: 'taken'; product: string }
  | { kind: 'invalid'; message: string }

export default function Catalog() {
  const toast = useToast()
  const [products, setProducts] = useState<Product[] | null>(null)
  const [zones, setZones] = useState<Zone[]>([])
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  const [draft, setDraft] = useState<ProductDraft>(EMPTY)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [priceText, setPriceText] = useState('')
  const [barcodeState, setBarcodeState] = useState<BarcodeState>({ kind: 'idle' })
  const [scanning, setScanning] = useState(false)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const [allProducts, allZones] = await Promise.all([api.products(), api.zones()])
      setProducts(allProducts)
      setZones(allZones.filter((zone) => zone.kind === 'sales'))
      setError(null)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Kataloq yüklənmədi')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  // Check the barcode as it is typed, so a mistake surfaces before saving.
  useEffect(() => {
    const code = draft.barcode.replace(/\s/g, '')
    if (code.length !== 8 && code.length !== 13) {
      setBarcodeState({ kind: 'idle' })
      return
    }
    let cancelled = false
    setBarcodeState({ kind: 'checking' })
    const timer = window.setTimeout(async () => {
      try {
        const result = await api.checkBarcode(code)
        if (cancelled) return
        if (result.exists && result.product !== currentName) {
          setBarcodeState({ kind: 'taken', product: result.product ?? '' })
        } else {
          setBarcodeState({ kind: 'ok' })
        }
      } catch (cause) {
        if (cancelled) return
        setBarcodeState({
          kind: 'invalid',
          message: cause instanceof ApiError ? cause.message : 'Barkod yoxlanmadı',
        })
      }
    }, 300)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
    // `currentName` lets an edit keep its own barcode without a clash.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.barcode, editingId])

  const currentName = useMemo(
    () => products?.find((p) => p.id === editingId)?.name ?? null,
    [products, editingId],
  )

  const visible = useMemo(() => {
    if (!products) return []
    const needle = query.trim().toLocaleLowerCase('az')
    if (!needle) return products
    return products.filter(
      (product) =>
        product.name.toLocaleLowerCase('az').includes(needle) ||
        product.barcode.includes(needle) ||
        (product.zone_name ?? '').toLocaleLowerCase('az').includes(needle),
    )
  }, [products, query])

  function startAdd() {
    setEditingId(null)
    setDraft({ ...EMPTY, zone_code: zones[0]?.code ?? '' })
    setPriceText('')
    setBarcodeState({ kind: 'idle' })
  }

  function startEdit(product: Product) {
    setEditingId(product.id)
    setDraft({
      barcode: product.barcode,
      name: product.name,
      price_qepik: product.price_qepik,
      zone_code: product.zone_code ?? '',
      category: product.category,
      stock: product.stock,
      emoji: product.emoji,
      keywords: '',
      level: product.shelf || null,
    })
    setPriceText((product.price_qepik / 100).toFixed(2))
    setBarcodeState({ kind: 'ok' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  /** Retry once with a PIN if the deployed app asks for one. */
  async function withPin<T>(action: () => Promise<T>): Promise<T | null> {
    try {
      return await action()
    } catch (cause) {
      if (!(cause instanceof ApiError) || cause.status !== 401) throw cause
      const pin = window.prompt('Admin PIN:', getAdminPin())
      if (!pin) return null
      setAdminPin(pin.trim())
      return await action()
    }
  }

  async function save() {
    const price = Math.round(Number(priceText.replace(',', '.')) * 100)
    if (!Number.isFinite(price) || price <= 0) {
      toast.error('Qiyməti düzgün yazın', 'Məsələn: 1.89')
      return
    }

    setBusy(true)
    try {
      const body: ProductDraft = { ...draft, price_qepik: price }
      const saved = await withPin(() =>
        editingId === null ? api.createProduct(body) : api.updateProduct(editingId, body),
      )
      if (!saved) return
      await load()
      toast.success(
        editingId === null ? 'Məhsul əlavə olundu' : 'Məhsul yeniləndi',
        `${saved.emoji} ${saved.name} · ${saved.aisle}`,
      )
      startAdd()
    } catch (cause) {
      toast.error(cause instanceof ApiError ? cause.message : 'Yadda saxlanmadı')
    } finally {
      setBusy(false)
    }
  }

  async function remove(product: Product) {
    if (!window.confirm(`“${product.name}” silinsin?`)) return
    setBusy(true)
    try {
      const done = await withPin(() => api.deleteProduct(product.id))
      if (done === null) return
      await load()
      toast.info('Məhsul silindi', product.name)
      if (editingId === product.id) startAdd()
    } catch (cause) {
      toast.error(cause instanceof ApiError ? cause.message : 'Silinmədi')
    } finally {
      setBusy(false)
    }
  }

  if (error && !products) {
    return (
      <Page title="Kataloq" wide>
        <ErrorNote message={error} onRetry={() => void load()} />
      </Page>
    )
  }
  if (!products) {
    return (
      <Page title="Kataloq" wide>
        <Spinner />
      </Page>
    )
  }

  const canSave =
    draft.name.trim().length > 0 &&
    draft.zone_code.length > 0 &&
    priceText.trim().length > 0 &&
    (barcodeState.kind === 'ok' || (editingId !== null && barcodeState.kind === 'checking'))

  return (
    <Page
      title="Kataloq"
      subtitle={`${products.length} məhsul · barkodları buradan idarə edin`}
      wide
    >
      <div className="grid gap-4 lg:grid-cols-[26rem_1fr]">
        {/* --- The form --- */}
        <Card className="lg:sticky lg:top-20 lg:self-start">
          <div className="flex items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 font-bold text-slate-900">
              {editingId === null ? (
                <>
                  <Plus className="size-5" aria-hidden /> Yeni məhsul
                </>
              ) : (
                <>
                  <Pencil className="size-5" aria-hidden /> Məhsulu dəyiş
                </>
              )}
            </h2>
            {editingId !== null && (
              <button
                type="button"
                onClick={startAdd}
                className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Yenisini əlavə et
              </button>
            )}
          </div>

          <form
            className="mt-3 space-y-3"
            onSubmit={(event) => {
              event.preventDefault()
              void save()
            }}
          >
            <Field label="Barkod" hint="EAN-13 və ya EAN-8">
              <div className="flex gap-2">
                <input
                  value={draft.barcode}
                  onChange={(event) => setDraft({ ...draft, barcode: event.target.value })}
                  inputMode="numeric"
                  placeholder="5449000189349"
                  aria-label="Barkod"
                  className="min-h-12 w-full rounded-xl border border-slate-300 px-3 font-mono tabular-nums focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
                />
                <button
                  type="button"
                  onClick={() => setScanning(!scanning)}
                  aria-pressed={scanning}
                  title="Kamera ilə oxu"
                  className={`flex size-12 shrink-0 items-center justify-center rounded-xl border transition ${
                    scanning
                      ? 'border-brand-400 bg-brand-50 text-brand-700'
                      : 'border-slate-300 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Camera className="size-5" aria-hidden />
                </button>
              </div>
              <BarcodeFeedback state={barcodeState} />
            </Field>

            {scanning && (
              <BarcodeScanner
                showProducts={false}
                onScan={(code) => {
                  setDraft((current) => ({ ...current, barcode: code }))
                  setScanning(false)
                  toast.info('Barkod oxundu', code)
                }}
              />
            )}

            <Field label="Ad">
              <input
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                placeholder="Fuse Tea 500ml"
                aria-label="Məhsulun adı"
                className="min-h-12 w-full rounded-xl border border-slate-300 px-3 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Qiymət (₼)">
                <input
                  value={priceText}
                  onChange={(event) => setPriceText(event.target.value)}
                  inputMode="decimal"
                  placeholder="1.89"
                  aria-label="Qiymət"
                  className="min-h-12 w-full rounded-xl border border-slate-300 px-3 tabular-nums focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
                />
              </Field>
              <Field label="Stok">
                <input
                  value={String(draft.stock ?? 0)}
                  onChange={(event) =>
                    setDraft({ ...draft, stock: Math.max(0, Number(event.target.value) || 0) })
                  }
                  inputMode="numeric"
                  aria-label="Stok"
                  className="min-h-12 w-full rounded-xl border border-slate-300 px-3 tabular-nums focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
                />
              </Field>
            </div>

            <Field label="Zona" hint="Rəf yeri avtomatik seçilir">
              <select
                value={draft.zone_code}
                onChange={(event) => setDraft({ ...draft, zone_code: event.target.value })}
                aria-label="Zona"
                className="min-h-12 w-full rounded-xl border border-slate-300 px-3 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              >
                <option value="">— zona seçin —</option>
                {zones.map((zone) => (
                  <option key={zone.code} value={zone.code}>
                    {zone.code} · {zone.name}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Rəf səviyyəsi">
              <div className="flex gap-1 rounded-xl bg-slate-100 p-1">
                {LEVELS.map((level) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => setDraft({ ...draft, level })}
                    aria-pressed={draft.level === level}
                    className={`flex-1 rounded-lg px-2 py-2 text-sm font-semibold transition ${
                      draft.level === level
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="İkon">
              <div className="flex flex-wrap gap-1">
                {EMOJIS.map((emoji) => (
                  <button
                    key={emoji}
                    type="button"
                    onClick={() => setDraft({ ...draft, emoji })}
                    aria-pressed={draft.emoji === emoji}
                    className={`flex size-10 items-center justify-center rounded-lg border text-xl transition ${
                      draft.emoji === emoji
                        ? 'border-brand-400 bg-brand-50'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Axtarış sözləri" hint="AZ/RU/EN sinonimlər, vergüllə">
              <input
                value={draft.keywords ?? ''}
                onChange={(event) => setDraft({ ...draft, keywords: event.target.value })}
                placeholder="buzlu çay, ice tea, холодный чай"
                aria-label="Axtarış sözləri"
                className="min-h-12 w-full rounded-xl border border-slate-300 px-3 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              />
            </Field>

            <button
              type="submit"
              disabled={!canSave || busy}
              className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-brand-600 font-bold text-white transition hover:bg-brand-700 disabled:opacity-40"
            >
              {busy ? (
                <Loader2 className="size-5 animate-spin" aria-hidden />
              ) : (
                <Check className="size-5" aria-hidden />
              )}
              {editingId === null ? 'Kataloqa əlavə et' : 'Dəyişikliyi saxla'}
            </button>
          </form>
        </Card>

        {/* --- The catalogue --- */}
        <Card>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="flex items-center gap-2 font-bold text-slate-900">
              <Package className="size-5" aria-hidden />
              Məhsullar
            </h2>
            <label className="relative ml-auto w-full sm:w-64">
              <SearchIcon
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
                aria-hidden
              />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ad, barkod və ya zona…"
                aria-label="Kataloqda axtar"
                className="min-h-11 w-full rounded-xl border border-slate-300 pl-9 pr-3 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
              />
            </label>
          </div>

          <p className="mt-1 text-sm text-slate-500">
            {visible.length} məhsul göstərilir
          </p>

          <div className="mt-2 max-h-[70vh] overflow-y-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Kataloqdakı məhsullar</caption>
              <thead className="sticky top-0 bg-white text-left text-slate-500">
                <tr>
                  <th scope="col" className="py-1.5">Məhsul</th>
                  <th scope="col" className="py-1.5">Barkod</th>
                  <th scope="col" className="py-1.5">Yer</th>
                  <th scope="col" className="py-1.5 text-right">Qiymət</th>
                  <th scope="col" className="py-1.5 text-right">Stok</th>
                  <th scope="col" className="py-1.5" />
                </tr>
              </thead>
              <tbody>
                {visible.map((product) => (
                  <tr
                    key={product.id}
                    className={`border-t border-slate-100 ${
                      editingId === product.id ? 'bg-brand-50' : ''
                    }`}
                  >
                    <td className="py-1.5 pr-2">
                      <span className="flex items-center gap-1.5">
                        <span aria-hidden>{product.emoji}</span>
                        <span className="truncate font-medium">{product.name}</span>
                      </span>
                    </td>
                    <td className="py-1.5 pr-2 font-mono text-xs tabular-nums text-slate-500">
                      {product.barcode}
                    </td>
                    <td className="py-1.5 pr-2 text-xs text-slate-500">
                      {product.zone_name} · {product.aisle}
                    </td>
                    <td className="py-1.5 text-right font-semibold tabular-nums">
                      {formatAZN(product.price_qepik)}
                    </td>
                    <td
                      className={`py-1.5 text-right tabular-nums ${
                        product.stock === 0 ? 'font-semibold text-red-600' : ''
                      }`}
                    >
                      {product.stock}
                    </td>
                    <td className="py-1.5">
                      <span className="flex justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => startEdit(product)}
                          aria-label={`${product.name} məhsulunu dəyiş`}
                          className="flex size-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-900"
                        >
                          <Pencil className="size-4" aria-hidden />
                        </button>
                        <button
                          type="button"
                          onClick={() => void remove(product)}
                          aria-label={`${product.name} məhsulunu sil`}
                          className="flex size-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                        >
                          <Trash2 className="size-4" aria-hidden />
                        </button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {visible.length === 0 && (
              <p className="py-10 text-center text-slate-500">Məhsul tapılmadı</p>
            )}
          </div>
        </Card>
      </div>
    </Page>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1 flex items-baseline gap-2">
        <span className="text-sm font-semibold text-slate-700">{label}</span>
        {hint && <span className="text-xs text-slate-400">{hint}</span>}
      </span>
      {children}
    </label>
  )
}

function BarcodeFeedback({ state }: { state: BarcodeState }) {
  if (state.kind === 'idle') {
    return <p className="mt-1 text-xs text-slate-400">13 və ya 8 rəqəm daxil edin</p>
  }
  if (state.kind === 'checking') {
    return (
      <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
        <Loader2 className="size-3 animate-spin" aria-hidden /> Yoxlanılır…
      </p>
    )
  }
  if (state.kind === 'ok') {
    return (
      <p className="mt-1 flex items-center gap-1 text-xs font-semibold text-brand-700">
        <Check className="size-3.5" aria-hidden /> Barkod düzgündür
      </p>
    )
  }
  if (state.kind === 'taken') {
    return (
      <p className="mt-1 flex items-start gap-1 text-xs font-semibold text-amber-700">
        <AlertCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
        Bu barkod artıq var: {state.product}
      </p>
    )
  }
  return (
    <p className="mt-1 flex items-start gap-1 text-xs font-semibold text-red-600">
      <X className="mt-0.5 size-3.5 shrink-0" aria-hidden />
      {state.message}
    </p>
  )
}
