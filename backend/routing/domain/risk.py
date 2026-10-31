"""Checkpoint risk classification from the PDF's Risk Rules and Load Rules tables."""
from enum import IntEnum


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


# Rounding absorbs float noise before comparing: 0.009 + 0.091 must land on the 0.10 edge.
# 3 decimals is Open-Meteo's precision for inch values.
WIND_DECIMALS = 2
PRECIP_DECIMALS = 3

# PDF bands repeat or skip their edges (0.25 is in two bands, 34.5 mph is in none), so each band
# starts at its lower edge inclusive. A value on a shared edge gets the riskier band.
WIND_BANDS_MPH = (
    (55, RiskLevel.NO_TRAVEL),
    (45, RiskLevel.SEVERE),
    (35, RiskLevel.HIGH),
    (25, RiskLevel.MODERATE),
)
RAIN_BANDS_IN_HR = (
    (0.50, RiskLevel.SEVERE),
    (0.25, RiskLevel.HIGH),
    (0.10, RiskLevel.MODERATE),
)
SNOW_BANDS_IN_HR = (
    (2.0, RiskLevel.SEVERE),
    (1.0, RiskLevel.HIGH),
    (0.5, RiskLevel.MODERATE),
)

# PDF writes ">1.00" and ">3.0", so Severe keeps its top value.
RAIN_NO_TRAVEL_ABOVE_IN_HR = 1.00
SNOW_NO_TRAVEL_ABOVE_IN_HR = 3.0

# PDF load rules use ">": a load of exactly this weight does not trigger the rule.
NO_TRAVEL_LOAD_LIMIT_LB = 30_000
SEVERE_LOAD_LIMIT_LB = 40_000


def _band_level(value: float, bands: tuple) -> RiskLevel:
    for lower_edge, level in bands:
        if value >= lower_edge:
            return level
    return RiskLevel.LOW


def _classify_precip(in_hr: float, bands: tuple, no_travel_above: float) -> RiskLevel:
    rounded = round(in_hr, PRECIP_DECIMALS)
    if rounded > no_travel_above:
        return RiskLevel.NO_TRAVEL
    return _band_level(rounded, bands)


def classify_wind(mph: float) -> RiskLevel:
    """PDF Wind row: <25, 25-34, 35-44, 45-54, >=55 mph."""
    return _band_level(round(mph, WIND_DECIMALS), WIND_BANDS_MPH)


def classify_rain(in_hr: float) -> RiskLevel:
    """PDF Rain row: <0.10, 0.10-0.25, 0.25-0.50, 0.50-1.00, >1.00 in/hr."""
    return _classify_precip(in_hr, RAIN_BANDS_IN_HR, RAIN_NO_TRAVEL_ABOVE_IN_HR)


def classify_snow(in_hr: float) -> RiskLevel:
    """PDF Snow row: <0.5, 0.5-1.0, 1.0-2.0, 2.0-3.0, >3.0 in/hr."""
    return _classify_precip(in_hr, SNOW_BANDS_IN_HR, SNOW_NO_TRAVEL_ABOVE_IN_HR)


def apply_load_rules(level: RiskLevel, wind_mph: float, load_lb: float) -> RiskLevel:
    """Raise level per the PDF load rules; never lowers it."""
    wind_level = classify_wind(wind_mph)
    # >=55 mph is No Travel for any load; 45-54 mph + >30,000 lb is No Travel.
    if wind_level == RiskLevel.NO_TRAVEL:
        return RiskLevel.NO_TRAVEL
    if wind_level == RiskLevel.SEVERE and load_lb > NO_TRAVEL_LOAD_LIMIT_LB:
        return RiskLevel.NO_TRAVEL
    # 35-44 mph + >40,000 lb is Severe; max() keeps a worse rain or snow level.
    if wind_level == RiskLevel.HIGH and load_lb > SEVERE_LOAD_LIMIT_LB:
        return max(level, RiskLevel.SEVERE)
    return level


def _readings(wind_mph: float | None, rain_in_hr: float | None,
              snow_in_hr: float | None) -> list[tuple[RiskLevel, str]]:
    """Level and driver text for each condition that was provided."""
    readings = []
    if wind_mph is not None:
        readings.append((classify_wind(wind_mph), f'wind {wind_mph:g} mph'))
    if rain_in_hr is not None:
        readings.append((classify_rain(rain_in_hr), f'rain {rain_in_hr:g} in/hr'))
    if snow_in_hr is not None:
        readings.append((classify_snow(snow_in_hr), f'snow {snow_in_hr:g} in/hr'))
    return readings


def checkpoint_risk(wind_mph: float | None, rain_in_hr: float | None, snow_in_hr: float | None,
                    load_lb: float | None) -> tuple[RiskLevel | None, str]:
    """Worst condition, raised by load rules, with a short driver text.

    A missing input gives (None, 'unknown'), unless the provided inputs already prove No Travel.
    """
    readings = _readings(wind_mph, rain_in_hr, snow_in_hr)
    worst = max((level for level, _ in readings), default=RiskLevel.LOW)
    has_load_rule_inputs = wind_mph is not None and load_lb is not None
    level = apply_load_rules(worst, wind_mph, load_lb) if has_load_rule_inputs else worst

    if None in (wind_mph, rain_in_hr, snow_in_hr, load_lb) and level != RiskLevel.NO_TRAVEL:
        return None, 'unknown'
    if level > worst:
        return level, f'wind {wind_mph:g} mph + load {load_lb:,.0f} lb'
    if level == RiskLevel.LOW:
        return level, 'all low'
    return level, ', '.join(text for reading_level, text in readings if reading_level == worst)
