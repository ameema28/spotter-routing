import Box from '@mui/material/Box'
import type { ReactNode } from 'react'

// A small labelled pill used for the start, the end and the stops, so they read as text, not just colour.
export default function MapPin({ children, color }: { children: ReactNode; color: string }) {
  return (
    <Box
      sx={{
        px: 1, py: 0.25, borderRadius: 999, bgcolor: color, color: '#ffffff', fontSize: 12, fontWeight: 600,
        whiteSpace: 'nowrap', boxShadow: 2, border: '2px solid #ffffff', cursor: 'pointer', lineHeight: 1.4,
      }}
    >
      {children}
    </Box>
  )
}
