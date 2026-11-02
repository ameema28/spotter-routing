import type { Feature, FeatureCollection, LineString, Point } from 'geojson'
import type { Break, LatLon, RoutePlan, Route, RiskLevel } from '../api/types'

// Everything here turns the API response into map data once per plan. Selecting a route never rebuilds it:
// the layers filter or restyle by these properties instead.

export type LonLat = [number, number]

export interface RouteProps { id: number; recommended: boolean }
export interface CheckpointProps { routeId: number; index: number; level: RiskLevel }
export interface BreakProps { routeId: number; index: number; type: Break['type'] }

// The API sends [lat, lon]; MapLibre and GeoJSON want [lon, lat].
const toLonLat = ([lat, lon]: LatLon): LonLat => [lon, lat]

export function planToRoutesGeoJSON(plan: RoutePlan): FeatureCollection<LineString, RouteProps> {
  return {
    type: 'FeatureCollection',
    features: plan.routes.map((route) => ({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: route.geometry.map(toLonLat) },
      properties: { id: route.id, recommended: route.id === plan.recommendation.route_id },
    })),
  }
}

export function planToCheckpointsGeoJSON(plan: RoutePlan): FeatureCollection<Point, CheckpointProps> {
  return {
    type: 'FeatureCollection',
    features: plan.routes.flatMap((route) => route.checkpoints.map((checkpoint, index) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [checkpoint.lon, checkpoint.lat] },
      properties: { routeId: route.id, index, level: checkpoint.level },
    }))),
  }
}

const EARTH_RADIUS_MI = 3958.8

function haversineMiles([lon1, lat1]: LonLat, [lon2, lat2]: LonLat): number {
  const rad = Math.PI / 180
  const a = Math.sin(((lat2 - lat1) * rad) / 2) ** 2
    + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lon2 - lon1) * rad) / 2) ** 2
  return 2 * EARTH_RADIUS_MI * Math.asin(Math.sqrt(a))
}

// Breaks only come with a mile, so walk along the drawn line to find where that mile is. The simplified line
// is a little shorter than the real road, so its length is stretched to the route's distance first.
export function pointAtMile(route: Route, mile: number): LonLat {
  const points = route.geometry.map(toLonLat)
  const segments = points.slice(1).map((point, index) => haversineMiles(points[index], point))
  const lineMiles = segments.reduce((sum, length) => sum + length, 0)
  if (lineMiles === 0 || mile <= 0) return points[0]
  let remaining = Math.min(mile, route.distance_mi) * (lineMiles / route.distance_mi)
  for (let index = 0; index < segments.length; index += 1) {
    if (remaining <= segments[index]) {
      const share = remaining / segments[index]
      const [lon1, lat1] = points[index]
      const [lon2, lat2] = points[index + 1]
      return [lon1 + (lon2 - lon1) * share, lat1 + (lat2 - lat1) * share]
    }
    remaining -= segments[index]
  }
  return points[points.length - 1]
}

export function planToBreaksGeoJSON(plan: RoutePlan): FeatureCollection<Point, BreakProps> {
  return {
    type: 'FeatureCollection',
    features: plan.routes.flatMap((route) => route.breaks.map((stop, index): Feature<Point, BreakProps> => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: pointAtMile(route, stop.mile) },
      properties: { routeId: route.id, index, type: stop.type },
    }))),
  }
}

// [[west, south], [east, north]] around every route, for fitBounds.
export function planBounds(plan: RoutePlan): [LonLat, LonLat] {
  const lons = plan.routes.flatMap((route) => route.geometry.map(([, lon]) => lon))
  const lats = plan.routes.flatMap((route) => route.geometry.map(([lat]) => lat))
  return [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]]
}
