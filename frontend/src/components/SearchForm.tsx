import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import FormLabel from '@mui/material/FormLabel'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import { useState, type FormEvent } from 'react'
import type { RoutePlanRequest } from '../api/types'
import { fromLocalInputValue, nextFullHour, toIsoWithOffset, toLocalInputValue, validateDeparture } from '../departure'
import { timeZoneLabel } from '../format'

type Step = RoutePlanRequest['step_miles']

// The three trips used in testing, so reviewers can try the app in one click.
const QUICK_TRIPS = [
  ['Dallas, TX', 'Chicago, IL'],
  ['Denver, CO', 'Salt Lake City, UT'],
  ['Kansas City, MO', 'Denver, CO'],
]
const MAX_LOAD_LB = 80_000

interface Props {
  loading: boolean
  serverErrors: Record<string, string>
  onSearch: (request: RoutePlanRequest) => void
  onCancel: () => void
}

export default function SearchForm({ loading, serverErrors, onSearch, onCancel }: Props) {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [departure, setDeparture] = useState(() => toLocalInputValue(nextFullHour(new Date())))
  const [load, setLoad] = useState('40000')
  const [step, setStep] = useState<Step>(25)
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})

  // The browser's own checks win; the server's are shown until the next search.
  const errors = { ...serverErrors, ...formErrors }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const departureDate = fromLocalInputValue(departure)
    const loadLb = Number(load)
    const found: Record<string, string> = {}
    if (!origin.trim()) found.origin = 'Enter a starting place.'
    if (!destination.trim()) found.destination = 'Enter a destination.'
    const departureError = validateDeparture(departureDate, new Date())
    if (departureError) found.departure = departureError
    if (!(loadLb > 0)) found.load_lb = 'Load must be more than 0 lb.'
    else if (loadLb > MAX_LOAD_LB) found.load_lb = 'Load must be at most 80,000 lb.'
    setFormErrors(found)
    if (Object.keys(found).length > 0 || !departureDate) return
    onSearch({
      origin: origin.trim(),
      destination: destination.trim(),
      departure: toIsoWithOffset(departureDate),
      load_lb: loadLb,
      step_miles: step,
    })
  }

  return (
    <Stack component="form" spacing={2} onSubmit={handleSubmit} noValidate>
      <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}>
        {QUICK_TRIPS.map(([from, to]) => (
          <Chip
            key={from + to}
            size="small"
            label={`${from.split(',')[0]} → ${to.split(',')[0]}`}
            onClick={() => { setOrigin(from); setDestination(to) }}
          />
        ))}
      </Stack>
      <TextField
        label="Origin" placeholder="Dallas, TX" value={origin} onChange={(event) => setOrigin(event.target.value)}
        error={Boolean(errors.origin)} helperText={errors.origin}
      />
      <TextField
        label="Destination" placeholder="Chicago, IL" value={destination}
        onChange={(event) => setDestination(event.target.value)}
        error={Boolean(errors.destination)} helperText={errors.destination}
      />
      <TextField
        label="Departure" type="datetime-local" value={departure} onChange={(event) => setDeparture(event.target.value)}
        error={Boolean(errors.departure)} helperText={errors.departure ?? `Your local time: ${timeZoneLabel()}`}
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <TextField
        label="Load (lb)" type="number" value={load} onChange={(event) => setLoad(event.target.value)}
        error={Boolean(errors.load_lb)}
        helperText={errors.load_lb
          ?? 'Over 30,000 lb, severe wind means No Travel; over 40,000 lb, high wind counts as Severe.'}
        slotProps={{ htmlInput: { min: 1, max: MAX_LOAD_LB, step: 1000 } }}
      />
      <Stack spacing={1}>
        <FormLabel id="step-label">Checkpoint spacing</FormLabel>
        <ToggleButtonGroup
          exclusive size="small" value={step} aria-labelledby="step-label"
          onChange={(_, value: Step | null) => { if (value) setStep(value) }}
        >
          {[10, 25, 50].map((miles) => <ToggleButton key={miles} value={miles}>{miles} mi</ToggleButton>)}
        </ToggleButtonGroup>
      </Stack>
      <Stack direction="row" spacing={1}>
        <Button type="submit" variant="contained" disabled={loading} sx={{ flex: 1 }}>Find safest route</Button>
        {loading && <Button onClick={onCancel}>Cancel</Button>}
      </Stack>
    </Stack>
  )
}
