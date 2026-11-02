"""Compare routes for a trip: the whole pipeline behind POST /api/route-plan/."""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

from routing.domain.alternatives import route_count_note, select_extra_routes
from routing.domain.formatting import format_duration
from routing.domain.geo import METERS_PER_MILE
from routing.domain.geometry import DISPLAY_TOLERANCE_DEGREES, corridor_grid_with_step, simplify_line
from routing.domain.ranking import rank_routes, recommend
from routing.domain.route_assessment import RouteAssessment, assess_route, heatmap_levels, plan_checkpoints
from routing.services import mapbox
from routing.services.candidates import generate_candidates
from routing.services.openmeteo import fetch_many

# D9: every location counts against Open-Meteo's 600 per minute, so the grid is what limits fresh
# searches, not the response size.
HEATMAP_BUFFER_MILES = 25
HEATMAP_MAX_POINTS = 250

# Departure can be 7 days out, plus the 48-hour slider or a long trip. Fixed, not per request, so
# cached cells can always be reused. 11 days costs the same as 7: Open-Meteo only adds weight above
# 2 weeks or 10 variables (https://open-meteo.com/en/pricing).
FORECAST_DAYS = 11

HEATMAP_UNAVAILABLE_NOTE = 'Heatmap unavailable: weather service is busy'


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def _geocode_both(origin: str, destination: str) -> tuple[dict, dict]:
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(mapbox.geocode, origin), pool.submit(mapbox.geocode, destination)
        return first.result(), second.result()


def _late_note(late: int) -> str:
    if late == 1:
        return '1 route candidate was too slow and was skipped'
    return f'{late} route candidates were too slow and were skipped'


def _find_routes(start: dict, end: dict) -> tuple[list[tuple[Any, str, str]], list[str]]:
    """(route, label, source) for each route to compare, plus notes for the driver."""
    routes, candidates, late = generate_candidates(start, end)
    chosen, _ = select_extra_routes(candidates, routes)
    labelled = [(route, 'Fastest route' if index == 0 else f'Alternative route {index}', 'mapbox')
                for index, route in enumerate(routes)]
    labelled += [(candidate.route, candidate.label, 'generated') for candidate in chosen]
    count_note = route_count_note(len(labelled))
    notes = [count_note] if count_note else []
    if late:
        notes.append(_late_note(late))
    return labelled, notes


def _checkpoint_json(checkpoint: Any) -> dict:
    return {
        'mile': round(checkpoint.mile, 1),
        'lat': round(checkpoint.lat, 4),
        'lon': round(checkpoint.lon, 4),
        'eta': checkpoint.eta.isoformat(),
        'level': None if checkpoint.level is None else int(checkpoint.level),
        'driver': checkpoint.driver,
        'wind': checkpoint.wind_mph,
        'gust': checkpoint.gust_mph,
        'rain': None if checkpoint.rain_in_hr is None else round(checkpoint.rain_in_hr, 3),
        'snow': checkpoint.snow_in_hr,
        'precip_hour': checkpoint.precip_hour.isoformat() if checkpoint.precip_hour else None,
        'wind_hour': checkpoint.wind_hour.isoformat() if checkpoint.wind_hour else None,
    }


def _summary_json(summary: Any) -> dict:
    flags = [name for name, active in (('no_travel', summary.has_no_travel),
                                       ('insufficient_data', summary.insufficient_data)) if active]
    return {
        'severe_miles': round(summary.severe_miles, 1),
        'high_miles': round(summary.high_miles, 1),
        'no_travel_miles': round(summary.no_travel_miles, 1),
        'unknown_miles': round(summary.unknown_miles, 1),
        'avg_risk': summary.avg_risk,
        'tier': summary.tier,
        'flags': flags,
    }


def _after(departure: datetime, seconds: float) -> str:
    return (departure + timedelta(seconds=seconds)).isoformat()


def _route_json(index: int, route: Any, label: str, source: str, assessment: RouteAssessment,
                departure: datetime) -> dict:
    display = simplify_line(route.coords_lonlat, DISPLAY_TOLERANCE_DEGREES)
    breaks = [{'mile': round(stop.mile, 1), 'type': stop.kind,
               'start': _after(departure, stop.start_s), 'end': _after(departure, stop.end_s)}
              for stop in assessment.stops]
    return {
        'id': index,
        'label': label,
        'source': source,
        'geometry': [[round(lat, 4), round(lon, 4)] for lon, lat in display],
        'distance_mi': round(route.distance_m / METERS_PER_MILE, 1),
        'drive_seconds': round(assessment.drive_seconds),
        'drive_time': format_duration(assessment.drive_seconds),
        'trip_seconds': round(assessment.trip_seconds),
        'trip_time': format_duration(assessment.trip_seconds),
        'breaks': breaks,
        'summary': _summary_json(assessment.summary),
        'checkpoints': [_checkpoint_json(checkpoint) for checkpoint in assessment.checkpoints],
    }


def _heatmap_json(step: tuple[float, float] | None, grid: list[dict], forecasts: list[Any] | None,
                  departure: datetime, load_lb: float) -> dict | None:
    if forecasts is None:
        return None
    hours, levels = heatmap_levels(forecasts, departure, load_lb)
    return {
        'start': departure.isoformat(),
        'hours': [hour.isoformat() for hour in hours],
        'step_deg': list(step),
        'points': [[point['lat'], point['lon']] for point in grid],
        'levels': levels,
    }


def _assess_all(labelled: list, plans: list[list[dict]], forecasts: list[Any], departure: datetime,
                load_lb: float) -> list[RouteAssessment]:
    assessments = []
    position = 0
    for index, ((route, _, _), points) in enumerate(zip(labelled, plans)):
        route_forecasts = forecasts[position:position + len(points)]
        position += len(points)
        assessments.append(assess_route(index, route, points, route_forecasts, departure, load_lb))
    return assessments


def build_route_plan(origin: str, destination: str, departure: datetime, load_lb: float,
                     step_miles: int) -> dict:
    """Geocode, find routes, fetch weather once, assess and rank. Returns the API response.

    Response: origin and destination {label, lat, lon}; routes[] {id, label, source, geometry
    [[lat, lon]], distance_mi, drive_seconds, drive_time, trip_seconds, trip_time, breaks[], summary,
    checkpoints[]}; ranking (route ids, best first); recommendation {route_id or null, reason};
    heatmap {start, hours (49), step_deg [lat, lon] (grid spacing, each point is the centre of a cell this
    size), points [[lat, lon]], levels (per point, 49 of 0-4 or null)} or null;
    notes[]; timings_ms {geocode, routing, weather, compute}.
    """
    started = time.perf_counter()
    start, end = _geocode_both(origin, destination)
    geocode_ms = _elapsed_ms(started)

    started = time.perf_counter()
    labelled, notes = _find_routes(start, end)
    routing_ms = _elapsed_ms(started)

    started = time.perf_counter()
    plans = [plan_checkpoints(route, step_miles) for route, _, _ in labelled]
    step, grid = corridor_grid_with_step([route for route, _, _ in labelled], HEATMAP_BUFFER_MILES,
                                         HEATMAP_MAX_POINTS)
    compute_ms = _elapsed_ms(started)

    started = time.perf_counter()
    points = [point for plan in plans for point in plan]
    forecasts, grid_forecasts = fetch_many(points, grid, FORECAST_DAYS)
    weather_ms = _elapsed_ms(started)

    started = time.perf_counter()
    assessments = _assess_all(labelled, plans, forecasts, departure, load_lb)
    ranked = rank_routes([assessment.summary for assessment in assessments])
    best, reason = recommend(ranked)
    heatmap = _heatmap_json(step, grid, grid_forecasts, departure, load_lb)
    if heatmap is None:
        notes.append(HEATMAP_UNAVAILABLE_NOTE)
    routes = [_route_json(index, route, label, source, assessments[index], departure)
              for index, (route, label, source) in enumerate(labelled)]
    compute_ms += _elapsed_ms(started)

    return {
        'origin': start,
        'destination': end,
        'routes': routes,
        'ranking': [summary.route_index for summary in ranked],
        'recommendation': {'route_id': best.route_index if best else None, 'reason': reason},
        'heatmap': heatmap,
        'notes': notes,
        'timings_ms': {'geocode': geocode_ms, 'routing': routing_ms, 'weather': weather_ms, 'compute': compute_ms},
    }
