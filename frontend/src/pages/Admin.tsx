/**
 * The store manager's dashboard.
 *
 * Every figure here is derived from events the shopping flow already writes,
 * so a live purchase appears on the next five-second poll.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Clock,
  Database,
  Lightbulb,
  RefreshCw,
  Search,
  ShoppingBag,
  Timer,
  TrendingUp,
  Wallet,
} from 'lucide-react'

import { api, ApiError, getAdminPin, setAdminPin } from '../api'
import KpiCard from '../components/KpiCard'
import StoreMap from '../components/StoreMap'
import { useToast } from '../components/Toast'
import { Card, ErrorNote, Page, Spinner } from '../components/ui'
import { formatAZN, formatCount, formatSeconds } from '../utils/format'
import type {
  AnalyticsSummary,
  CoPurchase,
  HourlyPoint,
  Insight,
  LiveBasket,
  SearchReport,
  StoreMapData,
  TopProduct,
  ZoneStat,
} from '../types'

const REFRESH_MS = 5000

/** Single-series charts, so one hue each — never a ramp across categories. */
const SERIES_TRAFFIC = '#2a78d6'
const SERIES_PRODUCTS = '#16a34a'

interface Data {
  summary: AnalyticsSummary
  topProducts: TopProduct[]
  zones: ZoneStat[]
  hourly: HourlyPoint[]
  coPurchase: CoPurchase[]
  searches: SearchReport
  live: { baskets: LiveBasket[]; active: number }
  insights: Insight[]
}

const INSIGHT_STYLES: Record<Insight['kind'], string> = {
  win: 'border-brand-200 bg-brand-50 text-brand-900',
  demand: 'border-amber-200 bg-amber-50 text-amber-900',
  zone: 'border-red-200 bg-red-50 text-red-900',
  layout: 'border-sky-200 bg-sky-50 text-sky-900',
  findability: 'border-violet-200 bg-violet-50 text-violet-900',
}

export default function Admin() {
  const toast = useToast()
  const [data, setData] = useState<Data | null>(null)
  const [map, setMap] = useState<StoreMapData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [asTable, setAsTable] = useState<'none' | 'hourly' | 'products'>('none')

  const load = useCallback(async () => {
    try {
      const [
        summary,
        topProducts,
        zones,
        hourly,
        coPurchase,
        searches,
        live,
        insights,
      ] = await Promise.all([
        api.analytics.summary(),
        api.analytics.topProducts(),
        api.analytics.zones(),
        api.analytics.hourly(),
        api.analytics.coPurchase(),
        api.analytics.searches(),
        api.analytics.live(),
        api.analytics.insights(),
      ])
      setData({ summary, topProducts, zones, hourly, coPurchase, searches, live, insights })
      setError(null)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Məlumat alınmadı')
    }
  }, [])

  useEffect(() => {
    void load()
    const timer = window.setInterval(load, REFRESH_MS)
    return () => window.clearInterval(timer)
  }, [load])

  useEffect(() => {
    api
      .map()
      .then(setMap)
      .catch(() => setMap(null))
  }, [])

  async function runDemoAction(action: () => Promise<unknown>, message: string) {
    setBusy(true)
    try {
      try {
        await action()
      } catch (cause) {
        // The deployed app asks for a PIN before letting anyone wipe the
        // demo. Ask once, remember it for the visit, and try again.
        if (!(cause instanceof ApiError) || cause.status !== 401) throw cause
        const pin = window.prompt('Admin PIN:', getAdminPin())
        if (!pin) return
        setAdminPin(pin.trim())
        await action()
      }
      await load()
      toast.success(message)
    } catch (cause) {
      toast.error(cause instanceof ApiError ? cause.message : 'Əməliyyat alınmadı')
    } finally {
      setBusy(false)
    }
  }

  if (error && !data) {
    return (
      <Page title="Analitika paneli" wide>
        <ErrorNote message={error} onRetry={() => void load()} />
      </Page>
    )
  }
  if (!data) {
    return (
      <Page title="Analitika paneli" wide>
        <Spinner />
      </Page>
    )
  }

  const { summary, topProducts, zones, hourly, coPurchase, searches, live, insights } = data
  const heat = Object.fromEntries(zones.map((zone) => [zone.code, zone.heat]))
  const dots = live.baskets.map((basket) => ({
    id: basket.id,
    x: basket.x,
    y: basket.y,
    label: basket.id.replace('BSK-', ''),
  }))
  const peak = hourly.reduce((best, row) => (row.sessions > best.sessions ? row : best), hourly[0])

  return (
    <Page
      title="Analitika paneli"
      subtitle={`${formatCount(summary.sessions_total)} sessiya · ${live.active} səbət mağazadadır`}
      wide
      actions={
        <div className="flex gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              void runDemoAction(() => api.simulate(500), '500 sessiya yaradıldı')
            }
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
          >
            <Database className="size-4" aria-hidden />
            Demo data
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void runDemoAction(api.resetDemo, 'Baza sıfırlandı')}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw className={`size-4 ${busy ? 'animate-spin' : ''}`} aria-hidden />
            Sıfırla
          </button>
        </div>
      }
    >
      {error && (
        <div className="mb-3">
          <ErrorNote message={error} onRetry={() => void load()} />
        </div>
      )}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <KpiCard
          label="Dövriyyə (24 saat)"
          value={formatAZN(summary.revenue_qepik)}
          hint={`${summary.sessions} ödəniş`}
          icon={<Wallet className="size-4" aria-hidden />}
        />
        <KpiCard
          label="Sessiyalar"
          value={formatCount(summary.sessions_total)}
          hint={`${summary.abandoned_sessions} tərk edilib`}
          icon={<ShoppingBag className="size-4" aria-hidden />}
        />
        <KpiCard
          label="Orta səbət"
          value={formatAZN(summary.avg_basket_qepik)}
          hint={`${summary.avg_items} məhsul`}
          icon={<TrendingUp className="size-4" aria-hidden />}
        />
        <KpiCard
          label="Orta ödəniş vaxtı"
          value={`${summary.avg_checkout_seconds} san`}
          hint="QR oxunuşundan ödənişə"
          icon={<Timer className="size-4" aria-hidden />}
        />
        <KpiCard
          label="Qənaət edilmiş vaxt"
          value={`${summary.saved_hours} saat`}
          hint="ənənəvi kassa ilə müqayisədə"
          icon={<Clock className="size-4" aria-hidden />}
          highlight
        />
      </section>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Hourly traffic — one series, so no legend: the title names it. */}
        <Card>
          <div className="mb-2 flex items-start justify-between gap-2">
            <div>
              <h2 className="font-bold text-slate-900">Saatlara görə ödənişlər</h2>
              <p className="text-sm text-slate-500">
                Ən sıx saat: <strong>{peak?.label}</strong> ({peak?.sessions} ödəniş)
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAsTable(asTable === 'hourly' ? 'none' : 'hourly')}
              className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              {asTable === 'hourly' ? 'Qrafik' : 'Cədvəl'}
            </button>
          </div>

          {asTable === 'hourly' ? (
            <div className="max-h-64 overflow-y-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">Saatlara görə ödəniş sayı</caption>
                <thead className="sticky top-0 bg-white text-left text-slate-500">
                  <tr>
                    <th scope="col" className="py-1">Saat</th>
                    <th scope="col" className="py-1 text-right">Ödəniş</th>
                    <th scope="col" className="py-1 text-right">Dövriyyə</th>
                  </tr>
                </thead>
                <tbody>
                  {hourly.filter((row) => row.sessions > 0).map((row) => (
                    <tr key={row.hour} className="border-t border-slate-100">
                      <td className="py-1 tabular-nums">{row.label}</td>
                      <td className="py-1 text-right tabular-nums">{row.sessions}</td>
                      <td className="py-1 text-right tabular-nums">
                        {formatAZN(row.revenue_qepik)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={hourly} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                  interval={2}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  formatter={(value) => [`${value} ödəniş`, '']}
                  labelFormatter={(label) => `Saat ${label}`}
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }}
                />
                <Line
                  type="monotone"
                  dataKey="sessions"
                  stroke={SERIES_TRAFFIC}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Top products — one hue for every bar; length already encodes size. */}
        <Card>
          <div className="mb-2 flex items-start justify-between gap-2">
            <div>
              <h2 className="font-bold text-slate-900">Ən çox satılan məhsullar</h2>
              <p className="text-sm text-slate-500">Satılan ədəd sayına görə</p>
            </div>
            <button
              type="button"
              onClick={() => setAsTable(asTable === 'products' ? 'none' : 'products')}
              className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              {asTable === 'products' ? 'Qrafik' : 'Cədvəl'}
            </button>
          </div>

          {topProducts.length === 0 ? (
            <p className="py-16 text-center text-slate-500">Hələ satış yoxdur</p>
          ) : asTable === 'products' ? (
            <div className="max-h-64 overflow-y-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">Ən çox satılan məhsullar</caption>
                <thead className="sticky top-0 bg-white text-left text-slate-500">
                  <tr>
                    <th scope="col" className="py-1">Məhsul</th>
                    <th scope="col" className="py-1 text-right">Ədəd</th>
                    <th scope="col" className="py-1 text-right">Gəlir</th>
                  </tr>
                </thead>
                <tbody>
                  {topProducts.map((row) => (
                    <tr key={row.id} className="border-t border-slate-100">
                      <td className="py-1">{row.emoji} {row.name}</td>
                      <td className="py-1 text-right tabular-nums">{row.qty}</td>
                      <td className="py-1 text-right tabular-nums">
                        {formatAZN(row.revenue_qepik)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={topProducts}
                layout="vertical"
                margin={{ top: 4, right: 30, bottom: 0, left: 8 }}
              >
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={140}
                  // Without interval=0 Recharts drops alternate labels and the
                  // reader cannot tell which bar is which product.
                  interval={0}
                  tick={{ fontSize: 10, fill: '#334155' }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  cursor={{ fill: '#f1f5f9' }}
                  formatter={(value, _name, item) => [
                    `${value} ədəd · ${formatAZN(
                      (item?.payload as TopProduct | undefined)?.revenue_qepik ?? 0,
                    )}`,
                    '',
                  ]}
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }}
                />
                <Bar dataKey="qty" radius={[0, 4, 4, 0]} barSize={14}>
                  {topProducts.map((row) => (
                    <Cell key={row.id} fill={SERIES_PRODUCTS} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* Heat map and live baskets. */}
      <Card className="mt-4">
        <h2 className="font-bold text-slate-900">Mağaza istilik xəritəsi</h2>
        <p className="mb-2 text-sm text-slate-500">
          Tünd zonalar daha çox ziyarət olunur. Qara nöqtələr — hazırda mağazadakı
          səbətlər.
        </p>
        <StoreMap map={map} heat={heat} dots={dots} />
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Zones. */}
        <Card>
          <h2 className="font-bold text-slate-900">Zonalar</h2>
          <p className="mb-2 text-sm text-slate-500">
            Aşağı konversiyalı zonalar qırmızı işarələnib.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-slate-500">
                <tr>
                  <th scope="col" className="py-1">Zona</th>
                  <th scope="col" className="py-1 text-right">Ziyarət</th>
                  <th scope="col" className="py-1 text-right">Orta qalma</th>
                  <th scope="col" className="py-1 text-right">Konversiya</th>
                </tr>
              </thead>
              <tbody>
                {zones.map((zone) => {
                  const low = zone.conversion < 0.45 && zone.sessions > 0
                  return (
                    <tr key={zone.code} className="border-t border-slate-100">
                      <td className="py-1.5">
                        <span className="inline-flex items-center gap-2">
                          <span
                            className="size-2.5 rounded-full"
                            style={{ backgroundColor: zone.color }}
                            aria-hidden
                          />
                          {zone.name}
                        </span>
                      </td>
                      <td className="py-1.5 text-right tabular-nums">{zone.visits}</td>
                      <td className="py-1.5 text-right tabular-nums">
                        {formatSeconds(zone.avg_dwell_seconds)}
                      </td>
                      <td
                        className={`py-1.5 text-right font-semibold tabular-nums ${
                          low ? 'text-red-600' : 'text-slate-700'
                        }`}
                      >
                        {Math.round(zone.conversion * 100)}%{low && ' ▼'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Co-purchase. */}
        <Card>
          <h2 className="font-bold text-slate-900">Birlikdə alınanlar</h2>
          <p className="mb-2 text-sm text-slate-500">Eyni səbətdə ən çox rast gələn cütlər</p>
          {coPurchase.length === 0 ? (
            <p className="py-10 text-center text-slate-500">Hələ kifayət qədər data yoxdur</p>
          ) : (
            <ul className="space-y-1.5">
              {coPurchase.map((pair) => (
                <li
                  key={`${pair.a}-${pair.b}`}
                  className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm"
                >
                  <span className="min-w-0 flex-1 truncate">
                    {pair.a_emoji} {pair.a}
                  </span>
                  <span className="text-slate-400">+</span>
                  <span className="min-w-0 flex-1 truncate">
                    {pair.b_emoji} {pair.b}
                  </span>
                  <span className="shrink-0 font-bold tabular-nums text-slate-700">
                    {pair.count}×
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* The three search reports. */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card>
          <h2 className="flex items-center gap-1.5 font-bold text-slate-900">
            <Search className="size-4" aria-hidden />
            Ən çox axtarılan
          </h2>
          <p className="mb-2 text-sm text-slate-500">{searches.total} axtarış</p>
          <SearchList
            rows={searches.top.map((row) => ({ label: row.query, count: row.count }))}
            empty="Hələ axtarış yoxdur"
          />
        </Card>

        <Card>
          <h2 className="flex items-center gap-1.5 font-bold text-slate-900">
            <Search className="size-4 text-amber-600" aria-hidden />
            Axtarılıb tapılmayanlar
          </h2>
          <p className="mb-2 text-sm text-slate-500">
            Tələb siqnalı · {searches.not_found_total} sorğu
          </p>
          <SearchList
            rows={searches.not_found.map((row) => ({ label: row.query, count: row.count }))}
            empty="Hamısı tapılıb"
            tone="amber"
          />
        </Card>

        <Card>
          <h2 className="flex items-center gap-1.5 font-bold text-slate-900">
            <Search className="size-4 text-violet-600" aria-hidden />
            Ən çox yolu soruşulan
          </h2>
          <p className="mb-2 text-sm text-slate-500">
            Müştərilər bu məhsulları çətin tapır, yerini dəyişməyi düşünün.
          </p>
          <SearchList
            rows={searches.most_routed.map((row) => ({
              label: `${row.emoji} ${row.name}`,
              hint: row.aisle,
              count: row.count,
            }))}
            empty="Hələ yol sorğusu yoxdur"
            tone="violet"
          />
        </Card>
      </div>

      {/* Recommendations. */}
      <Card className="mt-4">
        <h2 className="flex items-center gap-1.5 font-bold text-slate-900">
          <Lightbulb className="size-4" aria-hidden />
          Tövsiyələr
        </h2>
        <p className="mb-2 text-sm text-slate-500">
          Hər tövsiyə bu səhifədəki rəqəmlərdən çıxarılıb — mənbəyi yoxlanıla bilər.
        </p>
        {insights.length === 0 ? (
          <p className="py-8 text-center text-slate-500">
            Tövsiyə vermək üçün hələ kifayət qədər data yoxdur. “Demo data” düyməsinə
            toxunun.
          </p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {insights.map((tip) => (
              <li
                key={tip.title}
                className={`rounded-2xl border px-4 py-3 ${INSIGHT_STYLES[tip.kind]}`}
              >
                <p className="font-semibold">{tip.title}</p>
                <p className="mt-0.5 text-sm opacity-90">{tip.detail}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </Page>
  )
}

function SearchList({
  rows,
  empty,
  tone = 'slate',
}: {
  rows: { label: string; hint?: string; count: number }[]
  empty: string
  tone?: 'slate' | 'amber' | 'violet'
}) {
  const badge = {
    slate: 'bg-slate-100 text-slate-700',
    amber: 'bg-amber-100 text-amber-800',
    violet: 'bg-violet-100 text-violet-800',
  }[tone]

  if (rows.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-500">{empty}</p>
  }
  return (
    <ul className="space-y-1.5">
      {rows.map((row) => (
        <li key={row.label} className="flex items-center gap-2 text-sm">
          <span className="min-w-0 flex-1 truncate">
            {row.label}
            {row.hint && <span className="text-slate-400"> · {row.hint}</span>}
          </span>
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${badge}`}>
            {row.count}
          </span>
        </li>
      ))}
    </ul>
  )
}
