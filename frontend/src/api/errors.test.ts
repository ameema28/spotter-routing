import { describe, expect, it } from 'vitest'
import { NETWORK_MESSAGE, toApiError } from './errors'

describe('toApiError', () => {
  it('puts 400 messages under the matching fields', () => {
    const error = toApiError(400, { load_lb: ['Load must be more than 0 lb.'], departure: ['Too late.'] })
    expect(error.fields).toEqual({ load_lb: 'Load must be more than 0 lb.', departure: 'Too late.' })
    expect(error.message).toBe('Please fix the highlighted fields.')
  })

  it('puts a place not found under origin or destination', () => {
    const error = toApiError(422, { error: 'No US location found for that place', field: 'destination' })
    expect(error.fields).toEqual({ destination: 'No US location found for that place' })
  })

  it('shows a route not found as a message, not under a field', () => {
    const error = toApiError(422, { error: 'No drivable route between those places' })
    expect(error.message).toBe('No drivable route between those places')
    expect(error.fields).toEqual({})
  })

  it.each([429, 502, 503, 504])('shows the server message for HTTP %i', (status) => {
    expect(toApiError(status, { error: 'Weather service is busy' }).message).toBe('Weather service is busy')
  })

  it.each([
    [429, 'Too many searches. Please wait a minute and try again.'],
    [503, 'The weather service is busy. Please try again in a minute.'],
    [504, 'A map or weather service took too long. Please try again.'],
    [500, 'Something went wrong on the server (HTTP 500). Please try again.'],
  ])('falls back to a plain message for HTTP %i without a body', (status, message) => {
    expect(toApiError(status, null).message).toBe(message)
  })

  it('never shows an HTML error page as the message', () => {
    expect(toApiError(500, '<html>Traceback…</html>').message).not.toContain('Traceback')
  })

  it('has a clear message for a network failure', () => {
    expect(NETWORK_MESSAGE).toBe("Can't reach the server. Check your connection and try again.")
  })
})
