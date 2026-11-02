// Shapes of POST /api/route-plan/, copied from the build_route_plan docstring and the _*_json helpers
// in backend/routing/services/route_plan.py. Keep the two in step.

// 0 Low, 1 Moderate, 2 High, 3 Severe, 4 No Travel; null when weather data was missing.
export type RiskLevel = 0 | 1 | 2 | 3 | 4 | null

// The API sends [lat, lon]. MapLibre wants [lon, lat], so always convert at the map boundary.
export type LatLon = [number, number]

export interface Place {
  label: string
  lat: number
  lon: number
}

export interface Checkpoint {
  mile: number
  lat: number
  lon: number
  eta: string
  level: RiskLevel
  driver: string
  wind: number | null
  gust: number | null
  rain: number | null
  snow: number | null
  precip_hour: string | null
  wind_hour: string | null
}

export interface Break {
  mile: number
  type: string
  start: string
  end: string
}

export interface RouteSummary {
  severe_miles: number
  high_miles: number
  no_travel_miles: number
  unknown_miles: number
  avg_risk: number | null
  tier: number
  flags: ('no_travel' | 'insufficient_data')[]
}

export interface Route {
  id: number
  label: string
  source: 'mapbox' | 'generated'
  geometry: LatLon[]
  distance_mi: number
  drive_seconds: number
  drive_time: string
  trip_seconds: number
  trip_time: string
  breaks: Break[]
  summary: RouteSummary
  checkpoints: Checkpoint[]
}

export interface Heatmap {
  start: string
  hours: string[]
  // Grid spacing in degrees; each point is the centre of a cell this size.
  step_deg: LatLon
  points: LatLon[]
  // levels[point][hour], 49 hours per point.
  levels: RiskLevel[][]
}

export interface RoutePlan {
  origin: Place
  destination: Place
  routes: Route[]
  ranking: number[]
  recommendation: { route_id: number | null; reason: string }
  heatmap: Heatmap | null
  notes: string[]
  timings_ms: { geocode: number; routing: number; weather: number; compute: number }
}
