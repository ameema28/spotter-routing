import Button from '@mui/material/Button'
import FormControlLabel from '@mui/material/FormControlLabel'
import Paper from '@mui/material/Paper'
import Slider from '@mui/material/Slider'
import Stack from '@mui/material/Stack'
import Switch from '@mui/material/Switch'
import Typography from '@mui/material/Typography'
import { useEffect, useState } from 'react'
import { LAST_HOUR } from '../../map/heatmap'
import { sliderLabel } from '../../timeLabels'

interface Props {
  startIso: string
  hour: number
  onHourChange: (hour: number) => void
  heatmapAvailable: boolean
  showHeatmap: boolean
  onShowHeatmapChange: (show: boolean) => void
  lastUpdateMs: number | null    // only set when the page is opened with ?perf=1
}

const MARKS = [0, 6, 12, 18, 24, 30, 36, 42, 48].map((value) => ({ value, label: `${value} h` }))
const PLAY_STEP_MS = 400

export default function TimeSlider(props: Props) {
  const { startIso, hour, onHourChange, heatmapAvailable, showHeatmap, onShowHeatmapChange, lastUpdateMs } = props
  const [playing, setPlaying] = useState(false)

  // Play moves one hour per step and stops at the end.
  useEffect(() => {
    if (!playing) return
    const timer = setTimeout(() => {
      if (hour >= LAST_HOUR) setPlaying(false)
      else onHourChange(hour + 1)
    }, PLAY_STEP_MS)
    return () => clearTimeout(timer)
  }, [playing, hour, onHourChange])

  function togglePlay() {
    if (!playing && hour >= LAST_HOUR) onHourChange(0)
    setPlaying(!playing)
  }

  return (
    <Paper
      elevation={3}
      sx={{
        position: 'absolute', bottom: 28, left: '50%', transform: 'translateX(-50%)',
        width: 'min(560px, calc(100% - 24px))', px: 2, pt: 1, pb: 0.5,
      }}
    >
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
        <Button size="small" variant="outlined" onClick={togglePlay} sx={{ minWidth: 64 }}>
          {playing ? 'Pause' : 'Play'}
        </Button>
        <Typography variant="body2" sx={{ fontWeight: 600, flex: 1 }} aria-live="polite">
          {sliderLabel(startIso, hour)}
        </Typography>
        {heatmapAvailable ? (
          <FormControlLabel
            control={<Switch size="small" checked={showHeatmap} onChange={(event) => onShowHeatmapChange(event.target.checked)} />}
            label={<Typography variant="caption">Weather heatmap</Typography>}
            sx={{ mr: 0 }}
          />
        ) : (
          <Typography variant="caption" color="text.secondary">Heatmap unavailable for this search</Typography>
        )}
      </Stack>
      <Slider
        size="small" min={0} max={LAST_HOUR} step={1} marks={MARKS} value={hour}
        onChange={(_, value) => onHourChange(value as number)}
        aria-label="Hours after departure" getAriaValueText={(value) => sliderLabel(startIso, value)}
        sx={{ mx: 1, width: 'calc(100% - 16px)', '& .MuiSlider-markLabel': { fontSize: 11 } }}
      />
      {lastUpdateMs !== null && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'right' }}>
          Last slider update: {lastUpdateMs.toFixed(1)} ms
        </Typography>
      )}
    </Paper>
  )
}
