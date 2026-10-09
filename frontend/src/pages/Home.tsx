/** Landing page — the first thing the judges see. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart3,
  ChevronRight,
  MonitorPlay,
  Printer,
  ScanLine,
  ShoppingBasket,
  Sparkles,
} from 'lucide-react'

import { api } from '../api'
import { formatAZN } from '../utils/format'
import { Logo, StatusChip } from '../components/ui'
import type { BasketSummary, Health } from '../types'

const CARDS = [
  {
    to: '/basket/BSK-001',
    icon: ShoppingBasket,
    title: 'Səbət cihazı',
    text: 'Səbətin skaneri məhsulları avtomatik oxuyur — ekranda canlı yekun və məhsul axtarışı.',
    tone: 'bg-brand-600',
  },
  {
    to: '/checkout',
    icon: ScanLine,
    title: 'Kassa',
    text: 'Yalnız səbətin QR kodunu oxu — yekun dərhal ekranda, ödəniş bir toxunuşla.',
    tone: 'bg-sky-600',
  },
  {
    to: '/admin',
    icon: BarChart3,
    title: 'Analitika paneli',
    text: 'Dövriyyə, istilik xəritəsi, birlikdə alınan məhsullar və qənaət edilən vaxt.',
    tone: 'bg-violet-600',
  },
  {
    to: '/print',
    icon: Printer,
    title: 'Çap',
    text: 'Səbət QR kodları və demo məhsul barkodları — çap et və sına.',
    tone: 'bg-slate-700',
  },
]

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null)
  const [baskets, setBaskets] = useState<BasketSummary[]>([])

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
    api.baskets().then(setBaskets).catch(() => setBaskets([]))
  }, [])

  const busy = baskets.filter((basket) => basket.status !== 'idle')

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <Logo className="text-2xl" />
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-semibold ring-1 ${
              health
                ? 'bg-brand-50 text-brand-700 ring-brand-200'
                : 'bg-red-50 text-red-700 ring-red-200'
            }`}
          >
            <span className="size-1.5 rounded-full bg-current" aria-hidden />
            {health ? 'Server işləyir' : 'Server əlçatmazdır'}
          </span>
          {health && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-600 ring-1 ring-slate-200">
              <Sparkles className="size-3.5" aria-hidden />
              {health.store_name}
            </span>
          )}
        </div>
      </header>

      <section className="mt-8">
        <h2 className="text-balance text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Kassada növbə çəkmədən alış-veriş
        </h2>
        <p className="mt-3 max-w-2xl text-lg text-slate-600">
          Səbətin içindəki skaner qoyulan hər məhsulu özü oxuyur — müştəri heç nə etmir.
          Kassada yalnız səbətin QR kodu oxudulur və yekun məbləğ dərhal ekrana çıxır.
          Mağaza isə səbətlərin hərəkətindən canlı analitika alır.
        </p>
      </section>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {CARDS.map((card) => (
          <Link
            key={card.to}
            to={card.to}
            className="group flex items-start gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
          >
            <span
              className={`flex size-12 shrink-0 items-center justify-center rounded-2xl text-white ${card.tone}`}
            >
              <card.icon className="size-6" aria-hidden />
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-1 text-lg font-bold text-slate-900">
                {card.title}
                <ChevronRight
                  className="size-4 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-brand-600"
                  aria-hidden
                />
              </span>
              <span className="mt-1 block text-sm text-slate-600">{card.text}</span>
            </span>
          </Link>
        ))}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Link
          to="/demo"
          className="flex items-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-4 font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-700"
        >
          <MonitorPlay className="size-5" aria-hidden />
          Demo rejimi — səbət və kassa bir ekranda
        </Link>
        {busy.length > 0 && (
          <div className="rounded-2xl border border-slate-200 bg-white px-5 py-4">
            <p className="text-sm font-semibold text-slate-500">Hazırda işləkdə</p>
            <ul className="mt-2 space-y-1.5">
              {busy.slice(0, 3).map((basket) => (
                <li key={basket.id} className="flex items-center gap-2 text-sm">
                  <Link
                    to={`/basket/${basket.id}`}
                    className="font-mono font-semibold text-brand-700 hover:underline"
                  >
                    {basket.id}
                  </Link>
                  <StatusChip status={basket.status} />
                  <span className="ml-auto font-semibold">
                    {formatAZN(basket.total_qepik)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <p className="mt-10 text-sm text-slate-400">
        Səbət seçimi: {' '}
        {['BSK-001', 'BSK-002', 'BSK-003'].map((id) => (
          <Link
            key={id}
            to={`/basket/${id}`}
            className="mr-2 font-mono underline hover:text-brand-600"
          >
            {id}
          </Link>
        ))}
      </p>
    </div>
  )
}
