import { describe, expect, it } from 'vitest'
import { RISK_LEGEND, riskInfo } from './risk'

describe('riskInfo', () => {
  it('gives each backend level its label and colour', () => {
    expect(riskInfo(0)).toEqual({ label: 'Low', color: '#2e7d32' })
    expect(riskInfo(1).label).toBe('Moderate')
    expect(riskInfo(2).label).toBe('High')
    expect(riskInfo(3).label).toBe('Severe')
    expect(riskInfo(4).label).toBe('No Travel')
  })

  it('shows missing data as Unknown, never as Low', () => {
    expect(riskInfo(null).label).toBe('Unknown')
  })

  it('treats a level outside 0-4 as Unknown instead of crashing', () => {
    expect(riskInfo(7 as never).label).toBe('Unknown')
  })

  it('uses a different colour for every legend entry', () => {
    const colors = RISK_LEGEND.map((risk) => risk.color)
    expect(new Set(colors).size).toBe(colors.length)
    expect(RISK_LEGEND.map((risk) => risk.label)).toEqual(
      ['Low', 'Moderate', 'High', 'Severe', 'No Travel', 'Unknown'])
  })
})
