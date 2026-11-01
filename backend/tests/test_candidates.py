import threading
import time

import pytest

from routing.domain.hubs import Hub
from routing.services import candidates as candidates_module
from routing.services.candidates import generate_candidates
from routing.services.errors import ProviderError
from routing.services.mapbox import Route

ORIGIN = {'lat': 40.0, 'lon': -100.0}
DESTINATION = {'lat': 40.0, 'lon': -90.0}
NEARBY_DESTINATION = {'lat': 40.0, 'lon': -98.5}
HUB_A = Hub('Alpha, TX', 40.8, -95.0)
HUB_B = Hub('Beta, OK', 39.2, -95.0)


def route(name):
    return Route(coords_lonlat=[[0, 0], [1, 0]], seg_distances_m=[1.0], seg_durations_s=[1.0],
                 distance_m=1.0, duration_s=float(name))


@pytest.fixture(autouse=True)
def only_two_hubs(monkeypatch):
    monkeypatch.setattr(candidates_module, 'HUBS', (HUB_A, HUB_B))


@pytest.fixture
def directions(monkeypatch):
    """Fake mapbox.directions: main gives 2 routes, tolls 1, each via 2. Records each call."""
    calls = []

    def fake(origin, destination, via=None, exclude=None):
        calls.append({'via': via, 'exclude': exclude})
        if exclude:
            return [route(30)]
        if via:
            return [route(via['lat']), route(via['lat'] + 1)]
        return [route(10), route(20)]

    monkeypatch.setattr(candidates_module.mapbox, 'directions', fake)
    return calls


def test_returns_the_main_routes_and_every_candidate(directions):
    main_routes, candidates, late = generate_candidates(ORIGIN, DESTINATION)
    assert late == 0
    assert [item.duration_s for item in main_routes] == [10, 20]
    assert [(item.label, item.route.duration_s) for item in candidates] == [
        ('generated alternative (avoids tolls)', 30),
        ('generated alternative (via Alpha)', 40.8),
        ('generated alternative (via Alpha)', 41.8),
        ('generated alternative (via Beta)', 39.2),
        ('generated alternative (via Beta)', 40.2),
    ]


def test_makes_one_main_one_toll_and_one_call_per_hub(directions):
    generate_candidates(ORIGIN, DESTINATION)
    assert len(directions) == 4
    assert sum(1 for call in directions if call['exclude'] == 'toll') == 1
    assert sum(1 for call in directions if call['via']) == 2


def test_via_uses_stored_hub_coordinates(directions):
    generate_candidates(ORIGIN, DESTINATION)
    vias = [call['via'] for call in directions if call['via']]
    assert {'lat': 40.8, 'lon': -95.0} in vias


def test_short_trip_tries_avoiding_tolls_only(directions):
    _, candidates, _ = generate_candidates(ORIGIN, NEARBY_DESTINATION)
    assert len(directions) == 2
    assert [item.label for item in candidates] == ['generated alternative (avoids tolls)']


def test_all_calls_run_at_the_same_time(monkeypatch):
    # Each call waits for the other three, so calling them in turn would break the barrier.
    barrier = threading.Barrier(4, timeout=5)

    def fake(origin, destination, via=None, exclude=None):
        barrier.wait()
        return [route(1)]

    monkeypatch.setattr(candidates_module.mapbox, 'directions', fake)
    main_routes, candidates, _ = generate_candidates(ORIGIN, DESTINATION)
    assert len(main_routes) == 1
    assert len(candidates) == 3


def test_a_failed_main_call_is_an_error(monkeypatch):
    def fake(origin, destination, via=None, exclude=None):
        if via or exclude:
            return [route(1)]
        raise ProviderError('Mapbox returned HTTP 500')

    monkeypatch.setattr(candidates_module.mapbox, 'directions', fake)
    with pytest.raises(ProviderError, match='HTTP 500'):
        generate_candidates(ORIGIN, DESTINATION)


def test_a_failed_toll_candidate_is_skipped(monkeypatch):
    def fake(origin, destination, via=None, exclude=None):
        if exclude:
            raise ProviderError('Mapbox found no route (NoRoute)')
        return [route(1)]

    monkeypatch.setattr(candidates_module.mapbox, 'directions', fake)
    _, candidates, _ = generate_candidates(ORIGIN, DESTINATION)
    assert [item.label for item in candidates] == [
        'generated alternative (via Alpha)', 'generated alternative (via Beta)',
    ]


def test_a_failed_hub_candidate_is_skipped(monkeypatch):
    def fake(origin, destination, via=None, exclude=None):
        if via and via['lat'] == HUB_A.lat:
            raise ProviderError('Mapbox request failed (Timeout)')
        return [route(1)]

    monkeypatch.setattr(candidates_module.mapbox, 'directions', fake)
    _, candidates, _ = generate_candidates(ORIGIN, DESTINATION)
    assert 'generated alternative (via Alpha)' not in [item.label for item in candidates]
    assert len(candidates) == 2


def test_all_candidates_failing_still_returns_the_main_routes(monkeypatch):
    def fake(origin, destination, via=None, exclude=None):
        if via or exclude:
            raise ProviderError('Mapbox returned HTTP 429')
        return [route(1)]

    monkeypatch.setattr(candidates_module.mapbox, 'directions', fake)
    main_routes, candidates, _ = generate_candidates(ORIGIN, DESTINATION)
    assert len(main_routes) == 1
    assert candidates == []


def test_late_candidates_are_dropped_and_counted(monkeypatch):
    monkeypatch.setattr(candidates_module, 'CANDIDATE_DEADLINE_SECONDS', 0.05)
    release = threading.Event()

    def fake(origin, destination, via=None, exclude=None):
        if via:
            release.wait(5)
        return [route(1)]

    monkeypatch.setattr(candidates_module.mapbox, 'directions', fake)
    started = time.perf_counter()
    main_routes, candidates, late = generate_candidates(ORIGIN, DESTINATION)
    elapsed = time.perf_counter() - started
    release.set()

    assert elapsed < 2    # the search does not wait for the slow calls to finish
    assert len(main_routes) == 1
    assert [item.label for item in candidates] == ['generated alternative (avoids tolls)']
    assert late == 2


def test_the_deadline_starts_after_the_main_call(monkeypatch):
    monkeypatch.setattr(candidates_module, 'CANDIDATE_DEADLINE_SECONDS', 0.2)

    def fake(origin, destination, via=None, exclude=None):
        if via or exclude:
            time.sleep(0.3)
        else:
            time.sleep(0.2)
        return [route(1)]

    monkeypatch.setattr(candidates_module.mapbox, 'directions', fake)
    _, candidates, late = generate_candidates(ORIGIN, DESTINATION)
    assert late == 0
    assert len(candidates) == 3
