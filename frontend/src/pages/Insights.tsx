/**
 * Predictive analytics: what the models expect to happen next.
 *
 * Everything on this page is produced by models fitted on **synthetic**
 * trip data, and the page says so at the top and beside every figure that
 * could be mistaken for a measurement. The models only ever see what a
 * basket's scanner and position sensor could record — the provenance panel
 * lists each feature and where it would come from in a real shop.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  AlertTriangle,
  Boxes,
  Brain,
  FlaskConical,
  Layers,
  Link2,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
} from 'lucide-react'

import { api, ApiError } from '../api'
import { useToast } from '../components/Toast'
import { Card, ErrorNote, Page, Spinner } from '../components/ui'
import { formatAZN, formatCount } from '../utils/format'
import type {
  ForecastDay,
  MlAnomaly,
  MlInventoryRow,
  MlRiskBasket,
  MlRule,
  MlSegment,
  MlSummary,
} from '../types'

/** Two series on one axis, both in manat. Validated for contrast and CVD. */
const SERIES_FORECAST = '#2a78d6'
const SERIES_LAST_WEEK = '#eb6834'

const WEEKDAYS = ['B.e', 'Ç.a', 'Çər', 'C.a', 'Cümə', 'Şən', 'Baz']

interface Data {
  summary: MlSummary
  forecast: { days: ForecastDay[]; total_qepik: number; metrics: Record<string, number> }
  segments: { segments: MlSegment[]; metrics: Record<string, number> }
  anomalies: { anomalies: MlAnomaly[] }
  rules: { rules: MlRule[] }
  inventory: { products: MlInventoryRow[]; critical: number; warning: number; note: string }
  risk: {
    baskets: MlRiskBasket[]
    threshold: number
    drivers: { feature: string; importance: number }[]
    metrics: Record<string, number>
  }
}

export default function Insights() {
  const toast = useToast()
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const [summary, forecast, segments, anomalies, rules, inventory, risk] =
        await Promise.all([
          api.ml.summary(),
          api.ml.forecast(),
          api.ml.segments(),
          api.ml.anomalies(),
          api.ml.rules(),
          api.ml.inventory(),
          api.ml.risk(),
        ])
      setData({ summary, forecast, segments, anomalies, rules, inventory, risk })
      setError(null)
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Modellər yüklənmədi')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function retrain() {
    setBusy(true)
    try {
      await api.ml.retrain()
      await load()
      toast.success('Modellər yenidən öyrədildi')
    } catch (cause) {
      toast.error(cause instanceof ApiError ? cause.message : 'Öyrətmə alınmadı')
    } finally {
      setBusy(false)
    }
  }

  if (error && !data) {
    return (
      <Page title="Proqnoz və ML" wide>
        <ErrorNote message={error} onRetry={() => void load()} />
      </Page>
    )
  }
  if (!data) {
    return (
      <Page title="Proqnoz və ML" wide>
        <Spinner label="Modellər öyrədilir — bir neçə saniyə çəkir…" />
      </Page>
    )
  }

  const { summary, forecast, segments, anomalies, rules, inventory, risk } = data
  const supervised = summary.models.filter((m) => m.kind === 'supervised')
  const unsupervised = summary.models.filter((m) => m.kind === 'unsupervised')

  const chartData = forecast.days.map((day) => ({
    label: WEEKDAYS[day.weekday],
    date: day.date,
    proqnoz: day.forecast_qepik / 100,
    'keçən həftə': (day.last_week_qepik ?? 0) / 100,
    change: day.change_pct,
  }))

  return (
    <Page
      title="Proqnoz və ML"
      subtitle={`${formatCount(summary.training_rows)} səfər · ${summary.training_days} gün`}
      wide
      actions={
        <button
          type="button"
          disabled={busy}
          onClick={() => void retrain()}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw className={`size-4 ${busy ? 'animate-spin' : ''}`} aria-hidden />
          Yenidən öyrət
        </button>
      }
    >
      {/* The disclaimer is the first thing on the page, not a footnote. */}
      <section className="flex flex-wrap items-start gap-3 rounded-2xl border-2 border-amber-300 bg-amber-50 p-4">
        <FlaskConical className="size-6 shrink-0 text-amber-700" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="font-bold text-amber-900">
            Bu səhifədəki bütün rəqəmlər SİNTETİK datadan alınıb
          </p>
          <p className="mt-0.5 text-sm text-amber-900/90">
            Real müştəri məlumatı deyil. {formatCount(summary.training_rows)} süni
            alış-veriş səfəri yaradılıb və modellər onun üzərində öyrədilib. Məqsəd —
            sistem real mağazada işləyəndə nə verəcəyini göstərməkdir.
          </p>
          <p className="mt-2 text-sm font-semibold text-amber-900">
            Modellər yalnız skanerin görə biləcəyini bilir. Kənarda saxlanılan:{' '}
            {summary.excluded.join(' · ')} — barkod bunları oxuya bilmir.
          </p>
        </div>
      </section>

      {/* The pipeline itself. */}
      <section className="mt-4">
        <h2 className="flex items-center gap-2 font-bold text-slate-900">
          <Brain className="size-5" aria-hidden />
          ML boru xətti
        </h2>
        <p className="mb-2 text-sm text-slate-500">
          İki nəzarətli, iki nəzarətsiz model. Metrikalar ayrılmış test hissəsində
          ölçülüb.
        </p>
        <div className="grid gap-3 lg:grid-cols-2">
          <ModelGroup title="Nəzarətli öyrənmə (supervised)" models={supervised} tone="brand" />
          <ModelGroup
            title="Nəzarətsiz öyrənmə (unsupervised)"
            models={unsupervised}
            tone="violet"
          />
        </div>
      </section>

      {/* Forecast. */}
      <Card className="mt-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 className="flex items-center gap-2 font-bold text-slate-900">
              <TrendingUp className="size-5" aria-hidden />
              7 günlük dövriyyə proqnozu
            </h2>
            <p className="text-sm text-slate-500">
              Gradient Boosting · sadə üsuldan{' '}
              <strong className="text-brand-700">
                {forecast.metrics.improvement_vs_naive_pct}% daha dəqiq
              </strong>{' '}
              (“keçən həftənin eyni saatı” ilə müqayisədə)
            </p>
          </div>
          <p className="text-right">
            <span className="block text-xs font-medium text-slate-500">Həftəlik gözlənti</span>
            <span className="text-2xl font-extrabold tabular-nums text-slate-900">
              {formatAZN(forecast.total_qepik)}
            </span>
          </p>
        </div>

        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} margin={{ top: 16, right: 8, bottom: 0, left: -12 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12, fill: '#64748b' }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={false}
              width={52}
            />
            <Tooltip
              cursor={{ fill: '#f1f5f9' }}
              formatter={(value) => [`${Number(value).toFixed(0)} ₼`, '']}
              labelFormatter={(label, payload) =>
                payload?.[0] ? `${label} · ${payload[0].payload.date}` : String(label)
              }
              contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="keçən həftə" fill={SERIES_LAST_WEEK} radius={[4, 4, 0, 0]} />
            <Bar dataKey="proqnoz" fill={SERIES_FORECAST} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Günlük dövriyyə proqnozu</caption>
            <thead className="text-left text-slate-500">
              <tr>
                <th scope="col" className="py-1">Gün</th>
                <th scope="col" className="py-1 text-right">Proqnoz</th>
                <th scope="col" className="py-1 text-right">Keçən həftə</th>
                <th scope="col" className="py-1 text-right">Dəyişim</th>
              </tr>
            </thead>
            <tbody>
              {forecast.days.map((day) => (
                <tr key={day.date} className="border-t border-slate-100">
                  <td className="py-1.5">
                    {WEEKDAYS[day.weekday]} <span className="text-slate-400">{day.date}</span>
                  </td>
                  <td className="py-1.5 text-right font-semibold tabular-nums">
                    {formatAZN(day.forecast_qepik)}
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-slate-500">
                    {day.last_week_qepik ? formatAZN(day.last_week_qepik) : '—'}
                  </td>
                  <td
                    className={`py-1.5 text-right font-semibold tabular-nums ${
                      (day.change_pct ?? 0) >= 0 ? 'text-brand-700' : 'text-red-600'
                    }`}
                  >
                    {day.change_pct === null ? '—' : `${day.change_pct > 0 ? '+' : ''}${day.change_pct}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Segments. */}
        <Card>
          <h2 className="flex items-center gap-2 font-bold text-slate-900">
            <Layers className="size-5" aria-hidden />
            Alış-veriş davranışı qrupları
          </h2>
          <p className="mb-3 text-sm text-slate-500">
            K-Means · k={segments.metrics.k} (silhouette {segments.metrics.silhouette}).
            Bunlar <strong>davranış</strong> qruplarıdır, insan qrupları deyil — sistem
            müştərinin kim olduğunu bilmir.
          </p>
          <ul className="space-y-2">
            {segments.segments.map((segment) => (
              <li
                key={segment.cluster}
                className="rounded-2xl border border-slate-200 px-4 py-3"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <p className="font-bold text-slate-900">{segment.name}</p>
                  <p className="text-lg font-extrabold tabular-nums text-brand-700">
                    {Math.round(segment.share * 100)}%
                  </p>
                </div>
                <p className="text-sm text-slate-500">{segment.description}</p>
                <div
                  className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100"
                  role="presentation"
                >
                  <div
                    className="h-full rounded-full bg-brand-600"
                    style={{ width: `${segment.share * 100}%` }}
                  />
                </div>
                <dl className="mt-2 grid grid-cols-4 gap-2 text-xs">
                  <Stat label="Məhsul" value={String(segment.avg_items)} />
                  <Stat label="Səbət" value={formatAZN(segment.avg_value_qepik)} />
                  <Stat label="Müddət" value={`${segment.avg_minutes} dəq`} />
                  <Stat label="Pik saat" value={`${segment.peak_hour}:00`} />
                </dl>
              </li>
            ))}
          </ul>
        </Card>

        {/* Anomalies. */}
        <Card>
          <h2 className="flex items-center gap-2 font-bold text-slate-900">
            <AlertTriangle className="size-5" aria-hidden />
            Qeyri-adi saatlar
          </h2>
          <p className="mb-3 text-sm text-slate-500">
            Isolation Forest · {anomalies.anomalies.length} saat normadan kənar. Sadəcə
            “sıx” saat deyil — davranışı bütövlükdə fərqli olan saat.
          </p>
          {anomalies.anomalies.length === 0 ? (
            <p className="py-8 text-center text-slate-500">Anomaliya tapılmadı</p>
          ) : (
            <ul className="space-y-1.5">
              {anomalies.anomalies.slice(0, 8).map((anomaly) => (
                <li
                  key={anomaly.ts}
                  className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="font-mono text-sm font-semibold text-amber-900">
                      {anomaly.ts.slice(0, 10)} · {anomaly.ts.slice(11, 16)}
                    </p>
                    <p className="text-xs tabular-nums text-amber-800">
                      {anomaly.trips} səfər · {formatAZN(anomaly.revenue_qepik)}
                    </p>
                  </div>
                  <p className="text-sm text-amber-900/90">{anomaly.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* Inventory. */}
        <Card>
          <h2 className="flex items-center gap-2 font-bold text-slate-900">
            <Boxes className="size-5" aria-hidden />
            Stok riski
          </h2>
          <p className="mb-2 text-sm text-slate-500">
            {inventory.note} <strong className="text-red-700">{inventory.critical} kritik</strong>,{' '}
            {inventory.warning} xəbərdarlıq.
          </p>
          <div className="max-h-80 overflow-y-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Məhsullar üzrə stok riski</caption>
              <thead className="sticky top-0 bg-white text-left text-slate-500">
                <tr>
                  <th scope="col" className="py-1">Məhsul</th>
                  <th scope="col" className="py-1 text-right">Stok</th>
                  <th scope="col" className="py-1 text-right">Gündəlik</th>
                  <th scope="col" className="py-1 text-right">Qalan</th>
                  <th scope="col" className="py-1 text-right">Sifariş</th>
                </tr>
              </thead>
              <tbody>
                {inventory.products.slice(0, 20).map((row) => (
                  <tr key={row.product} className="border-t border-slate-100">
                    <td className="py-1.5 pr-2">
                      <span className="flex items-center gap-1.5">
                        <span
                          className={`size-2 shrink-0 rounded-full ${
                            row.risk === 'critical'
                              ? 'bg-red-500'
                              : row.risk === 'warning'
                                ? 'bg-amber-500'
                                : 'bg-brand-500'
                          }`}
                          aria-hidden
                        />
                        <span className="truncate">{row.product}</span>
                      </span>
                    </td>
                    <td className="py-1.5 text-right tabular-nums">{row.stock}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-500">
                      {row.daily_sales}
                    </td>
                    <td
                      className={`py-1.5 text-right font-semibold tabular-nums ${
                        row.risk === 'critical'
                          ? 'text-red-600'
                          : row.risk === 'warning'
                            ? 'text-amber-700'
                            : 'text-slate-700'
                      }`}
                    >
                      {row.days_left} gün
                    </td>
                    <td className="py-1.5 text-right tabular-nums">{row.reorder_units}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Association rules. */}
        <Card>
          <h2 className="flex items-center gap-2 font-bold text-slate-900">
            <Link2 className="size-5" aria-hidden />
            Birlikdə alınan məhsullar
          </h2>
          <p className="mb-2 text-sm text-slate-500">
            Assosiasiya qaydaları · <strong>lift</strong> = təsadüfi gözləntidən neçə dəfə
            çox birlikdə alınır.
          </p>
          <ul className="space-y-1.5">
            {rules.rules.slice(0, 8).map((rule) => (
              <li
                key={`${rule.antecedent}-${rule.consequent}`}
                className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                <span className="min-w-0 flex-1 truncate">{rule.antecedent}</span>
                <span className="shrink-0 text-slate-400">→</span>
                <span className="min-w-0 flex-1 truncate">{rule.consequent}</span>
                <span className="shrink-0 rounded-full bg-sky-100 px-2 py-0.5 text-xs font-bold tabular-nums text-sky-800">
                  {rule.lift}×
                </span>
                <span className="w-12 shrink-0 text-right text-xs tabular-nums text-slate-500">
                  {Math.round(rule.confidence * 100)}%
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Live abandonment risk. */}
      <Card className="mt-4">
        <h2 className="flex items-center gap-2 font-bold text-slate-900">
          <ShieldAlert className="size-5" aria-hidden />
          Tərk etmə riski — canlı səbətlər
        </h2>
        <p className="mb-3 text-sm text-slate-500">
          Model sintetik datada öyrədilib, amma burada <strong>real səbətləri</strong>{' '}
          qiymətləndirir. Ən riskli 10% səbətdə tərk etmə{' '}
          <strong className="text-slate-800">
            {risk.metrics.top_decile_lift}× daha çoxdur
          </strong>{' '}
          (ROC-AUC {risk.metrics.roc_auc}).
        </p>

        <div className="grid gap-3 lg:grid-cols-[1fr_18rem]">
          <div>
            {risk.baskets.length === 0 ? (
              <p className="py-8 text-center text-slate-500">
                Hazırda mağazada aktiv səbət yoxdur. Səbət cihazından məhsul skan edin —
                burada dərhal görünəcək.
              </p>
            ) : (
              <ul className="space-y-1.5">
                {risk.baskets.map((basket) => (
                  <li
                    key={basket.basket_id}
                    className={`flex items-center gap-3 rounded-xl border px-3 py-2 ${
                      basket.flagged
                        ? 'border-red-200 bg-red-50'
                        : 'border-slate-200'
                    }`}
                  >
                    <span className="font-mono font-bold">{basket.basket_id}</span>
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-500">
                      {basket.item_count} məhsul · {formatAZN(basket.value_qepik)}
                      {basket.zone_name && ` · ${basket.zone_name}`}
                    </span>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${
                        basket.flagged
                          ? 'bg-red-600 text-white'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {Math.round(basket.risk * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-2xl bg-slate-50 p-3">
            <p className="text-sm font-semibold text-slate-700">Riskə ən çox təsir edən</p>
            <ul className="mt-2 space-y-1.5">
              {risk.drivers.map((driver) => (
                <li key={driver.feature}>
                  <div className="flex items-baseline justify-between gap-2 text-xs">
                    <span className="truncate text-slate-600">{driver.feature}</span>
                    <span className="tabular-nums text-slate-500">
                      {Math.round(driver.importance * 100)}%
                    </span>
                  </div>
                  <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-slate-600"
                      style={{ width: `${driver.importance * 100 * 4}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Card>

      {/* Provenance: every column, and where it would come from. */}
      <Card className="mt-4">
        <h2 className="font-bold text-slate-900">Hansı məlumat haradan gəlir</h2>
        <p className="mb-2 text-sm text-slate-500">
          Modelin gördüyü hər sütun və onun real sistemdəki mənbəyi. Siyahıda olmayan
          heç nə istifadə edilmir.
        </p>
        <div className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
          {Object.entries(summary.feature_provenance).map(([feature, source]) => (
            <div key={feature} className="flex gap-2 border-b border-slate-100 py-1">
              <code className="shrink-0 font-mono text-xs text-slate-700">{feature}</code>
              <span className="min-w-0 flex-1 text-right text-xs text-slate-500">
                {source}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </Page>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-slate-400">{label}</dt>
      <dd className="font-semibold tabular-nums text-slate-700">{value}</dd>
    </div>
  )
}

function ModelGroup({
  title,
  models,
  tone,
}: {
  title: string
  models: MlSummary['models']
  tone: 'brand' | 'violet'
}) {
  const ring = tone === 'brand' ? 'border-brand-200 bg-brand-50' : 'border-violet-200 bg-violet-50'
  return (
    <div className={`rounded-2xl border p-3 ${ring}`}>
      <p className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-600">
        {title}
      </p>
      <div className="space-y-2">
        {models.map((model) => (
          <div key={model.key} className="rounded-xl bg-white p-3">
            <p className="font-semibold text-slate-900">{model.algorithm}</p>
            <p className="text-sm text-slate-500">
              {model.task} · {model.target}
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {Object.entries(model.metrics)
                .filter(([, value]) => typeof value === 'number')
                .slice(0, 5)
                .map(([name, value]) => (
                  <span
                    key={name}
                    className="rounded-full bg-slate-100 px-2 py-0.5 text-xs tabular-nums text-slate-700"
                  >
                    {name} <strong>{String(value)}</strong>
                  </span>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
