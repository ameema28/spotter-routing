import type { RoutePlan } from './api/types'
import { formatLocalDateTime } from './format'

const HOUR_MS = 3600 * 1000

// timeZone is only passed by tests; the app always shows the browser's own zone.
export function sliderLabel(startIso: string, hour: number, timeZone?: string): string {
  const at = new Date(Date.parse(startIso) + hour * HOUR_MS).toISOString()
  return `T+${hour} h · ${formatLocalDateTime(at, timeZone)}`
}

// Open-Meteo's HRRR (3 km) runs reach 48 h on the 00/06/12/18Z runs (https://open-meteo.com/en/docs/gfs-api);
// beyond that the forecast leans on coarser global models, so a later departure is less certain.
const WELL_FORECAST_HOURS = 48

export function departureNote(departureIso: string, now: Date): string | null {
  const hoursAway = (Date.parse(departureIso) - now.getTime()) / HOUR_MS
  return hoursAway > WELL_FORECAST_HOURS
    ? 'Departure is more than 2 days away — forecasts this far ahead are less certain.'
    : null
}

// The plan has no departure field, but the heatmap starts at departure and so does every route's mile 0.
export function departureOf(plan: RoutePlan): string | null {
  return plan.heatmap?.start ?? plan.routes[0]?.checkpoints[0]?.eta ?? null
}
