// The backend answers in one request, so these are the usual stages by elapsed time, not live progress.
// Timings come from the measured live search (about 3.3 s fresh).
const STAGES: [number, string][] = [
  [6000, 'Ranking routes…'],
  [2000, 'Checking weather at each checkpoint…'],
  [0, 'Finding routes…'],
]

export function loadingStage(elapsedMs: number, serverWaking: boolean): string {
  if (serverWaking) return 'Starting the server first… (this can take ~10 s)'
  return STAGES.find(([after]) => elapsedMs >= after)?.[1] ?? STAGES[STAGES.length - 1][1]
}
