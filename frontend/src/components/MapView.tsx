import Box from '@mui/material/Box'
import Map, { NavigationControl, type MapLayerMouseEvent, type MapRef } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
// maplibre-gl 6 runs its tile worker from a separate file; Vite needs to be told to bundle it.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { RoutePlan } from '../api/types'
import { routeTitle } from '../format'
import {
  planBounds, planToBreaksGeoJSON, planToCheckpointsGeoJSON, planToRoutesGeoJSON, type LonLat,
} from '../map/geojson'
import { breakPopupData, checkpointPopupData, type PopupData } from '../map/popups'
import BreakMarkers from './map/BreakMarkers'
import { CHECKPOINT_LAYER, ROUTE_HIT_LAYER } from '../map/styles'
import CheckpointLayer from './map/CheckpointLayer'
import MapLegend from './map/MapLegend'
import MapPopup from './map/MapPopup'
import PlaceMarkers from './map/PlaceMarkers'
import RouteLayers from './map/RouteLayers'

// OpenFreeMap: no key or sign-up. Positron is muted, so the risk colours stand out.
// The required OpenMapTiles and OpenStreetMap credit comes from the tile source; MapLibre's default control shows it.
const BASEMAP_STYLE = 'https://tiles.openfreemap.org/styles/positron'

const CONTINENTAL_US = { longitude: -98.5, latitude: 39.5, zoom: 3.5 }
const INTERACTIVE_LAYERS = [CHECKPOINT_LAYER, ROUTE_HIT_LAYER]
// The side panel sits beside the map, not over it, so the padding only keeps lines off the edges and the legend.
const FIT_PADDING = 56

interface Props {
  plan: RoutePlan | null
  selectedRouteId: number | null
  onSelectRoute: (id: number) => void
}

interface OpenPopup {
  plan: RoutePlan
  at: LonLat
  data: PopupData
}

function buildMapData(plan: RoutePlan) {
  const started = performance.now()
  const data = {
    routes: planToRoutesGeoJSON(plan),
    checkpoints: planToCheckpointsGeoJSON(plan),
    breaks: planToBreaksGeoJSON(plan),
  }
  // Shows in the dev console once per search; a route click should never print it again.
  if (import.meta.env.DEV) console.debug(`GeoJSON built in ${(performance.now() - started).toFixed(1)} ms`)
  return data
}

export default function MapView({ plan, selectedRouteId, onSelectRoute }: Props) {
  const mapRef = useRef<MapRef>(null)
  const [loaded, setLoaded] = useState(false)
  const [hovering, setHovering] = useState(false)
  const [popup, setPopup] = useState<OpenPopup | null>(null)

  // Built once per plan. Selecting a route changes layer filters and paint values, not this data.
  const data = useMemo(() => (plan ? buildMapData(plan) : null), [plan])

  // Fit to a new plan only, so clicking between routes never makes the map jump.
  useEffect(() => {
    if (plan && loaded) mapRef.current?.fitBounds(planBounds(plan), { padding: FIT_PADDING, duration: 800 })
  }, [plan, loaded])

  // A popup belongs to the plan it was opened on, so it disappears with a new search.
  const visiblePopup = popup && popup.plan === plan ? popup : null

  useEffect(() => {
    if (!visiblePopup) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setPopup(null)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [visiblePopup])

  function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features?.[0]
    if (!plan || !feature) {
      setPopup(null)
      return
    }
    if (feature.layer.id === CHECKPOINT_LAYER) {
      const { routeId, index } = feature.properties as { routeId: number; index: number }
      const checkpoint = plan.routes.find((route) => route.id === routeId)?.checkpoints[index]
      if (checkpoint) setPopup({ plan, at: [checkpoint.lon, checkpoint.lat], data: checkpointPopupData(checkpoint) })
      return
    }
    setPopup(null)
    onSelectRoute(Number(feature.properties.id))
  }

  function openBreak(routeId: number, index: number, at: LonLat) {
    const stop = plan?.routes.find((route) => route.id === routeId)?.breaks[index]
    if (plan && stop) setPopup({ plan, at, data: breakPopupData(stop) })
  }

  const recommended = plan?.routes.find((route) => route.id === plan.recommendation.route_id)

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
      <Map
        ref={mapRef}
        initialViewState={CONTINENTAL_US}
        mapStyle={BASEMAP_STYLE}
        workerUrl={workerUrl}
        style={{ width: '100%', height: '100%' }}
        interactiveLayerIds={data ? INTERACTIVE_LAYERS : []}
        cursor={hovering ? 'pointer' : 'grab'}
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
        onClick={handleClick}
        onLoad={() => setLoaded(true)}
      >
        <NavigationControl position="top-right" showCompass={false} />
        {plan && data && (
          <>
            <RouteLayers data={data.routes} selectedRouteId={selectedRouteId} />
            <CheckpointLayer data={data.checkpoints} selectedRouteId={selectedRouteId} />
            <PlaceMarkers origin={plan.origin} destination={plan.destination} />
            <BreakMarkers data={data.breaks} selectedRouteId={selectedRouteId} onOpen={openBreak} />
          </>
        )}
        {visiblePopup && <MapPopup at={visiblePopup.at} data={visiblePopup.data} onClose={() => setPopup(null)} />}
      </Map>
      {plan && <MapLegend recommendedLabel={recommended ? routeTitle(recommended.label) : null} />}
    </Box>
  )
}
