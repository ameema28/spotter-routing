import { describe, expect, it } from 'vitest'
import type { RoutePlan } from './api/types'
import samplePlan from './fixtures/sample-plan.json'
import { riskShares } from './riskShares'

const EMPTY = { low: 0, moderate: 0, high: 0, severe: 0, no_travel: 0, unknown: 0 }

describe('riskShares', () => {
  it('turns miles at each level into percentages, in level order', () => {
    const shares = riskShares({ ...EMPTY, low: 50, high: 25, unknown: 25 })
    expect(shares.map((share) => share.label)).toEqual(['Low', 'High', 'Unknown'])
    expect(shares.map((share) => share.percent)).toEqual([50, 25, 25])
    expect(shares[0].miles).toBe(50)
  })

  it('leaves out levels with no miles, so the bar has no empty slivers', () => {
    expect(riskShares({ ...EMPTY, moderate: 10 })).toHaveLength(1)
  })

  it('gives an empty bar for a route with no miles', () => {
    expect(riskShares(EMPTY)).toEqual([])
  })

  it('adds up to 100% on a real response', () => {
    // JSON imports widen literal types ("mapbox" becomes string), so the fixture needs a cast.
    const plan = samplePlan as unknown as RoutePlan
    for (const route of plan.routes) {
      const total = riskShares(route.summary.miles_by_level).reduce((sum, share) => sum + share.percent, 0)
      expect(total).toBeCloseTo(100, 6)
    }
  })
})
