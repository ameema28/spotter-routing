import { describe, expect, it } from 'vitest'
import type { RiskLevel, RoutePlan, RoutePlanRequest } from './api/types'
import samplePlan from './fixtures/sample-plan.json'
import {
  AUTO_RETRY_MS, heatmapRequest, initialRetry, mergeHeatmapLevels, secondsUntil, withHeatmapLevels,
  type SearchResult,
} from './heatmapRetry'

// JSON imports widen literal types ("mapbox" becomes string), so the fixture needs a cast.
const plan = samplePlan as unknown as RoutePlan
const BUSY_NOTE = 'Heatmap unavailable: weather service is busy'
const failed: RoutePlan = {
  ...plan,
  heatmap: plan.heatmap && { ...plan.heatmap, levels: null },
  notes: ['Only 2 distinct routes found', BUSY_NOTE],
}
const request: RoutePlanRequest = {
  origin: 'Dallas, TX', destination: 'Chicago, IL', departure: '2026-11-03T08:00:00-06:00', load_lb: 40000,
  step_miles: 25,
}
const result: SearchResult = { searchId: 3, plan: failed, request, receivedAt: 1000 }
const levels = plan.heatmap!.levels as RiskLevel[][]

describe('initialRetry', () => {
  it('schedules one retry a minute after a failed heatmap', () => {
    expect(initialRetry(failed, 1000)).toEqual({ kind: 'waiting', retryAt: 1000 + AUTO_RETRY_MS })
    expect(AUTO_RETRY_MS).toBe(60_000)
  })

  it('has nothing to retry when the heatmap arrived', () => {
    expect(initialRetry(plan, 1000)).toEqual({ kind: 'none' })
  })

  it('has nothing to retry without a grid', () => {
    expect(initialRetry({ ...plan, heatmap: null }, 1000)).toEqual({ kind: 'none' })
  })
})

describe('secondsUntil', () => {
  it('rounds up, so the countdown reaches 0 only when the retry starts', () => {
    expect(secondsUntil(60_000, 0)).toBe(60)
    expect(secondsUntil(60_000, 100)).toBe(60)
    expect(secondsUntil(60_000, 59_001)).toBe(1)
    expect(secondsUntil(60_000, 60_000)).toBe(0)
  })

  it('never goes below 0', () => {
    expect(secondsUntil(60_000, 70_000)).toBe(0)
  })
})

describe('heatmapRequest', () => {
  it('sends back the grid with the search departure and load', () => {
    expect(heatmapRequest(result)).toEqual({
      points: plan.heatmap!.points, step_deg: plan.heatmap!.step_deg,
      departure: request.departure, load_lb: 40000,
    })
  })

  it('has no request without a grid', () => {
    expect(heatmapRequest({ ...result, plan: { ...failed, heatmap: null } })).toBeNull()
  })
})

describe('withHeatmapLevels', () => {
  const recovered = withHeatmapLevels(failed, levels)

  it('fills in the levels and keeps the grid', () => {
    expect(recovered.heatmap?.levels).toBe(levels)
    expect(recovered.heatmap?.points).toBe(failed.heatmap!.points)
    expect(recovered.heatmap?.step_deg).toBe(failed.heatmap!.step_deg)
  })

  it('drops the busy note and keeps the others', () => {
    expect(recovered.notes).toEqual(['Only 2 distinct routes found'])
  })

  it('keeps the same routes object, so route and checkpoint map data are not rebuilt', () => {
    expect(recovered.routes).toBe(failed.routes)
    expect(recovered.origin).toBe(failed.origin)
    expect(recovered.recommendation).toBe(failed.recommendation)
  })
})

describe('mergeHeatmapLevels', () => {
  it('keeps the search id, so the map view and slider hour stay where they are', () => {
    const merged = mergeHeatmapLevels(result, 3, levels)
    expect(merged?.searchId).toBe(3)
    expect(merged?.request).toBe(request)
    expect(merged?.plan.heatmap?.levels).toBe(levels)
    expect(merged?.plan.routes).toBe(failed.routes)
  })

  it('ignores levels that arrive after a newer search', () => {
    expect(mergeHeatmapLevels(result, 2, levels)).toBe(result)
  })

  it('ignores levels when there is no search', () => {
    expect(mergeHeatmapLevels(null, 3, levels)).toBeNull()
  })
})
