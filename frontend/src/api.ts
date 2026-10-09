/**
 * Typed API client. Every call goes through `/api`, which Vite proxies to the
 * backend, so a phone only ever needs the frontend's address.
 *
 * Errors are thrown as `ApiError` carrying the backend's Azerbaijani
 * `detail` message, ready to show in a toast.
 */

import type {
  AssistantReply,
  BasketSummary,
  Cart,
  Health,
  PaymentMethod,
  Product,
  Receipt,
  ScanMode,
  Zone,
} from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
      ...init,
    })
  } catch {
    throw new ApiError('Serverə qoşulmaq mümkün olmadı', 0)
  }

  if (!response.ok) {
    let detail = `Xəta baş verdi (${response.status})`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      // Response had no JSON body; keep the generic message.
    }
    throw new ApiError(detail, response.status)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined })

export const api = {
  health: () => request<Health>('/health'),

  // --- Catalogue ---
  zones: () => request<Zone[]>('/zones'),
  products: (q?: string) =>
    request<Product[]>(`/products${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  productByBarcode: (barcode: string) =>
    request<Product>(`/products/barcode/${encodeURIComponent(barcode)}`),

  // --- Baskets ---
  baskets: () => request<BasketSummary[]>('/baskets'),
  cart: (basketId: string) => request<Cart>(`/baskets/${basketId}/cart`),
  scan: (basketId: string, barcode: string, mode: ScanMode = 'add') =>
    post<Cart>(`/baskets/${basketId}/scan`, { barcode, mode }),
  setItemQty: (basketId: string, itemId: number, qty: number) =>
    request<Cart>(`/baskets/${basketId}/items/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify({ qty }),
    }),
  removeItem: (basketId: string, itemId: number) =>
    request<Cart>(`/baskets/${basketId}/items/${itemId}`, { method: 'DELETE' }),
  setZone: (basketId: string, zoneCode: string) =>
    post<Cart>(`/baskets/${basketId}/zone`, { zone_code: zoneCode }),

  // --- Checkout ---
  lookup: (qrPayload: string) => post<Cart>('/checkout/lookup', { qr_payload: qrPayload }),
  pay: (sessionId: number, method: PaymentMethod) =>
    post<Receipt>(`/checkout/${sessionId}/pay`, { method }),
  cancelCheckout: (sessionId: number) => post<Cart>(`/checkout/${sessionId}/cancel`),

  // --- Assistant ---
  ask: (basketId: string, message: string) =>
    post<AssistantReply>('/assistant/ask', { basket_id: basketId, message }),
}
