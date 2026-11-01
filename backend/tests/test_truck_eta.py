import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from routing.domain.geo import cumulative_miles
from routing.domain.truck_eta import (
    HOURS_OF_SERVICE,
    TRUCK_MAX_MPH,
    HoursOfServiceRules,
    add_rest_breaks,
    apply_speed_cap,
)
from routing.domain.weather_time import eta_at_mile, time_profile

METERS_PER_MILE = 1609.344
HOUR = 3600
BREAK = 30 * 60
REST = 10 * HOUR
DEPARTURE = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
FIXTURE = Path(__file__).parent / 'fixtures' / 'mapbox_directions_dallas_chicago.json'


def hourly_profile(hours, mph=60):
    """A constant-speed drive with one vertex per hour."""
    return [(mph * hour, hour * HOUR) for hour in range(hours + 1)]


def stops(events):
    return [(event.kind, event.mile) for event in events]


@pytest.mark.parametrize('miles, seconds, expected', [
    (65, 1800, 3600),    # 130 mph is slowed to the cap
    (65, 3599, 3600),
    (65, 3600, 3600),    # exactly at the cap
    (65, 7200, 7200),    # slower segments are untouched
    (0, 30, 30),         # a zero-length segment keeps its time
])
def test_speed_cap_only_slows_fast_segments(miles, seconds, expected):
    capped = apply_speed_cap([miles * METERS_PER_MILE], [seconds], 65)
    assert capped == pytest.approx([expected])


def test_speed_cap_keeps_one_duration_per_segment():
    distances = [65 * METERS_PER_MILE, 65 * METERS_PER_MILE]
    assert apply_speed_cap(distances, [1800, 7200], 65) == pytest.approx([3600, 7200])


def test_speed_cap_leaves_total_distance_unchanged():
    distances = [65 * METERS_PER_MILE, 10 * METERS_PER_MILE]
    original = time_profile(distances, [1800, 7200])
    capped = time_profile(distances, apply_speed_cap(distances, [1800, 7200], 65))
    assert capped[-1][0] == original[-1][0]


def test_truck_speed_is_the_documented_assumption():
    assert TRUCK_MAX_MPH == 65


def test_rules_match_the_regulation():
    assert HOURS_OF_SERVICE.driving_before_break_s == 8 * HOUR
    assert HOURS_OF_SERVICE.break_s == 30 * 60
    assert HOURS_OF_SERVICE.driving_before_rest_s == 11 * HOUR
    assert HOURS_OF_SERVICE.rest_s == 10 * HOUR


def test_no_breaks_on_a_short_trip():
    profile = hourly_profile(5)
    assert add_rest_breaks(profile, HOURS_OF_SERVICE) == (profile, [])


def test_no_break_when_the_trip_ends_exactly_at_the_limit():
    profile = hourly_profile(8)
    assert add_rest_breaks(profile, HOURS_OF_SERVICE) == (profile, [])


def test_break_falls_at_8_driving_hours():
    _, events = add_rest_breaks(hourly_profile(9), HOURS_OF_SERVICE)
    assert stops(events) == [('break', 480)]
    assert (events[0].start_s, events[0].end_s) == (8 * HOUR, 8 * HOUR + BREAK)


def test_break_falls_inside_a_long_segment():
    new_profile, events = add_rest_breaks([(0, 0), (600, 10 * HOUR)], HOURS_OF_SERVICE)
    assert stops(events) == [('break', 480)]
    assert new_profile == [(0, 0), (480, 8 * HOUR), (480, 8 * HOUR + BREAK), (600, 10 * HOUR + BREAK)]


def test_rest_falls_at_11_driving_hours_and_break_time_is_not_driving():
    _, events = add_rest_breaks(hourly_profile(12), HOURS_OF_SERVICE)
    assert stops(events) == [('break', 480), ('rest', 660)]
    assert (events[1].start_s, events[1].end_s) == (11 * HOUR + BREAK, 11 * HOUR + BREAK + REST)


def test_rest_resets_both_clocks():
    _, events = add_rest_breaks(hourly_profile(25), HOURS_OF_SERVICE)
    assert stops(events) == [('break', 480), ('rest', 660), ('break', 1140), ('rest', 1320)]


def test_arrival_includes_all_stops():
    new_profile, _ = add_rest_breaks(hourly_profile(12), HOURS_OF_SERVICE)
    assert new_profile[-1] == (720, 12 * HOUR + BREAK + REST)


@pytest.mark.parametrize('mile, shift', [
    (300, 0),               # before any stop
    (480, 0),               # arriving at the stop is before it starts
    (540, BREAK),           # after the break
    (660, BREAK),           # arriving at the rest stop
    (700, BREAK + REST),    # after the rest
])
def test_etas_shift_only_after_each_stop(mile, shift):
    profile = hourly_profile(12)
    new_profile, _ = add_rest_breaks(profile, HOURS_OF_SERVICE)
    before = eta_at_mile(profile, mile, DEPARTURE)
    assert eta_at_mile(new_profile, mile, DEPARTURE) == before + timedelta(seconds=shift)


def test_profile_never_runs_backwards():
    new_profile, _ = add_rest_breaks(hourly_profile(30), HOURS_OF_SERVICE)
    miles, seconds = zip(*new_profile)
    assert list(miles) == sorted(miles)
    assert list(seconds) == sorted(seconds)


def test_driving_day_stays_inside_the_14_hour_window():
    _, events = add_rest_breaks(hourly_profile(40), HOURS_OF_SERVICE)
    day_start = 0
    for event in events:
        if event.kind == 'rest':
            assert event.start_s - day_start <= 14 * HOUR
            day_start = event.end_s


def test_input_profile_is_not_changed():
    profile = hourly_profile(12)
    add_rest_breaks(profile, HOURS_OF_SERVICE)
    assert profile == hourly_profile(12)


def test_zero_length_segment_at_a_stop_is_handled():
    profile = [(0, 0), (480, 8 * HOUR), (480, 8 * HOUR), (540, 9 * HOUR)]
    new_profile, events = add_rest_breaks(profile, HOURS_OF_SERVICE)
    assert stops(events) == [('break', 480)]
    assert new_profile[-1] == (540, 9 * HOUR + BREAK)


def test_rules_are_a_parameter():
    rules = HoursOfServiceRules(driving_before_break_s=HOUR, break_s=60,
                                driving_before_rest_s=3 * HOUR, rest_s=600)
    _, events = add_rest_breaks(hourly_profile(4), rules)
    assert stops(events) == [('break', 60), ('break', 120), ('rest', 180)]


def test_dallas_chicago_fixture_matches_the_measured_truck_trip():
    route = json.loads(FIXTURE.read_text(encoding='utf-8'))['routes'][0]
    annotation = route['legs'][0]['annotation']
    capped = apply_speed_cap(annotation['distance'], annotation['duration'], TRUCK_MAX_MPH)
    new_profile, events = add_rest_breaks(time_profile(annotation['distance'], capped), HOURS_OF_SERVICE)

    assert new_profile[-1][1] / HOUR == pytest.approx(26.05, abs=0.01)
    assert new_profile[-1][0] == pytest.approx(cumulative_miles(annotation['distance'])[-1])
    assert [event.kind for event in events] == ['break', 'rest']
    assert events[0].mile == pytest.approx(502, abs=2)
    assert events[1].mile == pytest.approx(692, abs=2)
