import { describe, expect, it } from 'vitest'
import type { Checkpoint } from '../api/types'
import { breakPopupData, checkpointPopupData } from './popups'

const CHECKPOINT: Checkpoint = {
  mile: 75, lat: 33.121, lon: -95.6622, eta: '2026-11-02T19:24:49+00:00', level: 0, driver: 'all low',
  wind: 17.7, gust: 24.2, rain: 0, snow: 0,
  precip_hour: '2026-11-02T20:00:00+00:00', wind_hour: '2026-11-02T19:00:00+00:00',
}

const valueOf = (rows: { label: string; value: string }[], label: string) =>
  rows.find((row) => row.label === label)?.value

describe('checkpointPopupData', () => {
  it('titles the popup with the mile and the risk label', () => {
    expect(checkpointPopupData(CHECKPOINT, 'America/Chicago').title).toBe('Mile 75 · Low')
  })

  it('lists the weather with units and the reason for the level', () => {
    const { rows } = checkpointPopupData(CHECKPOINT, 'America/Chicago')
    expect(valueOf(rows, 'Why')).toBe('all low')
    expect(valueOf(rows, 'Wind')).toBe('17.7 mph (gusts 24.2 mph)')
    expect(valueOf(rows, 'Rain')).toBe('0 in/hr')
    expect(valueOf(rows, 'Snow')).toBe('0 in/hr')
  })

  it('shows the ETA and the forecast hours in local time with the zone', () => {
    const { rows } = checkpointPopupData(CHECKPOINT, 'America/Chicago')
    expect(valueOf(rows, 'ETA')).toContain('1:24 PM CST')
    expect(valueOf(rows, 'Wind forecast hour')).toContain('1:00 PM CST')
    expect(valueOf(rows, 'Rain/snow forecast hour')).toContain('2:00 PM CST')
  })

  it('says "no data" instead of hiding a missing value', () => {
    const missing = { ...CHECKPOINT, level: null, wind: null, gust: null, rain: null, precip_hour: null }
    const data = checkpointPopupData(missing, 'America/Chicago')
    expect(data.title).toBe('Mile 75 · Unknown')
    expect(valueOf(data.rows, 'Wind')).toBe('no data')
    expect(valueOf(data.rows, 'Rain')).toBe('no data')
    expect(valueOf(data.rows, 'Rain/snow forecast hour')).toBe('no data')
  })
})

describe('breakPopupData', () => {
  it('names the stop and gives its times and mile', () => {
    const data = breakPopupData(
      { mile: 501.7, type: 'rest', start: '2026-11-03T03:00:00+00:00', end: '2026-11-03T13:00:00+00:00' },
      'America/Chicago',
    )
    expect(data.title).toBe('10-h rest · mile 501.7')
    expect(valueOf(data.rows, 'Starts')).toContain('9:00 PM CST')
    expect(valueOf(data.rows, 'Ends')).toContain('7:00 AM CST')
  })

  it('calls a short stop a 30-min break', () => {
    const data = breakPopupData({ mile: 10, type: 'break', start: '2026-11-03T03:00:00+00:00', end: '2026-11-03T03:30:00+00:00' })
    expect(data.title).toBe('30-min break · mile 10')
  })
})
