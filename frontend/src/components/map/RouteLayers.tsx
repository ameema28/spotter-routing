import { useTheme } from '@mui/material/styles'
import { Layer, Source } from 'react-map-gl/maplibre'
import type { FeatureCollection, LineString } from 'geojson'
import type { RouteProps } from '../../map/geojson'
import { OTHER_ROUTE_COLOR, ROUTE_HIT_LAYER } from '../../map/styles'

interface Props {
  data: FeatureCollection<LineString, RouteProps>
  selectedRouteId: number | null
}

// One source for all routes. Changing the selection only changes the filters below, never the data.
export default function RouteLayers({ data, selectedRouteId }: Props) {
  const theme = useTheme()
  const selected = selectedRouteId ?? -1

  return (
    <Source id="routes" type="geojson" data={data}>
      <Layer
        id="route-others" type="line" filter={['!=', ['get', 'id'], selected]}
        layout={{ 'line-join': 'round', 'line-cap': 'round' }}
        paint={{ 'line-color': OTHER_ROUTE_COLOR, 'line-width': 3, 'line-opacity': 0.8, 'line-dasharray': [2, 1.5] }}
      />
      {/* A white casing under the selected line keeps it readable over the basemap. */}
      <Layer
        id="route-selected-casing" type="line" filter={['==', ['get', 'id'], selected]}
        layout={{ 'line-join': 'round', 'line-cap': 'round' }}
        paint={{ 'line-color': '#ffffff', 'line-width': 9 }}
      />
      <Layer
        id="route-selected" type="line" filter={['==', ['get', 'id'], selected]}
        layout={{ 'line-join': 'round', 'line-cap': 'round' }}
        paint={{ 'line-color': theme.palette.primary.main, 'line-width': 5 }}
      />
      {/* Invisible and wide, so a route is easy to click or tap. */}
      <Layer id={ROUTE_HIT_LAYER} type="line" paint={{ 'line-color': '#000000', 'line-opacity': 0, 'line-width': 14 }} />
    </Source>
  )
}
