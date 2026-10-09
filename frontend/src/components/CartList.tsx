/** The basket's contents. Every number here comes from the backend. */

import { Minus, Plus, Trash2 } from 'lucide-react'

import { formatAZN } from '../utils/format'
import type { CartItem } from '../types'

interface Props {
  items: CartItem[]
  onChangeQty: (itemId: number, qty: number) => void
  onRemove: (itemId: number) => void
  disabled?: boolean
  /** Read-only rendering for the till and the receipt. */
  readOnly?: boolean
}

export default function CartList({
  items,
  onChangeQty,
  onRemove,
  disabled = false,
  readOnly = false,
}: Props) {
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li
          key={item.item_id}
          className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-2.5"
        >
          <span className="text-3xl leading-none" aria-hidden>
            {item.product.emoji}
          </span>

          <div className="min-w-0 flex-1">
            <p className="truncate font-semibold text-slate-900">{item.product.name}</p>
            <p className="text-sm text-slate-500">
              {formatAZN(item.product.price_qepik)} × {item.qty}
              {item.product.zone_name && (
                <span className="hidden sm:inline"> · {item.product.zone_name}</span>
              )}
            </p>
          </div>

          {!readOnly && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                aria-label={`${item.product.name} sayını azalt`}
                disabled={disabled}
                onClick={() => onChangeQty(item.item_id, item.qty - 1)}
                className="flex size-11 items-center justify-center rounded-xl border border-slate-200 text-slate-600 transition active:scale-95 hover:bg-slate-50 disabled:opacity-40"
              >
                <Minus className="size-4" aria-hidden />
              </button>
              <span className="w-7 text-center text-lg font-bold tabular-nums">
                {item.qty}
              </span>
              <button
                type="button"
                aria-label={`${item.product.name} sayını artır`}
                disabled={disabled}
                onClick={() => onChangeQty(item.item_id, item.qty + 1)}
                className="flex size-11 items-center justify-center rounded-xl border border-slate-200 text-slate-600 transition active:scale-95 hover:bg-slate-50 disabled:opacity-40"
              >
                <Plus className="size-4" aria-hidden />
              </button>
            </div>
          )}

          <span className="w-20 shrink-0 text-right font-bold tabular-nums text-slate-900">
            {formatAZN(item.line_total_qepik)}
          </span>

          {!readOnly && (
            <button
              type="button"
              aria-label={`${item.product.name} məhsulunu sil`}
              disabled={disabled}
              onClick={() => onRemove(item.item_id)}
              className="flex size-11 shrink-0 items-center justify-center rounded-xl text-slate-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
            >
              <Trash2 className="size-4" aria-hidden />
            </button>
          )}
        </li>
      ))}
    </ul>
  )
}
