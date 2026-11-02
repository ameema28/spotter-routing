import Alert from '@mui/material/Alert'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import type { RoutePlan } from '../api/types'
import { placeName } from '../format'
import RecommendationBanner from './RecommendationBanner'
import RouteCard from './RouteCard'

interface Props {
  plan: RoutePlan
  selectedRouteId: number | null
  onSelectRoute: (id: number) => void
}

export default function ResultsPanel({ plan, selectedRouteId, onSelectRoute }: Props) {
  const routesInRankOrder = plan.ranking
    .map((id) => plan.routes.find((route) => route.id === id))
    .filter((route) => route !== undefined)
  const { routing, weather, compute } = plan.timings_ms

  return (
    <Stack spacing={2}>
      {/* The places the geocoder matched, so a wrong match ("Nowhereville" → Dayton) is obvious. */}
      <Typography variant="subtitle1" component="h2" sx={{ fontWeight: 600 }}>
        {placeName(plan.origin.label)} → {placeName(plan.destination.label)}
      </Typography>
      <RecommendationBanner plan={plan} />
      {plan.notes.map((note) => <Alert key={note} severity="info">{note}</Alert>)}
      {routesInRankOrder.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          recommended={route.id === plan.recommendation.route_id}
          selected={route.id === selectedRouteId}
          onSelect={onSelectRoute}
        />
      ))}
      <Typography variant="caption" color="text.secondary">
        Server time: routing {routing} ms · weather {weather} ms · compute {compute} ms
      </Typography>
    </Stack>
  )
}
