import { Marker } from 'react-map-gl/maplibre'
import { memo } from 'react'
import type { Place } from '../../api/types'
import { placeName } from '../../format'
import MapPin from './MapPin'

// Labelled with the places the geocoder actually matched, so a wrong match is visible on the map.
function PlaceMarkers({ origin, destination }: { origin: Place; destination: Place }) {
  return (
    <>
      <Marker longitude={origin.lon} latitude={origin.lat} anchor="bottom" style={{ zIndex: 4 }}>
        <MapPin color="#1b5e20">Start: {placeName(origin.label)}</MapPin>
      </Marker>
      <Marker longitude={destination.lon} latitude={destination.lat} anchor="bottom" style={{ zIndex: 4 }}>
        <MapPin color="#263238">End: {placeName(destination.label)}</MapPin>
      </Marker>
    </>
  )
}

// memo: skip re-rendering when the props are unchanged, e.g. while the map is hovered.
export default memo(PlaceMarkers)
