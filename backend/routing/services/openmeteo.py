"""Open-Meteo hourly forecasts, cached per point on a snapped grid (D6 in DECISIONS.md)."""
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from django.core.cache import cache

from routing.services.errors import ProviderError

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
TIMEOUT_SECONDS = 15
MAX_POINTS_PER_REQUEST = 100    # Largest batch proven in the spike; the docs state no limit.
HOURLY_VARIABLES = 'wind_speed_10m,wind_gusts_10m,rain,showers,snowfall'

# D6: 0.1 degrees changed risk levels for storm rain while saving almost no points. 0.02 keeps
# nearly the same de-duplication and stays close to HRRR's 3 km grid.
CELL_DEGREES = 0.02
CELL_DECIMALS = 2
CACHE_TTL_SECONDS = 30 * 60     # HRRR updates hourly.


@dataclass(frozen=True)
class HourlyForecast:
    times: list[datetime]
    wind_mph: list[float | None]
    gust_mph: list[float | None]
    rain_in_hr: list[float | None]
    snow_in_hr: list[float | None]


def _snap(value: float) -> float:
    return round(round(value / CELL_DEGREES) * CELL_DEGREES, CELL_DECIMALS)


def _cache_key(cell: tuple[float, float], forecast_days: int) -> str:
    return f'openmeteo:{cell[0]}:{cell[1]}:{forecast_days}:{HOURLY_VARIABLES}'


def _rain_rate(rain: float | None, showers: float | None) -> float | None:
    # A missing part must read as unknown: treating it as 0 would call the hour Low.
    return None if rain is None or showers is None else rain + showers


def _parse_location(location: dict) -> HourlyForecast:
    hourly = location['hourly']
    return HourlyForecast(
        # Requested with timezone=GMT, so the zone-less strings are UTC.
        times=[datetime.fromisoformat(text).replace(tzinfo=timezone.utc) for text in hourly['time']],
        wind_mph=hourly['wind_speed_10m'],
        gust_mph=hourly['wind_gusts_10m'],
        rain_in_hr=[_rain_rate(*pair) for pair in zip(hourly['rain'], hourly['showers'], strict=True)],
        snow_in_hr=hourly['snowfall'],
    )


def _request_batch(cells: list[tuple[float, float]], forecast_days: int) -> requests.Response:
    params = {
        'latitude': ','.join(str(lat) for lat, _ in cells),
        'longitude': ','.join(str(lon) for _, lon in cells),
        'hourly': HOURLY_VARIABLES,
        'wind_speed_unit': 'mph',
        'precipitation_unit': 'inch',
        'timezone': 'GMT',
        'forecast_days': forecast_days,
    }
    # Raised outside the except block, so the requests exception and its URL don't chain.
    failure = None
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as error:
        failure = type(error).__name__
    if failure:
        raise ProviderError(f'Open-Meteo request failed ({failure})')
    return response


def _fetch_batch(cells: list[tuple[float, float]], forecast_days: int) -> list[HourlyForecast]:
    response = _request_batch(cells, forecast_days)
    if response.status_code != 200:
        raise ProviderError(f'Open-Meteo returned HTTP {response.status_code}')
    try:
        body = response.json()
        # A single location comes back as a bare object, not a one-item list (proven live).
        locations = [body] if isinstance(body, dict) else body
        if len(locations) != len(cells):
            raise ValueError('location count does not match the request')
        return [_parse_location(location) for location in locations]
    except (KeyError, TypeError, ValueError):
        raise ProviderError('Open-Meteo returned an unreadable response') from None


def _forecasts_by_cell(cells: list[tuple[float, float]],
                       forecast_days: int) -> dict[tuple[float, float], HourlyForecast]:
    keys = {cell: _cache_key(cell, forecast_days) for cell in cells}
    cached = cache.get_many(keys.values())
    forecasts = {cell: cached[key] for cell, key in keys.items() if key in cached}
    misses = [cell for cell in cells if cell not in forecasts]
    for start in range(0, len(misses), MAX_POINTS_PER_REQUEST):
        batch = misses[start:start + MAX_POINTS_PER_REQUEST]
        fetched = dict(zip(batch, _fetch_batch(batch, forecast_days)))
        # Stored per batch, so a later failure doesn't waste the requests that worked.
        cache.set_many({keys[cell]: forecast for cell, forecast in fetched.items()}, CACHE_TTL_SECONDS)
        forecasts.update(fetched)
    return forecasts


def fetch_hourly(points: list[dict], forecast_days: int) -> list[HourlyForecast]:
    """Hourly forecast for each {lat, lon} point, in input order."""
    cells = [(_snap(point['lat']), _snap(point['lon'])) for point in points]
    forecasts = _forecasts_by_cell(list(dict.fromkeys(cells)), forecast_days)
    return [forecasts[cell] for cell in cells]
