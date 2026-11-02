import { useCallback, useEffect, useState } from 'react'
import { wakeUp } from '../api/client'

export type ServerStatus =
  | { state: 'connecting' }
  | { state: 'waking' }
  | { state: 'ready'; ms: number }
  | { state: 'error'; message: string }

// A warm server answers well under this; slower means a cold start (7.7 s measured on Vercel).
const COLD_START_HINT_MS = 2000

export function useServerWakeUp() {
  const [status, setStatus] = useState<ServerStatus>({ state: 'connecting' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const hint = setTimeout(() => setStatus({ state: 'waking' }), COLD_START_HINT_MS)
    wakeUp(controller.signal)
      .then((ms) => setStatus({ state: 'ready', ms }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const message = error instanceof Error ? error.message : 'Unknown error'
        setStatus({ state: 'error', message })
      })
      .finally(() => clearTimeout(hint))
    return () => {
      clearTimeout(hint)
      controller.abort()
    }
  }, [attempt])

  const retry = useCallback(() => {
    setStatus({ state: 'connecting' })
    setAttempt((count) => count + 1)
  }, [])

  return { status, retry }
}
