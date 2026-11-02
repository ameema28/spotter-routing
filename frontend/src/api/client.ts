import { clientError, NETWORK_MESSAGE, toApiError } from './errors'
import type { RoutePlan, RoutePlanRequest } from './types'

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
export async function searchRoutes(request: RoutePlanRequest, signal: AbortSignal): Promise<RoutePlan> {
  if (!API_URL) throw clientError(MISSING_URL)
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/route-plan/`, {
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
  return body as RoutePlan
}
