# spotter-routing — rules for Claude Code

Spotter AI Full Stack assessment: React + Django app that recommends the safest of 3 truck routes
using weather, load weight and travel time.

## Hard limits
- 16h total, 4h/day hard stop. Scoring: 40% logic, 40% UI/map/heatmap smoothness, 15% code quality, 5% docs/Loom.
- "Prioritize correctness and clarity over extra features."

## How we work
- Plan first, wait for "go", one block at a time, commit after each block.
- Max 5 decisions per day; minor ones get a default reported in one line. No quizzes, no tutorials.
- I'm new to Django/DRF: explain a new concept in ONE sentence, mapped to FastAPI if possible.
- Core logic (risk, load rules, sampling, ETA, ranking) is TEST-FIRST, plain Python with no Django
  imports, in backend/routing/domain/.
- Never invent third-party API facts: prove them with a real call, or tell me what to check in the docs.
- Secrets only in .env (gitignored); commit .env.example with empty values. Never print tokens.
- Comments explain why, not what.
- After each UI change: headless Chrome (fixture-backed, no live search) screenshots at T+0/8/15/40 on desktop and
  phone; review them for overlaps, cut-off pins, misaligned cards and console errors before asking me to check.

## Logs
- DECISIONS.md: one line per decision.
- LOOM_NOTES.md: 3–5 bullets per day.
- PROGRESS.md: hours per block + running total.

## Decision protocol
For every decision that affects the score, BEFORE I choose:
1. Options: 2–3, each with its main trade-off in one line.
2. Your judgment: which you recommend and why, based on evidence (repo code, real API output,
   the brief). If you disagree with a suggested default, say so plainly and why.
3. "Why" for my defence: 2–3 sentences I can say in the Loom or an interview.
4. What would change your recommendation (one line).
Then STOP and wait for my choice. Minor decisions: pick a sensible default and report it in one line.
Max 5 score-affecting decisions per day.

## Current state
- Live: app https://spotter-routing-ameema.vercel.app, API https://spotter-routing-api.vercel.app (API contract: `build_route_plan` docstring).
- Backend 465 tests, frontend 89 tests; D1–D15, minor defaults and the carry-forward list are in DECISIONS.md.
- Open-Meteo 429s are logged server-side with the provider's reason (Vercel function logs).
- Heatmap retry: `POST /api/heatmap/` (`build_heatmap_levels` docstring).
- Next: Day 4 QA pass (PDF requirements, errors, mobile, Lighthouse), final README, Loom, submission.
