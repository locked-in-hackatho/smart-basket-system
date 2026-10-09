/**
 * Typed API client. Every call goes through `/api`, which Vite proxies to the
 * backend, so a phone only ever needs the frontend's address.
 *
 * Errors are thrown as `ApiError` carrying the backend's Azerbaijani
 * `detail` message, ready to show in a toast.
 */

import type {
  AnalyticsSummary,
  BasketSummary,
  CoPurchase,
  Cart,
  Health,
  HourlyPoint,
  Insight,
  LiveBasket,
  PaymentMethod,
  Product,
  Receipt,
  RouteResponse,
  ScanMode,
  SearchReport,
  SearchResponse,
  StoreMapData,
  TopProduct,
  Zone,
  ZoneStat,
} from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * The deployed app gates its destructive endpoints behind an admin PIN.
 * It is kept in sessionStorage so the dashboard asks once per visit, never
 * in the code, and never for a local run (where no PIN is configured).
 */
const PIN_KEY = 'smartbasket.adminPin'

export function getAdminPin(): string {
  try {
    return sessionStorage.getItem(PIN_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setAdminPin(pin: string): void {
  try {
    sessionStorage.setItem(PIN_KEY, pin)
  } catch {
    // Private browsing: the PIN simply will not be remembered.
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    const pin = getAdminPin()
    response = await fetch(`/api${path}`, {
      ...init,
      headers: {
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...(pin ? { 'X-Admin-Pin': pin } : {}),
        ...(init?.headers as Record<string, string> | undefined),
      },
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
  setPosition: (basketId: string, x: number, y: number) =>
    post<Cart>(`/baskets/${basketId}/position`, { x, y }),

  // --- Checkout ---
  lookup: (qrPayload: string) => post<Cart>('/checkout/lookup', { qr_payload: qrPayload }),
  pay: (sessionId: number, method: PaymentMethod) =>
    post<Receipt>(`/checkout/${sessionId}/pay`, { method }),
  cancelCheckout: (sessionId: number) => post<Cart>(`/checkout/${sessionId}/cancel`),

  // --- Map, search and navigation ---
  map: () => request<StoreMapData>('/map'),
  search: (query: string, basketId?: string) =>
    request<SearchResponse>(
      `/products/search?q=${encodeURIComponent(query)}` +
        (basketId ? `&basket_id=${encodeURIComponent(basketId)}` : ''),
    ),
  route: (basketId: string, productId: number) =>
    request<RouteResponse>(
      `/navigation/route?basket_id=${encodeURIComponent(basketId)}&product_id=${productId}`,
    ),

  // --- Analytics ---
  analytics: {
    summary: () => request<AnalyticsSummary>('/analytics/summary'),
    topProducts: () => request<TopProduct[]>('/analytics/top-products'),
    zones: () => request<ZoneStat[]>('/analytics/zones'),
    hourly: () => request<HourlyPoint[]>('/analytics/hourly'),
    coPurchase: () => request<CoPurchase[]>('/analytics/co-purchase'),
    searches: () => request<SearchReport>('/analytics/searches'),
    live: () => request<{ baskets: LiveBasket[]; active: number }>('/analytics/live'),
    insights: () => request<Insight[]>('/analytics/insights'),
  },

  // --- Demo helpers ---
  simulate: (sessions = 500) =>
    post<Record<string, unknown>>(`/dev/simulate?sessions=${sessions}`),
  resetDemo: () => post<Record<string, unknown>>('/dev/reset'),
}
