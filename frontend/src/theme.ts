import { createTheme } from '@mui/material/styles'

// One spacing unit (8 px) and a short type scale, so the panel lines up on a single rhythm.
export const theme = createTheme({
  palette: {
    primary: { main: '#1f4e79' },
    background: { default: '#f6f7f9' },
  },
  shape: { borderRadius: 8 },
  spacing: 8,
  typography: {
    fontFamily: 'system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    h1: { fontSize: '1.375rem', fontWeight: 600, lineHeight: 1.3 },
    body2: { lineHeight: 1.5 },
  },
})
