# Decisions

- D1 (Day 1): Routing + geocoding = Mapbox Directions + Geocoding; proven on 3 long-haul trips, but it returns only 2 routes and has no truck profile.
- D1 fallback (build Day 2): third route from a curated interstate hub-city via point; also test `exclude=toll` as a candidate and keep whichever passes the length/similarity check.
- D2 (Day 1): Weather = Open-Meteo; one batched call handled 100 points in about 1.15 s, with no key.
- D2 mapping (Day 1): rain = `rain + showers`, snow = `snowfall`, wind = sustained `wind_speed_10m`, gusts for display only.
- Geocoding (Day 1): results are not cached or saved as fixtures, because Mapbox doesn't allow caching temporary results.

## Carry forward
- Mapbox `driving` durations are car times, so truck ETAs need an adjustment.
- `rain`, `showers`, `snowfall` and `precipitation` are preceding-hour sums; `wind_speed_10m` is instantaneous.
