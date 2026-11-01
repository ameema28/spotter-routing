"""Truck ETAs along a route, and which Open-Meteo hourly row applies at each ETA."""
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from itertools import accumulate

from routing.domain.geo import cumulative_miles


def time_profile(segment_distances_m: list[float],
                 segment_durations_s: list[float]) -> list[tuple[float, float]]:
    """(cumulative miles, cumulative seconds) at each coordinate."""
    return list(zip(cumulative_miles(segment_distances_m),
                    accumulate(segment_durations_s, initial=0.0)))


def eta_at_mile(profile: list[tuple[float, float]], mile: float,
                departure_utc: datetime) -> datetime:
    """Departure plus time to reach the mile, linear within a segment; clamped past the end."""
    miles = [point_mile for point_mile, _ in profile]
    end = bisect_left(miles, mile)
    if end == 0:
        seconds = profile[0][1]
    elif end == len(profile):
        seconds = profile[-1][1]
    else:
        # bisect_left guarantees miles[end - 1] < mile <= miles[end], so the span is never zero.
        (mile1, seconds1), (mile2, seconds2) = profile[end - 1], profile[end]
        seconds = seconds1 + (mile - mile1) / (mile2 - mile1) * (seconds2 - seconds1)
    return departure_utc + timedelta(seconds=seconds)


def _locate(eta: datetime, times: list[datetime]) -> tuple[datetime, int | None]:
    """The ETA in UTC, and the first row at or after it (None if out of range)."""
    if eta.tzinfo is None:
        raise ValueError('eta must be timezone-aware')
    eta_utc = eta.astimezone(timezone.utc)
    if not times or eta_utc < times[0] or eta_utc > times[-1]:
        return eta_utc, None
    return eta_utc, bisect_left(times, eta_utc)


def precip_hour(eta: datetime, hourly_times: list[datetime]) -> int | None:
    """Row for rain, showers and snowfall, which are sums over the hour ENDING at the timestamp."""
    return _locate(eta, hourly_times)[1]


def wind_hour(eta: datetime, hourly_times: list[datetime]) -> int | None:
    """Row for wind, which is instantaneous: the nearest hour, with a tie rounding up."""
    eta_utc, after = _locate(eta, hourly_times)
    if after is None or after == 0:
        return after
    before = after - 1
    return before if eta_utc - hourly_times[before] < hourly_times[after] - eta_utc else after
