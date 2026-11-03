"""POST /api/heatmap/: levels for a route plan's grid when its weather fetch failed (D14)."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from routing import views
from routing.services.errors import ProviderBusy
from routing.throttles import HeatmapDayThrottle, HeatmapMinuteThrottle

URL = '/api/heatmap/'
STEP = [0.36, 0.46]


def valid(**overrides):
    body = {
        'points': [[32.76, -96.6], [33.12, -96.6], [33.12, -96.14]],
        'step_deg': STEP,
        'departure': (timezone.now() + timedelta(hours=2)).isoformat(),
        'load_lb': 40000,
    }
    body.update(overrides)
    return body


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def levels(monkeypatch):
    """Replace the weather step and record what it was called with."""
    calls = []

    def fake(points, departure, load_lb):
        calls.append({'points': points, 'departure': departure, 'load_lb': load_lb})
        return {'levels': [[0] * 49 for _ in points]}

    monkeypatch.setattr(views, 'build_heatmap_levels', fake)
    return calls


def post(client, body):
    return client.post(URL, body, format='json')


def test_valid_request_returns_levels(client, levels):
    response = post(client, valid())
    assert response.status_code == 200
    assert len(response.json()['levels']) == 3
    assert levels[0]['points'] == [[32.76, -96.6], [33.12, -96.6], [33.12, -96.14]]
    assert levels[0]['load_lb'] == 40000
    assert levels[0]['departure'].tzinfo is not None


@pytest.mark.parametrize('field', ['points', 'step_deg', 'departure', 'load_lb'])
def test_required_fields(client, levels, field):
    body = valid()
    del body[field]
    response = post(client, body)
    assert response.status_code == 400
    assert field in response.json()
    assert levels == []


def test_step_must_be_one_of_the_fixed_grids(client, levels):
    response = post(client, valid(step_deg=[0.3, 0.4]))
    assert response.status_code == 400
    assert 'step_deg' in response.json()


def test_points_off_the_grid_are_rejected(client, levels):
    # Arbitrary points would spend weather quota on places no route plan asked for.
    response = post(client, valid(points=[[32.77, -96.6]]))
    assert response.status_code == 400
    assert 'points' in response.json()


@pytest.mark.parametrize('points', [[], [[32.76]], [[32.76, -96.6, 1]], [[91.08, -96.6]]])
def test_malformed_points_are_rejected(client, levels, points):
    assert post(client, valid(points=points)).status_code == 400


def test_more_points_than_a_plan_sends_are_rejected(client, levels):
    points = [[round(row * 0.36, 2), -96.6] for row in range(251)]
    response = post(client, valid(points=points))
    assert response.status_code == 400
    assert 'points' in response.json()


def test_departure_without_a_timezone_is_rejected(client, levels):
    response = post(client, valid(departure='2026-11-02T08:00:00'))
    assert response.status_code == 400
    assert 'departure' in response.json()


@pytest.mark.parametrize('load', [0, 80_001])
def test_load_rules_match_the_search(client, levels, load):
    assert post(client, valid(load_lb=load)).status_code == 400


def test_busy_weather_gives_503_with_the_safe_message(client, monkeypatch):
    def busy(*args, **kwargs):
        raise ProviderBusy('Weather service is busy — please try again in a minute', retry_after='60')

    monkeypatch.setattr(views, 'build_heatmap_levels', busy)
    response = post(client, valid())
    assert response.status_code == 503
    assert response.json() == {'error': 'Weather service is busy — please try again in a minute'}
    assert response['Retry-After'] == '60'


def test_throttle_rates():
    assert HeatmapMinuteThrottle.rate == '10/minute'
    assert HeatmapDayThrottle.rate == '100/day'


def test_eleventh_retry_in_a_minute_is_refused(client, levels):
    assert [post(client, valid()).status_code for _ in range(10)] == [200] * 10
    response = post(client, valid())
    assert response.status_code == 429
    assert response.json() == {'error': 'Too many heatmap retries — please wait a minute and try again'}
    assert int(response['Retry-After']) > 0


def test_retries_do_not_use_up_searches(client, levels, monkeypatch):
    monkeypatch.setattr(views, 'build_route_plan', lambda **kwargs: {'routes': []})
    for _ in range(10):
        post(client, valid())
    search = {'origin': 'Dallas, TX', 'destination': 'Chicago, IL',
              'departure': (timezone.now() + timedelta(hours=2)).isoformat(), 'load_lb': 40000}
    assert client.post('/api/route-plan/', search, format='json').status_code == 200
