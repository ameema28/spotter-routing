"""Route geometry: distances, checkpoint sampling and the miles each checkpoint represents."""
import math
from bisect import bisect_left
from itertools import accumulate

METERS_PER_MILE = 1609.344
EARTH_RADIUS_MILES = 3958.8


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle miles between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def cumulative_miles(segment_distances_m: list[float]) -> list[float]:
    """Miles from the origin at each coordinate, from Mapbox per-segment distances.

    Summing annotations rather than haversine keeps miles, ETAs and the route total in agreement.
    """
    return list(accumulate((metres / METERS_PER_MILE for metres in segment_distances_m), initial=0.0))


def _point_at_mile(coords_lonlat: list[list[float]], cum_miles: list[float], mile: float) -> dict:
    end = bisect_left(cum_miles, mile)
    if end == 0:
        lon, lat = coords_lonlat[0]
        return {'lat': lat, 'lon': lon, 'mile': mile}
    # bisect_left guarantees cum_miles[end - 1] < mile <= cum_miles[end], so the span is never zero.
    fraction = (mile - cum_miles[end - 1]) / (cum_miles[end] - cum_miles[end - 1])
    (lon1, lat1), (lon2, lat2) = coords_lonlat[end - 1], coords_lonlat[end]
    return {'lat': lat1 + fraction * (lat2 - lat1), 'lon': lon1 + fraction * (lon2 - lon1), 'mile': mile}


def sample_checkpoints(coords_lonlat: list[list[float]], cum_miles: list[float],
                       step_miles: float) -> list[dict]:
    """Points at 0, step, 2*step, ... plus the destination, as {lat, lon, mile}."""
    total = cum_miles[-1]
    # Multiply rather than add repeatedly, so float error can't build up along a long route.
    miles = [step_miles * index for index in range(math.ceil(total / step_miles))] + [total]
    return [_point_at_mile(coords_lonlat, cum_miles, mile) for mile in miles]


def checkpoint_weights(miles: list[float]) -> list[float]:
    """Miles of road each checkpoint represents (D5): half the gap to each neighbour.

    Weights sum to the route length, and the destination keeps a share of the road.
    """
    gaps = [after - before for before, after in zip(miles, miles[1:])]
    return [(before + after) / 2 for before, after in zip([0.0] + gaps, gaps + [0.0])]
