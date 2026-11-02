import { describe, expect, it } from 'vitest'
import type { RoutePlan } from '../api/types'
import samplePlan from '../fixtures/sample-plan.json'
import {
  planBounds, planToBreaksGeoJSON, planToCheckpointsGeoJSON, planToRoutesGeoJSON, pointAtMile,
} from './geojson'

// JSON imports widen literal types ("mapbox" becomes string), so the fixture needs a cast.
const plan = samplePlan as unknown as RoutePlan
const [first] = plan.routes

describe('planToRoutesGeoJSON', () => {
  it('makes one line per route, swapping the API [lat, lon] to MapLibre [lon, lat]', () => {
    const routes = planToRoutesGeoJSON(plan)
    expect(routes.features).toHaveLength(plan.routes.length)
    const [lat, lon] = first.geometry[0]
    expect(routes.features[0].geometry.coordinates[0]).toEqual([lon, lat])
    expect(routes.features[0].properties).toEqual({ id: first.id, recommended: true })
  })
})

describe('planToCheckpointsGeoJSON', () => {
  it('makes one point per checkpoint, tagged with its route and position', () => {
    const points = planToCheckpointsGeoJSON(plan)
    const total = plan.routes.reduce((sum, route) => sum + route.checkpoints.length, 0)
    expect(points.features).toHaveLength(total)
    const checkpoint = first.checkpoints[3]
    expect(points.features[3].geometry.coordinates).toEqual([checkpoint.lon, checkpoint.lat])
    expect(points.features[3].properties).toEqual({ routeId: first.id, index: 3, level: checkpoint.level })
  })

  it('keeps a missing level as null, so the map shows it as Unknown', () => {
    const withGap = { ...plan, routes: [{ ...first, checkpoints: [{ ...first.checkpoints[0], level: null }] }] }
    expect(planToCheckpointsGeoJSON(withGap).features[0].properties.level).toBeNull()
  })
})

describe('pointAtMile', () => {
  it('starts at the first point and ends at the last', () => {
    const [startLat, startLon] = first.geometry[0]
    const [endLat, endLon] = first.geometry[first.geometry.length - 1]
    expect(pointAtMile(first, 0)).toEqual([startLon, startLat])
    expect(pointAtMile(first, first.distance_mi)).toEqual([endLon, endLat])
  })

  it('stays on the route ends for miles outside it', () => {
    expect(pointAtMile(first, -5)).toEqual(pointAtMile(first, 0))
    expect(pointAtMile(first, first.distance_mi + 50)).toEqual(pointAtMile(first, first.distance_mi))
  })

  it('lands close to the checkpoint at the same mile', () => {
    for (const checkpoint of first.checkpoints) {
      const [lon, lat] = pointAtMile(first, checkpoint.mile)
      // About 3 miles: the display line is simplified and its length is scaled to the route distance.
      expect(Math.abs(lat - checkpoint.lat)).toBeLessThan(0.05)
      expect(Math.abs(lon - checkpoint.lon)).toBeLessThan(0.05)
    }
  })
})

describe('planToBreaksGeoJSON', () => {
  it('places every break of every route on the map', () => {
    const breaks = planToBreaksGeoJSON(plan)
    const total = plan.routes.reduce((sum, route) => sum + route.breaks.length, 0)
    expect(breaks.features).toHaveLength(total)
    expect(breaks.features[0].properties).toEqual({ routeId: first.id, index: 0, type: first.breaks[0].type })
    expect(breaks.features[0].geometry.coordinates).toEqual(pointAtMile(first, first.breaks[0].mile))
  })
})

describe('planBounds', () => {
  it('contains the origin and the destination', () => {
    const [[west, south], [east, north]] = planBounds(plan)
    for (const place of [plan.origin, plan.destination]) {
      expect(place.lon).toBeGreaterThanOrEqual(west - 0.01)
      expect(place.lon).toBeLessThanOrEqual(east + 0.01)
      expect(place.lat).toBeGreaterThanOrEqual(south - 0.01)
      expect(place.lat).toBeLessThanOrEqual(north + 0.01)
    }
  })
})
