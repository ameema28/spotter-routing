"""Live run of the whole route-plan pipeline for one trip. Prints counts and timings only.

Each fresh trip uses about 320 of Open-Meteo's 600 locations per minute, so this runs one at a time.
Run from backend/:  ..\\.venv\\Scripts\\python.exe scripts\\smoke_route_plan.py [dallas|denver|kansascity]
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client  # noqa: E402

TRIPS = {
    'dallas': ('Dallas, TX', 'Chicago, IL'),
    'denver': ('Denver, CO', 'Salt Lake City, UT'),
    'kansascity': ('Kansas City, MO', 'Denver, CO'),
}
LOAD_LB = 40_000


def post(body, encoding):
    # SERVER_NAME matches the local ALLOWED_HOSTS fallback; no port or socket is used.
    return Client(SERVER_NAME='localhost').post('/api/route-plan/', json.dumps(body), content_type='application/json',
                                                HTTP_ACCEPT_ENCODING=encoding)


def report(plan):
    print(f'timings_ms: {plan["timings_ms"]}')
    ids = {route['id']: route for route in plan['routes']}
    for route in plan['routes']:
        summary = route['summary']
        print(f'  [{route["id"]}] {route["label"]}: {route["distance_mi"]} mi, drive {route["drive_time"]}, '
              f'trip {route["trip_time"]}, {len(route["breaks"])} stops, {len(route["geometry"])} display points, '
              f'{len(route["checkpoints"])} checkpoints, severe {summary["severe_miles"]}, '
              f'high {summary["high_miles"]}, avg {summary["avg_risk"]}, tier {summary["tier"]}')
    recommended = plan['recommendation']['route_id']
    print(f'recommendation: {ids[recommended]["label"] if recommended is not None else None}')
    print(f'reason: {plan["recommendation"]["reason"]}')
    print(f'ranking: {plan["ranking"]}')
    heatmap = plan['heatmap']
    print(f'heatmap points: {len(heatmap["points"]) if heatmap else None}')
    print(f'notes: {plan["notes"]}')


def main():
    trip = sys.argv[1] if len(sys.argv) > 1 else 'dallas'
    if trip not in TRIPS:
        sys.exit(f'Unknown trip. Choose from: {", ".join(TRIPS)}')
    origin, destination = TRIPS[trip]
    departure = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    body = {'origin': origin, 'destination': destination, 'departure': departure, 'load_lb': LOAD_LB}

    started = time.perf_counter()
    response = post(body, 'identity')
    total = round((time.perf_counter() - started) * 1000)
    print(f'{origin} -> {destination}: HTTP {response.status_code} in {total} ms')
    if response.status_code != 200:
        sys.exit(f'Error body: {response.content.decode()}')
    report(response.json())

    started = time.perf_counter()
    repeat = post(body, 'gzip')
    print(f'repeat request (weather cached): {round((time.perf_counter() - started) * 1000)} ms')
    print(f'size: raw {len(response.content) / 1024:.1f} KB, gzipped {len(repeat.content) / 1024:.1f} KB '
          f'({repeat.get("Content-Encoding")})')


if __name__ == '__main__':
    main()
