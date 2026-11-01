import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from django.conf import settings
from django.core.cache import cache

from routing.services import openmeteo
from routing.services.errors import ProviderBusy, ProviderError, ProviderTimeout

FIXTURE = Path(__file__).parent / 'fixtures' / 'openmeteo_5pts.json'
LOCATIONS = json.loads(FIXTURE.read_text(encoding='utf-8'))


class FakeResponse:
    def __init__(self, body=None, status_code=200, headers=None):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        if self.body is None:
            raise ValueError('not JSON')
        return self.body


def point(lat, lon=-96.0):
    return {'lat': lat, 'lon': lon}


def spaced_points(count):
    """Points in separate cells, so none merge."""
    return [point(30 + index * openmeteo.CELL_DEGREES) for index in range(count)]


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()


@pytest.fixture
def api(monkeypatch):
    """Answer every batch like Open-Meteo, and record the coordinates requested."""
    calls = []

    def fake_get(url, params=None, timeout=None):
        latitudes = params['latitude'].split(',')
        calls.append({'url': url, 'params': params, 'timeout': timeout, 'count': len(latitudes)})
        # A single location comes back as a bare object, not a one-item list (proven live).
        return FakeResponse(LOCATIONS[0] if len(latitudes) == 1 else [LOCATIONS[0]] * len(latitudes))

    monkeypatch.setattr(openmeteo.requests, 'get', fake_get)
    return calls


def test_parses_a_saved_response_into_hourly_data(monkeypatch):
    body = LOCATIONS[:5]
    monkeypatch.setattr(openmeteo.requests, 'get', lambda *args, **kwargs: FakeResponse(body))

    forecasts = openmeteo.fetch_hourly(spaced_points(5), 7)

    assert len(forecasts) == 5
    for forecast, location in zip(forecasts, body):
        hourly = location['hourly']
        assert len(forecast.times) == len(hourly['time'])
        assert forecast.wind_mph == hourly['wind_speed_10m']
        assert forecast.gust_mph == hourly['wind_gusts_10m']
        assert forecast.snow_in_hr == hourly['snowfall']


def test_times_are_utc_datetimes(api):
    forecast = openmeteo.fetch_hourly([point(32)], 7)[0]
    first = LOCATIONS[0]['hourly']['time'][0]
    assert forecast.times[0] == datetime.fromisoformat(first).replace(tzinfo=timezone.utc)
    assert forecast.times[0].tzinfo == timezone.utc


def test_rain_is_rain_plus_showers(monkeypatch):
    body = json.loads(json.dumps(LOCATIONS[0]))
    hourly = body['hourly']
    hourly['rain'][:3] = [0.1, 0.0, 0.2]
    hourly['showers'][:3] = [0.05, 0.3, 0.0]
    monkeypatch.setattr(openmeteo.requests, 'get', lambda *args, **kwargs: FakeResponse(body))

    forecast = openmeteo.fetch_hourly([point(32)], 7)[0]

    assert forecast.rain_in_hr[:3] == pytest.approx([0.15, 0.3, 0.2])


def test_rain_with_a_missing_part_is_unknown_not_zero(monkeypatch):
    body = json.loads(json.dumps(LOCATIONS[0]))
    body['hourly']['rain'][0] = None
    body['hourly']['showers'][1] = None
    monkeypatch.setattr(openmeteo.requests, 'get', lambda *args, **kwargs: FakeResponse(body))

    forecast = openmeteo.fetch_hourly([point(32)], 7)[0]

    assert forecast.rain_in_hr[:2] == [None, None]


def test_request_uses_the_spike_parameters(api):
    openmeteo.fetch_hourly(spaced_points(2), 7)
    params = api[0]['params']
    assert params['hourly'] == 'wind_speed_10m,wind_gusts_10m,rain,showers,snowfall'
    assert params['wind_speed_unit'] == 'mph'
    assert params['precipitation_unit'] == 'inch'
    assert params['timezone'] == 'GMT'
    assert params['forecast_days'] == 7
    assert api[0]['timeout'] == 15


def test_230_points_split_into_100_100_30(api):
    forecasts = openmeteo.fetch_hourly(spaced_points(230), 7)
    assert sorted(call['count'] for call in api) == [30, 100, 100]
    assert len(forecasts) == 230


def test_single_location_response_is_handled(api):
    assert len(openmeteo.fetch_hourly([point(32)], 7)) == 1


@pytest.mark.parametrize('value, expected', [
    (32.781, 32.78),
    (32.789, 32.78),    # nearest multiple of 0.02, not nearest 0.01
    (32.791, 32.8),
    (-96.799, -96.8),
])
def test_snaps_to_the_nearest_d6_cell(api, value, expected):
    openmeteo.fetch_hourly([point(value, value)], 7)
    assert float(api[0]['params']['latitude']) == expected
    assert float(api[0]['params']['longitude']) == expected


def test_two_points_in_the_same_cell_make_one_request_point(api):
    forecasts = openmeteo.fetch_hourly([point(32.781), point(32.785)], 7)
    assert [call['count'] for call in api] == [1]
    assert forecasts[0] == forecasts[1]


def test_points_in_different_cells_stay_separate(api):
    openmeteo.fetch_hourly([point(32.78), point(32.80)], 7)
    assert api[0]['count'] == 2


def test_results_keep_the_input_order_when_cells_repeat(monkeypatch):
    def by_latitude(url, params=None, timeout=None):
        locations = []
        for latitude in params['latitude'].split(','):
            location = json.loads(json.dumps(LOCATIONS[0]))
            location['hourly']['wind_speed_10m'][0] = float(latitude)
            locations.append(location)
        return FakeResponse(locations)

    monkeypatch.setattr(openmeteo.requests, 'get', by_latitude)
    forecasts = openmeteo.fetch_hourly([point(33), point(32), point(33), point(34)], 7)
    assert [forecast.wind_mph[0] for forecast in forecasts] == [33, 32, 33, 34]


def test_a_cache_hit_avoids_a_second_http_call(api):
    first = openmeteo.fetch_hourly([point(32), point(33)], 7)
    second = openmeteo.fetch_hourly([point(32), point(33)], 7)
    assert len(api) == 1
    assert first == second


def test_only_cache_misses_are_requested(api):
    openmeteo.fetch_hourly([point(32)], 7)
    openmeteo.fetch_hourly([point(32), point(33)], 7)
    assert [call['count'] for call in api] == [1, 1]
    assert float(api[1]['params']['latitude']) == 33


def test_a_different_forecast_length_is_a_different_cache_entry(api):
    openmeteo.fetch_hourly([point(32)], 7)
    openmeteo.fetch_hourly([point(32)], 3)
    assert len(api) == 2


def test_entries_use_the_30_minute_ttl(api, monkeypatch):
    seen = {}

    def spy(data, timeout=None):
        seen['timeout'] = timeout
        return []

    monkeypatch.setattr(openmeteo, 'cache', SimpleNamespace(get_many=cache.get_many, set_many=spy))
    openmeteo.fetch_hourly([point(32)], 7)
    assert seen['timeout'] == 30 * 60


def test_the_cache_holds_more_than_a_large_comparison(api):
    # LocMemCache's default of 300 entries would evict a 10-mile comparison while it runs.
    count = 400
    openmeteo.fetch_hourly(spaced_points(count), 7)
    calls_after_first_run = len(api)
    openmeteo.fetch_hourly(spaced_points(count), 7)
    assert len(api) == calls_after_first_run
    assert settings.CACHES['default']['OPTIONS']['MAX_ENTRIES'] >= count


def test_batches_that_succeeded_stay_cached_after_a_later_failure(monkeypatch):
    attempts = []

    def fail_the_small_batch(url, params=None, timeout=None):
        count = len(params['latitude'].split(','))
        if count == 50:
            return FakeResponse({'error': True}, status_code=500)
        return FakeResponse([LOCATIONS[0]] * count)

    monkeypatch.setattr(openmeteo.requests, 'get', fail_the_small_batch)
    with pytest.raises(ProviderError):
        openmeteo.fetch_hourly(spaced_points(150), 7)

    monkeypatch.setattr(openmeteo.requests, 'get', lambda url, params=None, timeout=None: (
        attempts.append(params) or FakeResponse([LOCATIONS[0]] * len(params['latitude'].split(',')))
    ))
    openmeteo.fetch_hourly(spaced_points(150), 7)
    assert len(attempts[0]['latitude'].split(',')) == 50


def test_failed_results_are_not_cached(monkeypatch):
    monkeypatch.setattr(openmeteo.requests, 'get',
                        lambda *args, **kwargs: FakeResponse({'error': True}, status_code=500))
    with pytest.raises(ProviderError):
        openmeteo.fetch_hourly([point(32)], 7)

    monkeypatch.setattr(openmeteo.requests, 'get', lambda *args, **kwargs: FakeResponse(LOCATIONS[0]))
    assert len(openmeteo.fetch_hourly([point(32)], 7)) == 1


def test_no_points_makes_no_request(api):
    assert openmeteo.fetch_hourly([], 7) == []
    assert api == []


@pytest.mark.parametrize('response', [
    FakeResponse({'error': True, 'reason': 'Latitude must be in range'}, status_code=400),
    FakeResponse({'error': True}, status_code=429),
    FakeResponse(None),
    FakeResponse([{'hourly': {}}]),
    FakeResponse([LOCATIONS[0], LOCATIONS[0]]),    # wrong number of locations for one point
], ids=['400', '429', 'not_json', 'malformed', 'wrong_count'])
def test_bad_responses_are_safe_provider_errors(monkeypatch, response):
    monkeypatch.setattr(openmeteo.requests, 'get', lambda *args, **kwargs: response)
    with pytest.raises(ProviderError) as caught:
        openmeteo.fetch_hourly([point(32)], 7)
    assert 'api.open-meteo.com' not in str(caught.value)


def test_network_errors_do_not_chain_the_url(monkeypatch):
    def fail(url, params=None, timeout=None):
        raise requests.Timeout('timed out: https://api.open-meteo.com/v1/forecast?latitude=32')

    monkeypatch.setattr(openmeteo.requests, 'get', fail)
    with pytest.raises(ProviderError) as caught:
        openmeteo.fetch_hourly([point(32)], 7)
    assert 'api.open-meteo.com' not in str(caught.value)
    assert caught.value.__context__ is None


def test_a_timeout_is_its_own_error(monkeypatch):
    def fail(url, params=None, timeout=None):
        raise requests.Timeout('timed out')

    monkeypatch.setattr(openmeteo.requests, 'get', fail)
    with pytest.raises(ProviderTimeout):
        openmeteo.fetch_hourly([point(32)], 7)


def test_429_is_a_clear_busy_error_with_no_retry(monkeypatch):
    calls = []

    def limited(url, params=None, timeout=None):
        calls.append(params)
        return FakeResponse({'error': True, 'reason': 'Minutely API request limit exceeded'}, status_code=429)

    monkeypatch.setattr(openmeteo.requests, 'get', limited)
    with pytest.raises(ProviderBusy) as caught:
        openmeteo.fetch_hourly([point(32)], 7)
    assert str(caught.value) == 'Weather service is busy — please try again in a minute'
    assert caught.value.retry_after is None
    assert len(calls) == 1


def test_429_keeps_retry_after_when_sent(monkeypatch):
    monkeypatch.setattr(openmeteo.requests, 'get', lambda *args, **kwargs: FakeResponse(
        {'error': True}, status_code=429, headers={'Retry-After': '30'}))
    with pytest.raises(ProviderBusy) as caught:
        openmeteo.fetch_hourly([point(32)], 7)
    assert caught.value.retry_after == '30'


def test_batches_run_at_the_same_time(monkeypatch):
    # Each batch waits for the others, so fetching them in turn would break the barrier.
    barrier = threading.Barrier(3, timeout=5)

    def fake(url, params=None, timeout=None):
        barrier.wait()
        return FakeResponse([LOCATIONS[0]] * len(params['latitude'].split(',')))

    monkeypatch.setattr(openmeteo.requests, 'get', fake)
    assert len(openmeteo.fetch_hourly(spaced_points(250), 7)) == 250


def test_fetch_many_returns_each_group_in_input_order(api):
    required, optional = openmeteo.fetch_many([point(32)], [point(33), point(34)], 7)
    assert len(required) == 1
    assert len(optional) == 2


def test_a_cell_in_both_groups_is_requested_once(api):
    openmeteo.fetch_many([point(32)], [point(32), point(33)], 7)
    assert sum(call['count'] for call in api) == 2


def test_required_and_optional_use_separate_batches(api):
    openmeteo.fetch_many([point(32)], [point(33)], 7)
    assert sorted(call['count'] for call in api) == [1, 1]


def test_a_failed_optional_batch_gives_none_and_keeps_the_required_data(monkeypatch):
    def fake(url, params=None, timeout=None):
        if params['latitude'].startswith('33'):
            return FakeResponse({'error': True}, status_code=429)
        return FakeResponse(LOCATIONS[0])

    monkeypatch.setattr(openmeteo.requests, 'get', fake)
    required, optional = openmeteo.fetch_many([point(32)], [point(33)], 7)
    assert len(required) == 1
    assert optional is None


def test_a_failed_required_batch_raises_even_if_optional_worked(monkeypatch):
    def fake(url, params=None, timeout=None):
        if params['latitude'].startswith('32'):
            return FakeResponse({'error': True}, status_code=500)
        return FakeResponse(LOCATIONS[0])

    monkeypatch.setattr(openmeteo.requests, 'get', fake)
    with pytest.raises(ProviderError):
        openmeteo.fetch_many([point(32)], [point(33)], 7)


def test_optional_cells_fully_cached_need_no_request(api):
    openmeteo.fetch_hourly([point(33)], 7)
    api.clear()
    _, optional = openmeteo.fetch_many([point(32)], [point(33)], 7)
    assert len(optional) == 1
    assert [call['count'] for call in api] == [1]


def test_values_survive_the_file_cache(api, file_cache):
    first = openmeteo.fetch_hourly([point(32)], 7)[0]
    second = openmeteo.fetch_hourly([point(32)], 7)[0]
    assert len(api) == 1
    assert second == first


def test_cached_values_survive_being_read_back(api):
    first = openmeteo.fetch_hourly([point(32)], 7)[0]
    second = openmeteo.fetch_hourly([point(32)], 7)[0]
    assert second.times[0].tzinfo == first.times[0].tzinfo
    assert second == first
