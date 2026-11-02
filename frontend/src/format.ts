const milesFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })

export function formatMiles(miles: number): string {
  return `${milesFormat.format(miles)} mi`
}

// Same rule as format_duration in backend/routing/domain/formatting.py.
export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return hours ? `${hours} h ${minutes} min` : `${minutes} min`
}

// Backend labels such as "generated alternative (via Kansas City)" start lower-case.
export function routeTitle(label: string): string {
  return label.charAt(0).toUpperCase() + label.slice(1)
}

// Geocoding is US-only, so the country adds nothing: "Dallas, Texas, United States" → "Dallas, Texas".
export function placeName(label: string): string {
  return label.replace(/, United States$/, '')
}

// Creating a formatter costs about 0.3 ms and the slider label needs one on every hour change, so keep one per zone.
const dateTimeFormats = new Map<string, Intl.DateTimeFormat>()

// timeZone is only passed by tests; the app always shows the browser's own zone.
export function formatLocalDateTime(iso: string, timeZone?: string): string {
  const key = timeZone ?? 'local'
  let format = dateTimeFormats.get(key)
  if (!format) {
    format = new Intl.DateTimeFormat('en-US', {
      weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
      timeZoneName: 'short', timeZone,
    })
    dateTimeFormats.set(key, format)
  }
  return format.format(new Date(iso))
}

// For example "America/Chicago (CST)".
export function timeZoneLabel(date: Date = new Date()): string {
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone
  const short = new Intl.DateTimeFormat('en-US', { timeZoneName: 'short' })
    .formatToParts(date).find((part) => part.type === 'timeZoneName')?.value
  return short ? `${zone} (${short})` : zone
}
