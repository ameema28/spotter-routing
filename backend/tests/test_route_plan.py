"""The pipeline on saved fixtures: no live calls."""
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from routing.domain.alternatives import Candidate
from routing.domain.geometry import GRID_STEPS
from routing.services import route_plan
from routing.services.errors import PlaceNotFound, ProviderBusy
from routing.services.mapbox import Route
from routing.services.openmeteo import _parse_location

FIXTURES = Path(__file__).parent / 'fixtures'
# Six level totals, each rounded to 0.1 mi, can drift from the route distance by up to 0.3 mi.
MILES_TOLERANCE = 0.3
DEPARTURE = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
DALLAS = {'lat': 32.7813, 'lon': -96.7998, 'label': 'Dallas, Texas, United States'}
CHICAGO = {'lat': 41.8820, 'lon': -87.6324, 'label': 'Chicago, Illinois, United States'}


def fixture_routes():
    body = json.loads((FIXTURES / 'mapbox_directions_dallas_chicago.json').read_text(encoding='utf-8'))
    return [Route(
        coords_lonlat=raw['geometry']['coordinates'],
        seg_distances_m=raw['legs'][0]['annotation']['distance'],
        seg_durations_s=raw['legs'][0]['annotation']['duration'],
        distance_m=raw['distance'],
        duration_s=raw['duration'],
    ) for raw in body['routes']]


def far_copy(route):
    """A distinct third route: the same shape, away from the other two."""
    return Route([[lon + 3, lat] for lon, lat in route.coords_lonlat], route.seg_distances_m,
                 route.seg_durations_s, route.distance_m, route.duration_s * 1.1)


FORECAST = _parse_location(json.loads((FIXTURES / 'openmeteo_5pts.json').read_text(encoding='utf-8'))[0])


@pytest.fixture
def providers(monkeypatch):
    """Patch every external call. Returns a dict the tests can adjust."""
    state = {'late': 0, 'candidates': None, 'optional_fails': False, 'requests': []}

    def fake_geocode(query):
        return DALLAS if 'Dallas' in query else CHICAGO

    def fake_generate(origin, destination):
        routes = fixture_routes()
        if state['candidates'] is None:
            candidates = [Candidate('generated alternative (via Memphis)', far_copy(routes[0]))]
        else:
            candidates = state['candidates']
        return routes, candidates, state['late']

    def fake_fetch(required, optional, forecast_days):
        state['requests'].append((len(required), len(optional), forecast_days))
        return [FORECAST] * len(required), None if state['optional_fails'] else [FORECAST] * len(optional)

    monkeypatch.setattr(route_plan.mapbox, 'geocode', fake_geocode)
    monkeypatch.setattr(route_plan, 'generate_candidates', fake_generate)
    monkeypatch.setattr(route_plan, 'fetch_many', fake_fetch)
    return state


def build(step_miles=25, load_lb=40_000):
    return route_plan.build_route_plan('Dallas, TX', 'Chicago, IL', DEPARTURE, load_lb, step_miles)


def test_resolves_both_places(providers):
    plan = build()
    assert plan['origin'] == DALLAS
    assert plan['destination'] == CHICAGO


def test_three_routes_ranked_with_a_recommendation(providers):
    plan = build()
    assert len(plan['routes']) == 3
    assert sorted(plan['ranking']) == [0, 1, 2]
    assert plan['recommendation']['route_id'] == plan['ranking'][0]
    assert plan['recommendation']['reason']


def test_route_sources_and_labels(providers):
    routes = build()['routes']
    assert [route['source'] for route in routes] == ['mapbox', 'mapbox', 'generated']
    assert routes[2]['label'] == 'generated alternative (via Memphis)'
    assert routes[0]['label'] != routes[1]['label']


def test_route_fields(providers):
    route = build()['routes'][0]
    assert route['distance_mi'] == pytest.approx(968.7, abs=0.1)
    assert route['drive_seconds'] == pytest.approx(55_980, abs=60)
    assert route['drive_time'] == '15 h 33 min'
    assert route['trip_time'] == '26 h 3 min'
    assert [stop['type'] for stop in route['breaks']] == ['break', 'rest']
    assert route['breaks'][0]['start'].endswith('+00:00')


def test_display_geometry_is_simplified_lat_lon(providers):
    route = build()['routes'][0]
    assert 2 <= len(route['geometry']) <= 800
    lat, lon = route['geometry'][0]
    assert lat == pytest.approx(32.78, abs=0.1)
    assert lon == pytest.approx(-96.8, abs=0.1)


def test_summary_fields(providers):
    summary = build()['routes'][0]['summary']
    assert set(summary) == {'severe_miles', 'high_miles', 'no_travel_miles', 'unknown_miles',
                            'avg_risk', 'tier', 'flags', 'miles_by_level'}


def test_miles_by_level_sums_to_the_route_distance(providers):
    for route in build()['routes']:
        by_level = route['summary']['miles_by_level']
        assert list(by_level) == ['low', 'moderate', 'high', 'severe', 'no_travel', 'unknown']
        assert by_level['severe'] == route['summary']['severe_miles']
        assert by_level['unknown'] == route['summary']['unknown_miles']
        assert sum(by_level.values()) == pytest.approx(route['distance_mi'], abs=MILES_TOLERANCE)


@pytest.mark.parametrize('missing, field', [('Dallas', 'origin'), ('Chicago', 'destination')])
def test_place_not_found_says_which_place(providers, monkeypatch, missing, field):
    def fake_geocode(query):
        if missing in query:
            raise PlaceNotFound('No US location found for that place')
        return DALLAS if 'Dallas' in query else CHICAGO

    monkeypatch.setattr(route_plan.mapbox, 'geocode', fake_geocode)
    with pytest.raises(PlaceNotFound) as caught:
        build()
    assert caught.value.field == field


def test_checkpoint_fields_are_json_ready(providers):
    plan = build()
    checkpoint = plan['routes'][0]['checkpoints'][1]
    assert set(checkpoint) == {'mile', 'lat', 'lon', 'eta', 'level', 'driver', 'wind', 'gust',
                               'rain', 'snow', 'precip_hour', 'wind_hour'}
    json.dumps(plan)


def test_step_changes_the_checkpoints(providers):
    fine = len(build(step_miles=10)['routes'][0]['checkpoints'])
    coarse = len(build(step_miles=50)['routes'][0]['checkpoints'])
    assert fine > coarse


def test_heatmap_shape(providers):
    heatmap = build()['heatmap']
    assert heatmap['start'] == DEPARTURE.isoformat()
    assert len(heatmap['hours']) == 49
    assert 0 < len(heatmap['points']) <= 250
    assert len(heatmap['levels']) == len(heatmap['points'])
    assert all(len(row) == 49 for row in heatmap['levels'])
    assert tuple(heatmap['step_deg']) in GRID_STEPS


def test_failed_heatmap_keeps_the_answer_and_adds_a_note(providers):
    providers['optional_fails'] = True
    plan = build()
    assert plan['heatmap'] is None
    assert plan['recommendation']['route_id'] is not None
    assert 'Heatmap unavailable: weather service is busy' in plan['notes']


def test_weather_is_fetched_once_with_the_fixed_range(providers):
    build()
    assert len(providers['requests']) == 1
    assert providers['requests'][0][2] == route_plan.FORECAST_DAYS == 11


def test_required_weather_failure_propagates(providers, monkeypatch):
    def busy(required, optional, forecast_days):
        raise ProviderBusy('Weather service is busy — please try again in a minute')

    monkeypatch.setattr(route_plan, 'fetch_many', busy)
    with pytest.raises(ProviderBusy):
        build()


def test_note_when_no_third_route_qualifies(providers):
    providers['candidates'] = []
    plan = build()
    assert len(plan['routes']) == 2
    assert 'Only 2 distinct routes found' in plan['notes']


def test_note_when_candidates_arrive_late(providers):
    providers['late'] = 2
    assert '2 route candidates were too slow and were skipped' in build()['notes']


def test_no_notes_on_a_clean_run(providers):
    assert build()['notes'] == []


def windy(mph):
    return replace(FORECAST, wind_mph=[mph] * len(FORECAST.times))


def test_each_route_gets_its_own_slice_of_the_weather(providers, monkeypatch):
    # Every checkpoint gets a different wind, so a misaligned slice shows up in the numbers.
    def by_position(required, optional, forecast_days):
        return [windy(float(index % 20)) for index in range(len(required))], None

    monkeypatch.setattr(route_plan, 'fetch_many', by_position)
    routes = build()['routes']
    first_count = len(routes[0]['checkpoints'])
    assert routes[0]['checkpoints'][3]['wind'] == 3
    assert routes[1]['checkpoints'][0]['wind'] == first_count % 20
    assert routes[1]['checkpoints'][3]['wind'] == (first_count + 3) % 20


def test_worst_weather_on_the_first_route_ranks_it_last(providers, monkeypatch):
    def storm_on_first_route(required, optional, forecast_days):
        # Fixture route 0 has 40 checkpoints at step 25.
        return [windy(47.0 if index < 40 else 5.0) for index in range(len(required))], None

    monkeypatch.setattr(route_plan, 'fetch_many', storm_on_first_route)
    plan = build(load_lb=20_000)
    assert plan['routes'][0]['summary']['severe_miles'] > 0
    assert plan['ranking'][-1] == 0
    assert plan['recommendation']['route_id'] != 0


def test_ranking_uses_trip_time_with_stops(providers):
    route = build()['routes'][0]
    assert route['trip_seconds'] > route['drive_seconds'] + 10 * 3600


def test_timings_are_reported(providers):
    assert set(build()['timings_ms']) == {'geocode', 'routing', 'weather', 'compute'}
