"""Open-Meteo hourly forecasts, cached per point on a snapped grid (D6 in DECISIONS.md)."""
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from django.core.cache import cache

from routing.services.errors import ProviderBusy, ProviderError, ProviderTimeout

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
TIMEOUT_SECONDS = 15
MAX_POINTS_PER_REQUEST = 100    # Largest batch proven in the spike; the docs state no limit.
MAX_PARALLEL_BATCHES = 4
HOURLY_VARIABLES = 'wind_speed_10m,wind_gusts_10m,rain,showers,snowfall'
BUSY_MESSAGE = 'Weather service is busy — please try again in a minute'
REASON_EXCERPT_CHARS = 200

logger = logging.getLogger(__name__)

# D6: 0.1 degrees changed risk levels for storm rain while saving almost no points. 0.02 keeps
# nearly the same de-duplication and stays close to HRRR's 3 km grid.
CELL_DEGREES = 0.02
CELL_DECIMALS = 2
CACHE_TTL_SECONDS = 30 * 60     # HRRR updates hourly.

Cell = tuple[float, float]


@dataclass(frozen=True)
class HourlyForecast:
    times: list[datetime]
    wind_mph: list[float | None]
    gust_mph: list[float | None]
    rain_in_hr: list[float | None]
    snow_in_hr: list[float | None]


def _snap(value: float) -> float:
    return round(round(value / CELL_DEGREES) * CELL_DEGREES, CELL_DECIMALS)


def _cell(point: dict) -> Cell:
    return _snap(point['lat']), _snap(point['lon'])


def _cache_key(cell: Cell, forecast_days: int) -> str:
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


def _request_batch(cells: list[Cell], forecast_days: int) -> requests.Response:
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
        failure = type(error)
    if failure:
        kind = ProviderTimeout if issubclass(failure, requests.Timeout) else ProviderError
        raise kind(f'Open-Meteo request failed ({failure.__name__})')
    return response


def _limit_reason(response: requests.Response) -> str:
    """Open-Meteo's own words for a 429, e.g. which limit was hit. The body format isn't documented, so
    fall back to the start of the raw text."""
    try:
        body = response.json()
        if isinstance(body, dict) and body.get('reason'):
            return str(body['reason'])[:REASON_EXCERPT_CHARS]
    except ValueError:
        pass
    return (response.text or 'no body')[:REASON_EXCERPT_CHARS]


def _fetch_batch(cells: list[Cell], forecast_days: int) -> list[HourlyForecast]:
    response = _request_batch(cells, forecast_days)
    # Each location counts against the 600 per minute, so a retry here would only dig deeper.
    if response.status_code == 429:
        retry_after = response.headers.get('Retry-After')
        # Server log only: tells minute, hour and day limits apart. Users see the plain busy message.
        logger.warning('Open-Meteo 429 for a batch of %d locations: %s (Retry-After %s)',
                       len(cells), _limit_reason(response), retry_after or 'not sent')
        raise ProviderBusy(BUSY_MESSAGE, retry_after=retry_after)
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


def _batches(cells: list[Cell]) -> list[list[Cell]]:
    return [cells[start:start + MAX_POINTS_PER_REQUEST]
            for start in range(0, len(cells), MAX_POINTS_PER_REQUEST)]


def _store_batch(batch: list[Cell], future: Future, forecast_days: int,
                 forecasts: dict[Cell, HourlyForecast]) -> ProviderError | None:
    """Keep one batch's results and return its error, if any."""
    try:
        fetched = dict(zip(batch, future.result()))
    except ProviderError as error:
        return error
    # Stored per batch, so a failed batch doesn't waste the requests that worked.
    cache.set_many({_cache_key(cell, forecast_days): forecast for cell, forecast in fetched.items()},
                   CACHE_TTL_SECONDS)
    forecasts.update(fetched)
    return None


def _fetch_missing(required: list[Cell], optional: list[Cell], forecast_days: int,
                   forecasts: dict[Cell, HourlyForecast]) -> bool:
    """Fill forecasts from the API. Returns False if an optional batch failed.

    The groups use separate batches so a failure in one can't take the other's cells with it.
    """
    required_error = None
    optional_ok = True
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_BATCHES) as pool:
        jobs = [(batch, True, pool.submit(_fetch_batch, batch, forecast_days)) for batch in _batches(required)]
        jobs += [(batch, False, pool.submit(_fetch_batch, batch, forecast_days)) for batch in _batches(optional)]
        for batch, is_required, future in jobs:
            error = _store_batch(batch, future, forecast_days, forecasts)
            if error and is_required:
                required_error = required_error or error
            elif error:
                optional_ok = False
    if required_error:
        raise required_error
    return optional_ok


def fetch_many(required: list[dict], optional: list[dict],
               forecast_days: int) -> tuple[list[HourlyForecast], list[HourlyForecast] | None]:
    """Forecasts for two groups of {lat, lon} points, in input order, from one de-duplicated fetch.

    A failure for required points raises. A failure for optional points gives None for that group.
    """
    required_cells = [_cell(point) for point in required]
    optional_cells = [_cell(point) for point in optional]
    keys = {cell: _cache_key(cell, forecast_days) for cell in required_cells + optional_cells}
    cached = cache.get_many(keys.values())
    forecasts = {cell: cached[key] for cell, key in keys.items() if key in cached}

    required_misses = [cell for cell in dict.fromkeys(required_cells) if cell not in forecasts]
    taken = set(required_misses)
    optional_misses = [cell for cell in dict.fromkeys(optional_cells)
                       if cell not in forecasts and cell not in taken]
    optional_ok = _fetch_missing(required_misses, optional_misses, forecast_days, forecasts)
    return ([forecasts[cell] for cell in required_cells],
            [forecasts[cell] for cell in optional_cells] if optional_ok else None)


def fetch_hourly(points: list[dict], forecast_days: int) -> list[HourlyForecast]:
    """Hourly forecast for each {lat, lon} point, in input order."""
    return fetch_many(points, [], forecast_days)[0]
