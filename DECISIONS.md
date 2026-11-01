# Decisions

- D1 (Day 1): Mapbox Directions + Geocoding; it returns only 2 routes and has no truck profile, so a third route is generated on Day 2.
- D2 (Day 1): Open-Meteo; rain = `rain + showers`, snow = `snowfall`, wind = sustained `wind_speed_10m`, gusts for display only.
- D3 (Day 1): Band edges are lower-inclusive, Severe keeps its top value for rain and snow, wind No Travel is >=55.
- D4 (Day 1): Worst of wind/rain/snow, load rules can only raise it; any missing input gives unknown unless No Travel is already proven.
- D5 (Day 1): Half-gap mile weights; tiers clean → over 25% unknown miles → No Travel, PDF order within each; recommend only a clean route, otherwise none.
- D6 (Day 2): Cache Open-Meteo per point in FileBasedCache (survives restarts, shared by workers), 30 min TTL, snapped to 0.02° because 0.1° changed storm-rain risk levels for almost no savings; no Mapbox route or geocode caching.
- D7 (Day 2): Third route from `exclude=toll` plus up to 4 hubs (left/right of the straight-line midpoint at 10% and 15%), sent in parallel with the main call; accept at <=1.25× fastest and <=75% overlap, pick the lowest overlap; a failed candidate is skipped; hubs within 50 mi of either end are skipped; short trips (<100 mi) try tolls only; otherwise "Only N distinct routes found".
- D8 (Day 2): Truck ETA = 65 mph cap (assumption) plus 30-min break after 8 h driving and 10-h rest after 11 h, per FMCSA summary https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations and 49 CFR 395.3 https://www.govinfo.gov/content/pkg/CFR-2023-title49-vol5/xml/CFR-2023-title49-vol5-sec395-3.xml
- D9 (Day 2): Heatmap hour 0 = departure; cells are combined risk levels 0–4 with load (raw values stay on checkpoints); one response; at most 250 points on a fixed, globally anchored grid; a failed grid batch gives `heatmap: null` plus a note, only failed checkpoint weather is an error.
- D10 (Day 2): Host the backend on Vercel Hobby (300 s limit, no fixed sleep), with Render as the documented fallback; no uptime pinging; Koyeb needs a card and PythonAnywhere has no threads in web apps; cache lives in `/tmp` through `CACHE_DIR`, so it is temporary and per instance.
- Minor defaults (Day 1): step 10/25/50 default 25; US-only geocoding; UTC; float rounding inside `risk.py`; precip uses the hour ending at or after the ETA, wind uses the nearest hour; no DB; no geocode caching.
- Minor defaults (Day 2): `forecast_days` fixed at 11, which costs no extra because Open-Meteo only adds weight above 10 variables or 2 weeks (https://open-meteo.com/en/pricing); Open-Meteo 429 returns HTTP 503 with no retry; candidate deadline 12 s after the main call; search throttled per client at 10/minute and 100/day, health unthrottled.

## Carry forward
- README limitations, D8 not modelled: rest-stop locations, team driving, 60/70-hour limits, sleeper-berth split, adverse-conditions extension, on-duty non-driving time.
- Open-Meteo counted each location as one call in real runs (HTTP 200 up to 603 in a minute, 429 by 703), and limits are per IP: a fresh search uses about 250–320 of the 600 per minute and 10,000 per day. Plan any demo or Loom run around this.
- Search time varies (8.7–26.4 s with fresh weather, 2.9–7.8 s with weather cached, in live runs): the frontend needs a clear loading state.
- Writing a fresh search to the file cache took about 2.3 s on Windows; re-measure on the host.
