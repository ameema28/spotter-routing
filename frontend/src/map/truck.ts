import type { Route } from '../api/types'
import { pointAtMile, type LonLat } from './geojson'
import { STOP_PIN } from './styles'

export type TruckStatus = 'driving' | '30-min break' | '10-h rest' | 'arrived'

export interface TruckState {
  lngLat: LonLat
  mile: number
  status: TruckStatus
}

interface Knot { time: number; mile: number }

// Known (time, mile) points: every checkpoint ETA, plus each stop's start and end at the same mile.
// Between two knots the truck moves evenly, so between a stop's start and end it stands still.
function knots(route: Route): Knot[] {
  const fromCheckpoints = route.checkpoints.map((checkpoint) => ({ time: Date.parse(checkpoint.eta), mile: checkpoint.mile }))
  const fromStops = route.breaks.flatMap((stop) => [
    { time: Date.parse(stop.start), mile: stop.mile },
    { time: Date.parse(stop.end), mile: stop.mile },
  ])
  return [...fromCheckpoints, ...fromStops].sort((a, b) => a.time - b.time || a.mile - b.mile)
}

export function mileAtTime(route: Route, time: number): number {
  const points = knots(route)
  if (points.length === 0 || time <= points[0].time) return 0
  const last = points[points.length - 1]
  if (time >= last.time) return route.distance_mi
  const after = points.findIndex((point) => point.time > time)
  const before = points[after - 1]
  const next = points[after]
  const share = (time - before.time) / (next.time - before.time)
  return before.mile + (next.mile - before.mile) * share
}

export function truckState(route: Route, time: number): TruckState {
  const mile = mileAtTime(route, time)
  const lastEta = Date.parse(route.checkpoints[route.checkpoints.length - 1]?.eta ?? '')
  const stop = route.breaks.find((candidate) => Date.parse(candidate.start) <= time && time < Date.parse(candidate.end))
  let status: TruckStatus = 'driving'
  if (stop) status = (STOP_PIN[stop.type]?.name ?? '30-min break') as TruckStatus
  else if (time >= lastEta) status = 'arrived'
  return { lngLat: pointAtMile(route, mile), mile, status }
}
