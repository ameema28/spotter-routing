import type { ExpressionSpecification } from 'maplibre-gl'
import { riskInfo, UNKNOWN_RISK } from '../risk'

// Layer ids the map listens to for clicks and hover.
export const CHECKPOINT_LAYER = 'checkpoints'
export const ROUTE_HIT_LAYER = 'route-hit'

export const OTHER_ROUTE_COLOR = '#7b8794'

// label is the short text on the map pin; name is the full name in the legend.
export const STOP_PIN: Record<string, { label: string; name: string; color: string }> = {
  break: { label: '30 min', name: '30-min break', color: '#455a64' },
  rest: { label: '10 h rest', name: '10-h rest', color: '#283593' },
}

// A GPU-side lookup from a feature's risk level to the same colours as the cards (risk.ts).
// A null level becomes -1 and, like any unexpected value, falls through to Unknown grey.
export function riskColorExpression(level: ExpressionSpecification = ['get', 'level']): ExpressionSpecification {
  return [
    'match', ['coalesce', level, -1],
    0, riskInfo(0).color,
    1, riskInfo(1).color,
    2, riskInfo(2).color,
    3, riskInfo(3).color,
    4, riskInfo(4).color,
    UNKNOWN_RISK.color,
  ]
}

// True for features on the selected route; used to size and fade checkpoints.
export function onRoute(routeId: number | null): ExpressionSpecification {
  return ['==', ['get', 'routeId'], routeId ?? -1]
}
