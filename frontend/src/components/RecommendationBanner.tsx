import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'
import type { RoutePlan } from '../api/types'
import { routeTitle } from '../format'

// With no recommendation the backend's reason is already the warning,
// e.g. "No safe route — consider delaying departure" or "Insufficient forecast data".
export default function RecommendationBanner({ plan }: { plan: RoutePlan }) {
  const { route_id: routeId, reason } = plan.recommendation
  const route = plan.routes.find((candidate) => candidate.id === routeId)

  if (!route) {
    return <Alert severity="warning"><AlertTitle>No route recommended</AlertTitle>{reason}</Alert>
  }
  return <Alert severity="success"><AlertTitle>Recommended: {routeTitle(route.label)}</AlertTitle>{reason}</Alert>
}
