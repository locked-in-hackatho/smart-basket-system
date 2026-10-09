/** Shapes returned by the backend. Money is always whole qepik. */

export type AiMode = 'ai' | 'offline'
export type BasketStatus = 'idle' | 'active' | 'checkout'
export type PaymentMethod = 'cash' | 'card'
export type ScanMode = 'add' | 'remove'

export interface Health {
  status: string
  ai_mode: AiMode
  store_name: string
}

export interface Zone {
  id: number
  code: string
  name: string
  x: number
  y: number
  w: number
  h: number
  color: string
  kind: 'sales' | 'entrance' | 'checkout'
}

export interface Product {
  id: number
  barcode: string
  name: string
  category: string
  price_qepik: number
  zone_id: number | null
  zone_code: string | null
  zone_name: string | null
  aisle: string
  shelf: string
  stock: number
  emoji: string
}

export interface CartItem {
  item_id: number
  qty: number
  line_total_qepik: number
  product: Product
}

export interface CurrentZone {
  id: number
  code: string
  name: string
}

/** The one source of truth for what a basket holds and costs. */
export interface Cart {
  basket_id: string
  session_id: number | null
  status: BasketStatus
  items: CartItem[]
  item_count: number
  total_qepik: number
  current_zone: CurrentZone | null
  last_seen_at: string
  /** Only present on a scan response, for the toast and the beep. */
  scanned_product?: Pick<Product, 'id' | 'name' | 'emoji' | 'price_qepik'>
  mode?: ScanMode
  checkout_started_at?: string | null
}

export interface BasketSummary {
  id: string
  status: BasketStatus
  current_session_id: number | null
  current_zone_id: number | null
  current_zone_code: string | null
  current_zone_name: string | null
  item_count: number
  total_qepik: number
  last_seen_at: string
}

export interface Receipt {
  payment_id: number
  session_id: number
  basket_id: string
  store_name: string
  method: PaymentMethod
  amount_qepik: number
  item_count: number
  items: CartItem[]
  checkout_seconds: number
  paid_at: string
}

export interface AssistantProduct {
  id: number
  barcode: string
  name: string
  category: string
  price_qepik: number
  price_azn: string
  zone_code: string | null
  zone_name: string | null
  aisle: string
  shelf: string
  stock: number
  emoji: string
}

export interface AssistantReply {
  answer: string
  products: AssistantProduct[]
  highlight_zone: string | null
  mode: AiMode
  found: boolean
}
