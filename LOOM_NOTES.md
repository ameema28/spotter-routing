# Loom notes

## Day 1
- **Real API spike:** show the spike output. Mapbox returns at most 2 routes (docs + real calls), so a third route is generated; arbitrary offsets sent trucks onto mining roads, so Day 2 uses interstate hub cities.
- **Open-Meteo:** show the 100-point call. One batched call covers the route; rain = rain + showers; snowfall is depth (~7× water), not water.
- **Risk table edges:** show `test_risk.py` rows next to the PDF table. Shared edges get the riskier band, and float rounding stops noise from missing an edge.
- **Test quality:** show a deliberate bug failing a test. Tests were written first and 35 deliberate bugs were injected (15 in geo/weather_time/risk, 20 in ranking), all caught; one gap found and closed (wind 35 + 40,001 lb).
- **Ranking:** show `test_ranking.py` tie-break cases. Strict PDF order inside tiers (clean → insufficient data → No Travel); recommend none if nothing is safe; reason text names the deciding criterion.

## Day 2
- **Third route:** show the live third-route table. Mapbox gives 2, so hub-city via and avoid-tolls candidates are sent in parallel, accepted at ≤1.25× time and ≤75% overlap, and the lowest overlap wins.
- **Truck ETA:** show Dallas–Chicago going from 15 h to 26 h. A 65 mph cap plus federal hours-of-service (verified in FMCSA and current eCFR) changes the forecast hour at most checkpoints.
- **Caching:** show the 0.1° vs 0.02° comparison. Measured on a real route, 0.02° won (finer than the 3 km model); file cache; Open-Meteo budget measured (each location counts), so the heatmap is capped at 250 points.
- **One endpoint:** show one response. It returns routes, checkpoints, ranking, reason and a 48-hour heatmap in ~11 KB gzipped, with simplified geometry for the browser.
- **Deployment:** show the live checks. Deployed free on Vercel (no fixed sleep, 300 s limit) rather than Render (1-min wake-up); live: fresh 3.3 s, repeat 2.1 s, cold start 7.7 s; throttling protects provider quotas.

AI use: planned with Claude, built with Claude Code block by block; I chose every decision and reviewed the tests.
