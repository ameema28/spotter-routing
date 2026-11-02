// Same window as backend/routing/serializers.py, checked here so the user hears about it before searching.
const EARLIEST_MS = 60 * 60 * 1000
const LATEST_MS = 7 * 24 * 60 * 60 * 1000
const OUT_OF_RANGE = 'Departure must be between 1 hour ago and 7 days from now.'

const pad = (value: number) => String(value).padStart(2, '0')

export function nextFullHour(now: Date): Date {
  const next = new Date(now)
  next.setHours(now.getHours() + 1, 0, 0, 0)
  return next
}

// A datetime-local input works in local time with no zone: "2026-11-02T08:05".
export function toLocalInputValue(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
    + `T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function fromLocalInputValue(value: string): Date | null {
  if (!value) return null
  // A date-time string with no zone is read as local time, which is what the input shows.
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

// The backend rejects a time without a zone, because it could be hours off for the driver.
export function toIsoWithOffset(date: Date): string {
  const offsetMinutes = -date.getTimezoneOffset()
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const absolute = Math.abs(offsetMinutes)
  return `${toLocalInputValue(date)}:${pad(date.getSeconds())}`
    + `${sign}${pad(Math.floor(absolute / 60))}:${pad(absolute % 60)}`
}

export function validateDeparture(date: Date | null, now: Date): string | null {
  if (!date) return 'Choose a departure date and time.'
  const fromNow = date.getTime() - now.getTime()
  return fromNow >= -EARLIEST_MS && fromNow <= LATEST_MS ? null : OUT_OF_RANGE
}
