from dataclasses import dataclass

import pytest

from routing.domain.alternatives import (
    Candidate,
    accept_candidate,
    overlap_fraction,
    route_count_note,
    select_extra_routes,
    select_hubs,
)
from routing.domain.hubs import HUBS, Hub


@dataclass
class FakeRoute:
    coords_lonlat: list
    seg_distances_m: list
    duration_s: float = 3600.0


def line(lat, lon_start, lon_end, step=0.01, duration_s=3600.0, metres=850.0):
    """An east-west route with a vertex every step degrees."""
    count = round((lon_end - lon_start) / step) + 1
    coords = [[lon_start + index * step, lat] for index in range(count)]
    return FakeRoute(coords, [metres] * (count - 1), duration_s)


def join(first, second):
    return FakeRoute(first.coords_lonlat + second.coords_lonlat[1:],
                     first.seg_distances_m + second.seg_distances_m)


def with_overlap(share, duration_s=3600.0):
    """A route sharing the given share of its length with BASE, then leaving it."""
    shared = round(100 * share)
    coords = [[-100 + index * 0.01, 40.0] for index in range(shared + 1)]
    coords += [[-100 + index * 0.01, 41.0] for index in range(shared, 101)]
    return FakeRoute(coords, [850.0] * shared + [0.0] + [850.0] * (100 - shared), duration_s)


BASE = line(40, -100, -99)
FAR_AWAY = line(41, -100, -99)


def test_identical_routes_overlap_fully():
    assert overlap_fraction(BASE, [BASE]) == 1


def test_distant_routes_do_not_overlap():
    assert overlap_fraction(FAR_AWAY, [BASE]) == 0


def test_half_shared_route_overlaps_by_half():
    assert overlap_fraction(with_overlap(0.5), [BASE]) == pytest.approx(0.5, abs=0.03)


def test_road_within_about_a_cell_counts_as_the_same_road():
    assert overlap_fraction(line(40.008, -100, -99), [BASE]) == 1


def test_a_parallel_road_a_few_cells_away_is_a_different_road():
    assert overlap_fraction(line(40.05, -100, -99), [BASE]) == 0


def test_overlap_is_measured_by_distance_not_vertices():
    shared = line(40, -100, -99.9, step=0.001, metres=85.0)    # many vertices, 8.5 km
    separate = FakeRoute([[-99.9, 40], [-99.9, 41]], [85_000.0])
    candidate = join(shared, separate)
    assert overlap_fraction(candidate, [BASE]) == pytest.approx(0.1, abs=0.02)


def test_a_long_segment_is_sampled_along_its_length():
    # Two vertices on the existing road with a detour between them are not a shared 100 km.
    candidate = FakeRoute([[-100, 40], [-100, 41], [-99, 41], [-99, 40]], [111_000.0, 85_000.0, 111_000.0])
    assert overlap_fraction(candidate, [BASE]) < 0.05


def test_a_long_straight_segment_is_not_judged_by_one_point():
    # Half of this segment is on BASE, and its midpoint alone would call all of it shared.
    candidate = FakeRoute([[-100, 40], [-98, 40]], [170_000.0])
    assert overlap_fraction(candidate, [BASE]) == pytest.approx(0.5, abs=0.02)


def test_overlap_counts_all_existing_routes():
    candidate = join(line(40, -100, -99.5), line(41, -99.5, -99))
    west_half = line(40, -100, -99.5)
    east_half = line(41, -99.5, -99)
    assert overlap_fraction(candidate, [west_half]) < overlap_fraction(candidate, [west_half, east_half])


def test_zero_length_candidate_is_not_distinct():
    assert overlap_fraction(FakeRoute([[-100, 40], [-100, 40]], [0.0]), [BASE]) == 1


def review(route, fastest_s=3600.0):
    return accept_candidate(Candidate('test', route), [BASE], fastest_s)


@pytest.mark.parametrize('ratio, accepted', [(1.0, True), (1.25, True), (1.26, False)])
def test_time_limit(ratio, accepted):
    assert review(line(41, -100, -99, duration_s=3600 * ratio)).accepted is accepted


@pytest.mark.parametrize('share, accepted', [(0.70, True), (0.75, True), (0.80, False)])
def test_overlap_limit(share, accepted):
    assert review(with_overlap(share)).accepted is accepted


def test_review_reports_the_numbers():
    result = review(line(41, -100, -99, duration_s=4320))
    assert result.duration_ratio == pytest.approx(1.2)
    assert result.overlap == 0
    assert result.reason == 'accepted'


def test_review_names_the_failed_check():
    assert 'time' in review(line(41, -100, -99, duration_s=7200)).reason
    assert 'overlap' in review(BASE).reason


def picked(*routes, existing=(BASE,)):
    candidates = [Candidate(f'c{index}', route) for index, route in enumerate(routes)]
    chosen, _ = select_extra_routes(candidates, list(existing))
    return [candidate.label for candidate in chosen]


def test_picks_the_lowest_overlap_not_the_fastest():
    slower_distinct = with_overlap(0.2, duration_s=4000)
    faster_similar = with_overlap(0.7, duration_s=3600)
    assert picked(faster_similar, slower_distinct, existing=(BASE, BASE)) == ['c1']


def test_rejected_candidates_are_never_picked():
    assert picked(BASE, line(41, -100, -99, duration_s=9000), existing=(BASE, BASE)) == []


def test_tie_keeps_the_first_candidate():
    assert picked(FAR_AWAY, line(42, -100, -99), existing=(BASE, BASE)) == ['c0']


def test_nothing_is_added_when_three_routes_exist():
    assert picked(FAR_AWAY, existing=(BASE, BASE, BASE)) == []


def test_two_are_added_when_mapbox_gives_one():
    assert picked(FAR_AWAY, line(42, -100, -99)) == ['c0', 'c1']


def test_a_second_pick_must_also_differ_from_the_first_pick():
    assert picked(FAR_AWAY, line(41, -100, -99)) == ['c0']


def test_every_candidate_gets_a_review():
    candidates = [Candidate('good', FAR_AWAY), Candidate('bad', BASE)]
    _, reviews = select_extra_routes(candidates, [BASE, BASE])
    assert [(item.candidate.label, item.accepted) for item in reviews] == [('good', True), ('bad', False)]


def test_fastest_time_comes_from_the_existing_routes():
    slow_base = line(40, -100, -99, duration_s=7200)
    fast_base = line(40, -100, -99, duration_s=3600)
    candidate = line(41, -100, -99, duration_s=7200)
    assert picked(candidate, existing=(slow_base, fast_base)) == []


@pytest.mark.parametrize('count, note', [
    (3, None),
    (2, 'Only 2 distinct routes found'),
    (1, 'Only 1 distinct route found'),
])
def test_route_count_note(count, note):
    assert route_count_note(count) == note


WEST = {'lat': 40.0, 'lon': -100.0}
EAST = {'lat': 40.0, 'lon': -90.0}    # about 530 mi: offsets of about 53 and 79 mi from (40, -95)
NORTH_NEAR = Hub('north near', 40.8, -95.0)
SOUTH_NEAR = Hub('south near', 39.2, -95.0)
NORTH_FAR = Hub('north far', 41.15, -95.0)
SOUTH_FAR = Hub('south far', 38.85, -95.0)


def test_up_to_four_hubs_left_and_right_at_both_offsets():
    hubs = [SOUTH_FAR, NORTH_NEAR, SOUTH_NEAR, NORTH_FAR]
    assert set(select_hubs(WEST, EAST, hubs)) == set(hubs)


def test_a_hub_is_used_once():
    assert select_hubs(WEST, EAST, [NORTH_NEAR]) == [NORTH_NEAR]


def test_hubs_near_either_end_are_skipped():
    near_origin = Hub('near origin', 40.3, -100.0)
    near_destination = Hub('near destination', 40.0, -90.5)
    assert select_hubs(WEST, EAST, [near_origin, near_destination]) == []


def test_a_hub_just_past_the_limit_is_kept():
    hub = Hub('just past', 40.0, -99.0)    # about 53 mi from the origin
    assert select_hubs(WEST, EAST, [hub]) == [hub]


def test_short_trips_skip_hubs():
    assert select_hubs(WEST, {'lat': 40.0, 'lon': -98.5}, [NORTH_NEAR]) == []


@pytest.mark.parametrize('origin, destination, expected', [
    ((32.7813, -96.7998), (41.8820, -87.6324), 'Kansas City, MO'),
    ((39.7417, -104.9861), (40.7628, -111.8898), 'Rock Springs, WY'),
    ((39.0985, -94.5786), (39.7417, -104.9861), 'North Platte, NE'),
])
def test_real_hub_list_finds_the_hub_each_test_trip_needs(origin, destination, expected):
    start = {'lat': origin[0], 'lon': origin[1]}
    end = {'lat': destination[0], 'lon': destination[1]}
    assert expected in [hub.name for hub in select_hubs(start, end, HUBS)]


def test_hub_list_size():
    assert 30 <= len(HUBS) <= 50
