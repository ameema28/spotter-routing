import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import type { ApiError } from '../api/errors'
import type { RoutePlan, RoutePlanRequest } from '../api/types'
import type { SearchState } from '../hooks/useRoutePlan'
import type { ServerStatus } from '../hooks/useServerWakeUp'
import ResultsPanel from './ResultsPanel'
import SearchForm from './SearchForm'
import { SearchError, SearchLoading } from './SearchStatus'
import ServerStatusChip from './ServerStatusChip'

interface Props {
  server: { status: ServerStatus; retry: () => void }
  search: {
    status: SearchState
    plan: RoutePlan | null
    error: ApiError | null
    search: (request: RoutePlanRequest) => void
    cancel: () => void
    retry: () => void
  }
  selectedRouteId: number | null
  onSelectRoute: (id: number) => void
}

export default function SidePanel({ server, search, selectedRouteId, onSelectRoute }: Props) {
  const { status, plan, error } = search

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h1">Safest truck route</Typography>
        <Typography variant="body2" color="text.secondary">
          Compares up to 3 routes by weather along the way, load weight and travel time.
        </Typography>
      </Stack>
      <ServerStatusChip status={server.status} onRetry={server.retry} />
      <SearchForm
        loading={status === 'loading'}
        serverErrors={status === 'error' && error ? error.fields : {}}
        onSearch={search.search}
        onCancel={search.cancel}
      />
      {status === 'loading' && <SearchLoading serverWaking={server.status.state === 'waking'} />}
      {/* Field errors also show under their fields; the alert keeps a Retry for every error. */}
      {status === 'error' && error && <SearchError error={error} onRetry={search.retry} />}
      {status === 'done' && plan && (
        <ResultsPanel plan={plan} selectedRouteId={selectedRouteId} onSelectRoute={onSelectRoute} />
      )}
    </Stack>
  )
}
