import { Marker } from 'react-map-gl/maplibre'
import type { FeatureCollection, Point } from 'geojson'
import type { BreakProps, LonLat } from '../../map/geojson'
import { STOP_PIN } from '../../map/styles'
import MapPin from './MapPin'

interface Props {
  data: FeatureCollection<Point, BreakProps>
  selectedRouteId: number | null
  onOpen: (routeId: number, index: number, at: LonLat) => void
}

// Only the selected route's stops, about 2 per trip, so plain React markers cost nothing here.
export default function BreakMarkers({ data, selectedRouteId, onOpen }: Props) {
  return data.features
    .filter((feature) => feature.properties.routeId === selectedRouteId)
    .map((feature) => {
      const { routeId, index, type } = feature.properties
      const [lon, lat] = feature.geometry.coordinates
      const pin = STOP_PIN[type] ?? STOP_PIN.break
      return (
        <Marker
          key={`${routeId}-${index}`} longitude={lon} latitude={lat} anchor="center"
          onClick={(event) => {
            // Stop the map's own click handler from closing the popup straight away.
            event.originalEvent.stopPropagation()
            onOpen(routeId, index, [lon, lat])
          }}
        >
          <MapPin color={pin.color}>{pin.label}</MapPin>
        </Marker>
      )
    })
}
