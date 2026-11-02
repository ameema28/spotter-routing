import type { RoutePlan } from './api/types'

// A new plan starts on the recommended route, or on the best ranked one when none is recommended.
export function defaultRouteId(plan: RoutePlan | null): number | null {
  if (!plan) return null
  return plan.recommendation.route_id ?? plan.ranking[0] ?? null
}
