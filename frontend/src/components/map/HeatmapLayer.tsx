import { Layer, Source } from 'react-map-gl/maplibre'
import type { FeatureCollection, Polygon } from 'geojson'
import { heatmapColorExpression, type HeatmapProps } from '../../map/heatmap'

interface Props {
  data: FeatureCollection<Polygon, HeatmapProps>
  hour: number
  visible: boolean
}

// Rendered before the route layers, so MapLibre draws the squares underneath the routes and checkpoints.
// The slider only changes 'fill-color' (which hour to read) and the switch only changes 'visibility':
// the squares themselves are never rebuilt.
export default function HeatmapLayer({ data, hour, visible }: Props) {
  return (
    <Source id="heatmap" type="geojson" data={data}>
      <Layer
        id="heatmap-cells" type="fill"
        layout={{ visibility: visible ? 'visible' : 'none' }}
        paint={{ 'fill-color': heatmapColorExpression(hour), 'fill-opacity': 0.4, 'fill-outline-color': 'rgba(0,0,0,0)' }}
      />
    </Source>
  )
}
