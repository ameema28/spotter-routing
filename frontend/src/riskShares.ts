import type { MilesByLevel, RiskLevel } from './api/types'
import { riskInfo } from './risk'

export interface RiskShare {
  label: string
  color: string
  miles: number
  percent: number
}

const ORDER: [keyof MilesByLevel, RiskLevel][] = [
  ['low', 0], ['moderate', 1], ['high', 2], ['severe', 3], ['no_travel', 4], ['unknown', null],
]

// The backend already worked out the miles at each level; this only turns them into bar widths.
export function riskShares(milesByLevel: MilesByLevel): RiskShare[] {
  const total = ORDER.reduce((sum, [key]) => sum + milesByLevel[key], 0)
  if (total <= 0) return []
  return ORDER
    .filter(([key]) => milesByLevel[key] > 0)
    .map(([key, level]) => ({
      ...riskInfo(level),
      miles: milesByLevel[key],
      percent: (milesByLevel[key] / total) * 100,
    }))
}
