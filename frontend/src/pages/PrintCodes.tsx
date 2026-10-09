/**
 * Printable sheets: basket QR codes to stick on the baskets, and product
 * barcodes to stand in for real packaging during the demo.
 */

import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Printer, ShoppingBasket } from 'lucide-react'

import { api } from '../api'
import Barcode from '../components/Barcode'
import { qrPayload } from '../components/QrModal'
import { Card, ErrorNote, Page, Spinner } from '../components/ui'
import { formatAZN } from '../utils/format'
import type { BasketSummary, Product } from '../types'

type Sheet = 'baskets' | 'products'

export default function PrintCodes() {
  const [sheet, setSheet] = useState<Sheet>('baskets')
  const [baskets, setBaskets] = useState<BasketSummary[] | null>(null)
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setError(null)
    Promise.all([api.baskets(), api.products()])
      .then(([allBaskets, allProducts]) => {
        setBaskets(allBaskets)
        setProducts(allProducts)
      })
      .catch((cause) => setError(cause.message))
  }, [])

  const loading = baskets === null || products === null

  return (
    <Page
      title="Çap"
      subtitle="Səbət QR kodları və demo məhsul barkodları"
      wide
      actions={
        <button
          type="button"
          onClick={() => window.print()}
          className="no-print inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand-600 px-4 font-semibold text-white transition hover:bg-brand-700"
        >
          <Printer className="size-5" aria-hidden />
          Çap et
        </button>
      }
    >
      <div className="no-print">
        {error && <ErrorNote message={error} />}

        <div className="flex gap-1 rounded-xl bg-slate-100 p-1 sm:w-max">
          {(
            [
              ['baskets', `Səbət QR kodları (${baskets?.length ?? 0})`],
              ['products', `Məhsul barkodları (${products?.length ?? 0})`],
            ] as [Sheet, string][]
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setSheet(id)}
              aria-pressed={sheet === id}
              className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-semibold transition sm:flex-none ${
                sheet === id
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <Card className="mt-3 text-sm text-slate-600">
          <p className="font-semibold text-slate-800">Necə istifadə etməli</p>
          <ul className="mt-1 list-inside list-disc space-y-0.5">
            <li>
              <strong>Səbət QR kodları:</strong> çap edib səbətlərə yapışdırın. Kassa
              məhz bu kodu oxuyur.
            </li>
            <li>
              <strong>Məhsul barkodları:</strong> çap edib demo məhsullarına yapışdırın
              və ya birbaşa ekrandan skan edin.
            </li>
            <li>Çap etməsəniz də olar — kamera ekrandakı kodu oxuya bilir.</li>
          </ul>
        </Card>
      </div>

      {loading && !error ? (
        <Spinner />
      ) : (
        <div className="print-sheet mt-4">
          {sheet === 'baskets' ? (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {baskets?.map((basket) => (
                <article
                  key={basket.id}
                  className="print-card flex flex-col items-center gap-2 rounded-2xl border border-slate-300 bg-white p-4 text-center"
                >
                  <p className="flex items-center gap-1.5 text-sm font-extrabold text-brand-700">
                    <ShoppingBasket className="size-4" aria-hidden />
                    Smart Basket
                  </p>
                  <QRCodeSVG value={qrPayload(basket.id)} size={150} level="M" marginSize={1} />
                  <p className="font-mono text-xl font-bold tracking-wide">{basket.id}</p>
                  <p className="text-[10px] text-slate-400">{qrPayload(basket.id)}</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {products?.map((product) => (
                <article
                  key={product.id}
                  className="print-card flex flex-col items-center gap-1 rounded-xl border border-slate-300 bg-white p-2 text-center"
                >
                  <p className="flex w-full items-center justify-center gap-1 text-xs font-semibold leading-tight">
                    <span aria-hidden>{product.emoji}</span>
                    <span className="truncate">{product.name}</span>
                  </p>
                  <Barcode value={product.barcode} />
                  <p className="text-sm font-bold text-brand-700">
                    {formatAZN(product.price_qepik)}
                  </p>
                </article>
              ))}
            </div>
          )}
        </div>
      )}
    </Page>
  )
}
