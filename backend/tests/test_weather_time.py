from datetime import datetime, timedelta, timezone

import pytest

from routing.domain.weather_time import eta_at_mile, precip_hour, time_profile, wind_hour

METERS_PER_MILE = 1609.344
DEPARTURE = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
HOURLY_TIMES = ['2026-11-01T13:00', '2026-11-01T14:00', '2026-11-01T15:00', '2026-11-01T16:00']


def at(hour, minute=0):
    return datetime(2026, 11, 1, hour, minute, tzinfo=timezone.utc)


@pytest.fixture
def two_segment_profile():
    # 10 mi in 600 s, then 10 mi in 1800 s: two speeds, so a single average would fail these tests.
    return time_profile([10 * METERS_PER_MILE, 10 * METERS_PER_MILE], [600, 1800])


def test_time_profile_starts_at_zero_and_accumulates(two_segment_profile):
    miles, seconds = zip(*two_segment_profile)
    assert miles == pytest.approx((0, 10, 20))
    assert seconds == (0, 600, 2400)


@pytest.mark.parametrize('mile, expected_seconds', [
    (0, 0),        # origin is the departure time
    (5, 300),      # midpoint of a constant-speed segment
    (10, 600),     # on a vertex
    (15, 1500),    # second segment uses its own, slower speed
    (20, 2400),    # destination is departure + total duration
    (25, 2400),    # beyond the end is clamped
])
def test_eta_at_mile(two_segment_profile, mile, expected_seconds):
    eta = eta_at_mile(two_segment_profile, mile, DEPARTURE)
    assert eta == DEPARTURE + timedelta(seconds=expected_seconds)


def test_eta_never_decreases_along_the_route(two_segment_profile):
    etas = [eta_at_mile(two_segment_profile, mile, DEPARTURE) for mile in range(21)]
    assert etas == sorted(etas)


def test_eta_handles_a_zero_length_segment():
    profile = time_profile([10 * METERS_PER_MILE, 0, 10 * METERS_PER_MILE], [600, 60, 600])
    assert eta_at_mile(profile, 15, DEPARTURE) == DEPARTURE + timedelta(seconds=960)


@pytest.mark.parametrize('eta, expected', [
    (at(14, 20), 2),   # 14:20 falls in the hour ending 15:00
    (at(14), 1),       # exactly on the hour: the row ending then
    (at(16), 3),       # last row
    (at(12, 59), None),
    (at(16, 1), None),
])
def test_precip_hour_uses_the_hour_ending_at_or_after_the_eta(eta, expected):
    assert precip_hour(eta, HOURLY_TIMES) == expected


@pytest.mark.parametrize('eta, expected', [
    (at(14, 29), 1),   # nearest hour is 14:00
    (at(14, 30), 2),   # a tie rounds up
    (at(14), 1),
    (at(16), 3),
    (at(12, 59), None),
    (at(16, 1), None),
])
def test_wind_hour_uses_the_nearest_hour(eta, expected):
    assert wind_hour(eta, HOURLY_TIMES) == expected


@pytest.mark.parametrize('lookup', [precip_hour, wind_hour])
def test_lookups_compare_instants_not_clock_faces(lookup):
    eta_in_chicago = datetime(2026, 11, 1, 9, 0, tzinfo=timezone(timedelta(hours=-5)))
    assert lookup(eta_in_chicago, HOURLY_TIMES) == 1   # 09:00 at UTC-5 is 14:00 UTC


@pytest.mark.parametrize('lookup', [precip_hour, wind_hour])
def test_lookups_find_rows_by_timestamp_not_position(lookup):
    # Open-Meteo starts at 00:00 GMT today, so row 0 is usually in the past.
    assert lookup(at(14), ['2026-11-01T00:00', '2026-11-01T14:00']) == 1


@pytest.mark.parametrize('lookup', [precip_hour, wind_hour])
def test_lookups_reject_a_naive_eta(lookup):
    with pytest.raises(ValueError):
        lookup(datetime(2026, 11, 1, 14, 0), HOURLY_TIMES)
