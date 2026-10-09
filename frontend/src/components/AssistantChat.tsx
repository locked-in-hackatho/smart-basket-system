/**
 * The shopping assistant, as a sheet that slides up from the basket screen.
 *
 * Every answer is paired with the map, because "Rəf 12, orta rəf" means far
 * less to a shopper than a flashing rectangle on the floor plan.
 */

import { useEffect, useRef, useState } from 'react'
import { Bot, Mic, Send, Sparkles, X } from 'lucide-react'

import { api, ApiError } from '../api'
import StoreMap from './StoreMap'
import { formatAZN } from '../utils/format'
import type { AssistantReply } from '../types'

const SUGGESTIONS = [
  'Süd haradadır?',
  'Diş pastası',
  'Uşaq üçün şirniyyat',
  'Ən ucuz çay hansıdır?',
]

interface Turn {
  question: string
  reply: AssistantReply | null
  error?: string
}

/** The Web Speech API is Chrome-only; the button hides where it is absent. */
type SpeechRecognitionLike = {
  lang: string
  interimResults: boolean
  onresult: ((event: { results: { 0: { 0: { transcript: string } } } }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

function createRecogniser(): SpeechRecognitionLike | null {
  const holder = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike
    webkitSpeechRecognition?: new () => SpeechRecognitionLike
  }
  const Recogniser = holder.SpeechRecognition ?? holder.webkitSpeechRecognition
  if (!Recogniser) return null
  const recogniser = new Recogniser()
  recogniser.lang = 'az-AZ'
  recogniser.interimResults = false
  return recogniser
}

export default function AssistantChat({
  basketId,
  currentZone,
  onClose,
}: {
  basketId: string
  currentZone: string | null
  onClose: () => void
}) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const [speechAvailable] = useState(() => createRecogniser() !== null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [turns, busy])

  async function send(question: string) {
    const text = question.trim()
    if (!text || busy) return
    setDraft('')
    setBusy(true)
    setTurns((current) => [...current, { question: text, reply: null }])
    try {
      const reply = await api.ask(basketId, text)
      setTurns((current) =>
        current.map((turn, index) =>
          index === current.length - 1 ? { ...turn, reply } : turn,
        ),
      )
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message : 'Xəta baş verdi'
      setTurns((current) =>
        current.map((turn, index) =>
          index === current.length - 1 ? { ...turn, error: message } : turn,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  function listen() {
    const recogniser = createRecogniser()
    if (!recogniser) return
    setListening(true)
    recogniser.onresult = (event) => {
      const said = event.results[0][0].transcript
      setDraft(said)
      void send(said)
    }
    recogniser.onend = () => setListening(false)
    recogniser.start()
  }

  const last = turns.at(-1)?.reply ?? null
  const mode = last?.mode

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="AI köməkçi"
      className="fixed inset-0 z-50 flex flex-col justify-end bg-slate-900/60"
      onClick={onClose}
    >
      <div
        className="flex max-h-[88vh] flex-col rounded-t-3xl bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
          <Bot className="size-6 text-brand-600" aria-hidden />
          <p className="flex-1 font-bold">Köməkçi</p>
          {mode && (
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${
                mode === 'ai'
                  ? 'bg-brand-50 text-brand-700 ring-brand-200'
                  : 'bg-slate-100 text-slate-600 ring-slate-200'
              }`}
            >
              <Sparkles className="size-3" aria-hidden />
              {mode === 'ai' ? 'AI' : 'Oflayn'}
            </span>
          )}
          <button
            type="button"
            onClick={onClose}
            aria-label="Bağla"
            className="flex size-11 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <X className="size-5" aria-hidden />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-3">
          {turns.length === 0 && (
            <div className="py-6 text-center">
              <p className="text-4xl" aria-hidden>
                🤖
              </p>
              <p className="mt-2 font-semibold text-slate-800">
                Məhsulun yerini soruşun
              </p>
              <p className="text-sm text-slate-500">
                Məsələn: “Süd haradadır?” — zonanı xəritədə göstərəcəyəm.
              </p>
            </div>
          )}

          {turns.map((turn, index) => (
            <div key={index} className="mb-4">
              <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-brand-600 px-3 py-2 text-white">
                {turn.question}
              </p>

              {turn.error && (
                <p className="mt-2 w-fit max-w-[90%] rounded-2xl rounded-bl-sm bg-red-50 px-3 py-2 text-red-700">
                  {turn.error}
                </p>
              )}

              {turn.reply === null && !turn.error && (
                <p className="mt-2 w-fit rounded-2xl rounded-bl-sm bg-slate-100 px-3 py-2 text-slate-500">
                  Düşünürəm…
                </p>
              )}

              {turn.reply && (
                <>
                  <p className="mt-2 w-fit max-w-[90%] whitespace-pre-line rounded-2xl rounded-bl-sm bg-slate-100 px-3 py-2 text-slate-800">
                    {turn.reply.answer}
                  </p>

                  {turn.reply.products.length > 0 && (
                    <ul className="mt-2 space-y-1.5">
                      {turn.reply.products.slice(0, 3).map((product) => (
                        <li
                          key={product.id}
                          className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2"
                        >
                          <span className="text-xl" aria-hidden>
                            {product.emoji}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-semibold">
                              {product.name}
                            </span>
                            <span className="block truncate text-xs text-slate-500">
                              {product.zone_name} · {product.aisle} · {product.shelf}
                              {product.stock <= 0 && ' · stokda yoxdur'}
                            </span>
                          </span>
                          <span className="text-sm font-bold text-brand-700">
                            {formatAZN(product.price_qepik)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {turn.reply.highlight_zone && (
                    <div className="mt-2">
                      <StoreMap
                        highlightZone={turn.reply.highlight_zone}
                        currentZone={currentZone}
                      />
                      <p className="mt-1 text-center text-xs text-slate-400">
                        Yanıb-sönən zona — axtardığınız məhsul oradadır
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <div className="border-t border-slate-200 p-3">
          <div className="mb-2 flex gap-1.5 overflow-x-auto pb-1">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={busy}
                onClick={() => send(suggestion)}
                className="shrink-0 rounded-full border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition hover:border-brand-400 hover:text-brand-700 disabled:opacity-40"
              >
                {suggestion}
              </button>
            ))}
          </div>

          <form
            onSubmit={(event) => {
              event.preventDefault()
              void send(draft)
            }}
            className="flex gap-2"
          >
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Sualınızı yazın…"
              aria-label="Sual"
              disabled={busy}
              className="min-h-12 w-full rounded-xl border border-slate-300 px-4 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
            />
            {speechAvailable && (
              <button
                type="button"
                onClick={listen}
                disabled={busy || listening}
                aria-label="Səslə soruş"
                className={`flex size-12 shrink-0 items-center justify-center rounded-xl border transition ${
                  listening
                    ? 'border-red-300 bg-red-50 text-red-600'
                    : 'border-slate-300 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Mic className="size-5" aria-hidden />
              </button>
            )}
            <button
              type="submit"
              disabled={busy || draft.trim().length === 0}
              aria-label="Göndər"
              className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-700 disabled:opacity-40"
            >
              <Send className="size-5" aria-hidden />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
