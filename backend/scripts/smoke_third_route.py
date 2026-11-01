"""Live check of third-route generation on the 3 test trips. Prints counts and timings only.

Run from backend/:  ..\\.venv\\Scripts\\python.exe scripts\\smoke_third_route.py
"""
import os
import sys
import time
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from routing.domain.alternatives import route_count_note, select_extra_routes  # noqa: E402
from routing.domain.geo import METERS_PER_MILE  # noqa: E402
from routing.services.candidates import generate_candidates  # noqa: E402
from routing.services.errors import ProviderError  # noqa: E402

TRIPS = [
    ('Dallas -> Chicago', {'lat': 32.7813, 'lon': -96.7998}, {'lat': 41.8820, 'lon': -87.6324}),
    ('Denver -> Salt Lake City', {'lat': 39.7417, 'lon': -104.9861}, {'lat': 40.7628, 'lon': -111.8898}),
    ('Kansas City -> Denver', {'lat': 39.0985, 'lon': -94.5786}, {'lat': 39.7417, 'lon': -104.9861}),
]


def miles_hours(route):
    return f'{route.distance_m / METERS_PER_MILE:.0f} mi, {route.duration_s / 3600:.2f} h'


def run_trip(name, origin, destination):
    started = time.perf_counter()
    routes, candidates, _ = generate_candidates(origin, destination)
    ms = round((time.perf_counter() - started) * 1000)
    chosen, reviews = select_extra_routes(candidates, routes)

    print(f'\n{name}: {len(routes)} Mapbox route(s), {len(candidates)} candidate(s), {ms} ms for all calls')
    for route in routes:
        print(f'  mapbox: {miles_hours(route)}')
    for review in reviews:
        print(f'  {review.candidate.label}: {miles_hours(review.candidate.route)}, '
              f'x{review.duration_ratio:.3f}, overlap {review.overlap:.0%}, {review.reason}')
    if chosen:
        print(f'  CHOSEN: {", ".join(candidate.label for candidate in chosen)}')
    print(f'  {route_count_note(len(routes) + len(chosen)) or "3 routes"}')


def main():
    for name, origin, destination in TRIPS:
        run_trip(name, origin, destination)


if __name__ == '__main__':
    try:
        main()
    except ProviderError as error:
        sys.exit(f'Provider error: {error}')
