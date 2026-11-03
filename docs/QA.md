# QA pass (Day 4, 2026-11-03)

How the app was checked against the assessment brief before submission. "Fixture" means a saved real API response
served to the frontend in headless Chrome, so the check costs no live API or weather calls.

## 1. Requirements from the brief

| Requirement | Where in the app | Evidence | Result |
|---|---|---|---|
| Inputs: origin, destination, departure date/time, load weight | Search form (side panel) | `RoutePlanRequestSerializer` tests in `backend/tests/test_route_plan_view.py`; UI matrix form rows below | Pass |
| 3 route options from a routing API | Mapbox Directions (2 routes) + a generated third (D1, D7); route cards | `test_alternatives.py`, `test_candidates.py`, `test_route_plan.py::test_three_routes_ranked_with_a_recommendation`; live searches a–d all returned 3 | Pass |
| Weather sampled every 10 / 25 / 50 miles | Checkpoint spacing toggle; checkpoints on the map | `test_route_assessment.py::test_checkpoints_follow_the_step`, `test_route_plan.py::test_step_changes_the_checkpoints`; live a (step 10) had 53–57 checkpoints, live b (step 50) 14–15 | Pass |
| …using the truck's ETA at each checkpoint | Truck ETA (65 mph cap + HOS breaks, D8); popup "ETA" and forecast hours | `test_truck_eta.py`, `test_route_assessment.py::test_checkpoint_carries_position_eta_and_conditions`, `::test_rest_stops_shift_later_etas_and_count_as_travel_time` | Pass |
| Risk table (wind, rain, snow) | `backend/routing/domain/risk.py` (D2–D4) | `test_risk.py` (band edges, worst-of, missing data) | Pass |
| Load rules (≥55 mph; 45–54 mph & >30,000 lb; 35–44 mph & >40,000 lb) | `risk.py`; form helper text | `test_risk.py::test_load_rules`, `::test_load_rule_never_lowers_a_level`, `test_route_assessment.py::test_load_reaches_the_risk_rules`, `::test_heatmap_cells_use_the_load_rules` | Pass |
| Recommendation order: Severe miles → High miles → avg risk → time | `backend/routing/domain/ranking.py` (D5); banner reason | `test_ranking.py::test_each_pdf_criterion_decides_on_its_own`, `::test_reason_names_the_deciding_criterion`; live c reason "lower average risk", live d "fewer High miles" | Pass |
| Map: all routes | Route layers, selected solid / others dashed | Screenshots `docs/qa/normal-*.png` | Pass |
| Map: checkpoints, risk levels, ETAs | Coloured checkpoint dots; popup with ETA, level, driver, wind/rain/snow | `docs/qa/popup-zorder.png`; `frontend/src/map/popups.test.ts` | Pass |
| Map/panel: route summaries | Route cards (distance, driving, trip, Severe/High/No Travel/Unknown miles, avg risk, risk bar) | Screenshots; `riskShares.test.ts` | Pass |
| Heatmap along the corridor | Grid squares around the routes (D9, D12) | `test_route_plan.py::test_heatmap_shape`; `map/heatmap.test.ts`; `map/accuracy.test.ts` (95.9% match with checkpoints) | Pass |
| 0–48 h forecast slider | Slider + Play, trucks move with the hour | `docs/qa/*.png`; keyboard row below; slider perf in D12 | Pass |
| Heatmap still reachable when the weather service is busy | Retry countdown + "Retry now" (D14) | `heatmapRetry.test.ts`, `test_heatmap_view.py`; UI matrix "levels null" | Pass |
| React frontend + Django backend | `frontend/` (React, MUI, MapLibre), `backend/` (Django + DRF) | Repo | Pass |
| Deliverables: GitHub repo, hosted app | https://spotter-routing-ameema.vercel.app, https://spotter-routing-api.vercel.app | Live searches below | Pass |
| Deliverable: Loom walkthrough | n/a | To be recorded (Day 4, step 4) | Pending |

## 2. Live searches (4, at least 65 s apart)

| # | Search | Status, time | Routes (trip time) | Recommendation and reason | Heatmap | Notes |
|---|---|---|---|---|---|---|
| a | Denver, CO → Salt Lake City, UT; step 10, 35,000 lb, +3 h | 200, 4.7 s | Fastest 519.8 mi (9 h 2 min); Alt 1 525.3 mi (9 h 21 min); via Rock Springs 551.7 mi (9 h 42 min); all Low | Fastest route: "Equal risk; shorter travel time (9 h 2 min vs 9 h 21 min)" | 225 cells, levels present | none |
| b | Kansas City, MO → Denver, CO; step 50, 45,000 lb, +5 days | 200, 4.5 s | Fastest 603.7 mi (10 h 5 min); Alt 1 613.2 mi; via North Platte 685.6 mi | Fastest route: "Equal risk; shorter travel time (10 h 5 min vs 10 h 26 min)" | 176 cells, levels present | Far-departure note shown in the UI ("more than 2 days away") |
| c | Dallas, TX → Chicago, IL; step 25, 20,000 lb, +1 h | 200, 3.5 s | Fastest 968.7 mi (26 h 2 min); Alt 1 960.1 mi (26 h 7 min); via Kansas City 1,017.8 mi (27 h 30 min) | via Kansas City: "Same Severe and High miles; lower average risk (0.00 vs 0.03)" | 158 cells, levels present | none |
| d | "Dalas TX" → Chicago, IL; step 25, 40,000 lb, +2 h | 200, 2.0 s | Same 3 routes as c; Fastest and Alt 1 had 25 High miles | via Kansas City: "Same Severe miles; fewer High miles (0.0 vs 25.0)" | 158 cells, levels present | Misspelling matched "Dallas, Texas, United States"; the results heading and the start pin show the matched label, so a wrong match would be visible |

Responses a and b are saved as `frontend/src/fixtures/plan-denver-slc.json` and `plan-kc-denver.json`.

## 3. UI matrix (fixture-backed headless Chrome, 1440×900 unless noted)

Each row checks the visible text and, where relevant, the field's `aria-invalid` and helper text, then the screenshot
was read. 28 rows, 28 pass after the two fixes below.

| Area | Row | Result |
|---|---|---|
| Normal | Dallas → Chicago; Denver → Salt Lake City (live a); Kansas City → Denver (live b) | Pass (KC start pin was cut off before fix 2) |
| Rare outcomes (edited fixtures) | High + Severe miles on one route (reason "Fewest Severe miles (0.0 vs 30.0)") | Pass |
| | One route with No Travel: ranked last, "Has No Travel miles" on its card | Pass |
| | All routes No Travel: "No route recommended — No safe route — consider delaying departure" | Pass |
| | Insufficient forecast data: "No route recommended — Insufficient forecast data" | Pass |
| | Only 2 routes: note "Only 2 distinct routes found" | Pass |
| | Heatmap levels null: countdown "Heatmap will retry in N s" + "Retry now" + busy note | Pass |
| Errors (intercepted) | 400 field error shown under Departure | Pass |
| | 422 origin / destination not found shown under the right field | Pass |
| | 429 throttle, 503 busy, 504 timeout: the server's message is shown | Pass |
| | Network down: "Can't reach the server…" | Pass |
| | Slow health (6 s): "Starting the server… (this can take ~10 s)" at 3 s | Pass |
| | Cancel mid-search: back to the form, no error, no stale result | Pass |
| Form validation | Departure in the past / more than 7 days ahead | Pass |
| | Load 0 / 90,000 | Pass |
| | Empty origin | Pass |
| Keyboard | Tab reaches an unselected route card, Enter selects it (`aria-pressed`) | Pass |
| | Slider: Home then ArrowRight ×3 = hour 3 | Pass |
| Map | Checkpoint popup next to a stop pill: popup on top (desktop: 2 overlapping markers, phone: 4, none paint over it) | Pass after fix 1 |
| Phone 390×844 | Dallas: layout, Legend button opens the legend, slider overlay | Pass |
| | Heatmap levels null: countdown row fits | Pass |
| | Popup over pills | Pass after fix 1 |

No console errors in any row (the basemap's own tile requests are excluded).

### Fixed in this pass
1. **Popup under the stop pills** (reported): markers carry z-index 1–4 and the popup had none, so the "10 h rest" and
   "30 min" pills covered it. The popup now has z-index 5 (`MapPopup.tsx`).
2. **Start/end pin cut off at the right edge** (Kansas City → Denver): desktop fit padding on the right was 56 px,
   less than half a pin's width. Now 96 px, the same as on phones (`MapView.tsx`).

### Cosmetic, not fixed
- Phone: the slider's hour labels (0 h … 48 h) are hidden and the time label wraps to three lines.
- Phone: the open legend covers the top-left of the map (it starts folded, so only when the user opens it).
- Basemap city labels sit under the route and checkpoints (e.g. "Memphis", "Little Rock").
- Geocoding is fuzzy by design (Mapbox): a misspelling is matched silently; the matched label is shown, but there is no
  "did you mean" prompt.
- The screenshots in `docs/qa/` are full-size PNGs (about 1.5 MB together).

## 4. Lighthouse (live frontend, desktop preset, Lighthouse 12.8.2)

| Category | Score |
|---|---|
| Performance | 89 |
| Accessibility | 100 |
| Best practices | 100 |

First and largest contentful paint 0.8 s, total blocking time 0 ms, cumulative layout shift 0.004.
