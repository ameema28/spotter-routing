import Box from '@mui/material/Box'
import { useTheme } from '@mui/material/styles'
import { Marker } from 'react-map-gl/maplibre'
import type { Route } from '../../api/types'
import { formatMiles, routeTitle } from '../../format'
import type { TruckState } from '../../map/truck'

interface Props {
  trucks: { route: Route; state: TruckState }[]
  selectedRouteId: number | null
}

export function TruckDot({ selected, color }: { selected: boolean; color: string }) {
  const size = selected ? 18 : 12
  return (
    <Box sx={{
      width: size, height: size, borderRadius: 1, bgcolor: color, border: '2px solid #ffffff', boxShadow: 2,
    }} />
  )
}

// One marker per route (3 at most), so plain React markers are cheap even while the slider moves.
// zIndex keeps them under the stop and place pins, which carry text that must stay readable.
export default function TruckMarkers({ trucks, selectedRouteId }: Props) {
  const theme = useTheme()
  return trucks.map(({ route, state }) => {
    const selected = route.id === selectedRouteId
    const tooltip = `${routeTitle(route.label)}: mile ${formatMiles(state.mile)}, ${state.status}`
    return (
      <Marker key={route.id} longitude={state.lngLat[0]} latitude={state.lngLat[1]} anchor="center"
        style={{ zIndex: selected ? 2 : 1 }}>
        <Box title={tooltip} aria-label={tooltip} role="img">
          <TruckDot selected={selected} color={selected ? theme.palette.primary.main : '#5f6b7a'} />
        </Box>
      </Marker>
    )
  })
}
