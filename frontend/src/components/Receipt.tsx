/**
 * The receipt shown after payment. Also the only thing on the page when
 * printed — see the `@media print` rules in index.css.
 */

import { Printer, Timer, X } from 'lucide-react'

import { secondsSaved, traditionalCheckoutSeconds } from '../constants'
import { formatAZN, formatDateTime, formatSeconds } from '../utils/format'
import type { Receipt as ReceiptData } from '../types'

const METHOD_LABEL: Record<string, string> = {
  cash: '💵 Nağd',
  card: '💳 Kart',
}

export default function Receipt({
  receipt,
  onClose,
}: {
  receipt: ReceiptData
  onClose: () => void
}) {
  const traditional = traditionalCheckoutSeconds(receipt.item_count)
  const saved = secondsSaved(receipt.item_count, receipt.checkout_seconds)

  return (
    <div className="print-overlay fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-900/70 p-4">
      <div className="receipt w-full max-w-sm rounded-3xl bg-white p-6 shadow-2xl">
        <div className="no-print flex justify-end">
          <button
            type="button"
            onClick={onClose}
            aria-label="Bağla"
            className="flex size-11 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>

        <header className="text-center">
          <p className="text-xl font-extrabold">{receipt.store_name}</p>
          <p className="text-sm text-slate-500">{formatDateTime(receipt.paid_at)}</p>
          <p className="mt-1 font-mono text-xs text-slate-400">
            Qəbz #{receipt.payment_id} · {receipt.basket_id}
          </p>
        </header>

        <div className="my-4 border-y border-dashed border-slate-300 py-3">
          <ul className="space-y-1.5 text-sm">
            {receipt.items.map((item) => (
              <li key={item.item_id} className="flex gap-2">
                <span className="flex-1 truncate">
                  {item.product.emoji} {item.product.name}
                  {item.qty > 1 && (
                    <span className="text-slate-500"> × {item.qty}</span>
                  )}
                </span>
                <span className="tabular-nums">{formatAZN(item.line_total_qepik)}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-end justify-between">
          <div>
            <p className="text-sm text-slate-500">{receipt.item_count} məhsul</p>
            <p className="font-semibold">{METHOD_LABEL[receipt.method] ?? receipt.method}</p>
          </div>
          <p className="text-3xl font-extrabold tabular-nums">
            {formatAZN(receipt.amount_qepik)}
          </p>
        </div>

        <div className="mt-4 rounded-2xl bg-brand-50 p-3 text-center text-brand-800">
          <p className="flex items-center justify-center gap-1.5 font-semibold">
            <Timer className="size-4" aria-hidden />
            Bu ödəniş {formatSeconds(receipt.checkout_seconds)} çəkdi
          </p>
          <p className="text-sm">
            Ənənəvi kassada təxminən {formatSeconds(traditional)} —{' '}
            <strong>{formatSeconds(saved)} qənaət</strong>
          </p>
        </div>

        <p className="mt-3 text-center text-xs text-slate-400">
          Smart Basket ilə növbəsiz alış-veriş. Təşəkkür edirik!
        </p>

        <div className="no-print mt-5 flex gap-2">
          <button
            type="button"
            onClick={() => window.print()}
            className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl border border-slate-300 font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <Printer className="size-5" aria-hidden />
            Çap et
          </button>
          <button
            type="button"
            onClick={onClose}
            className="min-h-12 flex-1 rounded-xl bg-brand-600 font-semibold text-white transition hover:bg-brand-700"
          >
            Növbəti müştəri
          </button>
        </div>
      </div>
    </div>
  )
}
