/** An EAN-13 barcode drawn as SVG, so it stays crisp when printed. */

import { useEffect, useRef } from 'react'
import JsBarcode from 'jsbarcode'

interface Props {
  value: string
  width?: number
  height?: number
  /** jsbarcode draws the digits itself; turn it off for a custom caption. */
  displayValue?: boolean
}

export default function Barcode({
  value,
  width = 1.6,
  height = 52,
  displayValue = true,
}: Props) {
  const ref = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!ref.current) return
    try {
      JsBarcode(ref.current, value, {
        format: 'EAN13',
        width,
        height,
        displayValue,
        fontSize: 13,
        margin: 4,
        background: '#ffffff',
        lineColor: '#000000',
      })
    } catch {
      // An invalid code should not take the page down; the caption below
      // still shows the digits so the product is identifiable.
    }
  }, [value, width, height, displayValue])

  return <svg ref={ref} role="img" aria-label={`Barkod ${value}`} />
}
