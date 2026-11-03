import Box from '@mui/material/Box'
import { useTheme } from '@mui/material/styles'
import Map, { NavigationControl, type MapLayerMouseEvent, type MapRef } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
// maplibre-gl 6 runs its tile worker from a separate file; Vite needs to be told to bundle it.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { RoutePlan } from '../api/types'
import { routeTitle } from '../format'
import type { HeatmapRetry } from '../heatmapRetry'
import {
  planBounds, planToBreaksGeoJSON, planToCheckpointsGeoJSON, planToRoutesGeoJSON, type LonLat,
} from '../map/geojson'
import { buildHeatmapGeoJSON } from '../map/heatmap'
import { breakPopupData, checkpointPopupData, type PopupData } from '../map/popups'
import { CHECKPOINT_LAYER, ROUTE_HIT_LAYER } from '../map/styles'
import { departureOf } from '../timeLabels'
import BreakMarkers from './map/BreakMarkers'
import CheckpointLayer from './map/CheckpointLayer'
import MapLegend from './map/MapLegend'
import MapPopup from './map/MapPopup'
import PlaceMarkers from './map/PlaceMarkers'
import RouteLayers from './map/RouteLayers'
import TimeOverlay from './map/TimeOverlay'

// OpenFreeMap: no key or sign-up. Positron is muted, so the risk colours stand out.
// The required OpenMapTiles and OpenStreetMap credit comes from the tile source; MapLibre's default control shows it.
const BASEMAP_STYLE = 'https://tiles.openfreemap.org/styles/positron'

const CONTINENTAL_US = { longitude: -98.5, latitude: 39.5, zoom: 3.5 }
const INTERACTIVE_LAYERS = [CHECKPOINT_LAYER, ROUTE_HIT_LAYER]
// Room for the overlays, so no pin ends up under them: the slider at the bottom, the open legend top-left on
// large screens. The side panel sits beside the map, not over it, so it needs nothing. The right side needs half
// a start or end pin (about 170 px wide, centred on its place) when the trip ends at the right edge.
const FIT_PADDING_WIDE = { top: 48, right: 96, bottom: 150, left: 250 }
// Narrow screens: the start and end pins are centred on their place and about 170 px wide, so half of that is
// needed at each side, and the top clears the zoom buttons.
const FIT_PADDING_NARROW = { top: 72, right: 96, bottom: 150, left: 96 }
const EMPTY_HEATMAP = buildHeatmapGeoJSON({ start: '', hours: [], step_deg: [0, 0], points: [], levels: [] })

interface Props {
  plan: RoutePlan | null
  searchId: number    // changes once per search, never on a heatmap retry
  heatmapRetry: { state: HeatmapRetry; retryNow: () => void }
  selectedRouteId: number | null
  onSelectRoute: (id: number) => void
}

interface OpenPopup {
  searchId: number
  at: LonLat
  data: PopupData
}

function buildRouteData(plan: RoutePlan) {
  const started = performance.now()
  const data = {
    routes: planToRoutesGeoJSON(plan),
    checkpoints: planToCheckpointsGeoJSON(plan),
    breaks: planToBreaksGeoJSON(plan),
  }
  // Shows in the dev console once per search; a route click, slider move or heatmap retry should never print it.
  if (import.meta.env.DEV) console.debug(`GeoJSON built in ${(performance.now() - started).toFixed(1)} ms`)
  return data
}

export default function MapView({ plan, searchId, heatmapRetry, selectedRouteId, onSelectRoute }: Props) {
  const theme = useTheme()
  const mapRef = useRef<MapRef>(null)
  const [loaded, setLoaded] = useState(false)
  const [hovering, setHovering] = useState(false)
  const [popup, setPopup] = useState<OpenPopup | null>(null)

  // Built once per search: within a search the routes never change. Selecting a route or moving the slider
  // changes layer filters and paint values only, and a heatmap retry only swaps the heatmap source below.
  // oxlint-disable-next-line react-hooks/exhaustive-deps -- keyed on the search: a retry replaces the plan object
  const data = useMemo(() => (plan ? buildRouteData(plan) : null), [searchId])
  // Always a collection, even when empty, so the heatmap layer stays first and under the routes.
  const heatmap = plan?.heatmap
  const heatmapData = useMemo(() => (heatmap ? buildHeatmapGeoJSON(heatmap) : EMPTY_HEATMAP), [heatmap])
  const departure = plan ? departureOf(plan) : null

  // Fit to a new search only, so clicking between routes, resizing or a heatmap retry never moves the map.
  useEffect(() => {
    if (!plan || !loaded) return
    const wide = window.matchMedia(`(min-width: ${theme.breakpoints.values.lg}px)`).matches
    mapRef.current?.fitBounds(planBounds(plan), { padding: wide ? FIT_PADDING_WIDE : FIT_PADDING_NARROW, duration: 800 })
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- keyed on the search: a retry replaces the plan object
  }, [searchId, loaded, theme])

  // A popup belongs to the search it was opened on, so it disappears with a new search.
  const visiblePopup = popup && popup.searchId === searchId ? popup : null

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
      if (checkpoint) setPopup({ searchId, at: [checkpoint.lon, checkpoint.lat], data: checkpointPopupData(checkpoint) })
      return
    }
    setPopup(null)
    onSelectRoute(Number(feature.properties.id))
  }

  // Stable between renders, so the memoised stop markers don't redraw on every hover.
  const openBreak = useCallback((routeId: number, index: number, at: LonLat) => {
    const stop = plan?.routes.find((route) => route.id === routeId)?.breaks[index]
    if (plan && stop) setPopup({ searchId, at, data: breakPopupData(stop) })
  }, [plan, searchId])

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
            {/* First, so its heatmap layer sits under the routes; it owns the slider hour. */}
            {departure && (
              <TimeOverlay
                plan={plan} searchId={searchId} departureIso={departure} heatmap={heatmapData}
                heatmapRetry={heatmapRetry} selectedRouteId={selectedRouteId}
              />
            )}
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
