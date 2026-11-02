# Decisions

- D1 (Day 1): Mapbox Directions + Geocoding; it returns only 2 routes and has no truck profile, so a third route is generated on Day 2.
- D2 (Day 1): Open-Meteo; rain = `rain + showers`, snow = `snowfall`, wind = sustained `wind_speed_10m`, gusts for display only.
- D3 (Day 1): Band edges are lower-inclusive, Severe keeps its top value for rain and snow, wind No Travel is >=55.
- D4 (Day 1): Worst of wind/rain/snow, load rules can only raise it; any missing input gives unknown unless No Travel is already proven.
- D5 (Day 1): Half-gap mile weights; tiers clean → over 25% unknown miles → No Travel, PDF order within each; recommend only a clean route, otherwise none.
- D6 (Day 2): Cache Open-Meteo per point for 30 min, snapped to 0.02° because 0.1° changed storm-rain risk levels for almost no savings; no Mapbox route or geocode caching.
- D7 (Day 2): Third route from `exclude=toll` plus up to 4 hub vias, sent in parallel with the main call; accept at <=1.25× fastest and <=75% overlap, lowest overlap wins; otherwise "Only N distinct routes found".
- D8 (Day 2): Truck ETA = 65 mph cap (assumption) plus 30-min break after 8 h driving and 10-h rest after 11 h, per https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations and https://www.govinfo.gov/content/pkg/CFR-2023-title49-vol5/xml/CFR-2023-title49-vol5-sec395-3.xml
- D8 source check: current eCFR 49 CFR 395.3 (ecfr.gov, up to date as of 2026-10-29; last amended 85 FR 33452, 2020) matches the implemented rules: 10 h off duty, 14-h window, 11 h driving, 30-min break after 8 h driving.
- D9 (Day 2): Heatmap hour 0 = departure; cells are risk levels 0–4 with load, in one response; at most 250 points on a fixed global grid; a failed grid gives `heatmap: null` plus a note.
- D10 (Day 2): Host the backend on Vercel Hobby (300 s limit, no fixed sleep) with Render as the documented fallback; no uptime pinging; cache lives in `/tmp` via `CACHE_DIR`, so it is temporary and per instance.
- Minor defaults (Day 1): step 10/25/50 default 25; US-only geocoding; UTC; float rounding inside `risk.py`; precip uses the hour ending at or after the ETA, wind uses the nearest hour; no DB; no geocode caching.
- Minor defaults (Day 2): `forecast_days` fixed at 11, which costs no extra because Open-Meteo only adds weight above 10 variables or 2 weeks (https://open-meteo.com/en/pricing); Open-Meteo 429 returns HTTP 503 with no retry; candidate deadline 12 s after the main call; search throttled per client at 10/minute and 100/day, health unthrottled.
- D11 (Day 3): MapLibre GL via react-map-gl/maplibre with OpenFreeMap Positron (no key, no stated request limit, credit comes from the tile source; as-is, no SLA, per https://openfreemap.org/ and https://openfreemap.org/tos/); Leaflet + OSM tiles rejected because access "may be blocked without prior notice" (https://operations.osmfoundation.org/policies/tiles/), Mapbox because its default token can't be restricted.
- D12 (Day 3): Heatmap as discrete grid squares in the checkpoint colours, Unknown grey; built once per search, and the slider only changes the colour rule for hour X; the API sends `heatmap.step_deg` [lat, lon] so cell size isn't guessed; smoothness measured per slider update (target < 16 ms) plus a Chrome Performance recording.
- D13 (Day 3): TypeScript kept plain (API types and props only) + Vitest for pure helpers.
- Minor defaults (Day 3): Vite 8 react-ts template (TypeScript 7, oxlint as `lint`); MUI 9.5; plain React state; fetch + AbortController; risk colours Low green, Moderate yellow, High orange, Severe red, No Travel purple, Unknown grey, always with a text label; `VITE_API_URL` in `frontend/.env`; "Starting the server…" hint after 2 s without a health answer.

## Carry forward
- When the frontend is deployed: add its domain to `CORS_ALLOWED_ORIGINS` (and `CSRF_TRUSTED_ORIGINS` if needed).
- `check --deploy` advisories (HSTS, SSL redirect, secure cookies): verify Vercel's HTTP→HTTPS behaviour before submission.
- Vercel redeploys on every push and resets the `/tmp` cache: don't push right before recording the Loom, and warm the demo trip.
- Confirm the 429 message dash renders correctly in the browser.
- README limitations: HOS not modelled (60/70-hour limits, sleeper-berth split, adverse conditions, team driving, rest-stop locations, on-duty non-driving time); car-based routing; Open-Meteo shared-IP limits; per-instance cache and throttling.
- Open-Meteo counted each location as one call in real runs (HTTP 200 up to 603 in a minute, 429 by 703), and limits are per IP: a fresh search uses about 250–320 of the 600 per minute and 10,000 per day. Plan any demo or Loom run around this.
- Live on Vercel: cold start 7.7 s after 20 idle minutes, then search 3.3–3.5 s fresh and 2.1 s repeat, from one session; earlier local runs reached 26 s, so the frontend still needs a loading state and the health wake-up.
