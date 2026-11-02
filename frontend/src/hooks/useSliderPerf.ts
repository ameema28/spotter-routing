import type { Map as MapLibreMap } from 'maplibre-gl'
import { useCallback, useLayoutEffect, useRef, useState } from 'react'

// Open the page with ?perf=1 to show the timings under the slider (the Loom demo); dev also logs them.
export const SHOW_PERF = new URLSearchParams(window.location.search).has('perf')

export interface SliderTiming {
  reactMs: number    // slider change → React finished updating the page
  drawnMs: number    // slider change → MapLibre drew the next frame (includes waiting for that frame)
}

export function useSliderPerf(getMap: () => MapLibreMap | undefined, hour: number) {
  const startedAt = useRef<number | null>(null)
  const reactMs = useRef(0)
  const [timing, setTiming] = useState<SliderTiming | null>(null)

  // Runs right after React applies the new hour, before the browser paints.
  useLayoutEffect(() => {
    if (startedAt.current !== null) reactMs.current = performance.now() - startedAt.current
  }, [hour])

  // Call just before changing the hour.
  const markChange = useCallback(() => {
    const map = getMap()
    if (!map || !(SHOW_PERF || import.meta.env.DEV)) return
    const started = performance.now()
    startedAt.current = started
    map.once('render', () => {
      const result = { reactMs: reactMs.current, drawnMs: performance.now() - started }
      startedAt.current = null
      if (import.meta.env.DEV) {
        console.debug(`Slider: React ${result.reactMs.toFixed(1)} ms, drawn after ${result.drawnMs.toFixed(1)} ms`)
      }
      if (SHOW_PERF) setTiming(result)
    })
    // Make sure a frame is drawn even if only the HTML overlays changed.
    map.triggerRepaint()
  }, [getMap])

  return { timing, markChange }
}
