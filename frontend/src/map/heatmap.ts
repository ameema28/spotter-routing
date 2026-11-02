import type { FeatureCollection, Polygon } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'
import type { Heatmap, RiskLevel } from '../api/types'
import { riskColorExpression } from './styles'

// h0 … h48: the cell's risk level at each hour after departure.
export type HeatmapProps = Record<string, RiskLevel>

export const LAST_HOUR = 48

// D12: built once per plan with every hour stored on each square, so moving the slider only changes which
// property the colour rule reads. Nothing here runs again when the hour changes.
export function buildHeatmapGeoJSON(heatmap: Heatmap): FeatureCollection<Polygon, HeatmapProps> {
  const [latStep, lonStep] = heatmap.step_deg
  return {
    type: 'FeatureCollection',
    features: heatmap.points.map(([lat, lon], index) => {
      const west = lon - lonStep / 2
      const east = lon + lonStep / 2
      const south = lat - latStep / 2
      const north = lat + latStep / 2
      const properties: HeatmapProps = {}
      heatmap.levels[index].forEach((level, hour) => { properties[`h${hour}`] = level })
      return {
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]] },
        properties,
      }
    }),
  }
}

export function heatmapColorExpression(hour: number): ExpressionSpecification {
  const safeHour = Math.min(LAST_HOUR, Math.max(0, Math.round(hour)))
  return riskColorExpression(['get', `h${safeHour}`])
}
