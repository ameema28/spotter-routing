import gzip
import json
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from routing import views
from routing.throttles import RoutePlanDayThrottle, RoutePlanMinuteThrottle
from routing.services.errors import (
    PlaceNotFound,
    ProviderBusy,
    ProviderError,
    ProviderTimeout,
    RouteNotFound,
)

URL = '/api/route-plan/'
SAFE_FAKE_TOKEN = 'pk.fake-token-for-tests'


def valid(**overrides):
    body = {
        'origin': 'Dallas, TX',
        'destination': 'Chicago, IL',
        'departure': (timezone.now() + timedelta(hours=2)).isoformat(),
        'load_lb': 40000,
    }
    body.update(overrides)
    return body


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def plan(monkeypatch):
    """Replace the pipeline and record what it was called with."""
    calls = []

    def fake(origin, destination, departure, load_lb, step_miles):
        calls.append({'origin': origin, 'destination': destination, 'departure': departure,
                      'load_lb': load_lb, 'step_miles': step_miles})
        return {'routes': [], 'padding': 'x' * 2000}

    monkeypatch.setattr(views, 'build_route_plan', fake)
    return calls


def post(client, body):
    return client.post(URL, body, format='json')


def failing(monkeypatch, error):
    def fake(*args, **kwargs):
        raise error

    monkeypatch.setattr(views, 'build_route_plan', fake)


def test_valid_request_runs_the_pipeline(client, plan):
    response = post(client, valid())
    assert response.status_code == 200
    assert plan[0]['origin'] == 'Dallas, TX'
    assert plan[0]['load_lb'] == 40000
    assert plan[0]['departure'].tzinfo is not None


def test_step_defaults_to_25(client, plan):
    post(client, valid())
    assert plan[0]['step_miles'] == 25


@pytest.mark.parametrize('step', [10, 25, 50])
def test_allowed_steps(client, plan, step):
    assert post(client, valid(step_miles=step)).status_code == 200
    assert plan[0]['step_miles'] == step


@pytest.mark.parametrize('field', ['origin', 'destination', 'departure', 'load_lb'])
def test_required_fields(client, plan, field):
    body = valid()
    del body[field]
    response = post(client, body)
    assert response.status_code == 400
    assert field in response.json()
    assert plan == []


@pytest.mark.parametrize('field, value', [
    ('origin', ''),
    ('origin', '   '),
    ('destination', 'x' * 201),
    ('load_lb', 0),
    ('load_lb', -1),
    ('load_lb', 80_001),
    ('load_lb', 'heavy'),
    ('step_miles', 30),
    ('departure', 'tomorrow'),
])
def test_invalid_values_get_field_messages(client, plan, field, value):
    response = post(client, valid(**{field: value}))
    assert response.status_code == 400
    assert field in response.json()
    assert plan == []


def test_departure_without_a_timezone_is_rejected(client, plan):
    # Inside the allowed window, so only the missing timezone can reject it.
    naive = (timezone.now() + timedelta(hours=2)).replace(tzinfo=None).isoformat()
    response = post(client, valid(departure=naive))
    assert response.status_code == 400
    assert 'timezone' in response.json()['departure'][0]
    assert plan == []


def test_load_at_the_cap_is_allowed(client, plan):
    assert post(client, valid(load_lb=80_000)).status_code == 200


@pytest.mark.parametrize('offset, status', [
    (timedelta(minutes=-59), 200),
    (timedelta(minutes=-61), 400),
    (timedelta(days=6, hours=23), 200),
    (timedelta(days=7, minutes=1), 400),
])
def test_departure_window(client, plan, offset, status):
    assert post(client, valid(departure=(timezone.now() + offset).isoformat())).status_code == status


def test_any_timezone_offset_is_accepted(client, plan):
    local = (timezone.now() + timedelta(hours=2)).astimezone(timezone.get_fixed_timezone(-300))
    assert post(client, valid(departure=local.isoformat())).status_code == 200


@pytest.mark.parametrize('error, status', [
    (PlaceNotFound('Mapbox found no US location for that place'), 422),
    (RouteNotFound('No drivable route between those places'), 422),
    (ProviderTimeout('Mapbox request failed (Timeout)'), 504),
    (ProviderBusy('Weather service is busy — please try again in a minute'), 503),
    (ProviderError('Mapbox returned HTTP 500'), 502),
])
def test_errors_map_to_status_codes(client, monkeypatch, error, status):
    failing(monkeypatch, error)
    response = post(client, valid())
    assert response.status_code == status
    assert response.json() == {'error': str(error)}


def test_busy_sends_retry_after_when_known(client, monkeypatch):
    failing(monkeypatch, ProviderBusy('busy', retry_after='30'))
    assert post(client, valid())['Retry-After'] == '30'


def test_busy_has_no_retry_after_when_unknown(client, monkeypatch):
    failing(monkeypatch, ProviderBusy('busy'))
    assert 'Retry-After' not in post(client, valid())


def test_error_bodies_never_hold_urls_or_tokens(client, monkeypatch):
    failing(monkeypatch, ProviderError('Mapbox returned HTTP 500'))
    text = post(client, valid()).content.decode()
    assert SAFE_FAKE_TOKEN not in text
    assert 'http' not in text.lower().replace('http 500', '')


def test_only_post_is_allowed(client):
    assert client.get(URL).status_code == 405


def test_large_responses_are_gzipped(client, plan):
    response = client.post(URL, json.dumps(valid()), content_type='application/json',
                           HTTP_ACCEPT_ENCODING='gzip')
    assert response['Content-Encoding'] == 'gzip'
    assert json.loads(gzip.decompress(response.content))['routes'] == []


def post_as(client, address):
    return client.post(URL, valid(), format='json', HTTP_X_FORWARDED_FOR=address)


def test_throttle_rates():
    assert RoutePlanMinuteThrottle.rate == '10/minute'
    assert RoutePlanDayThrottle.rate == '100/day'


def test_eleventh_search_in_a_minute_is_refused(client, plan):
    statuses = [post(client, valid()).status_code for _ in range(10)]
    assert statuses == [200] * 10
    response = post(client, valid())
    assert response.status_code == 429
    assert response.json() == {'error': 'Too many searches — please wait a minute and try again'}
    assert int(response['Retry-After']) > 0
    assert len(plan) == 10


def test_clients_are_limited_separately(client, plan):
    for _ in range(10):
        post_as(client, '203.0.113.1')
    assert post_as(client, '203.0.113.1').status_code == 429
    assert post_as(client, '203.0.113.2').status_code == 200


def test_a_forged_forwarded_address_does_not_dodge_the_limit(client, plan):
    # The proxy appends the real address last, so only that one identifies the client.
    for number in range(10):
        post_as(client, f'198.51.100.{number}, 203.0.113.1')
    assert post_as(client, '198.51.100.99, 203.0.113.1').status_code == 429


def test_health_is_never_throttled(client):
    assert {client.get('/api/health/').status_code for _ in range(15)} == {200}


def test_invalid_searches_count_too(client, plan):
    for _ in range(10):
        post(client, valid(load_lb=-1))
    assert post(client, valid()).status_code == 429
