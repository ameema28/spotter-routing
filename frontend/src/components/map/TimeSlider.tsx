import Button from '@mui/material/Button'
import FormControlLabel from '@mui/material/FormControlLabel'
import Paper from '@mui/material/Paper'
import Slider from '@mui/material/Slider'
import Stack from '@mui/material/Stack'
import Switch from '@mui/material/Switch'
import Typography from '@mui/material/Typography'
import { memo, useCallback, useEffect, useState } from 'react'
import type { HeatmapRetry } from '../../heatmapRetry'
import type { SliderTiming } from '../../hooks/useSliderPerf'
import { LAST_HOUR } from '../../map/heatmap'
import { sliderLabel } from '../../timeLabels'
import HeatmapStatus from './HeatmapStatus'

interface Props {
  startIso: string
  hour: number
  onHourChange: (hour: number) => void
  heatmapAvailable: boolean
  heatmapRetry: { state: HeatmapRetry; retryNow: () => void }
  showHeatmap: boolean
  onShowHeatmapChange: (show: boolean) => void
  timing: SliderTiming | null    // only set when the page is opened with ?perf=1
}

const MARKS = [0, 6, 12, 18, 24, 30, 36, 42, 48].map((value) => ({ value, label: `${value} h` }))
const PLAY_STEP_MS = 400

// Style objects are constants, so MUI's styling doesn't recompute them on every hour change.
const PANEL_SX = {
  position: 'absolute', bottom: 28, left: '50%', transform: 'translateX(-50%)',
  width: 'min(560px, calc(100% - 24px))', px: 2, pt: 1, pb: 0.5,
} as const
const SLIDER_SX = { mx: 1, width: 'calc(100% - 16px)', '& .MuiSlider-markLabel': { fontSize: 11 } } as const
const LABEL_SX = { fontWeight: 600, flex: 1 } as const

// The parts that don't depend on the hour are memoised, so a slider move only re-renders the slider and its label.
const PlayButton = memo(function PlayButton({ playing, onClick }: { playing: boolean; onClick: () => void }) {
  return (
    <Button size="small" variant="outlined" onClick={onClick} sx={{ minWidth: 64 }}>
      {playing ? 'Pause' : 'Play'}
    </Button>
  )
})

const HeatmapSwitch = memo(function HeatmapSwitch(
  { checked, onChange }: { checked: boolean; onChange: (show: boolean) => void },
) {
  return (
    <FormControlLabel
      control={<Switch size="small" checked={checked} onChange={(event) => onChange(event.target.checked)} />}
      label={<Typography variant="caption">Weather heatmap</Typography>}
      sx={{ mr: 0 }}
    />
  )
})

export default function TimeSlider(props: Props) {
  const { startIso, hour, onHourChange, heatmapAvailable, heatmapRetry, showHeatmap, onShowHeatmapChange, timing } = props
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

  // Stable unless the hour reaches the end, so the memoised button skips most slider moves.
  const atEnd = hour >= LAST_HOUR
  const togglePlay = useCallback(() => {
    if (!playing && atEnd) onHourChange(0)
    setPlaying(!playing)
  }, [playing, atEnd, onHourChange])
  const ariaValueText = useCallback((value: number) => sliderLabel(startIso, value), [startIso])

  return (
    <Paper elevation={3} sx={PANEL_SX}>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
        <PlayButton playing={playing} onClick={togglePlay} />
        <Typography variant="body2" sx={LABEL_SX} aria-live="polite">{sliderLabel(startIso, hour)}</Typography>
        {heatmapAvailable && <HeatmapSwitch checked={showHeatmap} onChange={onShowHeatmapChange} />}
      </Stack>
      {/* Its own row: the countdown and button don't fit beside the time on a phone. */}
      {!heatmapAvailable && <HeatmapStatus retry={heatmapRetry.state} onRetryNow={heatmapRetry.retryNow} />}
      <Slider
        size="small" min={0} max={LAST_HOUR} step={1} marks={MARKS} value={hour}
        onChange={(_, value) => onHourChange(value as number)}
        aria-label="Hours after departure" getAriaValueText={ariaValueText}
        sx={SLIDER_SX}
      />
      {timing && (
        <Typography variant="caption" color="text.secondary" data-testid="perf-readout"
          data-react-ms={timing.reactMs.toFixed(2)} data-drawn-ms={timing.drawnMs.toFixed(2)}
          sx={{ display: 'block', textAlign: 'right' }}>
          Last slider update: React {timing.reactMs.toFixed(1)} ms · drawn after {timing.drawnMs.toFixed(1)} ms
        </Typography>
      )}
    </Paper>
  )
}
