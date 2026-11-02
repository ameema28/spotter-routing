import { Layer, Source } from 'react-map-gl/maplibre'
import { memo } from 'react'
import type { FeatureCollection, Point } from 'geojson'
import type { CheckpointProps } from '../../map/geojson'
import { CHECKPOINT_LAYER, onRoute, riskColorExpression } from '../../map/styles'

interface Props {
  data: FeatureCollection<Point, CheckpointProps>
  selectedRouteId: number | null
}

// One circle per checkpoint, drawn by the GPU. The selected route's checkpoints are full size; the rest
// shrink and fade. Only these paint values change on selection.
function CheckpointLayer({ data, selectedRouteId }: Props) {
  const isSelected = onRoute(selectedRouteId)

  return (
    <Source id="checkpoints" type="geojson" data={data}>
      <Layer
        id={CHECKPOINT_LAYER} type="circle"
        paint={{
          'circle-color': riskColorExpression(),
          'circle-radius': ['case', isSelected, 5.5, 2.5],
          'circle-opacity': ['case', isSelected, 1, 0.35],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': ['case', isSelected, 1.5, 0],
        }}
      />
    </Source>
  )
}

// memo: skip re-rendering when the props are unchanged, e.g. while the map is hovered.
export default memo(CheckpointLayer)
