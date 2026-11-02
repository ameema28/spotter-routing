import Box from '@mui/material/Box'
import MapView from './components/MapView'
import SidePanel from './components/SidePanel'

const PANEL_WIDTH = 380

// Panel on the left and the map filling the rest; on narrow screens the panel stacks above the map.
export default function App() {
  return (
    <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, height: { md: '100vh' } }}>
      <Box
        component="aside"
        sx={{
          width: { md: PANEL_WIDTH },
          flexShrink: 0,
          p: 3,
          overflowY: 'auto',
          bgcolor: 'background.paper',
          borderRight: { md: 1 },
          borderBottom: { xs: 1, md: 0 },
          borderColor: 'divider',
        }}
      >
        <SidePanel />
      </Box>
      <Box component="main" sx={{ flex: 1, height: { xs: '70vh', md: 'auto' } }}>
        <MapView />
      </Box>
    </Box>
  )
}
