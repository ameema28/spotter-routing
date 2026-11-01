# Decisions

- D1 (Day 1): Mapbox Directions + Geocoding; it returns only 2 routes and has no truck profile, so a third route is generated on Day 2.
- D2 (Day 1): Open-Meteo; rain = `rain + showers`, snow = `snowfall`, wind = sustained `wind_speed_10m`, gusts for display only.
- D3 (Day 1): Band edges are lower-inclusive, Severe keeps its top value for rain and snow, wind No Travel is >=55.
- D4 (Day 1): Worst of wind/rain/snow, load rules can only raise it; any missing input gives unknown unless No Travel is already proven.
- D5 (Day 1): Half-gap mile weights; tiers clean → over 25% unknown miles → No Travel, PDF order within each; recommend only a clean route, otherwise none.
- D6 (Day 2): Cache Open-Meteo per point in LocMemCache, 30 min TTL, snapped to 0.02° because 0.1° changed storm-rain risk levels for almost no savings; no Mapbox route or geocode caching.
- Minor defaults (Day 1): step 10/25/50 default 25; US-only geocoding; UTC; float rounding inside `risk.py`; precip uses the hour ending at or after the ETA, wind uses the nearest hour; no DB; LocMemCache; no geocode caching.

## Carry forward to Day 2
- Third route: hub-city via + `exclude=toll`, keep whichever passes the length/similarity check.
- Truck ETA adjustment: `time_profile` still uses car-profile durations.
- Reason text shows "14.80 h vs 14.80 h" when durations differ by under ~18 s: format durations better in the API.
- `fetch_hourly` returns datetimes, but `precip_hour` and `wind_hour` take strings: align them in the pipeline.
- LocMemCache is per process, so each server worker has its own cache: settle the worker count at deploy.
