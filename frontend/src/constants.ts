/**
 * Tunable assumptions used in the pitch. Keep them here, and keep them
 * honest: these are estimates, not measurements, and the slide that uses
 * them should say so out loud.
 */

/**
 * How long a traditional till takes for one basket:
 * a fixed overhead (greeting, bagging, opening the payment terminal) plus a
 * per-item scan time.
 *
 * ASSUMPTION — not measured by us. Retail studies commonly quote 2–4 seconds
 * per item at a staffed till. We use the middle of that range and a 20 s
 * overhead. Cite a source when presenting, or label it clearly as an estimate.
 */
export const TRADITIONAL_CHECKOUT_BASE_SECONDS = 20
export const TRADITIONAL_CHECKOUT_SECONDS_PER_ITEM = 3

/** The estimate the Smart Basket time saving is measured against. */
export function traditionalCheckoutSeconds(itemCount: number): number {
  return (
    TRADITIONAL_CHECKOUT_BASE_SECONDS +
    TRADITIONAL_CHECKOUT_SECONDS_PER_ITEM * itemCount
  )
}

/** Seconds saved on one basket, never negative. */
export function secondsSaved(itemCount: number, actualSeconds: number): number {
  return Math.max(traditionalCheckoutSeconds(itemCount) - actualSeconds, 0)
}

/** How long the receipt stays up before the till returns to scan mode. */
export const NEXT_CUSTOMER_MS = 5000
