import type { HeatmapRequest, RiskLevel, RoutePlan, RoutePlanRequest } from './api/types'

// D14: one automatic retry, after Open-Meteo's per-minute window has had time to pass.
export const AUTO_RETRY_MS = 60_000

export type HeatmapRetry =
  | { kind: 'none' }                        // the heatmap arrived, or there is no grid to retry
  | { kind: 'waiting'; retryAt: number }    // the one automatic retry is scheduled (ms since epoch)
  | { kind: 'retrying' }
  | { kind: 'failed'; message: string }     // only "Retry now" from here

// A plan with the request it answered. The id changes once per search, never on a heatmap retry, so the map
// fit, slider hour and route choice can follow the search rather than the plan object.
export interface SearchResult {
  searchId: number
  plan: RoutePlan
  request: RoutePlanRequest
  receivedAt: number    // ms since epoch; the automatic heatmap retry counts from here
}

export function initialRetry(plan: RoutePlan, now: number): HeatmapRetry {
  return plan.heatmap && plan.heatmap.levels === null
    ? { kind: 'waiting', retryAt: now + AUTO_RETRY_MS }
    : { kind: 'none' }
}

export function secondsUntil(retryAt: number, now: number): number {
  return Math.max(0, Math.ceil((retryAt - now) / 1000))
}

export function heatmapRequest({ plan, request }: SearchResult): HeatmapRequest | null {
  if (!plan.heatmap) return null
  const { points, step_deg } = plan.heatmap
  return { points, step_deg, departure: request.departure, load_lb: request.load_lb }
}

// Only the heatmap changes: everything else keeps its identity, so nothing built from it is rebuilt.
export function withHeatmapLevels(plan: RoutePlan, levels: RiskLevel[][]): RoutePlan {
  if (!plan.heatmap) return plan
  return {
    ...plan,
    heatmap: { ...plan.heatmap, levels },
    notes: plan.notes.filter((note) => !note.startsWith('Heatmap unavailable')),
  }
}

export function mergeHeatmapLevels(result: SearchResult | null, searchId: number,
  levels: RiskLevel[][]): SearchResult | null {
  // A retry that lands after a newer search belongs to a plan that is no longer shown.
  if (!result || result.searchId !== searchId) return result
  return { ...result, plan: withHeatmapLevels(result.plan, levels) }
}
