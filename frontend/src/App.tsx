import Box from '@mui/material/Box'
import { useState } from 'react'
import type { RoutePlan } from './api/types'
import MapView from './components/MapView'
import SidePanel from './components/SidePanel'
import { useRoutePlan } from './hooks/useRoutePlan'
import { useServerWakeUp } from './hooks/useServerWakeUp'
import { defaultRouteId } from './selection'

const PANEL_WIDTH = 400

// App owns the shared state, so the side panel and (next) the map read the same plan and selected route.
export default function App() {
  const server = useServerWakeUp()
  const search = useRoutePlan()
  const { plan } = search

  // The user's pick only counts for the plan it was made on, so a new search starts on its default route.
  const [choice, setChoice] = useState<{ plan: RoutePlan; routeId: number } | null>(null)
  const selectedRouteId = plan && choice?.plan === plan ? choice.routeId : defaultRouteId(plan)
  const selectRoute = (routeId: number) => {
    if (plan) setChoice({ plan, routeId })
  }

  // Panel on the left and the map filling the rest; on narrow screens the panel stacks above the map.
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
        <SidePanel server={server} search={search} selectedRouteId={selectedRouteId} onSelectRoute={selectRoute} />
      </Box>
      <Box component="main" sx={{ flex: 1, height: { xs: '70vh', md: 'auto' } }}>
        <MapView />
      </Box>
    </Box>
  )
}
