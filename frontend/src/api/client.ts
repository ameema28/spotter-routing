const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

// Calls the health endpoint so a sleeping server starts before the first search. Returns the time taken in ms.
export async function wakeUp(signal?: AbortSignal): Promise<number> {
  if (!API_URL) throw new Error('VITE_API_URL is not set. Copy frontend/.env.example to frontend/.env.')
  const started = performance.now()
  const response = await fetch(`${API_URL}/api/health/`, { signal })
  if (!response.ok) throw new Error(`The server answered with an error (HTTP ${response.status}).`)
  return Math.round(performance.now() - started)
}
