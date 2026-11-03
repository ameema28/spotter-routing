import { clientError, NETWORK_MESSAGE, toApiError } from './errors'
import type { HeatmapLevels, HeatmapRequest, RoutePlan, RoutePlanRequest } from './types'

const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')
const MISSING_URL = 'VITE_API_URL is not set. Copy frontend/.env.example to frontend/.env.'

// Calls the health endpoint so a sleeping server starts before the first search. Returns the time taken in ms.
export async function wakeUp(signal?: AbortSignal): Promise<number> {
  if (!API_URL) throw new Error(MISSING_URL)
  const started = performance.now()
  const response = await fetch(`${API_URL}/api/health/`, { signal })
  if (!response.ok) throw new Error(`The server answered with an error (HTTP ${response.status}).`)
  return Math.round(performance.now() - started)
}

// Throws an ApiError the form can show. A cancelled request rejects with the browser's AbortError instead.
async function postJson<T>(path: string, request: unknown, signal: AbortSignal): Promise<T> {
  if (!API_URL) throw clientError(MISSING_URL)
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal,
    })
  } catch (error) {
    if (signal.aborted) throw error
    throw clientError(NETWORK_MESSAGE)
  }
  // A host error page may not be JSON; toApiError then falls back to a plain message.
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw toApiError(response.status, body)
  return body as T
}

export function searchRoutes(request: RoutePlanRequest, signal: AbortSignal): Promise<RoutePlan> {
  return postJson<RoutePlan>('/api/route-plan/', request, signal)
}

// Weather for a plan's heatmap grid only: no new route search (D14).
export function fetchHeatmapLevels(request: HeatmapRequest, signal: AbortSignal): Promise<HeatmapLevels> {
  return postJson<HeatmapLevels>('/api/heatmap/', request, signal)
}
