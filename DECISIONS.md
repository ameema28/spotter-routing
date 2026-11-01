# Decisions

- D1 (Day 1): Mapbox Directions + Geocoding; it returns only 2 routes and has no truck profile, so a third route is generated on Day 2.
- D2 (Day 1): Open-Meteo; rain = `rain + showers`, snow = `snowfall`, wind = sustained `wind_speed_10m`, gusts for display only.
- D3 (Day 1): Band edges are lower-inclusive, Severe keeps its top value for rain and snow, wind No Travel is >=55.
- D4 (Day 1): Worst of wind/rain/snow, load rules can only raise it; any missing input gives unknown unless No Travel is already proven.
- D5 (Day 1): Half-gap mile weights; tiers clean → over 25% unknown miles → No Travel, PDF order within each; recommend only a clean route, otherwise none.
- D6 (Day 2): Cache Open-Meteo per point in LocMemCache, 30 min TTL, snapped to 0.02° because 0.1° changed storm-rain risk levels for almost no savings; no Mapbox route or geocode caching.
- D7 (Day 2): Third route from `exclude=toll` plus up to 4 hubs (left/right of the straight-line midpoint at 10% and 15%), sent in parallel with the main call; accept at <=1.25× fastest and <=75% overlap, pick the lowest overlap; a failed candidate is skipped; hubs within 50 mi of either end are skipped; short trips (<100 mi) try tolls only; otherwise "Only N distinct routes found".
- D8 (Day 2): Truck ETA = 65 mph cap (assumption) plus 30-min break after 8 h driving and 10-h rest after 11 h, per FMCSA summary https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations and 49 CFR 395.3 https://www.govinfo.gov/content/pkg/CFR-2023-title49-vol5/xml/CFR-2023-title49-vol5-sec395-3.xml
- Minor defaults (Day 1): step 10/25/50 default 25; US-only geocoding; UTC; float rounding inside `risk.py`; precip uses the hour ending at or after the ETA, wind uses the nearest hour; no DB; LocMemCache; no geocode caching.

## Carry forward to Day 2
- README limitations, D8 not modelled: rest-stop locations, team driving, 60/70-hour limits, sleeper-berth split, adverse-conditions extension, on-duty non-driving time.
- Pipeline: pass route durations through `apply_speed_cap` and `add_rest_breaks`; ranking's travel time then includes stops.
- Reason text shows "14.80 h vs 14.80 h" when durations differ by under ~18 s: format durations better in the API.
- `fetch_hourly` returns datetimes, but `precip_hour` and `wind_hour` take strings: align them in the pipeline.
- LocMemCache is per process, so each server worker has its own cache: settle the worker count at deploy.
