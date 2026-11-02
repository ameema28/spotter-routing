import { describe, expect, it } from 'vitest'
import { loadingStage } from './loadingStage'

describe('loadingStage', () => {
  it('steps through the usual stages as time passes', () => {
    expect(loadingStage(0, false)).toBe('Finding routes…')
    expect(loadingStage(2500, false)).toBe('Checking weather at each checkpoint…')
    expect(loadingStage(7000, false)).toBe('Ranking routes…')
  })

  it('says the server is starting while it is still waking up', () => {
    expect(loadingStage(3000, true)).toBe('Starting the server first… (this can take ~10 s)')
  })
})
