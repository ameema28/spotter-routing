"""Choosing a generated third route (D7 in DECISIONS.md).

Routes here are anything with coords_lonlat, seg_distances_m and duration_s.
"""
import math
from dataclasses import dataclass
from typing import Any, Iterator

from routing.domain.geo import haversine_miles
from routing.domain.hubs import Hub

TARGET_ROUTE_COUNT = 3

# From real calls on 3 trips: 70% left Denver-Salt Lake City with no third route, and Mapbox's own
# second Kansas City-Denver route overlaps its first by 72%.
MAX_OVERLAP = 0.75
MAX_DURATION_RATIO = 1.25

OVERLAP_CELL_DEGREES = 0.01
OVERLAP_SAMPLE_METRES = 1000

HUB_OFFSET_SHARES = (0.10, 0.15)
HUB_MIN_MILES_FROM_ENDS = 50
SHORT_TRIP_MILES = 100
MILES_PER_DEGREE_LAT = 69.0


@dataclass(frozen=True)
class Candidate:
    label: str
    route: Any


@dataclass(frozen=True)
class CandidateReview:
    candidate: Candidate
    overlap: float
    duration_ratio: float
    accepted: bool
    reason: str


def _cell(lat: float, lon: float) -> tuple[int, int]:
    return round(lat / OVERLAP_CELL_DEGREES), round(lon / OVERLAP_CELL_DEGREES)


def _samples(route: Any) -> Iterator[tuple[float, float, float]]:
    """(lat, lon, metres represented) about every OVERLAP_SAMPLE_METRES along the route."""
    coords = route.coords_lonlat
    for index, metres in enumerate(route.seg_distances_m):
        (lon1, lat1), (lon2, lat2) = coords[index], coords[index + 1]
        pieces = math.ceil(metres / OVERLAP_SAMPLE_METRES)
        for piece in range(pieces):
            fraction = (piece + 0.5) / pieces
            yield lat1 + fraction * (lat2 - lat1), lon1 + fraction * (lon2 - lon1), metres / pieces


def _near_existing(lat: float, lon: float, cells: set[tuple[int, int]]) -> bool:
    row, column = _cell(lat, lon)
    return any((row + d_row, column + d_column) in cells
               for d_row in (-1, 0, 1) for d_column in (-1, 0, 1))


def _route_cells(routes: list[Any]) -> set[tuple[int, int]]:
    return {_cell(lat, lon) for route in routes for lon, lat in route.coords_lonlat}


def _overlap(candidate: Any, cells: set[tuple[int, int]]) -> float:
    total = shared = 0.0
    for lat, lon, metres in _samples(candidate):
        total += metres
        if _near_existing(lat, lon, cells):
            shared += metres
    # A route with no length adds nothing, so it counts as fully overlapping.
    return shared / total if total else 1.0


def overlap_fraction(candidate: Any, existing_routes: list[Any]) -> float:
    """Share of the candidate's distance within about a cell of any existing route.

    A cell lookup replaces comparing every point pair, which is too slow on 10,000-vertex routes.
    """
    return _overlap(candidate, _route_cells(existing_routes))


def _review(candidate: Candidate, cells: set[tuple[int, int]], fastest_duration_s: float) -> CandidateReview:
    overlap = _overlap(candidate.route, cells)
    ratio = candidate.route.duration_s / fastest_duration_s
    if ratio > MAX_DURATION_RATIO:
        reason = f'time {ratio:.2f}x fastest is over {MAX_DURATION_RATIO}x'
    elif overlap > MAX_OVERLAP:
        reason = f'overlap {overlap:.0%} is over {MAX_OVERLAP:.0%}'
    else:
        reason = 'accepted'
    return CandidateReview(candidate, overlap, ratio, reason == 'accepted', reason)


def accept_candidate(candidate: Candidate, existing_routes: list[Any],
                     fastest_duration_s: float) -> CandidateReview:
    """A candidate must be close to the fastest time and mostly on different road."""
    return _review(candidate, _route_cells(existing_routes), fastest_duration_s)


def select_extra_routes(candidates: list[Candidate],
                        existing_routes: list[Any]) -> tuple[list[Candidate], list[CandidateReview]]:
    """Fill up to TARGET_ROUTE_COUNT with the most distinct accepted candidates.

    Lowest overlap wins rather than fastest, because a third route only helps a weather comparison
    if it runs through different weather. Returns the picks, and the first review of each candidate.
    """
    fastest = min(route.duration_s for route in existing_routes)
    # Built once: rebuilding per candidate took about 2.5 s of CPU on a real long trip.
    cells = _route_cells(existing_routes)
    reviews = [_review(candidate, cells, fastest) for candidate in candidates]
    needed = TARGET_ROUTE_COUNT - len(existing_routes)
    chosen = []
    pool = reviews
    while len(chosen) < needed:
        best = min((item for item in pool if item.accepted), key=lambda item: item.overlap, default=None)
        if best is None:
            break
        chosen.append(best.candidate)
        if len(chosen) < needed:
            # Re-checked against the pick, so a second addition can't duplicate the first.
            cells |= _route_cells([best.candidate.route])
            pool = [_review(item.candidate, cells, fastest) for item in pool if item is not best]
    return chosen, reviews


def route_count_note(count: int) -> str | None:
    """Shown instead of inventing a poor route when too few distinct routes exist."""
    if count >= TARGET_ROUTE_COUNT:
        return None
    return f'Only {count} distinct route{"" if count == 1 else "s"} found'


def _offset_point(origin: dict, destination: dict, miles: float, side: int) -> tuple[float, float]:
    """Point a given distance to one side of the straight-line midpoint."""
    lat = (origin['lat'] + destination['lat']) / 2
    lon = (origin['lon'] + destination['lon']) / 2
    lon_scale = math.cos(math.radians(lat))
    # Work in miles so the perpendicular is a true right angle at this latitude.
    east = (destination['lon'] - origin['lon']) * lon_scale
    north = destination['lat'] - origin['lat']
    length = math.hypot(east, north)
    return (lat + side * east / length * miles / MILES_PER_DEGREE_LAT,
            lon - side * north / length * miles / (MILES_PER_DEGREE_LAT * lon_scale))


def select_hubs(origin: dict, destination: dict, hubs: tuple[Hub, ...] | list[Hub]) -> list[Hub]:
    """Hubs nearest points left and right of the trip, without repeats.

    Uses the straight line, not the main route, so via calls can run alongside the main call.
    """
    start, end = (origin['lat'], origin['lon']), (destination['lat'], destination['lon'])
    trip_miles = haversine_miles(start, end)
    if trip_miles < SHORT_TRIP_MILES:
        return []
    usable = [hub for hub in hubs
              if haversine_miles(start, (hub.lat, hub.lon)) > HUB_MIN_MILES_FROM_ENDS
              and haversine_miles(end, (hub.lat, hub.lon)) > HUB_MIN_MILES_FROM_ENDS]
    chosen = []
    for share in HUB_OFFSET_SHARES:
        for side in (1, -1):
            point = _offset_point(origin, destination, share * trip_miles, side)
            nearest = min(usable, key=lambda hub: haversine_miles(point, (hub.lat, hub.lon)), default=None)
            if nearest and nearest not in chosen:
                chosen.append(nearest)
    return chosen
