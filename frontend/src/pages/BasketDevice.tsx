/** Basket-mounted screen. Scanning and the assistant arrive in phase 4. */

import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ShoppingBasket } from 'lucide-react'

import { api, ApiError } from '../api'
import { formatAZN } from '../utils/format'
import { Card, EmptyState, ErrorNote, Page, Spinner, StatusChip } from '../components/ui'
import type { Cart } from '../types'

export default function BasketDevice() {
  const { basketId = 'BSK-001' } = useParams()
  const [cart, setCart] = useState<Cart | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setError(null)
    api
      .cart(basketId)
      .then(setCart)
      .catch((cause: ApiError) => setError(cause.message))
  }

  useEffect(load, [basketId])

  if (error) {
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

  return (
    <Page
      title={cart.basket_id}
      subtitle="Səbət cihazı"
      actions={<StatusChip status={cart.status} />}
    >
      <Card className="text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Yekun məbləğ
        </p>
        <p className="mt-1 text-5xl font-extrabold tabular-nums text-brand-700">
          {formatAZN(cart.total_qepik)}
        </p>
        <p className="mt-1 text-slate-500">{cart.item_count} məhsul</p>
      </Card>

      {cart.items.length === 0 ? (
        <EmptyState
          icon={<ShoppingBasket className="size-9" aria-hidden />}
          title="Məhsulu skan edərək alış-verişə başlayın"
          hint="Skan, AI köməkçi və mini xəritə növbəti fazada əlavə olunur."
        />
      ) : (
        <ul className="mt-4 space-y-2">
          {cart.items.map((item) => (
            <li
              key={item.item_id}
              className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3"
            >
              <span className="text-2xl" aria-hidden>
                {item.product.emoji}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-semibold">{item.product.name}</span>
                <span className="block text-sm text-slate-500">
                  {formatAZN(item.product.price_qepik)} × {item.qty}
                </span>
              </span>
              <span className="font-bold tabular-nums">
                {formatAZN(item.line_total_qepik)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Page>
  )
}
