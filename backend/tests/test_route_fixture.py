"""Domain functions run against a real Mapbox response, on both Dallas-Chicago routes."""
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from routing.domain.geo import (
    checkpoint_weights,
    cumulative_miles,
    haversine_miles,
    sample_checkpoints,
)
from routing.domain.weather_time import eta_at_mile, time_profile

METERS_PER_MILE = 1609.344
STEP_MILES = 25
DEPARTURE = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
FIXTURE = Path(__file__).parent / 'fixtures' / 'mapbox_directions_dallas_chicago.json'


@pytest.fixture(params=[0, 1], ids=['route0', 'route1'])
def route(request):
    return json.loads(FIXTURE.read_text(encoding='utf-8'))['routes'][request.param]


@pytest.fixture
def annotation(route):
    return route['legs'][0]['annotation']


@pytest.fixture
def cum_miles(annotation):
    return cumulative_miles(annotation['distance'])


@pytest.fixture
def checkpoints(route, cum_miles):
    return sample_checkpoints(route['geometry']['coordinates'], cum_miles, STEP_MILES)


def test_annotation_distances_are_metres(route, annotation):
    assert sum(annotation['distance']) == pytest.approx(route['distance'], rel=0.005)


def test_cumulative_miles_has_one_entry_per_coordinate(route, cum_miles):
    assert len(cum_miles) == len(route['geometry']['coordinates'])


def test_haversine_agrees_with_annotation_distances(route, cum_miles):
    lat_lon = [(lat, lon) for lon, lat in route['geometry']['coordinates']]
    measured = sum(haversine_miles(a, b) for a, b in zip(lat_lon, lat_lon[1:]))
    assert measured == pytest.approx(cum_miles[-1], rel=0.005)


def test_checkpoint_count(cum_miles, checkpoints):
    assert len(checkpoints) == math.ceil(cum_miles[-1] / STEP_MILES) + 1


def test_last_checkpoint_is_the_destination(route, cum_miles, checkpoints):
    lon, lat = route['geometry']['coordinates'][-1]
    assert checkpoints[-1] == pytest.approx({'lat': lat, 'lon': lon, 'mile': cum_miles[-1]})


def test_first_checkpoint_is_dallas():
    # Fails if lat and lon are swapped: Dallas is near 32.8, -96.8.
    route = json.loads(FIXTURE.read_text(encoding='utf-8'))['routes'][0]
    cum_miles = cumulative_miles(route['legs'][0]['annotation']['distance'])
    first = sample_checkpoints(route['geometry']['coordinates'], cum_miles, STEP_MILES)[0]
    assert first['lat'] == pytest.approx(32.8, abs=0.1)
    assert first['lon'] == pytest.approx(-96.8, abs=0.1)


def test_weights_sum_to_route_length(cum_miles, checkpoints):
    weights = checkpoint_weights([point['mile'] for point in checkpoints])
    assert sum(weights) == pytest.approx(cum_miles[-1])


def test_eta_at_destination_is_departure_plus_route_duration(route, annotation, cum_miles):
    profile = time_profile(annotation['distance'], annotation['duration'])
    eta = eta_at_mile(profile, cum_miles[-1], DEPARTURE)
    expected = DEPARTURE + timedelta(seconds=route['duration'])
    assert abs((eta - expected).total_seconds()) <= 60
