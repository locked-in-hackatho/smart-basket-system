/**
 * App-wide toasts. Green for success, red for errors — the basket screen
 * relies on colour being readable at arm's length.
 */

import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Info } from 'lucide-react'

type ToastKind = 'success' | 'error' | 'info'

interface Toast {
  id: number
  kind: ToastKind
  message: string
  detail?: string
}

interface ToastApi {
  success: (message: string, detail?: string) => void
  error: (message: string, detail?: string) => void
  info: (message: string, detail?: string) => void
}

const ToastContext = createContext<ToastApi | null>(null)

const STYLES: Record<ToastKind, string> = {
  success: 'bg-brand-600 text-white',
  error: 'bg-red-600 text-white',
  info: 'bg-slate-800 text-white',
}

const ICONS: Record<ToastKind, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
}

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const push = useCallback((kind: ToastKind, message: string, detail?: string) => {
    const id = nextId++
    setToasts((current) => [...current.slice(-2), { id, kind, message, detail }])
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id))
    }, 2600)
  }, [])

  const api = useMemo<ToastApi>(
    () => ({
      success: (message, detail) => push('success', message, detail),
      error: (message, detail) => push('error', message, detail),
      info: (message, detail) => push('info', message, detail),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 pb-6">
        {toasts.map((toast) => {
          const Icon = ICONS[toast.kind]
          return (
            <div
              key={toast.id}
              role="status"
              className={`animate-toast-in flex w-full max-w-md items-center gap-3 rounded-2xl px-4 py-3 shadow-xl ${STYLES[toast.kind]}`}
            >
              <Icon className="size-6 shrink-0" aria-hidden />
              <div className="min-w-0">
                <p className="truncate font-semibold">{toast.message}</p>
                {toast.detail && (
                  <p className="truncate text-sm opacity-90">{toast.detail}</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const context = useContext(ToastContext)
  if (context === null) {
    throw new Error('useToast must be used inside a ToastProvider')
  }
  return context
}
