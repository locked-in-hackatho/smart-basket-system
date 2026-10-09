/**
 * The store floor, drawn from the grid the backend serves at `/api/map`.
 *
 * One component serves three screens: the product finder (route to a shelf),
 * the basket's map tab ("where am I"), and the admin dashboard (heat map plus
 * live basket dots). The viewBox is computed from the grid, so the map always
 * scales to its container and never scrolls sideways on a phone.
 */

import { useEffect, useState } from 'react'

import { api } from '../api'
import type { StoreMapData } from '../types'

/** SVG units per grid cell. Arbitrary — the viewBox scales it to fit. */
const CELL = 10

export interface MapDot {
  id: string
  x: number
  y: number
  label?: string
}

interface Props {
  /** Pass the map in to avoid refetching it on every render. */
  map?: StoreMapData | null
  /** Path as [[x, y], ...] from the navigation endpoint. */
  path?: number[][] | null
  /** The shelf cell being navigated to — flashes with a pin. */
  target?: { x: number; y: number } | null
  /** Where this basket is. */
  position?: { x: number; y: number } | null
  /** Zone code -> 0..1 intensity, for the admin heat map. */
  heat?: Record<string, number>
  /** Other baskets, for the admin live view. */
  dots?: MapDot[]
  /** Tapping an aisle cell says "I am here". */
  onCellClick?: (x: number, y: number) => void
  className?: string
}

export default function StoreMap({
  map: given,
  path = null,
  target = null,
  position = null,
  heat,
  dots = [],
  onCellClick,
  className = '',
}: Props) {
  const [map, setMap] = useState<StoreMapData | null>(given ?? null)

  useEffect(() => {
    if (given) {
      setMap(given)
      return
    }
    if (map) return
    api
      .map()
      .then(setMap)
      .catch(() => setMap(null))
  }, [given, map])

  if (!map) {
    return (
      <div
        className={`flex aspect-[5/3] items-center justify-center rounded-2xl bg-slate-100 text-slate-400 ${className}`}
      >
        Xəritə yüklənir…
      </div>
    )
  }

  const width = map.width * CELL
  const height = map.height * CELL
  const centre = (value: number) => value * CELL + CELL / 2

  const pathD =
    path && path.length > 1
      ? path
          .map(
            ([x, y], index) =>
              `${index === 0 ? 'M' : 'L'} ${centre(x)} ${centre(y)}`,
          )
          .join(' ')
      : null

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={`block w-full rounded-2xl bg-slate-200 ${className}`}
      role="img"
      aria-label="Mağaza xəritəsi"
    >
      {/* Walls and aisles. Drawn as one rect per cell so tapping works. */}
      {map.rows.map((row, y) =>
        [...row].map((symbol, x) => {
          const isWalkable = map.walkable[y][x]
          if (!isWalkable && symbol !== '#') return null
          const clickable = isWalkable && Boolean(onCellClick)
          return (
            <rect
              key={`c-${x}-${y}`}
              data-cell={`${x},${y}`}
              x={x * CELL}
              y={y * CELL}
              width={CELL}
              height={CELL}
              fill={isWalkable ? '#f8fafc' : '#334155'}
              onClick={clickable ? () => onCellClick?.(x, y) : undefined}
              className={clickable ? 'cursor-pointer' : undefined}
            >
              {clickable && <title>Mən buradayam ({x}, {y})</title>}
            </rect>
          )
        }),
      )}

      {/* Shelf blocks, one rounded rectangle per block. */}
      {map.shelves.map((shelf) => {
        const intensity = heat?.[shelf.zone_code]
        const isTargetShelf =
          target != null &&
          shelf.cells.some((cell) => cell.x === target.x && cell.y === target.y)
        return (
          <g key={shelf.id} data-shelf={shelf.id} data-zone={shelf.zone_code}>
            <rect
              x={shelf.x * CELL + 0.6}
              y={shelf.y * CELL + 0.6}
              width={shelf.w * CELL - 1.2}
              height={shelf.h * CELL - 1.2}
              rx={2.5}
              fill={shelf.color}
              fillOpacity={
                intensity === undefined ? 0.75 : 0.18 + 0.8 * Math.min(intensity, 1)
              }
              stroke={shelf.color}
              strokeWidth={0.8}
            />
            <text
              x={shelf.x * CELL + (shelf.w * CELL) / 2}
              y={shelf.y * CELL + (shelf.h * CELL) / 2}
              textAnchor="middle"
              fontSize={shelf.w >= shelf.h ? 3.2 : 2.8}
              fontWeight={700}
              fill="#0f172a"
              fillOpacity={0.75}
              transform={
                shelf.h > shelf.w
                  ? `rotate(-90 ${shelf.x * CELL + (shelf.w * CELL) / 2} ${
                      shelf.y * CELL + (shelf.h * CELL) / 2
                    })`
                  : undefined
              }
              className="pointer-events-none select-none"
            >
              {shelf.label}
              <tspan fontWeight={500} fillOpacity={0.75}>
                {' · '}
                {shelf.zone_name}
              </tspan>
            </text>
            {intensity !== undefined && (
              <text
                x={shelf.x * CELL + 1.5}
                y={shelf.y * CELL + 4}
                fontSize={3}
                fontWeight={700}
                fill="#0f172a"
                className="pointer-events-none select-none"
              >
                {Math.round(intensity * 100)}%
              </text>
            )}
            {isTargetShelf && (
              <rect
                x={shelf.x * CELL + 0.6}
                y={shelf.y * CELL + 0.6}
                width={shelf.w * CELL - 1.2}
                height={shelf.h * CELL - 1.2}
                rx={2.5}
                fill="none"
                stroke="#0f172a"
                strokeWidth={1.4}
                strokeDasharray="3 2"
                className="animate-zone-flash pointer-events-none"
              />
            )}
          </g>
        )
      })}

      {/* Entrance and tills. */}
      <text
        x={centre(map.entrance.x)}
        y={centre(map.entrance.y) + 2.5}
        textAnchor="middle"
        fontSize={6}
        className="pointer-events-none select-none"
      >
        🚪
      </text>
      {map.checkouts.map((till) => (
        <text
          key={`t-${till.x}-${till.y}`}
          x={centre(till.x)}
          y={centre(till.y) + 2.5}
          textAnchor="middle"
          fontSize={5.5}
          className="pointer-events-none select-none"
        >
          💳
        </text>
      ))}

      {/* The route: a thick rounded line that flows towards the goal. */}
      {pathD && (
        <>
          <path
            d={pathD}
            fill="none"
            stroke="#0f172a"
            strokeOpacity={0.15}
            strokeWidth={3.4}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={pathD}
            fill="none"
            stroke="#2563eb"
            strokeWidth={2.4}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="5 3"
            className="animate-route-flow"
          />
        </>
      )}

      {/* The target shelf cell. */}
      {target && (
        <text
          x={centre(target.x)}
          y={centre(target.y) + 2.8}
          textAnchor="middle"
          fontSize={7}
          className="animate-zone-flash pointer-events-none select-none"
        >
          📍
        </text>
      )}

      {/* Other baskets (admin live view). */}
      {dots.map((dot) => (
        <g key={dot.id} className="pointer-events-none">
          <circle
            cx={centre(dot.x)}
            cy={centre(dot.y)}
            r={2.4}
            fill="#0f172a"
            stroke="#fff"
            strokeWidth={0.8}
          />
          {dot.label && (
            <text
              x={centre(dot.x)}
              y={centre(dot.y) - 3.4}
              textAnchor="middle"
              fontSize={2.6}
              fontWeight={600}
              fill="#0f172a"
            >
              {dot.label}
            </text>
          )}
        </g>
      ))}

      {/* "You are here". */}
      {position && (
        <g className="pointer-events-none" data-you-are-here={`${position.x},${position.y}`}>
          <circle
            cx={centre(position.x)}
            cy={centre(position.y)}
            r={4.5}
            fill="#3b82f6"
            fillOpacity={0.35}
            className="animate-ping-slow"
          />
          <circle
            cx={centre(position.x)}
            cy={centre(position.y)}
            r={2.6}
            fill="#2563eb"
            stroke="#fff"
            strokeWidth={1}
          />
        </g>
      )}
    </svg>
  )
}
