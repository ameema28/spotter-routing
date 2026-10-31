# Decisions

- D1 (Day 1): Routing + geocoding = Mapbox Directions + Geocoding; proven on 3 long-haul trips, but it returns only 2 routes and has no truck profile.
- D1 fallback (build Day 2): third route from a curated interstate hub-city via point; also test `exclude=toll` as a candidate and keep whichever passes the length/similarity check.
- D2 (Day 1): Weather = Open-Meteo; one batched call handled 100 points in about 1.15 s, with no key.
- D2 mapping (Day 1): rain = `rain + showers`, snow = `snowfall`, wind = sustained `wind_speed_10m`, gusts for display only.
- Geocoding (Day 1): results are not cached or saved as fixtures, because Mapbox doesn't allow caching temporary results.
- D3 (Day 1): Band edges are lower-inclusive, Severe keeps its top value for rain and snow, wind No Travel is >=55; inputs round first (rain/snow 3 decimals, wind 2) inside `risk.py`.
- D4 (Day 1): Checkpoint level is the worst of wind/rain/snow, and load rules can only raise it; any missing input gives unknown, unless the provided inputs already prove No Travel.
- D5 miles (Day 1): each checkpoint represents half the gap to each neighbour, so weights sum to route length; Severe/High miles = sum of weights at that level; average risk = distance-weighted mean of L0 M1 H2 S3 NT4 over known checkpoints, 2 decimals.
- D5 No Travel (Day 1): any route with a No Travel checkpoint ranks below every route without one, fewest No Travel miles first, with a warning; if all routes have No Travel, rank them but recommend none ("No safe route — consider delaying departure").
- D5 unknowns (Day 1): unknown checkpoints are excluded from miles and averages but counted; a route over 25% unknown miles is flagged "insufficient forecast data", ranks below unflagged non-NT routes and above NT routes, and can't be recommended; if no route is unflagged and NT-free, recommend none.

## Carry forward
- Mapbox `driving` durations are car times, so truck ETAs need an adjustment; `time_profile` uses them unchanged until the Day 2 decision.
- `rain`, `showers`, `snowfall` and `precipitation` are preceding-hour sums; `wind_speed_10m` is instantaneous.
- Prompt 5: the PDF ranking never mentions No Travel miles, and unknown checkpoints must not count as Low.
