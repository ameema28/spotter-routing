import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from routing.domain.geo import haversine_miles
from routing.domain.geometry import (
    DISPLAY_TOLERANCE_DEGREES,
    GRID_STEPS,
    _keep_distance,
    corridor_grid,
    simplify_line,
)

FIXTURE = Path(__file__).parent / 'fixtures' / 'mapbox_directions_dallas_chicago.json'


def fixture_routes():
    routes = json.loads(FIXTURE.read_text(encoding='utf-8'))['routes']
    return [SimpleNamespace(coords_lonlat=route['geometry']['coordinates']) for route in routes]


def east_west_route(miles, lat=40.0):
    degrees = miles / (69.09 * math.cos(math.radians(lat)))
    count = max(2, round(miles / 2))
    return SimpleNamespace(coords_lonlat=[
        [-100 + degrees * index / (count - 1), lat] for index in range(count)
    ])


def nearest_miles(lon, lat, grid):
    return min(haversine_miles((lat, lon), (point['lat'], point['lon'])) for point in grid)


def test_simplify_keeps_both_endpoints():
    line = [[0, 0], [1, 0.5], [2, 0], [3, 2]]
    result = simplify_line(line, 0.1)
    assert result[0] == line[0]
    assert result[-1] == line[-1]


def test_simplify_collapses_a_straight_line_to_two_points():
    line = [[index, index * 2] for index in range(100)]
    assert simplify_line(line, 0.001) == [line[0], line[-1]]


def test_simplify_keeps_a_corner():
    line = [[0, 0], [1, 0], [2, 0], [2, 1], [2, 2]]
    assert simplify_line(line, 0.01) == [[0, 0], [2, 0], [2, 2]]


def test_simplify_drops_wiggles_inside_the_tolerance():
    line = [[index, 0.001 * (index % 2)] for index in range(10)]
    assert len(simplify_line(line, 0.01)) == 2


def test_simplify_keeps_a_loop_back_to_the_start():
    line = [[0, 0], [1, 0], [1, 1], [0, 0]]
    assert len(simplify_line(line, 0.01)) > 2


def test_simplify_handles_short_lines():
    assert simplify_line([[0, 0]], 0.1) == [[0, 0]]
    assert simplify_line([[0, 0], [1, 1]], 0.1) == [[0, 0], [1, 1]]


def test_simplify_does_not_change_its_input():
    line = [[0, 0], [1, 0.5], [2, 0]]
    simplify_line(line, 1)
    assert line == [[0, 0], [1, 0.5], [2, 0]]


def point_to_segment_degrees(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = dx * dx + dy * dy
    t = 0 if length == 0 else max(0, min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length))
    return math.hypot(point[0] - start[0] - t * dx, point[1] - start[1] - t * dy)


@pytest.mark.parametrize('index', [0, 1])
def test_real_route_stays_under_the_display_target_and_keeps_its_shape(index):
    coords = fixture_routes()[index].coords_lonlat
    simplified = simplify_line(coords, DISPLAY_TOLERANCE_DEGREES)
    assert len(simplified) <= 800
    worst = 0
    positions = {tuple(point): position for position, point in reversed(list(enumerate(coords)))}
    kept = sorted(positions[tuple(point)] for point in simplified)
    for start, end in zip(kept, kept[1:]):
        for position in range(start + 1, end, 25):
            worst = max(worst, point_to_segment_degrees(coords[position], coords[start], coords[end]))
    assert worst <= DISPLAY_TOLERANCE_DEGREES * 1.01


def test_grid_covers_every_point_of_real_routes():
    routes = fixture_routes()
    grid = corridor_grid(routes, 25, 250)
    for route in routes:
        for lon, lat in route.coords_lonlat[::200]:
            assert nearest_miles(lon, lat, grid) <= 25


def test_grid_respects_the_point_cap():
    assert len(corridor_grid(fixture_routes(), 25, 250)) <= 250


def test_grid_uses_the_finest_step_under_the_cap():
    routes = fixture_routes()
    count = len(corridor_grid(routes, 25, 250))
    assert count > 100    # not a needlessly coarse step


def lat_spacing(grid):
    lats = sorted({point['lat'] for point in grid})
    return round(min(after - before for before, after in zip(lats, lats[1:])), 2)


def test_spacing_grows_with_trip_length():
    short = corridor_grid([east_west_route(200)], 25, 250)
    long = corridor_grid([east_west_route(2500)], 25, 250)
    assert lat_spacing(long) > lat_spacing(short)


@pytest.mark.parametrize('lat', [38.0, 39.6, 40.2, 41.0])
def test_very_long_trip_stays_under_the_cap_and_covered(lat):
    # Some of these latitudes fall between grid rows, further than the 25 mile buffer from any row.
    route = east_west_route(2800, lat=lat)
    grid = corridor_grid([route], 25, 60)
    coarsest = GRID_STEPS[-1]
    half_diagonal = math.hypot(coarsest[0], coarsest[1]) / 2 * 69
    assert len(grid) <= 60
    for lon, point_lat in route.coords_lonlat[::20]:
        assert nearest_miles(lon, point_lat, grid) <= half_diagonal


def test_keep_distance_is_the_buffer_until_a_coarse_step_needs_more():
    assert _keep_distance(GRID_STEPS[0], 25, 30) == 25
    # At the coarsest step a route can run 70+ miles from every grid point.
    assert _keep_distance(GRID_STEPS[-1], 25, 30) > 70


def test_grid_points_sit_on_multiples_of_their_step():
    # A global anchor is what lets overlapping trips share cached cells.
    grid = corridor_grid([east_west_route(300)], 25, 250)
    assert any(all(
        abs(point['lat'] / lat_step - round(point['lat'] / lat_step)) < 1e-6
        and abs(point['lon'] / lon_step - round(point['lon'] / lon_step)) < 1e-6
        for point in grid) for lat_step, lon_step in GRID_STEPS)


def test_overlapping_trips_share_grid_points():
    first = corridor_grid([east_west_route(300)], 25, 250)
    second = corridor_grid([SimpleNamespace(coords_lonlat=[
        [lon + 1.0, lat] for lon, lat in east_west_route(300).coords_lonlat])], 25, 250)
    as_set = {(point['lat'], point['lon']) for point in first}
    assert as_set & {(point['lat'], point['lon']) for point in second}


def test_grid_points_snap_to_themselves_on_the_cache_grid():
    grid = corridor_grid([east_west_route(300)], 25, 250)
    for point in grid:
        assert round(point['lat'] / 0.02) * 0.02 == pytest.approx(point['lat'])
        assert round(point['lon'] / 0.02) * 0.02 == pytest.approx(point['lon'])
        # Exact, not approximate: float noise here would be sent to the browser on every point.
        assert point['lat'] == round(point['lat'], 2)
        assert point['lon'] == round(point['lon'], 2)


def test_grid_has_no_duplicates():
    grid = corridor_grid(fixture_routes(), 25, 250)
    assert len({(point['lat'], point['lon']) for point in grid}) == len(grid)


def test_no_routes_gives_an_empty_grid():
    assert corridor_grid([], 25, 250) == []
