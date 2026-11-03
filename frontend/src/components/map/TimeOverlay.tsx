import { useCallback, useMemo, useState } from 'react'
import { useMap } from 'react-map-gl/maplibre'
import type { FeatureCollection, Polygon } from 'geojson'
import type { RoutePlan } from '../../api/types'
import type { HeatmapRetry } from '../../heatmapRetry'
import { useSliderPerf } from '../../hooks/useSliderPerf'
import type { HeatmapProps } from '../../map/heatmap'
import { truckTimeline } from '../../map/truck'
import HeatmapLayer from './HeatmapLayer'
import TimeSlider from './TimeSlider'
import TruckMarkers from './TruckMarkers'

interface Props {
  plan: RoutePlan
  searchId: number
  departureIso: string
  heatmap: FeatureCollection<Polygon, HeatmapProps>
  heatmapRetry: { state: HeatmapRetry; retryNow: () => void }
  selectedRouteId: number | null
}

// Everything that changes with the slider hour lives here, so moving the slider re-renders only the heatmap
// colour, the three trucks and the slider itself, not the routes, checkpoints, legend or side panel.
// Rendered first inside <Map>, so the heatmap layer is added before (and drawn under) the routes.
export default function TimeOverlay({ plan, searchId, departureIso, heatmap, heatmapRetry, selectedRouteId }: Props) {
  const { current: map } = useMap()
  // The hour belongs to its search, so each new search starts at departure and a heatmap retry keeps it.
  const [timeChoice, setTimeChoice] = useState<{ searchId: number; hour: number } | null>(null)
  const [showHeatmap, setShowHeatmap] = useState(true)
  const hour = timeChoice?.searchId === searchId ? timeChoice.hour : 0
  const hasLevels = Boolean(plan.heatmap?.levels)

  // 49 positions per route, worked out once per search; the slider then only picks one.
  const { routes } = plan
  const timelines = useMemo(() => {
    const departureMs = Date.parse(departureIso)
    return routes.map((route) => ({ route, states: truckTimeline(route, departureMs) }))
  }, [routes, departureIso])

  const getMap = useCallback(() => map?.getMap(), [map])
  const { timing, markChange } = useSliderPerf(getMap, hour)
  const changeHour = useCallback((next: number) => {
    markChange()
    setTimeChoice({ searchId, hour: next })
  }, [searchId, markChange])

  return (
    <>
      <HeatmapLayer data={heatmap} hour={hour} visible={showHeatmap && hasLevels} />
      <TruckMarkers
        trucks={timelines.map(({ route, states }) => ({ route, state: states[hour] }))}
        selectedRouteId={selectedRouteId}
      />
      <TimeSlider
        startIso={departureIso} hour={hour} onHourChange={changeHour}
        heatmapAvailable={hasLevels} heatmapRetry={heatmapRetry} showHeatmap={showHeatmap} onShowHeatmapChange={setShowHeatmap}
        timing={timing}
      />
    </>
  )
}
