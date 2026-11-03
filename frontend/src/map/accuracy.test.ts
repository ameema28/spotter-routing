import { expect, it } from 'vitest'
import type { Heatmap, RoutePlan } from '../api/types'
import samplePlan from '../fixtures/sample-plan.json'

// Cross-check on a real response: does the heatmap cell under each checkpoint, at the hour nearest its ETA,
// show the same risk level as the checkpoint itself? They can differ for two honest reasons:
// - the cell's forecast is for the cell centre, up to about 20 miles from the checkpoint;
// - the hour is rounded to the slider hour, up to 30 minutes from the ETA, which can move the precipitation
//   "hour ending at or after" row to the next hour.
const plan = samplePlan as unknown as RoutePlan
const heatmap = plan.heatmap as Heatmap
const HOUR = 3600 * 1000
// Set after measuring this fixture (see the BLOCK 3.4 report); a big drop means the two have drifted apart.
const MIN_AGREEMENT = 0.9

function cellIndexAt(lat: number, lon: number): number {
  const [latStep, lonStep] = heatmap.step_deg
  let best = -1
  let bestDistance = Infinity
  heatmap.points.forEach(([cellLat, cellLon], index) => {
    // In grid steps, so a point inside a cell is always nearest to that cell's centre.
    const distance = Math.max(Math.abs(cellLat - lat) / latStep, Math.abs(cellLon - lon) / lonStep)
    if (distance < bestDistance) {
      best = index
      bestDistance = distance
    }
  })
  return bestDistance <= 0.5 + 1e-9 ? best : -1
}

it('heatmap cells agree with the checkpoints they cover', () => {
  const start = new Date(heatmap.start).getTime()
  let compared = 0
  let matched = 0
  const mismatches: string[] = []
  for (const route of plan.routes) {
    for (const checkpoint of route.checkpoints) {
      const hour = Math.round((new Date(checkpoint.eta).getTime() - start) / HOUR)
      const cell = cellIndexAt(checkpoint.lat, checkpoint.lon)
      if (hour > 48 || cell < 0) continue
      compared += 1
      const cellLevel = heatmap.levels![cell][hour]
      if (cellLevel === checkpoint.level) matched += 1
      else mismatches.push(`route ${route.id} mile ${checkpoint.mile} h${hour}: checkpoint ${checkpoint.level}, cell ${cellLevel}`)
    }
  }
  const agreement = matched / compared
  console.info(`Heatmap/checkpoint agreement: ${matched}/${compared} = ${(agreement * 100).toFixed(1)}%`)
  for (const line of mismatches) console.info(`  mismatch ${line}`)
  expect(compared).toBeGreaterThan(100)
  expect(agreement).toBeGreaterThanOrEqual(MIN_AGREEMENT)
})
