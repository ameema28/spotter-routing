import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Collapse from '@mui/material/Collapse'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'
import { useTheme } from '@mui/material/styles'
import { useState, type ReactNode } from 'react'
import { RISK_LEGEND } from '../../risk'
import { OTHER_ROUTE_COLOR, STOP_PIN } from '../../map/styles'

function LineSample({ color, dashed }: { color: string; dashed?: boolean }) {
  return <Box sx={{ width: 24, borderTop: `${dashed ? 3 : 5}px ${dashed ? 'dashed' : 'solid'} ${color}` }} />
}

function Row({ swatch, label }: { swatch: ReactNode; label: string }) {
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
      <Box sx={{ width: 24, display: 'flex', justifyContent: 'center' }}>{swatch}</Box>
      <Typography variant="caption">{label}</Typography>
    </Stack>
  )
}

export default function MapLegend({ recommendedLabel }: { recommendedLabel: string | null }) {
  const theme = useTheme()
  const wide = useMediaQuery(theme.breakpoints.up('md'))
  // Starts open on a wide screen and folded on a phone, where it would cover the map.
  const [open, setOpen] = useState<boolean | null>(null)
  const isOpen = open ?? wide

  return (
    <Paper elevation={2} sx={{ position: 'absolute', left: 12, bottom: 32, p: 1.5, maxWidth: 240 }}>
      <Button size="small" onClick={() => setOpen(!isOpen)} aria-expanded={isOpen} sx={{ p: 0, minWidth: 0 }}>
        {isOpen ? 'Hide legend' : 'Legend'}
      </Button>
      <Collapse in={isOpen}>
        <Stack spacing={0.5} sx={{ mt: 1 }}>
          {RISK_LEGEND.map((risk) => (
            <Row key={risk.label} label={risk.label}
              swatch={<Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: risk.color }} />} />
          ))}
          <Row label="Selected route" swatch={<LineSample color={theme.palette.primary.main} />} />
          <Row label="Other routes" swatch={<LineSample color={OTHER_ROUTE_COLOR} dashed />} />
          {Object.values(STOP_PIN).map((pin) => (
            <Row key={pin.name} label={pin.name}
              swatch={<Box sx={{ width: 14, height: 10, borderRadius: 999, bgcolor: pin.color }} />} />
          ))}
          <Typography variant="caption" color="text.secondary" sx={{ pt: 0.5 }}>
            {recommendedLabel ? `Recommended: ${recommendedLabel}` : 'No route recommended'}
          </Typography>
        </Stack>
      </Collapse>
    </Paper>
  )
}
