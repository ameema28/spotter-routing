"""Route shapes for display, and the heatmap grid around them (D9 in DECISIONS.md)."""
import math

from routing.domain.geo import haversine_miles

# About 200 m. Real long-haul routes of 10,000+ vertices keep 300-400 points.
DISPLAY_TOLERANCE_DEGREES = 0.002

MILES_PER_DEGREE_LAT = 69.0
ROUTE_SAMPLE_DEGREES = 0.07     # About 5 miles.
ROUTE_SAMPLE_MILES = 5.0

# (lat, lon) degrees, roughly square near 39N, from about 15 to 100 miles apart. These are fixed and
# anchored at 0,0 rather than fitted to each trip, so overlapping trips land on the same cached cells.
# All are multiples of the D6 cache cell (0.02), so snapping leaves grid points where they are.
GRID_STEPS = (
    (0.22, 0.28), (0.28, 0.36), (0.36, 0.46), (0.44, 0.56), (0.50, 0.64),
    (0.58, 0.74), (0.72, 0.92), (0.86, 1.10), (1.16, 1.48), (1.44, 1.84),
)


def _distance_to_line(point: list[float], start: list[float], end: list[float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    # A closed loop has no line to measure from, so fall back to distance from its one point.
    if length == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    return abs(dx * (point[1] - start[1]) - dy * (point[0] - start[0])) / length


def simplify_line(coords: list[list[float]], tolerance: float) -> list[list[float]]:
    """Ramer-Douglas-Peucker: drop points within tolerance of the line between kept points."""
    if len(coords) < 3:
        return list(coords)
    keep = {0, len(coords) - 1}
    # A stack rather than recursion: a 10,000-point route can exceed Python's recursion limit.
    stack = [(0, len(coords) - 1)]
    while stack:
        first, last = stack.pop()
        distances = [(_distance_to_line(coords[index], coords[first], coords[last]), index)
                     for index in range(first + 1, last)]
        if distances:
            farthest, index = max(distances)
            if farthest > tolerance:
                keep.add(index)
                stack += [(first, index), (index, last)]
    return [coords[index] for index in sorted(keep)]


def _route_samples(routes: list) -> list[tuple[float, float]]:
    """(lat, lon) about every 5 miles along the routes: every vertex would be needlessly slow."""
    samples = []
    for route in routes:
        previous = None
        for lon, lat in route.coords_lonlat:
            if previous is None or math.hypot(lat - previous[0], lon - previous[1]) >= ROUTE_SAMPLE_DEGREES:
                previous = (lat, lon)
                samples.append(previous)
    return samples


def _keep_distance(step: tuple[float, float], buffer_mi: float, lowest_lat: float) -> float:
    """Miles from the route a grid point may be, wide enough that no route point is left uncovered."""
    east_west = step[1] * math.cos(math.radians(lowest_lat))
    half_diagonal = math.hypot(step[0], east_west) / 2 * MILES_PER_DEGREE_LAT
    return max(buffer_mi, half_diagonal + ROUTE_SAMPLE_MILES)


def _grid_at_step(samples: list[tuple[float, float]], step: tuple[float, float],
                  keep_miles: float) -> dict[tuple[int, int], dict]:
    grid = {}
    lat_reach = math.ceil(keep_miles / (step[0] * MILES_PER_DEGREE_LAT))
    for lat, lon in samples:
        lon_degrees = keep_miles / (MILES_PER_DEGREE_LAT * math.cos(math.radians(lat)))
        lon_reach = math.ceil(lon_degrees / step[1])
        row, column = round(lat / step[0]), round(lon / step[1])
        for near_row in range(row - lat_reach, row + lat_reach + 1):
            for near_column in range(column - lon_reach, column + lon_reach + 1):
                if (near_row, near_column) in grid:
                    continue
                point = (near_row * step[0], near_column * step[1])
                if haversine_miles((lat, lon), point) <= keep_miles:
                    grid[(near_row, near_column)] = {'lat': round(point[0], 2), 'lon': round(point[1], 2)}
    return grid


def corridor_grid_with_step(routes: list, buffer_mi: float, max_points: int
                            ) -> tuple[tuple[float, float] | None, list[dict]]:
    """The finest fixed grid around the routes that stays within max_points: its (lat, lon) step and
    its points as {lat, lon}. The step is sent so the map can draw each point as a cell of that size."""
    samples = _route_samples(routes)
    if not samples:
        return None, []
    lowest_lat = min(lat for lat, _ in samples)
    grid = {}
    for step in GRID_STEPS:
        grid = _grid_at_step(samples, step, _keep_distance(step, buffer_mi, lowest_lat))
        if len(grid) <= max_points:
            break
    return step, [grid[key] for key in sorted(grid)][:max_points]


def corridor_grid(routes: list, buffer_mi: float, max_points: int) -> list[dict]:
    """The grid points of corridor_grid_with_step, without the step."""
    return corridor_grid_with_step(routes, buffer_mi, max_points)[1]
