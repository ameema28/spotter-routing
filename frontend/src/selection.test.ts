import { describe, expect, it } from 'vitest'
import type { RoutePlan } from './api/types'
import samplePlan from './fixtures/sample-plan.json'
import { defaultRouteId } from './selection'

// JSON imports widen literal types ("mapbox" becomes string), so the fixture needs a cast.
const plan = samplePlan as unknown as RoutePlan

describe('defaultRouteId', () => {
  it('starts on the recommended route', () => {
    expect(defaultRouteId(plan)).toBe(plan.recommendation.route_id)
  })

  it('falls back to the best ranked route when none is recommended', () => {
    const none = { ...plan, recommendation: { route_id: null, reason: 'Insufficient forecast data' }, ranking: [2, 0, 1] }
    expect(defaultRouteId(none)).toBe(2)
  })

  it('has nothing to select before a search', () => {
    expect(defaultRouteId(null)).toBeNull()
  })
})
