import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { Popup } from 'react-map-gl/maplibre'
import type { LonLat } from '../../map/geojson'
import type { PopupData } from '../../map/popups'

interface Props {
  at: LonLat
  data: PopupData
  onClose: () => void
}

export default function MapPopup({ at, data, onClose }: Props) {
  return (
    // closeOnClick is off because the map's click handler decides: a feature click opens a new popup instead.
    // zIndex 5 sits above every marker (trucks 1–2, stop pills 3, place pins 4), so no pill covers the details.
    <Popup longitude={at[0]} latitude={at[1]} onClose={onClose} closeOnClick={false} maxWidth="300px" offset={10}
      style={{ zIndex: 5 }}>
      <Typography variant="subtitle2" sx={{ mb: 1, pr: 2 }}>{data.title}</Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: 'auto 1fr', columnGap: 1.5, rowGap: 0.5 }}>
        {data.rows.map((row) => (
          <Box key={row.label} sx={{ display: 'contents' }}>
            <Typography variant="caption" color="text.secondary">{row.label}</Typography>
            <Typography variant="caption">{row.value}</Typography>
          </Box>
        ))}
      </Box>
    </Popup>
  )
}
