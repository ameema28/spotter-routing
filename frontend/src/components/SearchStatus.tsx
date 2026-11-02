import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Skeleton from '@mui/material/Skeleton'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useEffect, useState } from 'react'
import type { ApiError } from '../api/errors'
import { loadingStage } from '../loadingStage'

export function SearchLoading({ serverWaking }: { serverWaking: boolean }) {
  // Mounted when a search starts, so the start time is the moment this first renders.
  const [startedAt] = useState(() => Date.now())
  const [elapsedMs, setElapsedMs] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => setElapsedMs(Date.now() - startedAt), 250)
    return () => clearInterval(timer)
  }, [startedAt])

  return (
    <Stack spacing={2} role="status" aria-live="polite">
      <Stack spacing={0.5}>
        <Typography variant="body2">
          {loadingStage(elapsedMs, serverWaking)} {(elapsedMs / 1000).toFixed(0)} s
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Typical stages: the server answers in one go, usually within 5 s.
        </Typography>
      </Stack>
      {[0, 1, 2].map((index) => <Skeleton key={index} variant="rounded" height={132} />)}
    </Stack>
  )
}

export function SearchError({ error, onRetry }: { error: ApiError; onRetry: () => void }) {
  return (
    <Alert severity="error" action={<Button color="inherit" size="small" onClick={onRetry}>Retry</Button>}>
      {error.message}
    </Alert>
  )
}
