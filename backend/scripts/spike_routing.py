"""Spike: what do Mapbox Geocoding and Directions really return for long-haul US trips?

Run from backend/:  ..\\.venv\\Scripts\\python.exe scripts\\spike_routing.py
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = BACKEND_DIR / 'tests' / 'fixtures'

GEOCODE_URL = 'https://api.mapbox.com/search/geocode/v6/forward'
DIRECTIONS_URL = 'https://api.mapbox.com/directions/v5/mapbox/driving/{coords}'

TRIPS = [
    ('dallas_chicago', 'Dallas, TX', 'Chicago, IL'),
    ('denver_saltlake', 'Denver, CO', 'Salt Lake City, UT'),
    ('kansascity_denver', 'Kansas City, MO', 'Denver, CO'),
]

METERS_PER_MILE = 1609.344
VIA_OFFSET_MILES = 75
MILES_PER_DEGREE_LAT = 69.0

load_dotenv(BACKEND_DIR / '.env')
TOKEN = os.getenv('MAPBOX_TOKEN', '').strip()


def get_json(url, params):
    """Return (status, body, ms). The token travels in the URL, so nothing here may print the URL
    or str(exception): requests embeds the full URL in both."""
    started = time.perf_counter()
    try:
        response = requests.get(url, params={**params, 'access_token': TOKEN}, timeout=30)
    except requests.RequestException as error:
        sys.exit(f'Request failed: {type(error).__name__}')
    ms = round((time.perf_counter() - started) * 1000)

    if response.status_code in (401, 403):
        sys.exit(f'Mapbox rejected the token (HTTP {response.status_code}). Stopping.')
    try:
        body = response.json()
    except ValueError:
        sys.exit(f'Non-JSON response (HTTP {response.status_code})')
    return response.status_code, body, ms


def geocode(place):
    status, body, ms = get_json(GEOCODE_URL, {'q': place, 'country': 'us', 'limit': 1})
    if status != 200 or not body.get('features'):
        sys.exit(f'Geocoding failed for {place}: HTTP {status}, {body.get("message")}')
    feature = body['features'][0]
    lon, lat = feature['geometry']['coordinates']
    print(f'  geocoded {place!r} -> {lat:.4f},{lon:.4f} '
          f'({feature["properties"].get("full_address")}) in {ms} ms')
    return lon, lat


def directions(points, **overrides):
    coords = ';'.join(f'{lon:.5f},{lat:.5f}' for lon, lat in points)
    params = {
        'alternatives': 'true',
        'geometries': 'geojson',
        'overview': 'full',
        'annotations': 'distance,duration',
        **overrides,
    }
    return get_json(DIRECTIONS_URL.format(coords=coords), params)


def describe_route(index, route):
    miles = route['distance'] / METERS_PER_MILE
    hours = route['duration'] / 3600
    coord_count = len(route['geometry']['coordinates'])
    print(f'  route {index}: {miles:.1f} mi, {hours:.2f} h, {coord_count} coords, '
          f'{len(route["legs"])} leg(s)')
    for leg_index, leg in enumerate(route['legs']):
        annotation = leg.get('annotation')
        if annotation is None:
            print(f'    leg {leg_index}: NO annotation object')
            continue
        lengths = {key: len(values) for key, values in annotation.items()}
        print(f'    leg {leg_index}: annotation lengths {lengths} '
              f'(coords minus array length: {coord_count - lengths.get("distance", 0)})')


def offset_midpoint(main_route, start, end):
    """Point VIA_OFFSET_MILES off the route midpoint, perpendicular to the overall trip direction."""
    coordinates = main_route['geometry']['coordinates']
    mid_lon, mid_lat = coordinates[len(coordinates) // 2]
    lon_scale = math.cos(math.radians(mid_lat))

    # Work in miles so the perpendicular is a true right angle at this latitude.
    east = (end[0] - start[0]) * lon_scale * MILES_PER_DEGREE_LAT
    north = (end[1] - start[1]) * MILES_PER_DEGREE_LAT
    length = math.hypot(east, north)
    left_east, left_north = -north / length, east / length

    return (
        mid_lon + left_east * VIA_OFFSET_MILES / (MILES_PER_DEGREE_LAT * lon_scale),
        mid_lat + left_north * VIA_OFFSET_MILES / MILES_PER_DEGREE_LAT,
    )


def save_fixture(filename, data):
    text = json.dumps(data)
    if TOKEN in text:
        sys.exit(f'Token found in {filename} payload. Not writing it.')
    path = FIXTURES_DIR / filename
    path.write_text(text, encoding='utf-8')
    print(f'  saved {path.relative_to(BACKEND_DIR)} ({path.stat().st_size / 1024:.0f} KB)')


def run_via_test(result):
    routes = result['body']['routes']
    main = routes[0]
    via = offset_midpoint(main, result['start'], result['end'])
    status, body, ms = directions(
        [result['start'], via, result['end']], alternatives='false', overview='false',
    )
    print(f'\n[{result["slug"]}] via point {via[1]:.4f},{via[0]:.4f}: '
          f'HTTP {status}, code={body.get("code")}, {ms} ms')
    if status != 200 or not body.get('routes'):
        print(f'  no route: {body.get("message")}')
        return
    via_route = body['routes'][0]
    snapped = body['waypoints'][1]['location']
    distance_gain = via_route['distance'] / main['distance'] - 1
    duration_gain = via_route['duration'] / main['duration'] - 1
    print(f'  via snapped to {snapped[1]:.4f},{snapped[0]:.4f} '
          f'on {body["waypoints"][1].get("name")!r}')
    print(f'  main {main["distance"] / METERS_PER_MILE:.1f} mi {main["duration"] / 3600:.2f} h | '
          f'via {via_route["distance"] / METERS_PER_MILE:.1f} mi {via_route["duration"] / 3600:.2f} h '
          f'| distance {distance_gain:+.1%}, duration {duration_gain:+.1%}')


def main():
    if not TOKEN:
        sys.exit('MAPBOX_TOKEN is missing from backend/.env. Stopping.')
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for slug, origin, destination in TRIPS:
        print(f'\n[{slug}] {origin} -> {destination}')
        start = geocode(origin)
        end = geocode(destination)
        status, body, ms = directions([start, end])
        if status != 200 or body.get('code') != 'Ok':
            sys.exit(f'Directions failed: HTTP {status}, {body.get("code")}, {body.get("message")}')

        print(f'  directions: {len(body["routes"])} route(s) in {ms} ms; '
              f'top-level keys {sorted(body)}')
        for index, route in enumerate(body['routes']):
            describe_route(index, route)
        results.append({'slug': slug, 'start': start, 'end': end, 'body': body})

    # max() keeps the first trip on a tie.
    best = max(results, key=lambda result: len(result['body']['routes']))
    print(f'\nMost routes: {best["slug"]}')
    # Geocoding responses are deliberately not saved: Mapbox doesn't allow caching temporary results.
    save_fixture(f'mapbox_directions_{best["slug"]}.json', best['body'])

    short_trips = [result for result in results if len(result['body']['routes']) < 3]
    print(f'\nVia-waypoint test for {len(short_trips)} trip(s) with fewer than 3 routes')
    for result in short_trips:
        run_via_test(result)


if __name__ == '__main__':
    main()
