from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from routing.domain.formatting import format_duration
from routing.domain.geo import METERS_PER_MILE
from routing.domain.risk import RiskLevel
from routing.domain.route_assessment import HEATMAP_HOURS, assess_route, heatmap_levels, plan_checkpoints
from routing.services.openmeteo import HourlyForecast

DEPARTURE = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
HOUR = 3600
BASE = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)


def forecast(hours=96, wind=5.0, gust=9.0, rain=0.0, snow=0.0, start=BASE):
    return HourlyForecast(
        times=[start + timedelta(hours=index) for index in range(hours)],
        wind_mph=[wind] * hours, gust_mph=[gust] * hours, rain_in_hr=[rain] * hours, snow_in_hr=[snow] * hours,
    )


def route(miles=100, hours=5.0, segments=20):
    return SimpleNamespace(
        coords_lonlat=[[-100 + index * 0.05, 40.0] for index in range(segments + 1)],
        seg_distances_m=[miles * METERS_PER_MILE / segments] * segments,
        seg_durations_s=[hours * HOUR / segments] * segments,
    )


def assess(trip=None, step=25, weather=None, load=20_000, departure=DEPARTURE):
    trip = trip or route()
    points = plan_checkpoints(trip, step)
    forecasts = [weather or forecast()] * len(points)
    return assess_route(0, trip, points, forecasts, departure, load)


def test_checkpoints_follow_the_step():
    assert [point['mile'] for point in plan_checkpoints(route(), 25)] == pytest.approx([0, 25, 50, 75, 100])


def test_checkpoint_carries_position_eta_and_conditions():
    result = assess(weather=forecast(wind=12, gust=20, rain=0.05, snow=0.1))
    first = result.checkpoints[0]
    assert first.mile == 0
    assert first.lat == 40
    assert first.lon == -100
    assert first.eta == DEPARTURE
    assert (first.wind_mph, first.gust_mph, first.rain_in_hr, first.snow_in_hr) == (12, 20, 0.05, 0.1)
    assert first.level == RiskLevel.LOW


def test_load_reaches_the_risk_rules():
    light = assess(weather=forecast(wind=50), load=30_000).checkpoints[0]
    heavy = assess(weather=forecast(wind=50), load=30_001).checkpoints[0]
    assert light.level == RiskLevel.SEVERE
    assert heavy.level == RiskLevel.NO_TRAVEL
    assert heavy.driver == 'wind 50 mph + load 30,001 lb'


def test_precip_and_wind_use_their_own_forecast_rows():
    weather = forecast()
    weather.rain_in_hr[11] = 0.3    # 11:00 row: the hour ending after a 10:20 ETA
    weather.wind_mph[10] = 30.0     # 10:00 row: nearest to 10:20
    trip = route(miles=60, hours=1.0, segments=6)
    checkpoint = assess(trip, step=20, weather=weather).checkpoints[1]
    assert checkpoint.eta == DEPARTURE + timedelta(minutes=20)
    assert checkpoint.rain_in_hr == 0.3
    assert checkpoint.wind_mph == 30.0
    assert checkpoint.precip_hour == BASE + timedelta(hours=11)
    assert checkpoint.wind_hour == BASE + timedelta(hours=10)


def test_truck_speed_cap_changes_etas():
    fast = route(miles=130, hours=1.0)
    result = assess(fast)
    assert result.drive_seconds == pytest.approx(2 * HOUR)
    assert result.checkpoints[-1].eta == DEPARTURE + timedelta(hours=2)


def test_rest_stops_shift_later_etas_and_count_as_travel_time():
    long_trip = route(miles=720, hours=12.0, segments=72)
    result = assess(long_trip)
    assert [stop.kind for stop in result.stops] == ['break', 'rest']
    assert result.drive_seconds == pytest.approx(12 * HOUR)
    assert result.trip_seconds == pytest.approx(22.5 * HOUR)
    assert result.summary.duration_s == result.trip_seconds
    assert result.checkpoints[-1].eta == DEPARTURE + timedelta(hours=22.5)


def test_summary_uses_half_gap_weights():
    result = assess(weather=forecast(wind=47), load=20_000)
    assert result.summary.severe_miles == pytest.approx(100)


def test_summary_carries_the_route_index():
    trip = route()
    points = plan_checkpoints(trip, 25)
    result = assess_route(7, trip, points, [forecast()] * len(points), DEPARTURE, 20_000)
    assert result.summary.route_index == 7


def test_eta_past_the_forecast_is_unknown_not_low():
    result = assess(weather=forecast(hours=11))
    last = result.checkpoints[-1]
    assert last.level is None
    assert last.driver == 'unknown'
    assert result.summary.unknown_miles > 0


def test_a_null_value_is_unknown():
    weather = forecast()
    weather.rain_in_hr[10] = None
    assert assess(weather=weather).checkpoints[0].level is None


def test_each_checkpoint_uses_its_own_forecast():
    trip = route()
    points = plan_checkpoints(trip, 25)
    forecasts = [forecast(), forecast(), forecast(wind=47), forecast(), forecast()]
    result = assess_route(0, trip, points, forecasts, DEPARTURE, 20_000)
    assert [item.level for item in result.checkpoints] == [0, 0, RiskLevel.SEVERE, 0, 0]


def test_heatmap_has_49_hours_starting_at_departure():
    hours, levels = heatmap_levels([forecast(), forecast()], DEPARTURE, 20_000)
    assert hours[0] == DEPARTURE
    assert hours[-1] == DEPARTURE + timedelta(hours=48)
    assert len(hours) == HEATMAP_HOURS + 1 == 49
    assert len(levels) == 2
    assert all(len(row) == 49 for row in levels)


def test_heatmap_cells_use_the_load_rules():
    _, light = heatmap_levels([forecast(wind=50)], DEPARTURE, 30_000)
    _, heavy = heatmap_levels([forecast(wind=50)], DEPARTURE, 30_001)
    assert light[0][0] == 3
    assert heavy[0][0] == 4


def test_heatmap_hour_rows_match_the_checkpoint_rules():
    weather = forecast()
    departure = DEPARTURE + timedelta(minutes=20)
    weather.rain_in_hr[11] = 0.3    # hour 0 at 10:20 uses the 11:00 precip row
    weather.wind_mph[10] = 30.0     # and the 10:00 wind row, level Moderate
    _, levels = heatmap_levels([weather], departure, 20_000)
    assert levels[0][0] == RiskLevel.HIGH
    assert levels[0][1] == RiskLevel.LOW


def test_heatmap_cells_are_plain_numbers_or_none():
    _, levels = heatmap_levels([forecast(hours=20)], DEPARTURE, 20_000)
    assert type(levels[0][0]) is int
    assert levels[0][-1] is None


def test_heatmap_handles_forecasts_with_different_start_days():
    # Cached cells can straddle midnight GMT, so rows must not be assumed to line up.
    later = forecast(start=BASE + timedelta(days=1))
    later.wind_mph[0] = 30.0
    _, levels = heatmap_levels([forecast(), later], BASE + timedelta(days=1), 20_000)
    assert levels[0][0] == 0
    assert levels[1][0] == 1


def test_no_forecasts_gives_no_rows():
    hours, levels = heatmap_levels([], DEPARTURE, 20_000)
    assert len(hours) == 49
    assert levels == []


@pytest.mark.parametrize('seconds, expected', [
    (0, '0 min'),
    (45 * 60, '45 min'),
    (3600, '1 h 0 min'),
    (14 * 3600 + 48 * 60, '14 h 48 min'),
    (14 * 3600 + 48 * 60 + 29, '14 h 48 min'),
    (14 * 3600 + 48 * 60 + 31, '14 h 49 min'),
    (3599.9, '1 h 0 min'),      # rounding carries into the hour
])
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected
