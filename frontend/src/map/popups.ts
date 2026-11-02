import type { Break, Checkpoint } from '../api/types'
import { formatLocalDateTime } from '../format'
import { riskInfo } from '../risk'

export interface PopupData {
  title: string
  rows: { label: string; value: string }[]
}

const NO_DATA = 'no data'

// timeZone is only passed by tests; the app always shows the browser's own zone.
const timeOrNoData = (iso: string | null, timeZone?: string) => (iso ? formatLocalDateTime(iso, timeZone) : NO_DATA)
const perHour = (inches: number | null) => (inches === null ? NO_DATA : `${inches} in/hr`)

function windText(wind: number | null, gust: number | null): string {
  if (wind === null) return NO_DATA
  // Gusts are shown for context only; the risk level uses sustained wind (D2).
  return gust === null ? `${wind} mph` : `${wind} mph (gusts ${gust} mph)`
}

export function checkpointPopupData(checkpoint: Checkpoint, timeZone?: string): PopupData {
  return {
    title: `Mile ${checkpoint.mile} · ${riskInfo(checkpoint.level).label}`,
    rows: [
      { label: 'ETA', value: formatLocalDateTime(checkpoint.eta, timeZone) },
      { label: 'Why', value: checkpoint.driver },
      { label: 'Wind', value: windText(checkpoint.wind, checkpoint.gust) },
      { label: 'Rain', value: perHour(checkpoint.rain) },
      { label: 'Snow', value: perHour(checkpoint.snow) },
      { label: 'Wind forecast hour', value: timeOrNoData(checkpoint.wind_hour, timeZone) },
      { label: 'Rain/snow forecast hour', value: timeOrNoData(checkpoint.precip_hour, timeZone) },
    ],
  }
}

const STOP_NAMES: Record<string, string> = { break: '30-min break', rest: '10-h rest' }

export function breakPopupData(stop: Break, timeZone?: string): PopupData {
  return {
    title: `${STOP_NAMES[stop.type] ?? stop.type} · mile ${stop.mile}`,
    rows: [
      { label: 'Starts', value: formatLocalDateTime(stop.start, timeZone) },
      { label: 'Ends', value: formatLocalDateTime(stop.end, timeZone) },
    ],
  }
}
