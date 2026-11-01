# Progress (16h budget)

Day 1 | 2.5h (1.5h build + ~1h planning and setup) | Running total 2.5h / 16h | Status: Day 1 plan complete
Day 2 | 3.25h | Running total 5.75h / 16h | Status: Backend complete and live (https://spotter-routing-api.vercel.app)

## Current state
Live backend: https://spotter-routing-api.vercel.app

Exists:
- `GET /api/health/` and `POST /api/route-plan/`, deployed on Vercel Hobby
- Domain modules in `backend/routing/domain/`: risk and load rules, sampling, ETA, truck ETA, ranking, third route, hubs, heatmap grid, route assessment
- Services in `backend/routing/services/`: Mapbox and Open-Meteo clients, candidates, route plan
- Caching and throttling
- 430 passing tests, on Python 3.11 and 3.12

Doesn't exist yet:
- Frontend
- Frontend hosting
- Final README
- Loom
