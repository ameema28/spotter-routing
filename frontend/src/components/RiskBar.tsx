import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import type { MilesByLevel } from '../api/types'
import { formatMiles } from '../format'
import { riskShares } from '../riskShares'

// Share of the route's miles at each risk level. The legend repeats it in text, so colour isn't the only signal.
export default function RiskBar({ milesByLevel }: { milesByLevel: MilesByLevel }) {
  const shares = riskShares(milesByLevel)
  const description = shares.map((share) => `${share.label} ${formatMiles(share.miles)}`).join(', ')

  return (
    <Stack spacing={0.5}>
      <Box role="img" aria-label={`Miles by risk: ${description}`}
        sx={{ display: 'flex', height: 8, borderRadius: 1, overflow: 'hidden', bgcolor: 'action.hover' }}>
        {shares.map((share) => (
          <Box key={share.label} sx={{ width: `${share.percent}%`, bgcolor: share.color }} />
        ))}
      </Box>
      <Stack direction="row" useFlexGap spacing={1.5} sx={{ flexWrap: 'wrap' }}>
        {shares.map((share) => (
          <Stack key={share.label} direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
            <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: share.color }} />
            <Typography variant="caption" color="text.secondary">
              {share.label} {formatMiles(share.miles)}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Stack>
  )
}
