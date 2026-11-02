import { describe, expect, it } from 'vitest'
import type { RoutePlan } from '../api/types'
import samplePlan from '../fixtures/sample-plan.json'
import { pointAtMile } from './geojson'
import { mileAtTime, truckState } from './truck'

// JSON imports widen literal types ("mapbox" becomes string), so the fixture needs a cast.
const route = (samplePlan as unknown as RoutePlan).routes[0]
const ms = (iso: string) => new Date(iso).getTime()
const departure = ms(route.checkpoints[0].eta)
const arrival = ms(route.checkpoints[route.checkpoints.length - 1].eta)
const [shortBreak, rest] = route.breaks
const HOUR = 3600 * 1000

describe('mileAtTime', () => {
  it('is at the start at departure and before it', () => {
    expect(mileAtTime(route, departure)).toBe(0)
    expect(mileAtTime(route, departure - HOUR)).toBe(0)
  })

  it('is at the destination on arrival and after it', () => {
    expect(mileAtTime(route, arrival)).toBeCloseTo(route.distance_mi, 6)
    expect(mileAtTime(route, arrival + 10 * HOUR)).toBe(route.distance_mi)
  })

  it('stays parked at the stop for the whole 10-h rest', () => {
    for (const time of [ms(rest.start), ms(rest.start) + 5 * HOUR, ms(rest.end)]) {
      expect(mileAtTime(route, time)).toBeCloseTo(rest.mile, 6)
    }
    expect(mileAtTime(route, ms(shortBreak.start) + 15 * 60 * 1000)).toBeCloseTo(shortBreak.mile, 6)
  })

  it('never goes backwards', () => {
    let previous = -1
    for (let time = departure; time <= departure + 48 * HOUR; time += 10 * 60 * 1000) {
      const mile = mileAtTime(route, time)
      expect(mile).toBeGreaterThanOrEqual(previous)
      previous = mile
    }
  })

  it('moves evenly between two checkpoints', () => {
    const [a, b] = route.checkpoints.slice(1, 3)
    const halfway = (ms(a.eta) + ms(b.eta)) / 2
    expect(mileAtTime(route, halfway)).toBeCloseTo((a.mile + b.mile) / 2, 6)
  })
})

describe('truckState', () => {
  it('reports driving, the stop it is at, or arrival', () => {
    expect(truckState(route, departure + HOUR).status).toBe('driving')
    expect(truckState(route, ms(shortBreak.start) + 60 * 1000).status).toBe('30-min break')
    expect(truckState(route, ms(rest.start) + HOUR).status).toBe('10-h rest')
    expect(truckState(route, arrival + HOUR).status).toBe('arrived')
  })

  it('places the truck on the route at its mile', () => {
    const state = truckState(route, ms(rest.start) + HOUR)
    expect(state.mile).toBeCloseTo(rest.mile, 6)
    expect(state.lngLat).toEqual(pointAtMile(route, state.mile))
  })
})
