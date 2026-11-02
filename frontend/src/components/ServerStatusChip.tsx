import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import type { ServerStatus } from '../hooks/useServerWakeUp'

interface Props {
  status: ServerStatus
  onRetry: () => void
}

export default function ServerStatusChip({ status, onRetry }: Props) {
  if (status.state === 'error') {
    return (
      <Alert severity="error" action={<Button color="inherit" size="small" onClick={onRetry}>Retry</Button>}>
        Can&apos;t reach the server. {status.message}
      </Alert>
    )
  }
  if (status.state === 'ready') {
    return <Chip color="success" variant="outlined" label={`Server ready (${(status.ms / 1000).toFixed(1)} s)`} />
  }
  const label = status.state === 'waking' ? 'Starting the server… (this can take ~10 s)' : 'Connecting…'
  return <Chip variant="outlined" icon={<CircularProgress size={14} />} label={label} />
}
