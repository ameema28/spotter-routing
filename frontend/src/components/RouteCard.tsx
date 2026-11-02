import Card from '@mui/material/Card'
import CardActionArea from '@mui/material/CardActionArea'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import type { Route } from '../api/types'
import { formatMiles, routeTitle } from '../format'
import RiskBar from './RiskBar'

interface Props {
  route: Route
  recommended: boolean
  selected: boolean
  onSelect: (id: number) => void
}

// Backend tiers (ranking.py): 1 = too many unknown miles, 2 = has No Travel miles.
const TIER_TEXT: Record<number, string> = {
  1: 'Insufficient forecast data: over 25% of the miles have no forecast',
  2: 'Has No Travel miles',
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Stack>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography variant="body2">{value}</Typography>
    </Stack>
  )
}

export default function RouteCard({ route, recommended, selected, onSelect }: Props) {
  const { summary } = route
  const breaks = route.breaks.length

  return (
    <Card variant="outlined" sx={{ borderColor: selected ? 'primary.main' : 'divider', borderWidth: selected ? 2 : 1 }}>
      {/* A button: Tab reaches it, Enter or Space selects it, and aria-pressed tells screen readers it's chosen. */}
      <CardActionArea onClick={() => onSelect(route.id)} aria-pressed={selected}>
        <CardContent>
          <Stack spacing={1.5}>
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }} useFlexGap>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mr: 'auto' }}>{routeTitle(route.label)}</Typography>
              {recommended && <Chip size="small" color="success" label="Recommended" />}
              <Chip size="small" variant="outlined" label={route.source === 'mapbox' ? 'Mapbox' : 'Generated'} />
            </Stack>
            <Stack direction="row" spacing={2} useFlexGap sx={{ flexWrap: 'wrap' }}>
              <Stat label="Distance" value={formatMiles(route.distance_mi)} />
              <Stat label="Driving" value={route.drive_time} />
              <Stat label="Trip incl. breaks" value={`${route.trip_time} (${breaks} break${breaks === 1 ? '' : 's'})`} />
            </Stack>
            <Stack direction="row" spacing={2} useFlexGap sx={{ flexWrap: 'wrap' }}>
              <Stat label="Severe" value={formatMiles(summary.severe_miles)} />
              <Stat label="High" value={formatMiles(summary.high_miles)} />
              <Stat label="No Travel" value={formatMiles(summary.no_travel_miles)} />
              <Stat label="Unknown" value={formatMiles(summary.unknown_miles)} />
              <Stat label="Avg risk (0–4)" value={summary.avg_risk === null ? '–' : summary.avg_risk.toFixed(2)} />
            </Stack>
            <RiskBar milesByLevel={summary.miles_by_level} />
            {TIER_TEXT[summary.tier] && (
              <Typography variant="body2" color="warning.dark">{TIER_TEXT[summary.tier]}</Typography>
            )}
          </Stack>
        </CardContent>
      </CardActionArea>
    </Card>
  )
}
