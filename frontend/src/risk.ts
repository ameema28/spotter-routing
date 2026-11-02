import type { RiskLevel } from './api/types'

export interface RiskInfo {
  label: string
  color: string
}

// Same scale as the backend (0-4). Colour is never the only signal: every use shows the label too.
const RISK_BY_LEVEL: Record<number, RiskInfo> = {
  0: { label: 'Low', color: '#2e7d32' },
  1: { label: 'Moderate', color: '#f9a825' },
  2: { label: 'High', color: '#ef6c00' },
  3: { label: 'Severe', color: '#c62828' },
  4: { label: 'No Travel', color: '#6a1b9a' },
}

// null means a weather input was missing, which the backend treats as unknown rather than safe.
export const UNKNOWN_RISK: RiskInfo = { label: 'Unknown', color: '#9e9e9e' }

export function riskInfo(level: RiskLevel): RiskInfo {
  if (level === null) return UNKNOWN_RISK
  return RISK_BY_LEVEL[level] ?? UNKNOWN_RISK
}

export const RISK_LEGEND: RiskInfo[] = [0, 1, 2, 3, 4].map((level) => RISK_BY_LEVEL[level]).concat(UNKNOWN_RISK)
