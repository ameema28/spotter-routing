import Box from '@mui/material/Box'
import { useState } from 'react'
import MapView from './components/MapView'
import SidePanel from './components/SidePanel'
import { useHeatmapRetry } from './hooks/useHeatmapRetry'
import { useRoutePlan } from './hooks/useRoutePlan'
import { useServerWakeUp } from './hooks/useServerWakeUp'
import { defaultRouteId } from './selection'

const PANEL_WIDTH = 400

// App owns the shared state, so the side panel and (next) the map read the same plan and selected route.
export default function App() {
  const server = useServerWakeUp()
  const search = useRoutePlan()
  const { plan } = search
  const searchId = search.result?.searchId ?? 0
  const heatmapRetry = useHeatmapRetry(search.result, search.applyHeatmapLevels)

  // The user's pick only counts for the search it was made on, so a new search starts on its default route.
  // Keyed on the search, not the plan: a heatmap retry replaces the plan object but keeps the pick.
  const [choice, setChoice] = useState<{ searchId: number; routeId: number } | null>(null)
  const selectedRouteId = plan && choice?.searchId === searchId ? choice.routeId : defaultRouteId(plan)
  const selectRoute = (routeId: number) => {
    if (plan) setChoice({ searchId, routeId })
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
      {/* On phones the page scrolls, so the map gets a fixed height; flex: 1 there would collapse it to zero. */}
      <Box component="main" sx={{ flex: { md: 1 }, height: { xs: '70vh', md: 'auto' } }}>
        <MapView
          plan={plan} searchId={searchId} heatmapRetry={heatmapRetry}
          selectedRouteId={selectedRouteId} onSelectRoute={selectRoute}
        />
      </Box>
    </Box>
  )
}
