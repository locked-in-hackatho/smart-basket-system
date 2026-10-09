/**
 * The basket's QR code, big enough for the till camera to read straight off
 * the screen — the fallback when the printed sticker is not to hand.
 */

import { QRCodeSVG } from 'qrcode.react'
import { X } from 'lucide-react'

export const qrPayload = (basketId: string) => `SMARTBASKET:${basketId}`

export default function QrModal({
  basketId,
  onClose,
}: {
  basketId: string
  onClose: () => void
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`${basketId} QR kodu`}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-3xl bg-white p-6 text-center shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div className="text-left">
            <p className="text-sm text-slate-500">Kassada bu kodu oxudun</p>
            <p className="font-mono text-xl font-bold">{basketId}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Bağla"
            className="flex size-11 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>

        <div className="mt-4 flex justify-center rounded-2xl bg-white p-3 ring-1 ring-slate-200">
          <QRCodeSVG value={qrPayload(basketId)} size={232} level="M" marginSize={2} />
        </div>

        <p className="mt-3 break-all font-mono text-xs text-slate-400">
          {qrPayload(basketId)}
        </p>
      </div>
    </div>
  )
}
