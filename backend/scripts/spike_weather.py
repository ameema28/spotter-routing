"""Spike: what does Open-Meteo really return for batched points along a saved route?

Run spike_routing.py first. Run from backend/:  ..\\.venv\\Scripts\\python.exe scripts\\spike_weather.py
"""
import json
import sys
import time
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = BACKEND_DIR / 'tests' / 'fixtures'

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
BASE_PARAMS = {
    'hourly': 'wind_speed_10m,wind_gusts_10m,rain,showers,snowfall,precipitation',
    'wind_speed_unit': 'mph',
    'precipitation_unit': 'inch',
    'timezone': 'GMT',
    'forecast_days': 7,
}
MAX_HALVINGS = 3


def load_route_coordinates():
    paths = sorted(FIXTURES_DIR.glob('mapbox_directions_*.json'))
    if not paths:
        sys.exit('No Directions fixture found. Run spike_routing.py first.')
    print(f'Route source: {paths[0].name}')
    body = json.loads(paths[0].read_text(encoding='utf-8'))
    return body['routes'][0]['geometry']['coordinates']


def sample_evenly(coordinates, count):
    last = len(coordinates) - 1
    return [coordinates[round(i * last / (count - 1))] for i in range(count)]


def fetch(points):
    # GeoJSON order is [lon, lat]; Open-Meteo takes two separate lists.
    params = {
        **BASE_PARAMS,
        'latitude': ','.join(f'{lat:.4f}' for _, lat in points),
        'longitude': ','.join(f'{lon:.4f}' for lon, _ in points),
    }
    url_length = len(requests.Request('GET', FORECAST_URL, params=params).prepare().url)
    started = time.perf_counter()
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=60)
    except requests.RequestException as error:
        return None, None, url_length, 0, type(error).__name__
    ms = round((time.perf_counter() - started) * 1000)
    try:
        body = response.json()
    except ValueError:
        body = None
    return response.status_code, body, url_length, ms, None


def describe_five_points(status, body, url_length, ms):
    print(f'\n5 points: HTTP {status}, {ms} ms, URL length {url_length}')
    if status != 200:
        sys.exit(f'5-point request failed: {body}')

    print(f'Shape for multiple locations: {type(body).__name__} of {len(body)}')
    first = body[0]
    print(f'Location keys: {sorted(first)}')
    print(f'hourly_units exactly as returned: {json.dumps(first["hourly_units"])}')
    print(f'timezone: {first["timezone"]}, utc_offset_seconds: {first["utc_offset_seconds"]}')

    hourly = first['hourly']
    print(f'Hourly array lengths: { {key: len(values) for key, values in hourly.items()} }')
    print(f'First timestamp: {hourly["time"][0]}  Last timestamp: {hourly["time"][-1]}')
    nulls = {key: sum(value is None for value in values) for key, values in hourly.items()}
    print(f'Null counts: {nulls}')

    print('Grid snapping (returned point and elevation):')
    for location in body:
        print(f'  {location["latitude"]:.4f},{location["longitude"]:.4f} '
              f'elevation {location["elevation"]} m')


def try_batch(coordinates, count):
    status, body, url_length, ms, error = fetch(sample_evenly(coordinates, count))
    if error:
        print(f'{count} points: FAILED {error}, URL length {url_length}')
        return False
    if status != 200:
        reason = body.get('reason') if isinstance(body, dict) else None
        print(f'{count} points: HTTP {status}, {ms} ms, URL length {url_length}, reason: {reason}')
        return False
    lengths = {len(location['hourly']['time']) for location in body}
    print(f'{count} points: HTTP {status}, {ms} ms, URL length {url_length}, '
          f'{len(body)} locations returned, hourly lengths {sorted(lengths)}')
    return True


def main():
    coordinates = load_route_coordinates()
    print(f'Route coordinates: {len(coordinates)}')

    status, body, url_length, ms, error = fetch(sample_evenly(coordinates, 5))
    if error:
        sys.exit(f'5-point request failed: {error}')
    describe_five_points(status, body, url_length, ms)

    path = FIXTURES_DIR / 'openmeteo_5pts.json'
    path.write_text(json.dumps(body), encoding='utf-8')
    print(f'Saved {path.relative_to(BACKEND_DIR)} ({path.stat().st_size / 1024:.0f} KB)\n')

    count = 100
    for _ in range(MAX_HALVINGS + 1):
        if try_batch(coordinates, count):
            break
        count //= 2


if __name__ == '__main__':
    main()
