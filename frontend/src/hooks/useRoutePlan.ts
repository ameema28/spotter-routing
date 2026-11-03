import { useCallback, useEffect, useRef, useState } from 'react'
import { searchRoutes } from '../api/client'
import { clientError, isApiError, type ApiError } from '../api/errors'
import type { RiskLevel, RoutePlanRequest } from '../api/types'
import { mergeHeatmapLevels, type SearchResult } from '../heatmapRetry'

export type SearchState = 'idle' | 'loading' | 'done' | 'error'

export function useRoutePlan() {
  const [status, setStatus] = useState<SearchState>('idle')
  const [result, setResult] = useState<SearchResult | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  // Refs, not state: changing them shouldn't redraw anything.
  const controller = useRef<AbortController | null>(null)
  const lastRequest = useRef<RoutePlanRequest | null>(null)
  const lastSearchId = useRef(0)
  const plan = result?.plan ?? null

  const search = useCallback(async (request: RoutePlanRequest) => {
    // A new search replaces the one in flight, so an old answer can never overwrite a newer one.
    controller.current?.abort()
    const current = new AbortController()
    controller.current = current
    lastRequest.current = request
    setStatus('loading')
    setError(null)
    try {
      const answer = await searchRoutes(request, current.signal)
      lastSearchId.current += 1
      setResult({ searchId: lastSearchId.current, plan: answer, request, receivedAt: Date.now() })
      setStatus('done')
    } catch (caught) {
      if (current.signal.aborted) return
      setError(isApiError(caught) ? caught : clientError('Something went wrong. Please try again.'))
      setStatus('error')
    }
  }, [])

  const cancel = useCallback(() => {
    controller.current?.abort()
    setStatus(plan ? 'done' : 'idle')
  }, [plan])

  const retry = useCallback(() => {
    if (lastRequest.current) void search(lastRequest.current)
  }, [search])

  // Fills in a heatmap that was missing; the search id stays, so the map and slider don't reset.
  const applyHeatmapLevels = useCallback((searchId: number, levels: RiskLevel[][]) => {
    setResult((current) => mergeHeatmapLevels(current, searchId, levels))
  }, [])

  // Stop a search that is still running if the page goes away.
  useEffect(() => () => controller.current?.abort(), [])

  return { status, plan, result, error, search, cancel, retry, applyHeatmapLevels }
}
