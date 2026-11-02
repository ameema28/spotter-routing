import { Marker } from 'react-map-gl/maplibre'
import type { Place } from '../../api/types'
import { placeName } from '../../format'
import MapPin from './MapPin'

// Labelled with the places the geocoder actually matched, so a wrong match is visible on the map.
export default function PlaceMarkers({ origin, destination }: { origin: Place; destination: Place }) {
  return (
    <>
      <Marker longitude={origin.lon} latitude={origin.lat} anchor="bottom">
        <MapPin color="#1b5e20">Start: {placeName(origin.label)}</MapPin>
      </Marker>
      <Marker longitude={destination.lon} latitude={destination.lat} anchor="bottom">
        <MapPin color="#263238">End: {placeName(destination.label)}</MapPin>
      </Marker>
    </>
  )
}
