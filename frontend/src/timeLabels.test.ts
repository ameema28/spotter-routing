import { describe, expect, it } from 'vitest'
import type { RoutePlan } from './api/types'
import samplePlan from './fixtures/sample-plan.json'
import { departureNote, departureOf, sliderLabel } from './timeLabels'

const plan = samplePlan as unknown as RoutePlan
const HOUR = 3600 * 1000

describe('sliderLabel', () => {
  it('shows hours since departure and the local clock time', () => {
    const label = sliderLabel('2026-11-02T18:00:00+00:00', 12, 'America/Chicago')
    expect(label).toMatch(/^T\+12 h · /)
    expect(label).toContain('Nov 3')
    expect(label).toContain('12:00 AM CST')
  })

  it('starts at T+0 h', () => {
    expect(sliderLabel('2026-11-02T18:00:00+00:00', 0, 'America/Chicago')).toMatch(/^T\+0 h · .*12:00 PM CST$/)
  })
})

describe('departureNote', () => {
  const now = new Date('2026-11-02T12:00:00Z')
  const at = (hours: number) => new Date(now.getTime() + hours * HOUR).toISOString()

  it('warns when departure is more than 2 days away', () => {
    expect(departureNote(at(49), now)).toBe(
      'Departure is more than 2 days away — forecasts this far ahead are less certain.')
  })

  it('says nothing for a departure within 2 days', () => {
    expect(departureNote(at(2), now)).toBeNull()
    expect(departureNote(at(48), now)).toBeNull()
  })
})

describe('departureOf', () => {
  it('reads the departure from the heatmap start', () => {
    expect(departureOf(plan)).toBe(plan.heatmap?.start)
  })

  it('falls back to the first checkpoint when there is no heatmap', () => {
    expect(departureOf({ ...plan, heatmap: null })).toBe(plan.routes[0].checkpoints[0].eta)
  })
})
