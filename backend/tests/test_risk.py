import pytest

from routing.domain.risk import (
    RiskLevel,
    apply_load_rules,
    checkpoint_risk,
    classify_rain,
    classify_snow,
    classify_wind,
)

L = RiskLevel.LOW
M = RiskLevel.MODERATE
H = RiskLevel.HIGH
S = RiskLevel.SEVERE
NT = RiskLevel.NO_TRAVEL


@pytest.mark.parametrize('mph, expected', [
    (0, L),
    (24.99, L),
    (25, M),
    (34.5, M),  # falls in the PDF's gap between 25-34 and 35-44
    (34.99, M),
    (35, H),
    (44.99, H),
    (45, S),
    (54.99, S),
    (55, NT),
    (80, NT),
])
def test_wind_bands(mph, expected):
    assert classify_wind(mph) == expected


@pytest.mark.parametrize('in_hr, expected', [
    (0, L),
    (0.099, L),
    (0.10, M),
    (0.249, M),
    (0.25, H),
    (0.50, S),
    (1.00, S),
    (1.001, NT),
])
def test_rain_bands(in_hr, expected):
    assert classify_rain(in_hr) == expected


@pytest.mark.parametrize('in_hr, expected', [
    (0, L),
    (0.49, L),
    (0.5, M),
    (1.0, H),
    (1.99, H),
    (2.0, S),
    (3.0, S),
    (3.01, NT),
])
def test_snow_bands(in_hr, expected):
    assert classify_snow(in_hr) == expected


@pytest.mark.parametrize('classify, value, expected', [
    (classify_rain, 0.009 + 0.091, M),  # float sum is 0.09999999999999999
    (classify_rain, 0.0999, M),
    (classify_rain, 0.2499, H),
    (classify_rain, 1.0001, S),
    (classify_snow, 0.4999999, M),
    (classify_snow, 3.0001, S),
    (classify_wind, 34.999999, H),
    (classify_wind, 54.999, NT),
])
def test_inputs_are_rounded_before_comparing(classify, value, expected):
    assert classify(value) == expected


@pytest.mark.parametrize('wind_mph, load_lb, expected', [
    (55, 0, NT),
    (50, 30_000, S),
    (50, 30_001, NT),
    (40, 40_000, H),
    (40, 40_001, S),
    (30, 80_000, M),
    (44.99, 45_000, S),
    (45, 45_000, NT),
    (44.999, 45_000, NT),  # rounds to 45.00, same rounding as classify_wind
    (35, 40_001, S),       # lower wind edge of each load rule, not only the upper one
    (45, 30_001, NT),
])
def test_load_rules(wind_mph, load_lb, expected):
    assert apply_load_rules(classify_wind(wind_mph), wind_mph, load_lb) == expected


def test_load_rule_never_lowers_a_level():
    level, _ = checkpoint_risk(40, 0, 3.5, 45_000)

    assert level == NT


def test_worst_condition_sets_level_and_driver():
    level, driver = checkpoint_risk(10, 0.30, 0.6, 20_000)

    assert level == H
    assert 'rain' in driver


def test_all_low():
    assert checkpoint_risk(10, 0, 0, 20_000) == (L, 'all low')


@pytest.mark.parametrize('wind_mph, rain, snow, load_lb, expected', [
    (47, 0, 0, 35_000, (NT, 'wind 47 mph + load 35,000 lb')),
    (40, 0, 0, 45_000, (S, 'wind 40 mph + load 45,000 lb')),
    (10, 0, 2.4, 20_000, (S, 'snow 2.4 in/hr')),
    (40, 0.30, 0, 20_000, (H, 'wind 40 mph, rain 0.3 in/hr')),
])
def test_driver_text(wind_mph, rain, snow, load_lb, expected):
    assert checkpoint_risk(wind_mph, rain, snow, load_lb) == expected


@pytest.mark.parametrize('wind_mph, rain, snow, load_lb', [
    (None, 0, 0, 20_000),
    (10, None, 0, 20_000),
    (10, 0, None, 20_000),
    (10, 0, 0, None),
    (None, 0, 0.2, 20_000),
    (50, 0, 0, None),  # 50 mph is No Travel only with a known load over 30,000 lb
    (None, None, None, None),
])
def test_missing_input_is_unknown(wind_mph, rain, snow, load_lb):
    assert checkpoint_risk(wind_mph, rain, snow, load_lb) == (None, 'unknown')


@pytest.mark.parametrize('wind_mph, rain, snow, load_lb, expected', [
    (None, 0, 3.5, 20_000, (NT, 'snow 3.5 in/hr')),
    (10, None, 3.5, 20_000, (NT, 'snow 3.5 in/hr')),
    (None, 1.5, 0, 20_000, (NT, 'rain 1.5 in/hr')),
    (60, None, None, None, (NT, 'wind 60 mph')),
    (50, None, 0, 35_000, (NT, 'wind 50 mph + load 35,000 lb')),
])
def test_missing_input_never_hides_known_no_travel(wind_mph, rain, snow, load_lb, expected):
    assert checkpoint_risk(wind_mph, rain, snow, load_lb) == expected
