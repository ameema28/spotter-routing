import Box from '@mui/material/Box'
import { useTheme } from '@mui/material/styles'
import Map, { NavigationControl, type MapLayerMouseEvent, type MapRef } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
// maplibre-gl 6 runs its tile worker from a separate file; Vite needs to be told to bundle it.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { RoutePlan } from '../api/types'
import { routeTitle } from '../format'
import {
  planBounds, planToBreaksGeoJSON, planToCheckpointsGeoJSON, planToRoutesGeoJSON, type LonLat,
} from '../map/geojson'
import { buildHeatmapGeoJSON } from '../map/heatmap'
import { breakPopupData, checkpointPopupData, type PopupData } from '../map/popups'
import { CHECKPOINT_LAYER, ROUTE_HIT_LAYER } from '../map/styles'
import { departureOf } from '../timeLabels'
import BreakMarkers from './map/BreakMarkers'
import CheckpointLayer from './map/CheckpointLayer'
import HeatmapLayer from './map/HeatmapLayer'
import MapLegend from './map/MapLegend'
import MapPopup from './map/MapPopup'
import PlaceMarkers from './map/PlaceMarkers'
import RouteLayers from './map/RouteLayers'
import TimeSlider from './map/TimeSlider'
import TruckMarkers from './map/TruckMarkers'

// OpenFreeMap: no key or sign-up. Positron is muted, so the risk colours stand out.
// The required OpenMapTiles and OpenStreetMap credit comes from the tile source; MapLibre's default control shows it.
const BASEMAP_STYLE = 'https://tiles.openfreemap.org/styles/positron'

const CONTINENTAL_US = { longitude: -98.5, latitude: 39.5, zoom: 3.5 }
const INTERACTIVE_LAYERS = [CHECKPOINT_LAYER, ROUTE_HIT_LAYER]
const HOUR_MS = 3600 * 1000
// Room for the overlays, so no pin ends up under them: the slider at the bottom, the open legend top-left on
// wide screens. The side panel sits beside the map, not over it, so it needs nothing.
const FIT_PADDING_WIDE = { top: 48, right: 56, bottom: 150, left: 250 }
const FIT_PADDING_NARROW = { top: 56, right: 40, bottom: 150, left: 40 }
// Open the page with ?perf=1 to show how long each slider move takes to reach the screen.
const SHOW_PERF = new URLSearchParams(window.location.search).has('perf')
const EMPTY_HEATMAP = buildHeatmapGeoJSON({ start: '', hours: [], step_deg: [0, 0], points: [], levels: [] })

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
    // Always a collection, even when empty, so the heatmap layer stays first and under the routes.
    heatmap: plan.heatmap ? buildHeatmapGeoJSON(plan.heatmap) : EMPTY_HEATMAP,
  }
  // Shows in the dev console once per search; a route click or slider move should never print it again.
  if (import.meta.env.DEV) console.debug(`GeoJSON built in ${(performance.now() - started).toFixed(1)} ms`)
  return data
}

export default function MapView({ plan, selectedRouteId, onSelectRoute }: Props) {
  const theme = useTheme()
  const mapRef = useRef<MapRef>(null)
  const [loaded, setLoaded] = useState(false)
  const [hovering, setHovering] = useState(false)
  const [popup, setPopup] = useState<OpenPopup | null>(null)
  // Like the popup, the slider hour belongs to its plan, so each new search starts at departure.
  const [timeChoice, setTimeChoice] = useState<{ plan: RoutePlan; hour: number } | null>(null)
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [lastUpdateMs, setLastUpdateMs] = useState<number | null>(null)

  // Built once per plan. Selecting a route or moving the slider changes layer filters and paint values only.
  const data = useMemo(() => (plan ? buildMapData(plan) : null), [plan])
  const hour = plan && timeChoice?.plan === plan ? timeChoice.hour : 0
  const departure = plan ? departureOf(plan) : null

  // Fit to a new plan only, so clicking between routes or resizing never makes the map jump.
  useEffect(() => {
    if (!plan || !loaded) return
    const wide = window.matchMedia(`(min-width: ${theme.breakpoints.values.md}px)`).matches
    mapRef.current?.fitBounds(planBounds(plan), { padding: wide ? FIT_PADDING_WIDE : FIT_PADDING_NARROW, duration: 800 })
  }, [plan, loaded, theme])

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

  const changeHour = useCallback((next: number) => {
    if (!plan) return
    const map = mapRef.current?.getMap()
    if (map && (SHOW_PERF || import.meta.env.DEV)) {
      // From the slider change to the next frame MapLibre draws, including React's update and the paint change.
      const started = performance.now()
      map.once('render', () => {
        const ms = performance.now() - started
        if (import.meta.env.DEV) console.debug(`Slider update drawn in ${ms.toFixed(1)} ms`)
        if (SHOW_PERF) setLastUpdateMs(ms)
      })
      map.triggerRepaint()
    }
    setTimeChoice({ plan, hour: next })
  }, [plan])

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
            <HeatmapLayer data={data.heatmap} hour={hour} visible={showHeatmap && plan.heatmap !== null} />
            <RouteLayers data={data.routes} selectedRouteId={selectedRouteId} />
            <CheckpointLayer data={data.checkpoints} selectedRouteId={selectedRouteId} />
            <PlaceMarkers origin={plan.origin} destination={plan.destination} />
            <BreakMarkers data={data.breaks} selectedRouteId={selectedRouteId} onOpen={openBreak} />
            {departure && (
              <TruckMarkers routes={plan.routes} time={Date.parse(departure) + hour * HOUR_MS} selectedRouteId={selectedRouteId} />
            )}
          </>
        )}
        {visiblePopup && <MapPopup at={visiblePopup.at} data={visiblePopup.data} onClose={() => setPopup(null)} />}
      </Map>
      {plan && <MapLegend recommendedLabel={recommended ? routeTitle(recommended.label) : null} />}
      {plan && departure && (
        <TimeSlider
          startIso={departure} hour={hour} onHourChange={changeHour}
          heatmapAvailable={plan.heatmap !== null} showHeatmap={showHeatmap} onShowHeatmapChange={setShowHeatmap}
          lastUpdateMs={SHOW_PERF ? lastUpdateMs : null}
        />
      )}
    </Box>
  )
}
