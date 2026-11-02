import { describe, expect, it } from 'vitest'
import { formatDuration, formatLocalDateTime, formatMiles, routeTitle } from './format'

describe('formatMiles', () => {
  it('adds thousands separators and one decimal', () => {
    expect(formatMiles(968.7)).toBe('968.7 mi')
    expect(formatMiles(1234.56)).toBe('1,234.6 mi')
    expect(formatMiles(0)).toBe('0 mi')
  })
})

describe('formatDuration', () => {
  // Same rule as backend/routing/domain/formatting.py, so both sides read the same.
  it('shows hours and minutes, rounded to the minute', () => {
    expect(formatDuration(26 * 3600 + 5 * 60)).toBe('26 h 5 min')
    expect(formatDuration(14 * 3600 + 48 * 60 + 29)).toBe('14 h 48 min')
  })

  it('drops the hours under an hour', () => {
    expect(formatDuration(45 * 60)).toBe('45 min')
    expect(formatDuration(0)).toBe('0 min')
  })

  it('carries 59.5 minutes up to the next hour', () => {
    expect(formatDuration(3600 + 59 * 60 + 30)).toBe('2 h 0 min')
  })
})

describe('routeTitle', () => {
  it('capitalises a generated route label and leaves the rest alone', () => {
    expect(routeTitle('generated alternative (via Kansas City)')).toBe('Generated alternative (via Kansas City)')
    expect(routeTitle('Fastest route')).toBe('Fastest route')
  })
})

describe('formatLocalDateTime', () => {
  it('shows the time in the given zone with its name', () => {
    const text = formatLocalDateTime('2026-11-02T22:00:00-06:00', 'America/Chicago')
    expect(text).toContain('10:00')
    expect(text).toContain('CST')
  })
})
