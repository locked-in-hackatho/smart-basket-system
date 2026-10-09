/** Shapes returned by the backend. Money is always whole qepik. */

export type BasketStatus = 'idle' | 'active' | 'checkout'
export type PaymentMethod = 'cash' | 'card'
export type ScanMode = 'add' | 'remove'

export interface Health {
  status: string
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
  position: { x: number; y: number }
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
  pos_x: number | null
  pos_y: number | null
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

export interface MapShelf {
  id: number
  label: string
  zone_code: string
  zone_name: string
  color: string
  cells: { x: number; y: number }[]
  x: number
  y: number
  w: number
  h: number
}

export interface StoreMapData {
  width: number
  height: number
  rows: string[]
  walkable: boolean[][]
  entrance: { x: number; y: number }
  checkouts: { x: number; y: number }[]
  zones: { code: string; name: string; color: string }[]
  shelves: MapShelf[]
}

/** A product as the search endpoint returns it. */
export interface FoundProduct {
  id: number
  barcode: string
  name: string
  category: string
  price_qepik: number
  emoji: string
  stock: number
  zone_code: string | null
  zone_name: string | null
  aisle: string
  level: string
  shelf_x: number | null
  shelf_y: number | null
  pick_x: number | null
  pick_y: number | null
  shelf_id: number | null
  distance_m: number | null
  score?: number
}

export interface SearchResponse {
  query: string
  found: boolean
  results: FoundProduct[]
  suggestions: FoundProduct[]
}

export interface RouteResponse {
  start: { x: number; y: number }
  goal: { x: number; y: number }
  path: number[][]
  distance_m: number
  eta_seconds: number
  steps: string[]
  product: FoundProduct
  shelf: { id: number; label: string; level: string; x: number; y: number }
}

// --- Analytics ------------------------------------------------------------

export interface AnalyticsSummary {
  revenue_qepik: number
  sessions: number
  sessions_total: number
  avg_basket_qepik: number
  avg_items: number
  avg_checkout_seconds: number
  saved_seconds: number
  saved_hours: number
  abandoned_sessions: number
}

export interface TopProduct {
  id: number
  name: string
  emoji: string
  category: string
  qty: number
  revenue_qepik: number
}

export interface ZoneStat {
  code: string
  name: string
  color: string
  visits: number
  sessions: number
  avg_dwell_seconds: number
  conversion: number
  heat: number
}

export interface HourlyPoint {
  hour: number
  label: string
  sessions: number
  revenue_qepik: number
}

export interface CoPurchase {
  a: string
  a_emoji: string
  b: string
  b_emoji: string
  count: number
}

export interface SearchReport {
  top: { query: string; count: number }[]
  not_found: { query: string; count: number }[]
  most_routed: {
    id: number
    name: string
    emoji: string
    aisle: string
    zone: string
    count: number
  }[]
  total: number
  not_found_total: number
}

export interface LiveBasket {
  id: string
  status: BasketStatus
  x: number
  y: number
  zone_name: string | null
  item_count: number
  total_qepik: number
}

export interface Insight {
  kind: 'zone' | 'layout' | 'demand' | 'findability' | 'win'
  title: string
  detail: string
}
