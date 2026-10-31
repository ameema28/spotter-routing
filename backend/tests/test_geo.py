import pytest

from routing.domain.geo import (
    checkpoint_weights,
    cumulative_miles,
    haversine_miles,
    sample_checkpoints,
)

METERS_PER_MILE = 1609.344


def checkpoint_miles(total_miles, step_miles):
    """Sample a two-point straight line of the given length, returning only the miles."""
    points = sample_checkpoints([[0, 0], [1, 0]], [0, total_miles], step_miles)
    return [point['mile'] for point in points]


def test_one_degree_of_latitude_is_about_69_miles():
    assert haversine_miles((40, -100), (41, -100)) == pytest.approx(69.09, abs=0.1)


def test_cumulative_miles_has_one_entry_per_coordinate():
    assert cumulative_miles([METERS_PER_MILE, 2 * METERS_PER_MILE]) == pytest.approx([0, 1, 3])


@pytest.mark.parametrize('total_miles, step_miles, expected', [
    (100, 25, [0, 25, 50, 75, 100]),         # divisible: destination is not repeated
    (110, 25, [0, 25, 50, 75, 100, 110]),    # remainder: destination is added
    (10, 25, [0, 10]),                       # route shorter than the step
    (0, 25, [0]),                            # origin and destination coincide
])
def test_checkpoint_miles(total_miles, step_miles, expected):
    assert checkpoint_miles(total_miles, step_miles) == expected


def test_mid_segment_checkpoint_is_interpolated_between_endpoints():
    points = sample_checkpoints([[-100, 40], [-96, 44]], [0, 100], 25)
    assert points[1] == pytest.approx({'lat': 41, 'lon': -99, 'mile': 25})


def test_geojson_lon_lat_order_becomes_explicit_lat_lon():
    first = sample_checkpoints([[-96.8, 32.78], [-87.63, 41.88]], [0, 100], 25)[0]
    assert (first['lat'], first['lon']) == (32.78, -96.8)


def test_checkpoint_on_a_vertex_uses_that_vertex():
    points = sample_checkpoints([[0, 0], [1, 0], [2, 0]], [0, 25, 50], 25)
    assert [point['lon'] for point in points] == [0, 1, 2]


def test_repeated_vertex_does_not_divide_by_zero():
    points = sample_checkpoints([[0, 0], [1, 0], [1, 0], [2, 0]], [0, 25, 25, 50], 25)
    assert [point['lon'] for point in points] == [0, 1, 2]


@pytest.mark.parametrize('miles, expected', [
    ([0, 25, 50, 75, 100], [12.5, 25, 25, 25, 12.5]),
    ([0, 25, 50, 75, 100, 110], [12.5, 25, 25, 25, 17.5, 5]),
    ([0, 10], [5, 5]),
    ([0], [0]),
])
def test_weights_are_half_the_gap_to_each_neighbour(miles, expected):
    assert checkpoint_weights(miles) == pytest.approx(expected)


def test_weights_sum_to_route_length():
    assert sum(checkpoint_weights([0, 25, 50, 75, 100, 110])) == pytest.approx(110)
