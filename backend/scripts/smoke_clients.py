"""Live smoke run of the API clients. Prints counts and timings only.

Run from backend/:  ..\\.venv\\Scripts\\python.exe scripts\\smoke_clients.py
"""
import os
import sys
import time
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from routing.services import mapbox, openmeteo  # noqa: E402
from routing.services.errors import ProviderError  # noqa: E402

VIA = {'lat': 38.6270, 'lon': -90.1994}     # St. Louis, as a stand-in via point
WEATHER_POINTS = 10


def timed(call, *args, **kwargs):
    started = time.perf_counter()
    result = call(*args, **kwargs)
    return result, round((time.perf_counter() - started) * 1000)


def describe_routes(label, routes, ms):
    print(f'{label}: {len(routes)} route(s) in {ms} ms')
    for index, route in enumerate(routes):
        segments = len(route.seg_distances_m)
        zero_segments = route.seg_distances_m.count(0)
        print(f'  route {index}: {len(route.coords_lonlat)} coords, {segments} segments '
              f'(coords minus segments: {len(route.coords_lonlat) - segments}), '
              f'{zero_segments} zero-length, sum vs distance {sum(route.seg_distances_m) / route.distance_m:.6f}')


def main():
    origin, ms = timed(mapbox.geocode, 'Dallas, TX')
    print(f'geocode 1: found in {ms} ms')
    destination, ms = timed(mapbox.geocode, 'Chicago, IL')
    print(f'geocode 2: found in {ms} ms')

    routes, ms = timed(mapbox.directions, origin, destination)
    describe_routes('directions', routes, ms)
    via_routes, ms = timed(mapbox.directions, origin, destination, via=VIA)
    describe_routes('directions via', via_routes, ms)

    coords = routes[0].coords_lonlat
    last = len(coords) - 1
    points = [{'lat': coords[round(i * last / (WEATHER_POINTS - 1))][1],
               'lon': coords[round(i * last / (WEATHER_POINTS - 1))][0]} for i in range(WEATHER_POINTS)]

    forecasts, ms = timed(openmeteo.fetch_hourly, points, 7)
    print(f'weather: {len(forecasts)} points, {len(forecasts[0].times)} hours each, {ms} ms')
    print(f'  first time tz: {forecasts[0].times[0].tzinfo}')
    _, ms = timed(openmeteo.fetch_hourly, points, 7)
    print(f'weather again (cached): {ms} ms')

    # A point away from the route, so this really is a one-location request.
    single, ms = timed(openmeteo.fetch_hourly, [{'lat': 45.0, 'lon': -100.0}], 7)
    print(f'weather single location: {len(single)} point, {len(single[0].times)} hours, {ms} ms')


if __name__ == '__main__':
    try:
        main()
    except ProviderError as error:
        sys.exit(f'Provider error: {error}')
