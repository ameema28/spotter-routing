import Button from '@mui/material/Button'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { memo, useEffect, useState } from 'react'
import { secondsUntil, type HeatmapRetry } from '../../heatmapRetry'

interface Props {
  retry: HeatmapRetry
  onRetryNow: () => void
}

const ROW_SX = { alignItems: 'center', minHeight: 30 } as const

// Ticks on its own, so the countdown re-renders this text only, not the slider or the map.
function Countdown({ retryAt }: { retryAt: number }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  return <>Heatmap will retry in {secondsUntil(retryAt, now)} s</>
}

function message(retry: HeatmapRetry) {
  if (retry.kind === 'waiting') return <Countdown retryAt={retry.retryAt} />
  if (retry.kind === 'retrying') return 'Loading the heatmap…'
  if (retry.kind === 'failed') return retry.message
  return 'Heatmap unavailable for this search'
}

// Shown instead of the heatmap switch while a search has no heatmap levels (D14).
export default memo(function HeatmapStatus({ retry, onRetryNow }: Props) {
  const canRetry = retry.kind === 'waiting' || retry.kind === 'failed'
  return (
    <Stack direction="row" spacing={1} sx={ROW_SX}>
      {/* Not announced every second while counting down, only when the state changes. */}
      <Typography variant="caption" color="text.secondary" aria-live={retry.kind === 'waiting' ? 'off' : 'polite'}
        sx={{ flex: 1 }}>
        {message(retry)}
      </Typography>
      {canRetry && <Button size="small" onClick={onRetryNow}>Retry now</Button>}
    </Stack>
  )
})
