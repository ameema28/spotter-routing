import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fetchHeatmapLevels } from '../api/client'
import { isApiError } from '../api/errors'
import type { RiskLevel } from '../api/types'
import { heatmapRequest, initialRetry, type HeatmapRetry, type SearchResult } from '../heatmapRetry'

const NONE: HeatmapRetry = { kind: 'none' }
const FAILED_MESSAGE = 'Heatmap still unavailable'

// D14: when a search comes back without heatmap levels, fetch just those once after a minute, or on "Retry now".
// The countdown text ticks in its own component, so this state only changes a few times per search.
export function useHeatmapRetry(result: SearchResult | null,
  onLevels: (searchId: number, levels: RiskLevel[][]) => void) {
  // Only what happened after the search; until then the schedule follows from the result itself.
  const [retry, setRetry] = useState<{ searchId: number; state: HeatmapRetry } | null>(null)
  const controller = useRef<AbortController | null>(null)
  const searchId = result?.searchId ?? null

  const state = useMemo(() => {
    if (!result) return NONE
    return retry?.searchId === result.searchId ? retry.state : initialRetry(result.plan, result.receivedAt)
  }, [result, retry])

  const retryNow = useCallback(async () => {
    const body = result && heatmapRequest(result)
    if (!result || !body) return
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    setRetry({ searchId: result.searchId, state: { kind: 'retrying' } })
    try {
      const { levels } = await fetchHeatmapLevels(body, current.signal)
      onLevels(result.searchId, levels)
      setRetry({ searchId: result.searchId, state: NONE })
    } catch (caught) {
      if (current.signal.aborted) return
      const message = isApiError(caught) ? `${FAILED_MESSAGE}: ${caught.message}` : FAILED_MESSAGE
      setRetry({ searchId: result.searchId, state: { kind: 'failed', message } })
    }
  }, [result, onLevels])

  const retryAt = state.kind === 'waiting' ? state.retryAt : null
  useEffect(() => {
    if (retryAt === null) return
    const timer = setTimeout(() => void retryNow(), Math.max(0, retryAt - Date.now()))
    return () => clearTimeout(timer)
  }, [retryAt, retryNow])

  // A retry still running for an old search is dropped when a new search arrives or the page goes away.
  useEffect(() => () => controller.current?.abort(), [searchId])

  return { state, retryNow }
}
