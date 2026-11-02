import pytest

from routing.domain.ranking import RouteSummary, rank_routes, recommend, summarize_route
from routing.domain.risk import RiskLevel

L = RiskLevel.LOW
M = RiskLevel.MODERATE
H = RiskLevel.HIGH
S = RiskLevel.SEVERE
NT = RiskLevel.NO_TRAVEL

ELIGIBLE, INSUFFICIENT, NO_TRAVEL = 0, 1, 2
NO_SAFE_ROUTE = 'No safe route — consider delaying departure'
INSUFFICIENT_DATA = 'Insufficient forecast data'


def summary(index=0, severe=0.0, high=0.0, nt=0.0, avg=0.5, hours=10.0, tier=ELIGIBLE):
    return RouteSummary(
        route_index=index, total_miles=500.0, duration_s=hours * 3600, severe_miles=severe,
        high_miles=high, no_travel_miles=nt, unknown_miles=0.0, avg_risk=avg,
        has_no_travel=tier == NO_TRAVEL, insufficient_data=tier == INSUFFICIENT, tier=tier,
    )


def order(*summaries):
    return [route.route_index for route in rank_routes(list(summaries))]


def test_summarize_splits_miles_by_level():
    route = summarize_route(3, [L, H, S, NT, None], [10, 20, 30, 5, 15], 3600)
    assert route.route_index == 3
    assert route.total_miles == 80
    assert route.duration_s == 3600
    assert (route.severe_miles, route.high_miles) == (30, 20)
    assert (route.no_travel_miles, route.unknown_miles) == (5, 15)


def test_miles_by_level_covers_every_level_and_sums_to_the_route():
    route = summarize_route(0, [L, M, M, H, S, NT, None], [10, 4, 6, 20, 30, 5, 15], 3600)
    assert route.miles_by_level == {L: 10, M: 10, H: 20, S: 30, NT: 5, None: 15}
    assert sum(route.miles_by_level.values()) == route.total_miles


def test_miles_by_level_lists_levels_with_no_miles_as_zero():
    route = summarize_route(0, [L, L], [5, 5], 3600)
    assert route.miles_by_level == {L: 10, M: 0, H: 0, S: 0, NT: 0, None: 0}


def test_avg_risk_is_distance_weighted_over_known_checkpoints_only():
    route = summarize_route(0, [L, H, S, NT, None], [10, 20, 30, 5, 15], 3600)
    assert route.avg_risk == 2.31   # (0*10 + 2*20 + 3*30 + 4*5) / 65; the 15 unknown miles are out


def test_avg_risk_is_not_a_plain_mean_of_checkpoints():
    assert summarize_route(0, [L, S], [90, 10], 3600).avg_risk == 0.3


def test_avg_risk_is_rounded_to_2_decimals():
    assert summarize_route(0, [L, M, M], [1, 1, 1], 3600).avg_risk == 0.67


@pytest.mark.parametrize('known, unknown, insufficient, tier', [
    (75, 25, False, ELIGIBLE),         # exactly 25% is not over
    (74.9, 25.1, True, INSUFFICIENT),  # just over
    (74.96, 25.04, False, ELIGIBLE),   # within the 0.1 mi rounding used for ranking
])
def test_insufficient_data_threshold(known, unknown, insufficient, tier):
    route = summarize_route(0, [L, None], [known, unknown], 3600)
    assert (route.insufficient_data, route.tier) == (insufficient, tier)


def test_no_travel_outranks_insufficient_data_for_the_tier():
    route = summarize_route(0, [NT, None], [10, 90], 3600)
    assert route.has_no_travel and route.insufficient_data
    assert route.tier == NO_TRAVEL


@pytest.mark.parametrize('levels, weights', [
    ([None, None], [50, 50]),   # nothing known
    ([None], [0]),              # zero-length route: 25% of nothing must not read as eligible
    ([L], [0]),                 # known level, but no miles to average over
])
def test_no_known_miles_has_no_average_and_is_insufficient(levels, weights):
    route = summarize_route(0, levels, weights, 3600)
    assert route.avg_risk is None
    assert route.tier == INSUFFICIENT


def test_mismatched_levels_and_weights_are_rejected():
    with pytest.raises(ValueError):
        summarize_route(0, [L, M], [10], 3600)


# Each loser is better on every later key, so only the named criterion can decide the case.
TIE_BREAKS = [
    pytest.param(
        summary(0, severe=0, high=50, avg=2.0, hours=15), summary(1, severe=25, high=0, avg=0.1, hours=9),
        'Fewest Severe miles (0.0 vs 25.0)', id='severe'),
    pytest.param(
        summary(0, severe=10, high=0, avg=2.0, hours=15), summary(1, severe=10, high=25, avg=0.1, hours=9),
        'Same Severe miles; fewer High miles (0.0 vs 25.0)', id='high'),
    pytest.param(
        summary(0, severe=10, high=10, avg=0.42, hours=15), summary(1, severe=10, high=10, avg=0.61, hours=9),
        'Same Severe and High miles; lower average risk (0.42 vs 0.61)', id='avg_risk'),
    pytest.param(
        summary(0, severe=10, high=10, avg=0.5, hours=14.8), summary(1, severe=10, high=10, avg=0.5, hours=14.9),
        'Equal risk; shorter travel time (14 h 48 min vs 14 h 54 min)', id='duration'),
]


@pytest.mark.parametrize('winner, loser, reason', TIE_BREAKS)
def test_each_pdf_criterion_decides_on_its_own(winner, loser, reason):
    assert rank_routes([loser, winner]) == [winner, loser]


@pytest.mark.parametrize('winner, loser, reason', TIE_BREAKS)
def test_reason_names_the_deciding_criterion(winner, loser, reason):
    assert recommend([winner, loser]) == (winner, reason)


def test_fastest_route_with_no_travel_ranks_below_slower_clean_route():
    fast = summary(0, nt=5, hours=8, tier=NO_TRAVEL)
    slow = summary(1, severe=200, high=200, avg=3.0, hours=20)
    assert order(fast, slow) == [1, 0]


def test_among_no_travel_routes_fewer_no_travel_miles_ranks_first():
    many = summary(0, nt=50, severe=0, tier=NO_TRAVEL)
    few = summary(1, nt=25, severe=100, tier=NO_TRAVEL)
    assert order(many, few) == [1, 0]


def test_no_travel_tie_falls_through_to_the_pdf_order():
    worse = summary(0, nt=25, severe=50, tier=NO_TRAVEL)
    better = summary(1, nt=25, severe=10, tier=NO_TRAVEL)
    assert order(worse, better) == [1, 0]


def test_no_travel_miles_do_not_affect_the_other_tiers():
    # Tier 0 and 1 routes have no No Travel miles in practice; this pins that the key is tier-2 only.
    with_stray_value = summary(0, nt=5, severe=0)
    plain = summary(1, nt=0, severe=10)
    assert order(with_stray_value, plain) == [0, 1]


def test_insufficient_data_sits_between_clean_and_no_travel():
    no_travel = summary(0, nt=5, tier=NO_TRAVEL)
    insufficient = summary(1, tier=INSUFFICIENT)
    clean = summary(2, severe=300, high=100, avg=3.5, hours=30)
    assert order(no_travel, insufficient, clean) == [2, 1, 0]


def test_insufficient_data_routes_use_the_pdf_order_within_their_tier():
    worse = summary(0, severe=50, tier=INSUFFICIENT)
    better = summary(1, severe=10, tier=INSUFFICIENT)
    assert order(worse, better) == [1, 0]


def test_missing_avg_risk_sorts_after_a_known_one():
    unknown_average = summary(0, avg=None, tier=INSUFFICIENT)
    known_average = summary(1, avg=3.9, tier=INSUFFICIENT)
    assert order(unknown_average, known_average) == [1, 0]


def test_float_noise_in_miles_falls_through_to_the_next_key():
    noisy = summary(0, severe=25.000000001, high=0)
    plain = summary(1, severe=25.0, high=10)
    assert order(plain, noisy) == [0, 1]
    assert recommend([noisy, plain])[1] == 'Same Severe miles; fewer High miles (0.0 vs 10.0)'


def test_float_noise_in_high_miles_falls_through_to_avg_risk():
    noisy = summary(0, high=25.000000001, avg=0.2)
    plain = summary(1, high=25.0, avg=0.9)
    assert order(plain, noisy) == [0, 1]


def test_float_noise_in_no_travel_miles_falls_through_to_severe_miles():
    noisy = summary(0, nt=25.000000001, severe=0, tier=NO_TRAVEL)
    plain = summary(1, nt=25.0, severe=10, tier=NO_TRAVEL)
    assert order(plain, noisy) == [0, 1]


def test_float_noise_in_avg_risk_falls_through_to_duration():
    slower = summary(0, avg=0.421, hours=11)
    faster = summary(1, avg=0.424, hours=10)
    assert order(slower, faster) == [1, 0]


def test_exact_ties_keep_the_original_order():
    assert order(summary(2), summary(0), summary(1)) == [2, 0, 1]


def test_exact_tie_reason():
    first, second = summary(0), summary(1)
    assert recommend([first, second]) == (first, 'Tied on all criteria; first route returned')


def test_durations_within_a_minute_show_the_gap_in_the_reason():
    faster, slower = summary(0, hours=14.8), summary(1, hours=14.8 + 12 / 3600)
    assert recommend([faster, slower])[1] == 'Equal risk; shorter travel time by 12 s'


@pytest.mark.parametrize('others', [
    [],
    [summary(1, tier=INSUFFICIENT)],
    [summary(1, nt=5, tier=NO_TRAVEL)],
])
def test_only_eligible_route(others):
    best = summary(0)
    assert recommend([best, *others]) == (best, 'Only eligible route')


@pytest.mark.parametrize('routes, reason', [
    ([summary(0, nt=5, tier=NO_TRAVEL), summary(1, nt=9, tier=NO_TRAVEL)], NO_SAFE_ROUTE),
    ([summary(0, tier=INSUFFICIENT), summary(1, tier=INSUFFICIENT)], INSUFFICIENT_DATA),
    ([summary(0, tier=INSUFFICIENT), summary(1, nt=5, tier=NO_TRAVEL)], INSUFFICIENT_DATA),
    ([], 'No routes to compare'),
])
def test_recommends_none_without_an_eligible_route(routes, reason):
    assert recommend(routes) == (None, reason)


def test_insufficient_data_is_never_recommended_even_with_the_best_numbers():
    routes = rank_routes([
        summary(0, severe=0, high=0, avg=0.0, hours=8, tier=INSUFFICIENT),
        summary(1, severe=300, high=100, avg=3.5, hours=30),
    ])
    recommended, _ = recommend(routes)
    assert recommended.route_index == 1
