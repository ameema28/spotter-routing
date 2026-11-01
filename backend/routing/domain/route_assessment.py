"""Turn a route and its weather into checkpoint risks and a summary (the D3, D4, D5 and D8 rules)."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from routing.domain.geo import checkpoint_weights, cumulative_miles, sample_checkpoints
from routing.domain.ranking import RouteSummary, summarize_route
from routing.domain.risk import RiskLevel, checkpoint_risk
from routing.domain.truck_eta import (
    HOURS_OF_SERVICE,
    TRUCK_MAX_MPH,
    StopEvent,
    add_rest_breaks,
    apply_speed_cap,
)
from routing.domain.weather_time import eta_at_mile, precip_hour, time_profile, wind_hour

HEATMAP_HOURS = 48


@dataclass(frozen=True)
class AssessedCheckpoint:
    mile: float
    lat: float
    lon: float
    eta: datetime
    level: RiskLevel | None
    driver: str
    wind_mph: float | None
    gust_mph: float | None
    rain_in_hr: float | None
    snow_in_hr: float | None
    precip_hour: datetime | None
    wind_hour: datetime | None


@dataclass(frozen=True)
class RouteAssessment:
    summary: RouteSummary
    checkpoints: list[AssessedCheckpoint]
    stops: list[StopEvent]
    drive_seconds: float
    trip_seconds: float


def plan_checkpoints(route: Any, step_miles: float) -> list[dict]:
    """Where weather is needed for this route, as {lat, lon, mile}."""
    return sample_checkpoints(route.coords_lonlat, cumulative_miles(route.seg_distances_m), step_miles)


def _at(values: list, index: int | None) -> Any:
    return None if index is None else values[index]


def _assess_checkpoint(point: dict, forecast: Any, eta: datetime, load_lb: float) -> AssessedCheckpoint:
    precip_row = precip_hour(eta, forecast.times)
    wind_row = wind_hour(eta, forecast.times)
    wind = _at(forecast.wind_mph, wind_row)
    rain = _at(forecast.rain_in_hr, precip_row)
    snow = _at(forecast.snow_in_hr, precip_row)
    level, driver = checkpoint_risk(wind, rain, snow, load_lb)
    return AssessedCheckpoint(
        mile=point['mile'], lat=point['lat'], lon=point['lon'], eta=eta, level=level, driver=driver,
        wind_mph=wind, gust_mph=_at(forecast.gust_mph, wind_row), rain_in_hr=rain, snow_in_hr=snow,
        precip_hour=_at(forecast.times, precip_row), wind_hour=_at(forecast.times, wind_row),
    )


def assess_route(route_index: int, route: Any, points: list[dict], forecasts: list[Any],
                 departure: datetime, load_lb: float) -> RouteAssessment:
    """Truck ETAs at each checkpoint, then risk from the forecast for that hour."""
    capped = apply_speed_cap(route.seg_distances_m, route.seg_durations_s, TRUCK_MAX_MPH)
    driving = time_profile(route.seg_distances_m, capped)
    profile, stops = add_rest_breaks(driving, HOURS_OF_SERVICE)
    checkpoints = [_assess_checkpoint(point, forecast, eta_at_mile(profile, point['mile'], departure), load_lb)
                   for point, forecast in zip(points, forecasts, strict=True)]
    weights = checkpoint_weights([checkpoint.mile for checkpoint in checkpoints])
    trip_seconds = profile[-1][1]
    summary = summarize_route(route_index, [checkpoint.level for checkpoint in checkpoints], weights, trip_seconds)
    return RouteAssessment(summary, checkpoints, stops, driving[-1][1], trip_seconds)


def _hour_rows(times: list[datetime], hours: list[datetime]) -> list[tuple[int | None, int | None]]:
    return [(precip_hour(hour, times), wind_hour(hour, times)) for hour in hours]


def _cell_level(forecast: Any, precip_row: int | None, wind_row: int | None, load_lb: float) -> int | None:
    level, _ = checkpoint_risk(_at(forecast.wind_mph, wind_row), _at(forecast.rain_in_hr, precip_row),
                               _at(forecast.snow_in_hr, precip_row), load_lb)
    return None if level is None else int(level)


def heatmap_levels(forecasts: list[Any], departure: datetime,
                   load_lb: float) -> tuple[list[datetime], list[list[int | None]]]:
    """Risk level per point for each hour after departure, with the same rules as checkpoints."""
    hours = [departure + timedelta(hours=offset) for offset in range(HEATMAP_HOURS + 1)]
    rows_by_start: dict[tuple, list] = {}
    levels = []
    for forecast in forecasts:
        # Most points share the same rows, but cached cells can straddle midnight GMT.
        key = (forecast.times[0], len(forecast.times))
        rows = rows_by_start.setdefault(key, _hour_rows(forecast.times, hours))
        levels.append([_cell_level(forecast, precip_row, wind_row, load_lb) for precip_row, wind_row in rows])
    return hours, levels
