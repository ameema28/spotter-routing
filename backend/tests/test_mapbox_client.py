import json
import traceback
from pathlib import Path

import pytest
import requests

from routing.services import mapbox
from routing.services.errors import PlaceNotFound, ProviderError, ProviderTimeout, RouteNotFound

FAKE_TOKEN = 'pk.fake-token-for-tests'
FIXTURE = Path(__file__).parent / 'fixtures' / 'mapbox_directions_dallas_chicago.json'
DALLAS = {'lat': 32.7813, 'lon': -96.7998}
CHICAGO = {'lat': 41.8820, 'lon': -87.6324}
ST_LOUIS = {'lat': 38.6270, 'lon': -90.1994}

GEOCODE_BODY = {'features': [{
    'geometry': {'coordinates': [-96.7998, 32.7813]},
    'properties': {'full_address': 'Dallas, Texas, United States'},
}]}

# Shaped like the real via response: the join repeats a vertex, giving a zero-length segment.
TWO_LEG_BODY = {'code': 'Ok', 'routes': [{
    'distance': 300.0,
    'duration': 30.0,
    'geometry': {'coordinates': [[0, 0], [1, 0], [1, 0], [2, 0]]},
    'legs': [
        {'annotation': {'distance': [100.0, 0.0], 'duration': [10.0, 0.0]}},
        {'annotation': {'distance': [200.0], 'duration': [20.0]}},
    ],
}]}


class FakeResponse:
    def __init__(self, body=None, status_code=200):
        self.body = body
        self.status_code = status_code

    def json(self):
        if self.body is None:
            raise ValueError('not JSON')
        return self.body


@pytest.fixture(autouse=True)
def fake_token(settings):
    settings.MAPBOX_TOKEN = FAKE_TOKEN


@pytest.fixture
def respond_with(monkeypatch):
    """Patch requests.get to return a response, and record each call."""
    def install(response):
        calls = []

        def fake_get(url, params=None, timeout=None):
            calls.append({'url': url, 'params': params, 'timeout': timeout})
            return response

        monkeypatch.setattr(mapbox.requests, 'get', fake_get)
        return calls
    return install


def assert_safe(error):
    text = ' '.join([str(error), repr(error), *traceback.format_exception(error)])
    assert FAKE_TOKEN not in text
    assert 'api.mapbox.com' not in text
    assert 'access_token' not in text


def test_geocode_returns_lat_lon_and_label(respond_with):
    respond_with(FakeResponse(GEOCODE_BODY))
    assert mapbox.geocode('Dallas, TX') == {
        'lat': 32.7813, 'lon': -96.7998, 'label': 'Dallas, Texas, United States',
    }


def test_geocode_is_us_only_and_uses_the_timeout(respond_with):
    calls = respond_with(FakeResponse(GEOCODE_BODY))
    mapbox.geocode('Dallas, TX')
    assert calls[0]['params']['q'] == 'Dallas, TX'
    assert calls[0]['params']['country'] == 'us'
    assert calls[0]['timeout'] == 15


def test_geocode_is_not_cached(respond_with):
    calls = respond_with(FakeResponse(GEOCODE_BODY))
    mapbox.geocode('Dallas, TX')
    mapbox.geocode('Dallas, TX')
    assert len(calls) == 2


def test_geocode_without_a_match_is_place_not_found(respond_with):
    respond_with(FakeResponse({'features': []}))
    with pytest.raises(PlaceNotFound) as caught:
        mapbox.geocode('Nowhere')
    assert_safe(caught.value)


def test_directions_parses_the_real_fixture_into_routes(respond_with):
    body = json.loads(FIXTURE.read_text(encoding='utf-8'))
    respond_with(FakeResponse(body))

    routes = mapbox.directions(DALLAS, CHICAGO)

    assert len(routes) == 2
    for route, raw in zip(routes, body['routes']):
        assert route.distance_m == raw['distance']
        assert route.duration_s == raw['duration']
        assert route.coords_lonlat == raw['geometry']['coordinates']
        assert route.seg_distances_m == raw['legs'][0]['annotation']['distance']
        assert route.seg_durations_s == raw['legs'][0]['annotation']['duration']


def test_directions_sends_the_parameters_proven_in_the_spike(respond_with):
    calls = respond_with(FakeResponse(TWO_LEG_BODY))
    mapbox.directions(DALLAS, CHICAGO)
    assert '/mapbox/driving/-96.79980,32.78130;-87.63240,41.88200' in calls[0]['url']
    assert calls[0]['params'] == {
        'alternatives': 'true', 'geometries': 'geojson', 'overview': 'full',
        'annotations': 'distance,duration', 'access_token': FAKE_TOKEN,
    }
    assert calls[0]['timeout'] == 15


def test_directions_puts_via_between_origin_and_destination(respond_with):
    calls = respond_with(FakeResponse(TWO_LEG_BODY))
    mapbox.directions(DALLAS, CHICAGO, via=ST_LOUIS)
    assert '-96.79980,32.78130;-90.19940,38.62700;-87.63240,41.88200' in calls[0]['url']


def test_directions_passes_exclude(respond_with):
    calls = respond_with(FakeResponse(TWO_LEG_BODY))
    mapbox.directions(DALLAS, CHICAGO, exclude='toll')
    assert calls[0]['params']['exclude'] == 'toll'


def test_directions_joins_annotations_across_legs(respond_with):
    respond_with(FakeResponse(TWO_LEG_BODY))
    route = mapbox.directions(DALLAS, CHICAGO, via=ST_LOUIS)[0]
    assert route.seg_distances_m == [100.0, 0.0, 200.0]
    assert route.seg_durations_s == [10.0, 0.0, 20.0]
    assert len(route.seg_distances_m) == len(route.coords_lonlat) - 1


def test_annotations_that_do_not_fit_the_geometry_are_rejected(respond_with):
    body = json.loads(json.dumps(TWO_LEG_BODY))
    body['routes'][0]['geometry']['coordinates'].pop()
    respond_with(FakeResponse(body))
    with pytest.raises(ProviderError):
        mapbox.directions(DALLAS, CHICAGO)


@pytest.mark.parametrize('response', [
    FakeResponse({'code': 'NoRoute', 'routes': []}),
    FakeResponse({'code': 'Ok', 'routes': []}),
    FakeResponse({'code': 'Ok', 'routes': [{'distance': 1.0}]}),
    FakeResponse(None),
    FakeResponse({'message': 'Not Authorized - Invalid Token'}, status_code=401),
    FakeResponse({'message': 'Too Many Requests'}, status_code=429),
    FakeResponse({'message': 'Server error'}, status_code=500),
], ids=['no_route', 'empty', 'malformed', 'not_json', '401', '429', '500'])
def test_bad_responses_are_safe_provider_errors(respond_with, response):
    respond_with(response)
    with pytest.raises(ProviderError) as caught:
        mapbox.directions(DALLAS, CHICAGO)
    assert_safe(caught.value)


def test_no_route_is_its_own_error(respond_with):
    respond_with(FakeResponse({'code': 'NoRoute', 'routes': []}))
    with pytest.raises(RouteNotFound) as caught:
        mapbox.directions(DALLAS, CHICAGO)
    assert_safe(caught.value)


def test_a_timeout_is_its_own_safe_error(monkeypatch):
    def fail(url, params=None, timeout=None):
        raise requests.Timeout(f'timed out: https://api.mapbox.com/x?access_token={FAKE_TOKEN}')

    monkeypatch.setattr(mapbox.requests, 'get', fail)
    with pytest.raises(ProviderTimeout) as caught:
        mapbox.directions(DALLAS, CHICAGO)
    assert_safe(caught.value)


def test_a_failed_status_is_rejected_even_with_a_usable_body(respond_with):
    respond_with(FakeResponse(TWO_LEG_BODY, status_code=429))
    with pytest.raises(ProviderError, match='HTTP 429'):
        mapbox.directions(DALLAS, CHICAGO)


def test_a_failed_code_is_rejected_even_with_routes(respond_with):
    respond_with(FakeResponse({**TWO_LEG_BODY, 'code': 'InvalidInput'}))
    with pytest.raises(ProviderError, match='InvalidInput'):
        mapbox.directions(DALLAS, CHICAGO)


@pytest.mark.parametrize('exception', [requests.ConnectionError, requests.Timeout])
@pytest.mark.parametrize('call', [
    lambda: mapbox.geocode('Dallas, TX'),
    lambda: mapbox.directions(DALLAS, CHICAGO),
], ids=['geocode', 'directions'])
def test_network_errors_never_carry_the_url_or_token(monkeypatch, exception, call):
    def fail(url, params=None, timeout=None):
        # requests puts the full URL, token included, in its exception text.
        raise exception(f'failed: https://api.mapbox.com/x?access_token={FAKE_TOKEN}')

    monkeypatch.setattr(mapbox.requests, 'get', fail)
    with pytest.raises(ProviderError) as caught:
        call()
    assert_safe(caught.value)
    # Chained exceptions outlive tracebacks: debug pages and loggers can walk these attributes.
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_missing_token_is_a_provider_error_and_sends_nothing(respond_with, settings):
    settings.MAPBOX_TOKEN = ''
    calls = respond_with(FakeResponse(GEOCODE_BODY))
    with pytest.raises(ProviderError):
        mapbox.geocode('Dallas, TX')
    assert calls == []
