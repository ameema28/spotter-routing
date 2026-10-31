"""Route summary, ranking and recommendation from the PDF's "Prefer" list and decision D5."""
from dataclasses import dataclass

from routing.domain.risk import RiskLevel

# D5: a route over this share of unknown miles can't be called safe.
INSUFFICIENT_DATA_SHARE = 0.25

# Comparing at these precisions stops float noise from deciding a ranking.
MILE_DECIMALS = 1
RISK_DECIMALS = 2

TIER_ELIGIBLE = 0
TIER_INSUFFICIENT_DATA = 1
TIER_NO_TRAVEL = 2

NO_ROUTES_REASON = 'No routes to compare'
NO_SAFE_ROUTE_REASON = 'No safe route — consider delaying departure'
INSUFFICIENT_DATA_REASON = 'Insufficient forecast data'
ONLY_ELIGIBLE_REASON = 'Only eligible route'
TIED_REASON = 'Tied on all criteria; first route returned'


@dataclass(frozen=True)
class RouteSummary:
    route_index: int
    total_miles: float
    duration_s: float
    severe_miles: float
    high_miles: float
    no_travel_miles: float
    unknown_miles: float
    avg_risk: float | None
    has_no_travel: bool
    insufficient_data: bool
    tier: int


def _miles(value: float) -> float:
    return round(value, MILE_DECIMALS)


def _risk(value: float) -> float:
    return round(value, RISK_DECIMALS)


def _average_risk(pairs: list[tuple[RiskLevel | None, float]]) -> float | None:
    """Distance-weighted mean of L0 M1 H2 S3 NT4 over known checkpoints (D5)."""
    known = [(level, weight) for level, weight in pairs if level is not None]
    known_miles = sum(weight for _, weight in known)
    if known_miles == 0:
        return None
    return _risk(sum(level * weight for level, weight in known) / known_miles)


def _tier(has_no_travel: bool, insufficient_data: bool) -> int:
    # No Travel is proven unsafe while missing data is only unproven, so No Travel ranks lower.
    if has_no_travel:
        return TIER_NO_TRAVEL
    return TIER_INSUFFICIENT_DATA if insufficient_data else TIER_ELIGIBLE


def summarize_route(route_index: int, levels: list[RiskLevel | None], weights: list[float],
                    duration_s: float) -> RouteSummary:
    """Turn checkpoint levels and mile weights into one route's totals (D5)."""
    pairs = list(zip(levels, weights, strict=True))

    def miles_at(target: RiskLevel | None) -> float:
        return sum(weight for level, weight in pairs if level == target)

    total_miles = sum(weights)
    unknown_miles = miles_at(None)
    avg_risk = _average_risk(pairs)
    # avg_risk None covers a zero-length route, where "over 25% of nothing" would read as eligible.
    insufficient_data = (avg_risk is None
                         or _miles(unknown_miles) > _miles(INSUFFICIENT_DATA_SHARE * total_miles))
    has_no_travel = RiskLevel.NO_TRAVEL in levels
    return RouteSummary(
        route_index, total_miles, duration_s, miles_at(RiskLevel.SEVERE), miles_at(RiskLevel.HIGH),
        miles_at(RiskLevel.NO_TRAVEL), unknown_miles, avg_risk, has_no_travel, insufficient_data,
        _tier(has_no_travel, insufficient_data),
    )


def _rank_key(route: RouteSummary) -> tuple:
    no_travel_miles = _miles(route.no_travel_miles) if route.tier == TIER_NO_TRAVEL else 0.0
    # PDF "Prefer" order: Severe miles, High miles, average risk, travel time.
    return (
        route.tier,
        no_travel_miles,
        _miles(route.severe_miles),
        _miles(route.high_miles),
        route.avg_risk is None,
        _risk(route.avg_risk or 0),
        route.duration_s,
    )


def rank_routes(summaries: list[RouteSummary]) -> list[RouteSummary]:
    """Safest first. sorted() is stable, so exact ties keep their original order."""
    return sorted(summaries, key=_rank_key)


def _hours_pair(best: RouteSummary, other: RouteSummary) -> str:
    decimals = 1 if round(best.duration_s / 3600, 1) != round(other.duration_s / 3600, 1) else 2
    return f'{best.duration_s / 3600:.{decimals}f} h vs {other.duration_s / 3600:.{decimals}f} h'


def _deciding_reason(best: RouteSummary, other: RouteSummary) -> str:
    """Name the first PDF criterion that separates the two routes."""
    if _miles(best.severe_miles) != _miles(other.severe_miles):
        return f'Fewest Severe miles ({best.severe_miles:.1f} vs {other.severe_miles:.1f})'
    if _miles(best.high_miles) != _miles(other.high_miles):
        return f'Same Severe miles; fewer High miles ({best.high_miles:.1f} vs {other.high_miles:.1f})'
    if _risk(best.avg_risk) != _risk(other.avg_risk):
        return f'Same Severe and High miles; lower average risk ({best.avg_risk:.2f} vs {other.avg_risk:.2f})'
    if best.duration_s != other.duration_s:
        return f'Equal risk; shorter travel time ({_hours_pair(best, other)})'
    return TIED_REASON


def recommend(ranked: list[RouteSummary]) -> tuple[RouteSummary | None, str]:
    """First ranked route if it is eligible, with the reason it beat the runner-up."""
    if not ranked:
        return None, NO_ROUTES_REASON
    best = ranked[0]
    if best.tier == TIER_NO_TRAVEL:
        return None, NO_SAFE_ROUTE_REASON
    if best.tier == TIER_INSUFFICIENT_DATA:
        return None, INSUFFICIENT_DATA_REASON
    if len(ranked) == 1 or ranked[1].tier != TIER_ELIGIBLE:
        return best, ONLY_ELIGIBLE_REASON
    return best, _deciding_reason(best, ranked[1])
