import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useServerWakeUp } from '../hooks/useServerWakeUp'
import ServerStatusChip from './ServerStatusChip'

export default function SidePanel() {
  const { status, retry } = useServerWakeUp()

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h1">Safest truck route</Typography>
        <Typography variant="body2" color="text.secondary">
          Compares up to 3 routes by weather along the way, load weight and travel time.
        </Typography>
      </Stack>
      <ServerStatusChip status={status} onRetry={retry} />
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">Trip form goes here.</Typography>
      </Paper>
    </Stack>
  )
}
