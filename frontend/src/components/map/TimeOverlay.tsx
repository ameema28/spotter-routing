import { useCallback, useMemo, useState } from 'react'
import { useMap } from 'react-map-gl/maplibre'
import type { FeatureCollection, Polygon } from 'geojson'
import type { RoutePlan } from '../../api/types'
import { useSliderPerf } from '../../hooks/useSliderPerf'
import type { HeatmapProps } from '../../map/heatmap'
import { truckTimeline } from '../../map/truck'
import HeatmapLayer from './HeatmapLayer'
import TimeSlider from './TimeSlider'
import TruckMarkers from './TruckMarkers'

interface Props {
  plan: RoutePlan
  departureIso: string
  heatmap: FeatureCollection<Polygon, HeatmapProps>
  selectedRouteId: number | null
}

// Everything that changes with the slider hour lives here, so moving the slider re-renders only the heatmap
// colour, the three trucks and the slider itself, not the routes, checkpoints, legend or side panel.
// Rendered first inside <Map>, so the heatmap layer is added before (and drawn under) the routes.
export default function TimeOverlay({ plan, departureIso, heatmap, selectedRouteId }: Props) {
  const { current: map } = useMap()
  // The hour belongs to its plan, so each new search starts at departure.
  const [timeChoice, setTimeChoice] = useState<{ plan: RoutePlan; hour: number } | null>(null)
  const [showHeatmap, setShowHeatmap] = useState(true)
  const hour = timeChoice?.plan === plan ? timeChoice.hour : 0

  // 49 positions per route, worked out once per plan; the slider then only picks one.
  const timelines = useMemo(() => {
    const departureMs = Date.parse(departureIso)
    return plan.routes.map((route) => ({ route, states: truckTimeline(route, departureMs) }))
  }, [plan, departureIso])

  const getMap = useCallback(() => map?.getMap(), [map])
  const { timing, markChange } = useSliderPerf(getMap, hour)
  const changeHour = useCallback((next: number) => {
    markChange()
    setTimeChoice({ plan, hour: next })
  }, [plan, markChange])

  return (
    <>
      <HeatmapLayer data={heatmap} hour={hour} visible={showHeatmap && plan.heatmap !== null} />
      <TruckMarkers
        trucks={timelines.map(({ route, states }) => ({ route, state: states[hour] }))}
        selectedRouteId={selectedRouteId}
      />
      <TimeSlider
        startIso={departureIso} hour={hour} onHourChange={changeHour}
        heatmapAvailable={plan.heatmap !== null} showHeatmap={showHeatmap} onShowHeatmapChange={setShowHeatmap}
        timing={timing}
      />
    </>
  )
}
