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

## Logs
- DECISIONS.md: one line per decision.
- LOOM_NOTES.md: 3–5 bullets per day.
- PROGRESS.md: hours per block + running total.