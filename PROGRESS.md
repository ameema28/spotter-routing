# Progress (16h budget)

Day 1 | 2.5h (1.5h build + ~1h planning and setup) | Running total 2.5h / 16h | Status: Day 1 plan complete
Day 2 | 3.25h | Running total 5.75h / 16h | Status: Backend complete and live (https://spotter-routing-api.vercel.app)
Day 3 | 2.75h | Running total 8.5h / 16h | Status: Frontend complete and live (https://spotter-routing-ameema.vercel.app)

## Current state
Live app: https://spotter-routing-ameema.vercel.app
Live API: https://spotter-routing-api.vercel.app

Exists:
- Backend: `GET /api/health/` and `POST /api/route-plan/` on Vercel Hobby; domain modules in `backend/routing/domain/`, services in `backend/routing/services/`; caching, throttling, server-side logging of Open-Meteo 429 reasons; 441 passing tests
- Frontend (`frontend/`, React + TypeScript + MUI + MapLibre) on Vercel: search form with field errors, loading stages, ranked route cards, map with routes, checkpoints, stops, popups and legend, corridor heatmap with a 0–48 h slider and moving trucks; 75 passing tests

Doesn't exist yet:
- Day 4 QA pass (requirements vs the PDF, error cases, mobile width, Lighthouse)
- Final README (limitations)
- Loom
- Submission
