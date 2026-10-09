/**
 * The store floor as an SVG, built from the zones' grid coordinates.
 *
 * One component serves three screens: the basket (where am I, where is the
 * thing I asked about), the assistant (highlight a zone) and the admin
 * dashboard (heat map plus live basket dots).
 */

import { useEffect, useState } from 'react'

import { api } from '../api'
import type { Zone } from '../types'

/** Grid cell size in SVG units. The grid itself is 12 x 8. */
const CELL = 100
const GRID_W = 12
const GRID_H = 8

export interface MapDot {
  id: string
  zoneCode: string
  label?: string
}

interface Props {
  /** Pass zones in to avoid refetching; otherwise the map loads them itself. */
  zones?: Zone[]
  /** Zone code to flash — "the milk is over there". */
  highlightZone?: string | null
  /** Zone code the basket is in — "you are here". */
  currentZone?: string | null
  /** Zone code -> 0..1 intensity, for the admin heat map. */
  heat?: Record<string, number>
  /** Live baskets to draw as dots. */
  dots?: MapDot[]
  onZoneClick?: (zone: Zone) => void
  className?: string
}

/** SVG text does not wrap, so split the label into lines that fit the zone. */
function wrap(name: string, zoneWidth: number, fontSize: number): string[] {
  const maxChars = Math.max(6, Math.floor((zoneWidth * CELL - 16) / (fontSize * 0.5)))
  const lines: string[] = []
  let line = ''
  for (const word of name.split(' ')) {
    const candidate = line ? `${line} ${word}` : word
    if (candidate.length > maxChars && line) {
      lines.push(line)
      line = word
    } else {
      line = candidate
    }
  }
  if (line) lines.push(line)
  return lines.slice(0, 3)
}

export default function StoreMap({
  zones: given,
  highlightZone = null,
  currentZone = null,
  heat,
  dots = [],
  onZoneClick,
  className = '',
}: Props) {
  const [zones, setZones] = useState<Zone[]>(given ?? [])

  useEffect(() => {
    if (given) {
      setZones(given)
      return
    }
    api
      .zones()
      .then(setZones)
      .catch(() => setZones([]))
  }, [given])

  if (zones.length === 0) {
    return (
      <div
        className={`flex aspect-[3/2] items-center justify-center rounded-2xl bg-slate-100 text-slate-400 ${className}`}
      >
        Xəritə yüklənir…
      </div>
    )
  }

  const byCode = new Map(zones.map((zone) => [zone.code, zone]))
  const dotsByZone = new Map<string, MapDot[]>()
  for (const dot of dots) {
    if (!byCode.has(dot.zoneCode)) continue
    dotsByZone.set(dot.zoneCode, [...(dotsByZone.get(dot.zoneCode) ?? []), dot])
  }

  return (
    <svg
      viewBox={`0 0 ${GRID_W * CELL} ${GRID_H * CELL}`}
      className={`w-full rounded-2xl bg-slate-100 ${className}`}
      role="img"
      aria-label="Mağaza xəritəsi"
    >
      {zones.map((zone) => {
        const isCurrent = zone.code === currentZone
        const isHighlight = zone.code === highlightZone
        const intensity = heat?.[zone.code]
        const fontSize = zone.w >= 4 ? 25 : 22
        const lines = wrap(zone.name, zone.w, fontSize)
        const centreX = (zone.x + zone.w / 2) * CELL
        const centreY = (zone.y + zone.h / 2) * CELL
        const clickable = Boolean(onZoneClick)

        return (
          <g
            key={zone.id}
            data-zone={zone.code}
            onClick={clickable ? () => onZoneClick?.(zone) : undefined}
            className={clickable ? 'cursor-pointer' : undefined}
            role={clickable ? 'button' : undefined}
            aria-label={clickable ? `${zone.name} zonasına keç` : undefined}
          >
            <rect
              x={zone.x * CELL + 6}
              y={zone.y * CELL + 6}
              width={zone.w * CELL - 12}
              height={zone.h * CELL - 12}
              rx={14}
              fill={zone.color}
              // With a heat map the fill carries the value; otherwise zones
              // stay muted so the dots and the highlight stand out.
              fillOpacity={
                intensity === undefined ? 0.18 : 0.12 + 0.78 * Math.min(intensity, 1)
              }
              stroke={zone.color}
              strokeWidth={isCurrent ? 6 : 3}
              strokeOpacity={isCurrent ? 1 : 0.55}
              className={isHighlight ? 'animate-zone-flash' : undefined}
            />

            {isHighlight && (
              <rect
                x={zone.x * CELL + 6}
                y={zone.y * CELL + 6}
                width={zone.w * CELL - 12}
                height={zone.h * CELL - 12}
                rx={14}
                fill="none"
                stroke="#0f172a"
                strokeWidth={6}
                strokeDasharray="18 12"
                className="animate-zone-flash"
              />
            )}

            <text
              x={centreX}
              y={centreY - (lines.length - 1) * (fontSize * 0.6)}
              textAnchor="middle"
              fontSize={fontSize}
              fontWeight={600}
              fill="#0f172a"
              className="pointer-events-none select-none"
            >
              {lines.map((line, index) => (
                <tspan key={line} x={centreX} dy={index === 0 ? 0 : fontSize * 1.15}>
                  {line}
                </tspan>
              ))}
            </text>

            {zone.kind !== 'sales' && (
              <text
                x={centreX}
                y={(zone.y + zone.h) * CELL - 22}
                textAnchor="middle"
                fontSize={30}
                className="pointer-events-none select-none"
              >
                {zone.kind === 'entrance' ? '🚪' : '💳'}
              </text>
            )}

            {intensity !== undefined && (
              <text
                x={zone.x * CELL + 18}
                y={zone.y * CELL + 34}
                fontSize={18}
                fontWeight={700}
                fill="#0f172a"
                fillOpacity={0.55}
                className="pointer-events-none select-none"
              >
                {Math.round(intensity * 100)}%
              </text>
            )}

            {/* Live baskets, fanned out so several in one zone stay readable. */}
            {(dotsByZone.get(zone.code) ?? []).map((dot, index, all) => {
              const spread = (index - (all.length - 1) / 2) * 42
              return (
                <g key={dot.id}>
                  <circle
                    cx={centreX + spread}
                    cy={centreY + fontSize * 1.6}
                    r={14}
                    fill="#0f172a"
                    stroke="#fff"
                    strokeWidth={3}
                  />
                  {dot.label && (
                    <text
                      x={centreX + spread}
                      y={centreY + fontSize * 1.6 + 32}
                      textAnchor="middle"
                      fontSize={15}
                      fill="#0f172a"
                      className="pointer-events-none select-none"
                    >
                      {dot.label}
                    </text>
                  )}
                </g>
              )
            })}

            {/* "You are here". */}
            {isCurrent && (
              <g className="pointer-events-none">
                <circle
                  cx={centreX}
                  cy={centreY + fontSize * 1.7}
                  r={26}
                  fill={zone.color}
                  fillOpacity={0.35}
                  className="animate-ping-slow"
                />
                <circle
                  cx={centreX}
                  cy={centreY + fontSize * 1.7}
                  r={13}
                  fill="#16a34a"
                  stroke="#fff"
                  strokeWidth={4}
                />
              </g>
            )}
          </g>
        )
      })}
    </svg>
  )
}
