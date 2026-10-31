# Loom notes

## Day 1
- **Real API spike:** show the spike output. Mapbox returns at most 2 routes (docs + real calls), so a third route is generated; arbitrary offsets sent trucks onto mining roads, so Day 2 uses interstate hub cities.
- **Open-Meteo:** show the 100-point call. One batched call covers the route; rain = rain + showers; snowfall is depth (~7× water), not water.
- **Risk table edges:** show `test_risk.py` rows next to the PDF table. Shared edges get the riskier band, and float rounding stops noise from missing an edge.
- **Test quality:** show a deliberate bug failing a test. Tests were written first and 35 deliberate bugs were injected (15 in geo/weather_time/risk, 20 in ranking), all caught; one gap found and closed (wind 35 + 40,001 lb).
- **Ranking:** show `test_ranking.py` tie-break cases. Strict PDF order inside tiers (clean → insufficient data → No Travel); recommend none if nothing is safe; reason text names the deciding criterion.

AI use: planned with Claude, built with Claude Code block by block; I chose every decision and reviewed the tests.
