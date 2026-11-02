import { describe, expect, it } from 'vitest'
import { fromLocalInputValue, nextFullHour, toIsoWithOffset, toLocalInputValue, validateDeparture } from './departure'

const NOW = new Date(2026, 10, 2, 21, 20, 45)    // 2 Nov 2026, 21:20:45 local time
const HOUR = 3600 * 1000

describe('nextFullHour', () => {
  it('rounds up to the next hour on the clock', () => {
    const next = nextFullHour(NOW)
    expect([next.getHours(), next.getMinutes(), next.getSeconds()]).toEqual([22, 0, 0])
  })

  it('moves an exact hour on by one, so the default is never in the past', () => {
    expect(nextFullHour(new Date(2026, 10, 2, 21, 0, 0)).getHours()).toBe(22)
  })
})

describe('local input value', () => {
  it('formats for a datetime-local input and reads back the same time', () => {
    const value = toLocalInputValue(new Date(2026, 10, 2, 8, 5))
    expect(value).toBe('2026-11-02T08:05')
    expect(fromLocalInputValue(value)?.getTime()).toBe(new Date(2026, 10, 2, 8, 5).getTime())
  })

  it('reads an empty or broken value as no date', () => {
    expect(fromLocalInputValue('')).toBeNull()
    expect(fromLocalInputValue('not a date')).toBeNull()
  })
})

describe('toIsoWithOffset', () => {
  it('writes local time with its UTC offset, which the backend requires', () => {
    const date = new Date(2026, 10, 2, 22, 0, 0)
    const iso = toIsoWithOffset(date)
    expect(iso).toMatch(/^2026-11-02T22:00:00[+-]\d{2}:\d{2}$/)
    expect(new Date(iso).getTime()).toBe(date.getTime())
  })
})

describe('validateDeparture', () => {
  it('accepts from 1 hour ago to 7 days ahead, like the backend', () => {
    expect(validateDeparture(new Date(NOW.getTime() - HOUR + 1000), NOW)).toBeNull()
    expect(validateDeparture(new Date(NOW.getTime() + 7 * 24 * HOUR - 1000), NOW)).toBeNull()
  })

  it('rejects times outside that window with the backend wording', () => {
    const message = 'Departure must be between 1 hour ago and 7 days from now.'
    expect(validateDeparture(new Date(NOW.getTime() - 2 * HOUR), NOW)).toBe(message)
    expect(validateDeparture(new Date(NOW.getTime() + 8 * 24 * HOUR), NOW)).toBe(message)
  })

  it('asks for a time when there is none', () => {
    expect(validateDeparture(null, NOW)).toBe('Choose a departure date and time.')
  })
})
