"""Mapbox Geocoding and Directions. Nothing here is cached: see D6 in DECISIONS.md."""
from dataclasses import dataclass

import requests
from django.conf import settings

from routing.services.errors import ProviderError

GEOCODE_URL = 'https://api.mapbox.com/search/geocode/v6/forward'
DIRECTIONS_URL = 'https://api.mapbox.com/directions/v5/mapbox/driving/{coords}'
TIMEOUT_SECONDS = 15    # New queries took up to 9.9 s in real calls.


@dataclass(frozen=True)
class Route:
    coords_lonlat: list[list[float]]
    seg_distances_m: list[float]
    seg_durations_s: list[float]
    distance_m: float
    duration_s: float


def _get_json(url: str, params: dict) -> dict:
    if not settings.MAPBOX_TOKEN:
        raise ProviderError('Mapbox token is not configured')
    # The token travels in the URL, and requests copies the URL into its exception text. Raising
    # outside the except block keeps that exception off __context__ as well as out of the message.
    failure = None
    try:
        response = requests.get(url, params={**params, 'access_token': settings.MAPBOX_TOKEN},
                                timeout=TIMEOUT_SECONDS)
    except requests.RequestException as error:
        failure = type(error).__name__
    if failure:
        raise ProviderError(f'Mapbox request failed ({failure})')
    return _parse_body(response)


def _parse_body(response: requests.Response) -> dict:
    if response.status_code != 200:
        raise ProviderError(f'Mapbox returned HTTP {response.status_code}')
    try:
        return response.json()
    except ValueError:
        raise ProviderError('Mapbox returned an unreadable response') from None


def geocode(query: str) -> dict:
    """Best US match for a place name, as {lat, lon, label}."""
    body = _get_json(GEOCODE_URL, {'q': query, 'country': 'us', 'limit': 1})
    try:
        feature = body['features'][0]
        lon, lat = feature['geometry']['coordinates']
        return {'lat': lat, 'lon': lon, 'label': feature['properties']['full_address']}
    except (KeyError, IndexError, TypeError, ValueError):
        raise ProviderError('Mapbox found no US location for that place') from None


def _parse_route(raw: dict) -> Route:
    # A via point splits the route into legs. Joined, they still fit the geometry (proven live): the
    # join repeats a vertex and adds a zero-length segment, which the domain functions allow for.
    annotations = [leg['annotation'] for leg in raw['legs']]
    route = Route(
        coords_lonlat=raw['geometry']['coordinates'],
        seg_distances_m=[value for annotation in annotations for value in annotation['distance']],
        seg_durations_s=[value for annotation in annotations for value in annotation['duration']],
        distance_m=raw['distance'],
        duration_s=raw['duration'],
    )
    segment_count = len(route.coords_lonlat) - 1
    if not len(route.seg_distances_m) == len(route.seg_durations_s) == segment_count:
        raise ValueError('annotations do not fit the geometry')
    return route


def directions(origin: dict, destination: dict, via: dict | None = None,
               exclude: str | None = None) -> list[Route]:
    """Driving routes between {lat, lon} points, in Mapbox's order."""
    stops = [origin, via, destination] if via else [origin, destination]
    coords = ';'.join(f'{stop["lon"]:.5f},{stop["lat"]:.5f}' for stop in stops)
    params = {
        'alternatives': 'true',
        'geometries': 'geojson',
        'overview': 'full',
        'annotations': 'distance,duration',
    }
    if exclude:
        params['exclude'] = exclude
    body = _get_json(DIRECTIONS_URL.format(coords=coords), params)
    if body.get('code') != 'Ok' or not body.get('routes'):
        raise ProviderError(f'Mapbox found no route ({body.get("code")})')
    try:
        return [_parse_route(raw) for raw in body['routes']]
    except (KeyError, TypeError, ValueError):
        raise ProviderError('Mapbox returned an unreadable route') from None
