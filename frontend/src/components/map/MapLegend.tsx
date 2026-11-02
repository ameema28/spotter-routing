import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'
import { useTheme } from '@mui/material/styles'
import { useState, type ReactNode } from 'react'
import { RISK_LEGEND } from '../../risk'
import { OTHER_ROUTE_COLOR, STOP_PIN } from '../../map/styles'
import { TruckDot } from './TruckMarkers'

function LineSample({ color, dashed }: { color: string; dashed?: boolean }) {
  return <Box sx={{ width: 20, borderTop: `${dashed ? 2 : 4}px ${dashed ? 'dashed' : 'solid'} ${color}` }} />
}

function Row({ swatch, children }: { swatch: ReactNode; children: ReactNode }) {
  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', minWidth: 0 }}>
      <Box sx={{ width: 20, flexShrink: 0, display: 'flex', justifyContent: 'center' }}>{swatch}</Box>
      <Typography variant="caption" sx={{ lineHeight: 1.3 }}>{children}</Typography>
    </Stack>
  )
}

const dot = (color: string) => <Box sx={{ width: 9, height: 9, borderRadius: '50%', bgcolor: color }} />

// Top-left, away from the slider at the bottom. Open on wide screens, a small button on phones.
export default function MapLegend({ recommendedLabel }: { recommendedLabel: string | null }) {
  const theme = useTheme()
  const wide = useMediaQuery(theme.breakpoints.up('md'))
  const [open, setOpen] = useState<boolean | null>(null)
  const isOpen = open ?? wide
  const toggle = (
    <Button size="small" onClick={() => setOpen(!isOpen)} aria-expanded={isOpen}
      sx={{ textTransform: 'none', minWidth: 0, px: 1, py: 0.25 }}>
      {isOpen ? 'Hide legend' : 'Legend'}
    </Button>
  )

  if (!isOpen) {
    return <Paper elevation={2} sx={{ position: 'absolute', left: 12, top: 12 }}>{toggle}</Paper>
  }
  return (
    <Paper elevation={2} sx={{ position: 'absolute', left: 12, top: 12, width: 220, p: 1 }}>
      <Stack spacing={0.75}>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', rowGap: 0.25, columnGap: 1 }}>
          {RISK_LEGEND.map((risk) => <Row key={risk.label} swatch={dot(risk.color)}>{risk.label}</Row>)}
        </Box>
        <Row swatch={<Box sx={{ width: 14, height: 10, bgcolor: RISK_LEGEND[0].color, opacity: 0.4 }} />}>
          Heatmap: corridor risk at the slider hour
        </Row>
        <Row swatch={<LineSample color={theme.palette.primary.main} />}>Selected route</Row>
        <Row swatch={<LineSample color={OTHER_ROUTE_COLOR} dashed />}>Other routes</Row>
        <Row swatch={<TruckDot selected={false} color={theme.palette.primary.main} />}>Truck at the slider hour</Row>
        {Object.values(STOP_PIN).map((pin) => (
          <Row key={pin.name} swatch={<Box sx={{ width: 14, height: 9, borderRadius: 999, bgcolor: pin.color }} />}>
            {pin.name}
          </Row>
        ))}
        <Typography variant="caption" color="text.secondary">
          {recommendedLabel ? `Recommended: ${recommendedLabel}` : 'No route recommended'}
        </Typography>
        <Box>{toggle}</Box>
      </Stack>
    </Paper>
  )
}
