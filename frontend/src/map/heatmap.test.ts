import { describe, expect, it } from 'vitest'
import type { Heatmap, RoutePlan } from '../api/types'
import samplePlan from '../fixtures/sample-plan.json'
import { buildHeatmapGeoJSON, heatmapColorExpression } from './heatmap'

// JSON imports widen literal types ("mapbox" becomes string), so the fixture needs a cast.
const heatmap = (samplePlan as unknown as RoutePlan).heatmap as Heatmap

describe('buildHeatmapGeoJSON', () => {
  const cells = buildHeatmapGeoJSON(heatmap)

  it('makes one square per grid point', () => {
    expect(cells.features).toHaveLength(heatmap.points.length)
  })

  it('sizes each square to the grid step and centres it on its point', () => {
    const [latStep, lonStep] = heatmap.step_deg
    const [lat, lon] = heatmap.points[0]
    const ring = cells.features[0].geometry.coordinates[0]
    const lons = ring.map(([x]) => x)
    const lats = ring.map(([, y]) => y)
    expect(ring).toHaveLength(5)    // a closed ring repeats its first corner
    expect(Math.max(...lons) - Math.min(...lons)).toBeCloseTo(lonStep, 9)
    expect(Math.max(...lats) - Math.min(...lats)).toBeCloseTo(latStep, 9)
    expect((Math.max(...lons) + Math.min(...lons)) / 2).toBeCloseTo(lon, 9)
    expect((Math.max(...lats) + Math.min(...lats)) / 2).toBeCloseTo(lat, 9)
  })

  it('stores the level for every hour, so the slider never rebuilds the data', () => {
    const props = cells.features[5].properties
    for (let hour = 0; hour <= 48; hour += 1) expect(props[`h${hour}`]).toBe(heatmap.levels![5][hour])
  })

  it('draws nothing while the levels are still missing', () => {
    expect(buildHeatmapGeoJSON({ ...heatmap, levels: null }).features).toEqual([])
  })
})

describe('heatmapColorExpression', () => {
  it('reads the property for the chosen hour', () => {
    expect(JSON.stringify(heatmapColorExpression(12))).toContain('"h12"')
  })

  it('keeps the hour inside 0-48', () => {
    expect(JSON.stringify(heatmapColorExpression(60))).toContain('"h48"')
    expect(JSON.stringify(heatmapColorExpression(-3))).toContain('"h0"')
  })
})
