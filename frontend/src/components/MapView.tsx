import Map, { NavigationControl } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
// maplibre-gl 6 runs its tile worker from a separate file; Vite needs to be told to bundle it.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

// OpenFreeMap: no key or sign-up. Positron is muted, so the risk colours stand out.
// The required OpenMapTiles and OpenStreetMap credit comes from the tile source; MapLibre's default control shows it.
const BASEMAP_STYLE = 'https://tiles.openfreemap.org/styles/positron'

const CONTINENTAL_US = { longitude: -98.5, latitude: 39.5, zoom: 3.5 }

export default function MapView() {
  return (
    <Map
      initialViewState={CONTINENTAL_US}
      mapStyle={BASEMAP_STYLE}
      workerUrl={workerUrl}
      style={{ width: '100%', height: '100%' }}
    >
      <NavigationControl position="top-right" showCompass={false} />
    </Map>
  )
}
