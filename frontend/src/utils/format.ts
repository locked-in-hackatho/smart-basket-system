/** Display helpers. The backend owns the numbers; we only format them. */

/** 1250 -> "12.50 ₼" */
export function formatAZN(qepik: number): string {
  const sign = qepik < 0 ? '-' : ''
  const absolute = Math.abs(Math.round(qepik))
  const manat = Math.floor(absolute / 100)
  const remainder = absolute % 100
  return `${sign}${manat}.${String(remainder).padStart(2, '0')} ₼`
}

/** 65 -> "1 dəq 5 san", 42 -> "42 san" */
export function formatSeconds(seconds: number): string {
  const total = Math.max(0, Math.round(seconds))
  if (total < 60) return `${total} san`
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return rest === 0 ? `${minutes} dəq` : `${minutes} dəq ${rest} san`
}

/** 9000 -> "2.5 saat" — used for the "time saved" KPI. */
export function formatHours(seconds: number): string {
  const hours = seconds / 3600
  if (hours < 1) return `${Math.round(seconds / 60)} dəq`
  return `${hours.toFixed(1)} saat`
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('az-AZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleTimeString('az-AZ', { hour: '2-digit', minute: '2-digit' })
}

/** 1234 -> "1 234" */
export function formatCount(value: number): string {
  return Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

export const BASKET_STATUS_LABEL: Record<string, string> = {
  idle: 'Boş',
  active: 'Alış-veriş gedir',
  checkout: 'Kassada',
}
