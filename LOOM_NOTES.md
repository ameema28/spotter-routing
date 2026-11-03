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

## Day 3
- **WebGL map:** show the map and a route click. Routes, checkpoints and heatmap are MapLibre GPU layers built once per search; picking a route only changes layer filters and colours, never the data. Free OpenFreeMap basemap, so no API key in the browser.
- **Heatmap + slider:** open `?perf=1` and drag. The heatmap squares store all 49 hours, so the slider only changes which hour the colour reads. On the live production site a move takes about 2.6 ms of React work and is drawn in the next frame (15.6 ms median, p95 30 ms) on an Intel Iris Xe laptop GPU.
- **Legal breaks:** drag across T+8 h and T+11.5–21.5 h. The truck stands still at the 30-min break and the 10-h rest, because its position follows checkpoint ETAs plus each stop's start and end.
- **Accuracy check:** show `accuracy.test.ts`. Heatmap cells agree with the checkpoints they cover 95.9% of the time (117/122); the 5 differences are one level apart, from the cell centre being 8–14 miles from the checkpoint and wind sitting near the Moderate edge.
- **UX details:** server wake-up chip, errors under the right field, matched place names (a fuzzy geocode shows), far-departure note beyond 48 h, aligned cards; screenshots checked headless at four slider hours on desktop and phone before each hand-off.

AI use: planned with Claude, built with Claude Code block by block; I chose every decision and reviewed the tests.

## Final Loom outline (target 8–9 min, max 10)

| Time | SHOW | Script (1–2 lines) |
|---|---|---|
| 0:00 | README top: live app, API, GitHub | "Weather-aware truck routing in React and Django. It compares 3 routes and recommends the safest one, using weather, load and travel time." |
| 0:30 | Live app: Dallas → Chicago chip, 40,000 lb, Find safest route | "One request comes back with the routes, checkpoints, stops, ranking and a 48-hour heatmap." |
| 0:50 | Banner reason, then the cards | "The reason names the criterion that decided it, in the brief's order: Severe miles, High miles, average risk, then time. Each card shows the miles at every risk level." |
| 1:20 | Click a checkpoint popup and read it line by line | "Mile and level; the ETA from the truck model; why it's this level; wind, rain and snow; and the forecast hours used: rain and snow from the hour ending at or after the ETA, wind from the nearest hour." |
| 1:50 | Break pills ("30 min", "10 h rest") | "The ETA follows hours-of-service: a 30-minute break after 8 hours of driving and a 10-hour rest after 11." |
| 2:10 | Slider + Play; drag across T+11.5–21.5 h | "The heatmap and the trucks move through 48 hours. During the 10-hour rest the truck stays parked, because its position follows the ETAs and the stops." |
| 2:35 | Open `?perf=1`, drag | "About 2.6 ms of React work per move, drawn in the next frame: the squares store all 49 hours and the slider only changes which hour the colour reads." |
| 2:50 | Mention the retry (or show `docs/qa` countdown) | "If the weather service is busy, the routes still arrive and the heatmap retries itself after a minute, without a new search." |
| 3:00 | `backend/tests/test_risk.py` edge rows next to the PDF table | "Shared edges like 25 mph or 0.25 in/hr needed one rule: the lower edge is inclusive, and every edge is tested." |
| 3:40 | `risk.py` load rules; `test_load_rule_never_lowers_a_level` | "The worst of wind, rain and snow, then the load rules, which can only raise a level. Missing data is Unknown, never Low." |
| 4:00 | Truck ETA: Dallas–Chicago 15 h driving → 26 h trip | "65 mph cap plus federal hours-of-service, checked against FMCSA and the eCFR. It changes the forecast hour at most checkpoints." |
| 4:20 | `ranking.py`: tiers + tie-breaks | "Clean routes first, then too many unknown miles, then No Travel; the brief's order inside each tier. If no clean route exists, nothing is recommended." |
| 4:40 | Third route (via hubs) on the map / D7 | "Mapbox gives 2 routes, so a third comes from avoid-tolls plus interstate hub vias, accepted at ≤1.25× time and ≤75% overlap." |
| 5:00 | README Mermaid diagram | "React, MUI and MapLibre on Vercel; Django and DRF as one Vercel function; Mapbox and Open-Meteo behind it." |
| 5:30 | `build_route_plan` docstring; caching; throttles | "One endpoint, about 11 KB gzipped. Weather is cached 30 minutes at 0.02°, and each client is limited to 10 searches a minute to protect the provider quotas." |
| 6:00 | README performance table, Lighthouse | "Lighthouse 89, 100, 100 on desktop; searches take 2 to 5 seconds live." |
| 6:30 | Test run output (465 backend, 89 frontend) | "The core logic was written test-first, with no Django imports." |
| 6:50 | LOOM_NOTES Day 1: deliberate bugs | "I injected 35 deliberate bugs into the logic; the tests caught all of them, and one gap was found and closed." |
| 7:10 | `docs/QA.md` matrix | "A 28-row UI matrix: rare outcomes, every error, form validation, keyboard and phone, plus 4 live searches." |
| 7:30 | README limitations | "Trade-offs: car-profile routing, simplified hours-of-service, Open-Meteo's free-tier limits on shared IPs, per-instance cache. Next: a truck routing API, Redis, a paid weather plan." |
| 8:30 | README AI section | "I planned with Claude and built with Claude Code one block at a time. I made every decision, reviewed the plans and tests, and checked everything in the browser. Thanks for watching." |

### Pre-recording checklist
- Both Vercel projects show **Ready** after the last push (and no push within an hour of recording: a redeploy clears the cache).
- One warm-up search on the live site (Dallas → Chicago) so the server and the weather cache are warm.
- Notifications off; browser zoom 100%.
- Tabs ready: live app; live app with `?perf=1`; GitHub README; `backend/tests/test_risk.py`; `backend/routing/domain/ranking.py`; DECISIONS.md.
- Backup screenshots if live weather is calm: `docs/qa/high-severe.jpg` ("Fewest Severe miles", an edited fixture), `docs/qa/all-no-travel.jpg`, `docs/qa/popup-zorder.jpg`. Say they are edited fixtures.
