# Progress (16h budget)

Day 1 | 2.5h (1.5h build + ~1h planning and setup) | Running total 2.5h / 16h | Status: Day 1 plan complete

## Current state
Live backend: https://spotter-routing-api.vercel.app (health at `/api/health/`)

Exists:
- `GET /api/health/` and `POST /api/route-plan/`, deployed on Vercel Hobby
- Domain modules in `backend/routing/domain/`: risk, load rules, sampling, ETA, truck ETA, ranking, third route, heatmap grid
- Mapbox and Open-Meteo clients with caching and throttling
- 430 passing tests, on Python 3.11 and 3.12

Doesn't exist yet:
- Frontend
- Frontend hosting
